"""
Knowledge Base CRUD API

Endpoints to manage M00's internal knowledge base.
Chunks are automatically embedded via NVIDIA NIM when created.
"""

import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends

from database.db import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.knowledge import (
    KnowledgeChunkCreate,
    KnowledgeChunkOut,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    BulkKnowledgeCreate,
)
from services.embeddings import embed_text, embed_texts
from services.rag import retrieve

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _doc_to_out(doc: dict) -> KnowledgeChunkOut:
    return KnowledgeChunkOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        content=doc.get("content", ""),
        source=doc.get("source"),
        category=doc.get("category"),
        created_at=doc.get("created_at", _utc_now()),
    )


# ─── List all chunks ──────────────────────────────────────────────────────────

@router.get("", response_model=list[KnowledgeChunkOut])
async def list_knowledge(
    skip: int = 0,
    limit: int = 50,
    category: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List knowledge chunks, newest first. Filter by category if provided."""
    query: dict = {}
    if category:
        query["category"] = category

    cursor = db["knowledge_chunks"].find(query, {"embedding": 0}).sort("created_at", -1).skip(skip).limit(limit)
    results = []
    async for doc in cursor:
        results.append(_doc_to_out(doc))
    return results


# ─── Add a single chunk ───────────────────────────────────────────────────────

@router.post("", response_model=KnowledgeChunkOut, status_code=201)
async def add_knowledge(
    body: KnowledgeChunkCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Add a knowledge chunk. The content is automatically embedded via NVIDIA."""
    try:
        embedding = await embed_text(body.content, input_type="passage")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding failed: {e}")

    now = _utc_now()
    doc = {
        "title": body.title,
        "content": body.content,
        "embedding": embedding,
        "source": body.source,
        "category": body.category,
        "created_at": now,
    }
    res = await db["knowledge_chunks"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _doc_to_out(doc)


# ─── Bulk import ──────────────────────────────────────────────────────────────

@router.post("/bulk", status_code=201)
async def bulk_add_knowledge(
    body: BulkKnowledgeCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Bulk import up to 50 knowledge chunks in one call.
    All chunks are embedded in a single batched NVIDIA API call.
    """
    texts = [c.content for c in body.chunks]
    try:
        embeddings = await embed_texts(texts, input_type="passage")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Batch embedding failed: {e}")

    now = _utc_now()
    docs = [
        {
            "title": chunk.title,
            "content": chunk.content,
            "embedding": emb,
            "source": chunk.source,
            "category": chunk.category,
            "created_at": now,
        }
        for chunk, emb in zip(body.chunks, embeddings)
    ]
    res = await db["knowledge_chunks"].insert_many(docs)
    return {"inserted": len(res.inserted_ids), "ids": [str(i) for i in res.inserted_ids]}


# ─── Get a single chunk ───────────────────────────────────────────────────────

@router.get("/{chunk_id}", response_model=KnowledgeChunkOut)
async def get_knowledge(
    chunk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        oid = ObjectId(chunk_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chunk ID")

    doc = await db["knowledge_chunks"].find_one({"_id": oid}, {"embedding": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return _doc_to_out(doc)


# ─── Delete a chunk ───────────────────────────────────────────────────────────

@router.delete("/{chunk_id}", status_code=204)
async def delete_knowledge(
    chunk_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        oid = ObjectId(chunk_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chunk ID")

    res = await db["knowledge_chunks"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chunk not found")


# ─── Semantic search ──────────────────────────────────────────────────────────

@router.post("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge(
    body: KnowledgeSearchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Test the vector search — useful for verifying RAG quality."""
    chunks = await retrieve(body.query, db, top_k=body.top_k, min_score=body.min_score)
    return [KnowledgeSearchResult(**c) for c in chunks]


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats/summary")
async def knowledge_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Return count of chunks and available categories."""
    total = await db["knowledge_chunks"].count_documents({})
    pipeline = [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
    categories = {}
    async for doc in db["knowledge_chunks"].aggregate(pipeline):
        cat = doc["_id"] or "uncategorized"
        categories[cat] = doc["count"]
    return {"total_chunks": total, "categories": categories}
