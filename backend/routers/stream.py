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
import re

router = APIRouter(prefix="/api/chats", tags=["stream"])


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

    chat = await db["chats"].find_one({"_id": chat_oid})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Extract the latest user message (last in list)
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    last_user = body.messages[-1]
    if last_user.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    now = _utc_now()

    # ── 1. Save user message to MongoDB ────────────────────────────────────────
    user_msg_doc = {
        "chat_id": chat_oid,
        "role": "user",
        "content": last_user.content,
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

    # Determine intent for external tools (including image search)
    use_rag = body.use_rag
    web_search = body.web_search
    use_image_search = False  # always determined by intent

    if use_rag or web_search or True:  # always run intent check for image detection
        available_tools = []
        if web_search: available_tools.append("web_search")
        if use_rag: available_tools.append("rag")
        available_tools.append("image_search")  # always available

        prompt = (
            f"Given the user's message: '{last_user.content}'\n"
            f"Determine which external tools are strictly necessary to answer. "
            f"Available tools: {available_tools}. "
            f"Use 'image_search' ONLY if the user explicitly asks to see, find, show, or display images/pictures/photos (e.g. 'show me a cat image', 'find pictures of dogs'). "
            f"Use 'web_search' ONLY for questions requiring live/current web data. "
            f"Use 'rag' ONLY if the query requires specific internal documents. "
            f"If the query is a simple greeting, casual conversation, or a standard coding/math/writing request, reply with exactly 'NONE'. "
            f"Otherwise, reply with a comma-separated list of required tools from the available tools (e.g. 'image_search' or 'web_search,rag')."
        )
        # Check intent cache first (same query → same tool decision)
        intent_cache_key = f"{last_user.content}|{available_tools}"
        intent_resp = await cache_get("intent", intent_cache_key)
        if intent_resp is None:
            intent_resp = await get_completion([{"role": "user", "content": prompt}], max_tokens=256)
            if intent_resp:
                await cache_set("intent", intent_cache_key, intent_resp, INTENT_TTL)
        if intent_resp:
            ans = intent_resp.strip().lower()
            print(f"[IntentRouter] Query: '{last_user.content}' -> Tools: {ans}")
            if "none" in ans:
                use_rag = False
                web_search = False
                use_image_search = False
            else:
                if "image_search" in ans or "image" in ans: use_image_search = True
                if "rag" not in ans: use_rag = False
                if "web_search" not in ans and "search" not in ans and "image" not in ans: web_search = False
                # If it's purely an image search, no need for web_search
                if use_image_search and "web_search" not in ans: web_search = False

    if use_rag:
        tasks.append(retrieve(last_user.content, db))
        task_types.append("rag")

    async def _image_search_task(query: str) -> list[dict]:
        from services.image_search import search_images
        print(f"[ImageSearch] Searching for: {query!r}")
        return await search_images(query, max_results=6)

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

    if web_search:
        tasks.append(_search_and_crawl(last_user.content))
        task_types.append("search")

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

    # Build the layered system prompt
    system_parts = [get_identity_prompt()]

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

    system_prompt = "\n\n---\n\n".join(system_parts)

    # ── 4. Build full-history message list for NVIDIA API ─────────────────────
    # build_context_messages loads ALL messages from MongoDB for this chat,
    # fits them into the model context window with smart compression if needed.
    api_messages = await build_context_messages(chat_oid, db, system_prompt)

    print(f"[Context] Sending {len(api_messages)} messages to API (incl. system).")

    # ── 5. Stream generator ───────────────────────────────────────────────────
    async def event_generator():
        full_content = ""
        full_thinking = ""
        assistant_msg_id: str | None = None

        # Emit image results first (highest visual priority)
        if image_results:
            yield _sse("images", {"images": image_results})

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
            async for token_type, text in stream_completion(api_messages, body.thinking_level):
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
