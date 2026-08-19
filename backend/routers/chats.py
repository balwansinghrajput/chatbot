from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.db import get_db
from models.chat import ChatCreate, ChatOut, ChatUpdate, MessageOut, serialize_message

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─── List all chats ───────────────────────────────────────────────────────────

@router.get("", response_model=list[ChatOut])
async def list_chats(db: AsyncIOMotorDatabase = Depends(get_db)):
    chats_col = db["chats"]
    cursor = chats_col.find({}).sort("updated_at", -1)
    result = []
    async for doc in cursor:
        result.append(
            ChatOut(
                id=str(doc["_id"]),
                title=doc["title"],
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            )
        )
    return result


# ─── Create chat ─────────────────────────────────────────────────────────────

@router.post("", response_model=ChatOut, status_code=201)
async def create_chat(body: ChatCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    now = _utc_now()
    doc = {
        "title": body.title,
        "created_at": now,
        "updated_at": now,
    }
    res = await db["chats"].insert_one(doc)
    return ChatOut(
        id=str(res.inserted_id),
        title=body.title,
        created_at=now,
        updated_at=now,
    )


# ─── Get chat + messages ──────────────────────────────────────────────────────

@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    doc = await db["chats"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Load messages
    msgs_cursor = db["messages"].find({"chat_id": oid}).sort("timestamp", 1)
    messages: list[MessageOut] = []
    async for m in msgs_cursor:
        messages.append(serialize_message(m))

    return ChatOut(
        id=str(doc["_id"]),
        title=doc["title"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        messages=messages,
    )


# ─── Rename chat ──────────────────────────────────────────────────────────────

@router.patch("/{chat_id}", response_model=ChatOut)
async def rename_chat(
    chat_id: str, body: ChatUpdate, db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    now = _utc_now()
    res = await db["chats"].find_one_and_update(
        {"_id": oid},
        {"$set": {"title": body.title, "updated_at": now}},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Chat not found")

    return ChatOut(
        id=str(res["_id"]),
        title=res["title"],
        created_at=res["created_at"],
        updated_at=res["updated_at"],
    )


# ─── Delete chat + messages ───────────────────────────────────────────────────

@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    res = await db["chats"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")

    await db["messages"].delete_many({"chat_id": oid})


# ─── Get messages for a chat ──────────────────────────────────────────────────

@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    cursor = db["messages"].find({"chat_id": oid}).sort("timestamp", 1)
    result = []
    async for doc in cursor:
        result.append(serialize_message(doc))
    return result
