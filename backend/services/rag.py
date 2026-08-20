"""
RAG (Retrieval-Augmented Generation) Service

Retrieves the most semantically relevant knowledge chunks from MongoDB Atlas
using vector similarity search, then formats them as a system prompt block.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from services.embeddings import embed_text


# ─── Retrieval ────────────────────────────────────────────────────────────────

async def retrieve(
    query: str,
    db: AsyncIOMotorDatabase,
    top_k: int = 5,
    min_score: float = 0.5,
) -> list[dict]:
    """
    Embed the query and run MongoDB Atlas Vector Search to find the top-K
    most semantically similar knowledge chunks.

    Args:
        query:     The user's message to embed and search with.
        db:        Motor async database instance.
        top_k:     Maximum number of chunks to return.
        min_score: Minimum cosine similarity score (0-1). Lower = less strict.

    Returns:
        List of matching chunk dicts with keys: title, content, source, score.
    """
    try:
        query_embedding = await embed_text(query, input_type="query")
    except Exception as e:
        print(f"[RAG] Embedding error: {e}")
        return []

    pipeline = [
        {
            "$vectorSearch": {
                "index": "knowledge_vector_index",   # Atlas Search index name
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 10,          # oversample for better accuracy
                "limit": top_k,
            }
        },
        {
            "$project": {
                "_id": 1,
                "title": 1,
                "content": 1,
                "source": 1,
                "category": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
        {
            "$match": {"score": {"$gte": min_score}}
        },
    ]

    try:
        cursor = db["knowledge_chunks"].aggregate(pipeline)
        results = []
        async for doc in cursor:
            results.append({
                "id": str(doc["_id"]),
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "source": doc.get("source", ""),
                "category": doc.get("category", ""),
                "score": round(doc.get("score", 0), 3),
            })
        print(f"[RAG] Retrieved {len(results)} chunks for query: {query!r}")
        return results
    except Exception as e:
        print(f"[RAG] Vector search error: {e}")
        return []


# ─── Context builder ──────────────────────────────────────────────────────────

def format_rag_context(chunks: list[dict]) -> str:
    """
    Format retrieved knowledge chunks into a system prompt context block.
    """
    if not chunks:
        return ""

    lines = [
        "## Knowledge Base Context\n",
        "The following information is from M00's internal knowledge base. "
        "Use it to answer the user's question accurately.\n\n",
    ]

    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title", f"Chunk {i}")
        content = chunk.get("content", "")
        source = chunk.get("source", "")
        lines.append(f"### [{i}] {title}")
        if source:
            lines.append(f"Source: {source}")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
