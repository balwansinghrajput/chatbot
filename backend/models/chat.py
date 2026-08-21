from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


# ─── Helpers ────────────────────────────────────────────────────────────────

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_object_id() -> str:
    return str(ObjectId())


# ─── Chat Models ─────────────────────────────────────────────────────────────

class ChatCreate(BaseModel):
    title: str = "New Chat"


class ChatUpdate(BaseModel):
    title: str


class MessageOut(BaseModel):
    id: str
    chat_id: str
    role: Literal["user", "assistant"]
    content: str
    thinking: Optional[str] = None
    timestamp: datetime


class ChatOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


# ─── Stream Request ───────────────────────────────────────────────────────────

ThinkingLevel = Literal["low", "medium", "high"]

THINKING_BUDGETS: dict[str, int] = {
    "low":    2_048,   # fast, short answers
    "medium": 8_192,   # standard balanced responses
    "high":   32_768,  # detailed, long-form analysis
}


class MessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class StreamRequest(BaseModel):
    messages: list[MessageIn]
    thinking_level: ThinkingLevel = "medium"
    web_search: bool = False
    use_rag: bool = True


# ─── DB Serialization Helpers ────────────────────────────────────────────────

def serialize_chat(doc: dict) -> ChatOut:
    return ChatOut(
        id=str(doc["_id"]),
        title=doc["title"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        messages=[],
    )


def serialize_message(doc: dict) -> MessageOut:
    return MessageOut(
        id=str(doc["_id"]),
        chat_id=str(doc["chat_id"]),
        role=doc["role"],
        content=doc["content"],
        thinking=doc.get("thinking"),
        timestamp=doc["timestamp"],
    )
