import json
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.db import get_db
from models.chat import StreamRequest, serialize_message
from services.nvidia import stream_completion
from services.knowledge_base import get_identity_prompt
from services.rag import retrieve, format_rag_context
from services.scraper import scrape, format_url_context
from services.nvidia import get_completion
from services.context_manager import build_context_messages
from services.cache import cache_get, cache_set, INTENT_TTL, SCRAPE_TTL
from config import get_settings
from services.auth import get_current_user
import re

router = APIRouter(prefix="/api/chats", tags=["stream"])


def _parse_tool_intent(query: str, response: str | None, rag_enabled: bool) -> dict[str, bool]:
    """Turn the classifier response into safe, explicit tool decisions.

    The classifier may explain its answer or echo the available tool names.  We
    therefore accept only exact comma-separated tool tokens.  High-confidence
    wording in the user's own query is used to guard specialized visual/profile/
    map tools and to guarantee web search for live information.
    """
    query_lower = query.lower()
    normalized = (response or "").strip().lower().replace("`", "")
    selected = {part.strip() for part in normalized.split(",")}
    allowed = {"web_search", "rag", "image_search", "linkedin_finder", "map_directions"}
    selected &= allowed

    asks_for_images = bool(re.search(
        r"\b(image|images|photo|photos|picture|pictures|wallpaper|wallpapers|illustration|illustrations)\b",
        query_lower,
    ))
    asks_for_linkedin = "linkedin" in query_lower
    asks_for_map = bool(re.search(
        r"\b(map|maps|route|routes|direction|directions|navigate|navigation)\b",
        query_lower,
    ))
    needs_live_web = bool(re.search(
        r"\b(live|latest|current|today|tonight|score|scores|news|weather|price|prices|result|results|standing|standings)\b",
        query_lower,
    ))

    return {
        "rag": rag_enabled and "rag" in selected,
        "web_search": "web_search" in selected or needs_live_web,
        "image_search": "image_search" in selected and asks_for_images,
        "linkedin_finder": "linkedin_finder" in selected and asks_for_linkedin,
        "map_directions": "map_directions" in selected and asks_for_map,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sse(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event line."""
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


@router.post("/{chat_id}/stream")
async def stream_chat(
    chat_id: str,
    body: StreamRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    POST /api/chats/{chat_id}/stream
    Accepts the conversation history + settings, saves user message,
    streams the AI response as SSE, then saves the complete assistant message.

    SSE event shapes:
      {"type": "thinking", "text": "..."}
      {"type": "content",  "text": "..."}
      {"type": "done",     "message_id": "..."}
      {"type": "error",    "text": "..."}
    """
    # Validate chat exists
    try:
        chat_oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    chat = await db["chats"].find_one({"_id": chat_oid, "user_id": user["_id"]})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Extract the latest user message (last in list)
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    last_user = body.messages[-1]
    if last_user.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    allowed_mime_prefixes = {
        "image": ("image/png", "image/jpeg", "image/webp"),
        "audio": ("audio/mpeg", "audio/wav", "audio/x-wav"),
        "video": ("video/mp4", "video/quicktime", "video/webm"),
    }
    max_data_url_chars = {"image": 14_000_000, "audio": 28_000_000, "video": 35_000_000}
    for attachment in body.attachments:
        if attachment.mime_type not in allowed_mime_prefixes[attachment.media_type]:
            raise HTTPException(status_code=400, detail=f"Unsupported {attachment.media_type} format")
        if not attachment.data_url.startswith(f"data:{attachment.mime_type};base64,"):
            raise HTTPException(status_code=400, detail="Invalid media data URL")
        if len(attachment.data_url) > max_data_url_chars[attachment.media_type]:
            raise HTTPException(status_code=413, detail=f"{attachment.name} is too large")

    now = _utc_now()

    # ── 1. Save user message to MongoDB ────────────────────────────────────────
    user_msg_doc = {
        "chat_id": chat_oid,
        "role": "user",
        "content": last_user.content + (
            "\n\n[Attached media: " + ", ".join(a.name for a in body.attachments) + "]"
            if body.attachments else ""
        ),
        "thinking": None,
        "timestamp": now,
    }
    await db["messages"].insert_one(user_msg_doc)

    # ── 2. Auto-update chat title on first message ─────────────────────────────
    existing_msgs_count = await db["messages"].count_documents({"chat_id": chat_oid})
    if existing_msgs_count <= 1:  # just inserted the first user msg
        title = last_user.content[:50] + ("..." if len(last_user.content) > 50 else "")
        await db["chats"].update_one(
            {"_id": chat_oid},
            {"$set": {"title": title, "updated_at": now}},
        )

    # ── 3. Build system prompt ───────────────────────────────────────────────────
    # Layer order: [Identity] + [URL Contexts] + [RAG] + [Web Search]
    # The identity block (M00/Balwan) is always first.
    sources: list[dict] = []
    rag_chunks: list[dict] = []
    url_contexts: list[dict] = []
    image_results: list[dict] = []
    linkedin_profile: dict | None = None

    # Extract URLs from the user's message
    urls_to_scrape = re.findall(r'(https?://[^\s]+)', last_user.content)
    # Deduplicate and limit to max 3 URLs to avoid overload
    urls_to_scrape = list(dict.fromkeys(urls_to_scrape))[:3]

    async def _deep_scrape(url: str, user_query: str) -> list[dict]:
        """Scrape the url (with Redis cache). If it has links, ask the LLM which to follow."""
        # Check page cache first
        cached_page = await cache_get("scrape", url)
        if cached_page:
            print(f"[Cache] HIT  scrape:{url[:60]!r}")
            page = type('P', (), {'to_dict': lambda _: cached_page,
                                  'internal_links': cached_page.get('internal_links', []),
                                  'content': cached_page.get('content', '')})()
        else:
            page = await scrape(url, max_chars=10000)
            page_dict = page.to_dict()
            await cache_set("scrape", url, page_dict, SCRAPE_TTL)

        page_dict = cached_page if cached_page else page.to_dict()
        results = [page_dict]
        links = page_dict.get("internal_links", [])

        if links:
            # Prepare a fast LLM prompt to select a link
            links_text = "\n".join([f"- [{i}] {link['text']} ({link['href']})" for i, link in enumerate(links[:30])])
            prompt = (
                f"The user asked: '{user_query}'\n\n"
                f"I am on {url} and found these internal links:\n{links_text}\n\n"
                "If the user's query requires information that is highly likely to be found on ONE of these specific sub-pages "
                "(e.g., pricing, about, documentation), reply ONLY with the exact URL of that sub-page. "
                "If none of the links are highly relevant, reply with exactly 'NONE'."
            )
            response = await get_completion([{"role": "user", "content": prompt}], max_tokens=256)
            if response:
                selected = response.strip()
                if selected.startswith("http") and selected != url:
                    print(f"[DeepScrape] LLM selected secondary link: {selected}")
                    try:
                        second_page = await scrape(selected, max_chars=10000)
                        results.append(second_page.to_dict())
                    except Exception as e:
                        print(f"[DeepScrape] Secondary scrape failed: {e}")
        return results

    # Run scraping, RAG, and web search concurrently
    import asyncio as _asyncio
    tasks = []
    
    # Track task types to unpack results later
    task_types = []

    for url in urls_to_scrape:
        tasks.append(_deep_scrape(url, last_user.content))
        task_types.append("scrape")

    # Determine intent for external tools (including image search and LinkedIn)
    use_rag = body.use_rag
    web_search = True         # inherently available, determined by intent
    use_image_search = False  # always determined by intent
    use_linkedin = False      # always determined by intent
    use_map = False           # always determined by intent

    if use_rag or web_search or True:  # always run intent check
        available_tools = []
        available_tools.append("web_search") # always available
        if use_rag: available_tools.append("rag")
        available_tools.append("image_search")   # always available
        available_tools.append("linkedin_finder") # always available
        available_tools.append("map_directions") # always available

        prompt = (
            f"Given the user's message: '{last_user.content}'\n"
            f"Determine which external tools are strictly necessary to answer. "
            f"Available tools: {available_tools}. "
            f"Use 'linkedin_finder' ONLY if the user wants to find a LinkedIn profile, professional info, or contact details for a specific person. "
            f"Use 'image_search' ONLY if the user explicitly asks to see, find, show, or display images/pictures/photos. "
            f"Use 'map_directions' ONLY if the user asks for directions, a route, distance, or a map between two locations. "
            f"Use 'web_search' ONLY for questions requiring live/current web data. "
            f"Use 'rag' ONLY if the query requires specific internal documents. "
            f"If the query is a simple greeting, casual conversation, or a standard coding/math/writing request, reply with exactly 'NONE'. "
            f"Otherwise, reply with a comma-separated list of required tools (e.g. 'linkedin_finder' or 'image_search')."
        )
        # Check intent cache first (same query → same tool decision)
        intent_cache_key = f"{last_user.content}|{available_tools}"
        intent_resp = await cache_get("intent", intent_cache_key)
        if intent_resp is None:
            intent_resp = await get_completion([{"role": "user", "content": prompt}], max_tokens=256)
            if intent_resp:
                await cache_set("intent", intent_cache_key, intent_resp, INTENT_TTL)
        decisions = _parse_tool_intent(last_user.content, intent_resp, use_rag)
        use_rag = decisions["rag"]
        web_search = decisions["web_search"]
        use_image_search = decisions["image_search"]
        use_linkedin = decisions["linkedin_finder"]
        use_map = decisions["map_directions"]
        enabled = [name for name, value in decisions.items() if value]
        print(f"[IntentRouter] Query: '{last_user.content}' -> Tools: {enabled or ['NONE']}")

    if use_rag:
        tasks.append(retrieve(last_user.content, db))
        task_types.append("rag")

    async def _image_search_task(query: str) -> list[dict]:
        from services.image_search import search_images
        print(f"[ImageSearch] Searching for: {query!r}")
        return await search_images(query, max_results=6)

    async def _linkedin_task(query: str) -> dict | None:
        from services.linkedin_finder import find_linkedin_profile
        from services.nvidia import get_completion
        
        # Use LLM to robustly extract the person's name or LinkedIn URL from the query
        ext_prompt = (
            f"Extract ONLY the person's name or the direct LinkedIn URL from this query: '{query}'. "
            f"Do not include any conversational text, just the name (e.g. 'John Doe') or URL. "
            f"If none found, reply with 'NONE'."
        )
        ans = await get_completion([{"role": "user", "content": ext_prompt}], max_tokens=50)
        person_name = ans.strip(' "\'\n')
        
        if not person_name or person_name.upper() == "NONE":
            # Fallback to the raw query stripped of common trigger words
            import re
            person_name = re.sub(r"(?i)\s*(find|search|show|tell me about|linkedin|profile|detail[s]?|for|of)\s*", " ", query).strip()
            
        print(f"[LinkedIn] Extracted target: {person_name!r}")
        return await find_linkedin_profile(person_name)

    async def _search_and_crawl(query: str) -> list[dict]:
        from services.search import search as web_search
        # Get top 2 results to crawl to save time and token limits
        results = await web_search(query, max_results=2)
        if not results:
            return []
        
        urls = [r.get("href") for r in results if r.get("href")]
        if not urls:
            return results
            
        print(f"[SearchCrawl] Crawling {len(urls)} live search results...")
        scrape_tasks = [scrape(u, max_chars=8000) for u in urls]
        pages = await _asyncio.gather(*scrape_tasks, return_exceptions=True)
        
        for i, page in enumerate(pages):
            if not isinstance(page, Exception) and getattr(page, "content", None):
                if not page.content.startswith("[Scraping failed:"):
                    results[i]["body"] = "FULL PAGE CONTENT:\n" + page.content
        return results

    if use_image_search:
        tasks.append(_image_search_task(last_user.content))
        task_types.append("images")

    if use_linkedin:
        tasks.append(_linkedin_task(last_user.content))
        task_types.append("linkedin")

    async def _map_task(query: str) -> dict | None:
        from services.map_directions import extract_and_route
        return await extract_and_route(query)

    if use_map:
        tasks.append(_map_task(last_user.content))
        task_types.append("map")

    if web_search:
        tasks.append(_search_and_crawl(last_user.content))
        task_types.append("search")

    # Build the layered system prompt
    system_parts = [get_identity_prompt()]
    
    map_result = None
    if tasks:
        results = await _asyncio.gather(*tasks, return_exceptions=True)
        for t_type, res in zip(task_types, results):
            if isinstance(res, Exception):
                print(f"[Stream] Task {t_type} failed: {res}")
                continue
            
            if t_type == "scrape":
                url_contexts.extend(res)
            elif t_type == "rag":
                rag_chunks = res
            elif t_type == "search":
                sources = res
            elif t_type == "images":
                image_results = res
            elif t_type == "linkedin":
                linkedin_profile = res
            elif t_type == "map":
                map_result = res

    # URL contexts come first (user-provided, highest specificity)
    if url_contexts:
        url_ctx = format_url_context(url_contexts)
        system_parts.append(url_ctx)

    if rag_chunks:
        rag_ctx = format_rag_context(rag_chunks)
        system_parts.append(rag_ctx)

    if web_search and sources:
        from services.search import format_search_context
        web_ctx = format_search_context(sources, query=last_user.content)
        system_parts.append(
            "When using information from the web search results, cite the source number like [1], [2] etc. "
            "and also explicitly include the full URL of the source in your response.\n\n" + web_ctx
        )

    if use_linkedin:
        if linkedin_profile:
            system_parts.append(
                f"You have retrieved a LinkedIn profile for {linkedin_profile.get('name')}:\n"
                f"- Headline: {linkedin_profile.get('headline')}\n"
                f"- Snippet: {linkedin_profile.get('snippet')}\n"
                f"- Profile URL: {linkedin_profile.get('profile_url')}\n"
                f"The profile card and photo are already displayed to the user in the UI, so do not output the raw image URL. "
                f"Briefly summarize their professional background based on this snippet."
            )
        else:
            system_parts.append(
                "You just attempted to search the web for this person's LinkedIn profile in real-time, "
                "but the search engine blocked the request or the profile could not be found. "
                "Inform the user that you actively searched the web for it right now, but were unable to locate a public LinkedIn profile for them."
            )

    if map_result:
        system_parts.append(
            f"You have retrieved route directions from {map_result['origin_full']} to {map_result['dest_full']}.\n"
            f"- Total Distance: {map_result['distance']}\n"
            f"- Estimated Duration: {map_result['duration']}\n"
            f"Turn-by-turn steps:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(map_result['steps'])) +
            "\n\nThe interactive map is already rendered to the user. Provide a summary of the full route guidance."
        )

    system_prompt = "\n\n---\n\n".join(system_parts)

    # ── 4. Build full-history message list for NVIDIA API ─────────────────────
    # build_context_messages loads ALL messages from MongoDB for this chat,
    # fits them into the model context window with smart compression if needed.
    api_messages = await build_context_messages(chat_oid, db, system_prompt)

    if body.attachments:
        media_parts: list[dict] = [{"type": "text", "text": last_user.content}]
        for attachment in body.attachments:
            media_parts.append({
                "type": f"{attachment.media_type}_url",
                f"{attachment.media_type}_url": {"url": attachment.data_url},
            })
        api_messages[-1] = {"role": "user", "content": media_parts}

    print(f"[Context] Sending {len(api_messages)} messages to API (incl. system).")

    # ── 5. Stream generator ───────────────────────────────────────────────────
    async def event_generator():
        full_content = ""
        full_thinking = ""
        assistant_msg_id: str | None = None

        # Emit image results first (highest visual priority)
        if image_results:
            yield _sse("images", {"images": image_results})

        # Emit LinkedIn profile next
        if linkedin_profile:
            yield _sse("linkedin", {"profile": linkedin_profile})

        # Emit map route next
        if map_result:
            yield _sse("map_route", {"origin": map_result["origin"], "destination": map_result["destination"]})

        # Emit sources so frontend can render them right away
        if sources:
            yield _sse("sources", {"sources": sources})

        # If images found, add a system note about them into the AI context
        # The AI should acknowledge the images in its response
        if image_results:
            img_note = f"\n\n[System Note: {len(image_results)} relevant images have been retrieved and displayed to the user above. Briefly acknowledge that you found and displayed the images, and optionally describe what they show.]"
            # Inject into the last user message content in api_messages
            api_messages[-1]["content"] = api_messages[-1]["content"] + img_note

        try:
            settings = get_settings()
            async for token_type, text in stream_completion(
                api_messages,
                body.thinking_level,
                model=settings.nvidia_multimodal_model if body.attachments else settings.nvidia_model,
                multimodal=bool(body.attachments),
            ):
                # Check if client disconnected
                if await request.is_disconnected():
                    break


                if token_type == "thinking":
                    full_thinking += text
                    yield _sse("thinking", {"text": text})

                elif token_type == "content":
                    full_content += text
                    yield _sse("content", {"text": text})

                elif token_type == "done":
                    # Save complete assistant message to MongoDB
                    asst_doc = {
                        "chat_id": chat_oid,
                        "role": "assistant",
                        "content": full_content,
                        "thinking": full_thinking if full_thinking else None,
                        "timestamp": _utc_now(),
                    }
                    res = await db["messages"].insert_one(asst_doc)
                    assistant_msg_id = str(res.inserted_id)

                    # Update chat updated_at
                    await db["chats"].update_one(
                        {"_id": chat_oid},
                        {"$set": {"updated_at": _utc_now()}},
                    )

                    yield _sse("done", {"message_id": assistant_msg_id or ""})
                    return

                elif token_type == "error":
                    yield _sse("error", {"text": text})
                    return

        except asyncio.CancelledError:
            # Client disconnected mid-stream — save what we have
            if full_content:
                asst_doc = {
                    "chat_id": chat_oid,
                    "role": "assistant",
                    "content": full_content,
                    "thinking": full_thinking if full_thinking else None,
                    "timestamp": _utc_now(),
                }
                await db["messages"].insert_one(asst_doc)
            return

        except Exception as e:
            yield _sse("error", {"text": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
