"""
NVIDIA Embeddings Service
Generates vector embeddings using NVIDIA NIM embedding API.
Model: nvidia/nv-embedqa-e5-v5  (1024 dimensions)
"""

import httpx
from config import get_settings


async def embed_text(text: str, input_type: str = "passage") -> list[float]:
    """
    Generate a 1024-dimensional embedding for a single text string.

    Args:
        text: The text to embed.
        input_type: "passage" for documents being stored,
                    "query" for user queries at retrieval time.

    Returns:
        A list of 1024 floats representing the embedding vector.
    """
    settings = get_settings()
    payload = {
        "input": [text[:8000]],          # truncate to safe token limit
        "model": settings.nvidia_embedding_model,
        "input_type": input_type,
    }
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.nvidia_base_url}/embeddings",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    return data["data"][0]["embedding"]


async def embed_texts(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.
    Sends all texts in a single API call (max 96 per call per NVIDIA limits).
    """
    settings = get_settings()
    payload = {
        "input": [t[:8000] for t in texts],
        "model": settings.nvidia_embedding_model,
        "input_type": input_type,
    }
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.nvidia_base_url}/embeddings",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    # Sort by index to preserve original order
    items = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in items]
