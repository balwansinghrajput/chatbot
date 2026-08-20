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

    # Extract URLs from the user's message
    urls_to_scrape = re.findall(r'(https?://[^\s]+)', last_user.content)
    # Deduplicate and limit to max 3 URLs to avoid overload
    urls_to_scrape = list(dict.fromkeys(urls_to_scrape))[:3]

    async def _deep_scrape(url: str, user_query: str) -> list[dict]:
        """Scrape the url. If it has links, ask the LLM which to follow, and scrape that too."""
        page = await scrape(url, max_chars=10000)
        results = [page.to_dict()]
        
        links = page.internal_links
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

    # Determine intent for external tools
    use_rag = body.use_rag
    web_search = body.web_search

    if use_rag or web_search:
        available = []
        if web_search: available.append("web_search")
        if use_rag: available.append("rag")
        
        prompt = (
            f"Given the user's message: '{last_user.content}'\n"
            f"Determine which external tools are strictly necessary to answer. "
            f"Available tools: {available}. "
            f"If the query is a simple greeting (e.g. 'hi', 'hello'), casual conversation, or a standard coding request that does not require live external data or specific internal documents, reply with exactly 'NONE'. "
            f"Otherwise, reply with a comma-separated list of required tools from the available tools."
        )
        intent_resp = await get_completion([{"role": "user", "content": prompt}], max_tokens=256)
        if intent_resp:
            ans = intent_resp.strip().lower()
            print(f"[IntentRouter] User Query: '{last_user.content}' -> Routing to: {ans}")
            if "none" in ans:
                use_rag = False
                web_search = False
            else:
                if "rag" not in ans: use_rag = False
                if "web_search" not in ans and "search" not in ans: web_search = False

    if use_rag:
        tasks.append(retrieve(last_user.content, db))
        task_types.append("rag")
        
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
                # res is a list of ScrapedPage dicts
                url_contexts.extend(res)
            elif t_type == "rag":
                rag_chunks = res
            elif t_type == "search":
                sources = res

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

    # ── 4. Build message list for NVIDIA API ──────────────────────────────────
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in body.messages:
        api_messages.append({"role": m.role, "content": m.content})


    # ── 5. Stream generator ───────────────────────────────────────────────────
    async def event_generator():
        full_content = ""
        full_thinking = ""
        assistant_msg_id: str | None = None

        # Emit sources immediately so frontend can render them right away
        if sources:
            yield _sse("sources", {"sources": sources})

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
