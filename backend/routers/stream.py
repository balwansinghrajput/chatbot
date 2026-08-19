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
from services.search import build_search_system_prompt

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

    # ── 3. Build system prompt (with optional DuckDuckGo context) ─────────────
    sources: list[dict] = []
    if body.web_search:
        system_prompt, sources = await build_search_system_prompt(last_user.content)
    else:
        system_prompt = (
            "You are a helpful AI assistant with deep reasoning capabilities. "
            "Answer questions thoughtfully and precisely."
        )

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
