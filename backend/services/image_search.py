"""
Image search service.

Primary:  DuckDuckGo Image Search (via ddgs package, free, no key needed)
Fallback: Unsplash public API (free, curated, high quality)
"""

import asyncio
import httpx
from services.cache import cached, IMAGE_TTL


# ─── Primary: DuckDuckGo Images ──────────────────────────────────────────────

async def _ddg_image_search(query: str, max_results: int) -> list[dict]:
    """Search DuckDuckGo for images. Returns list of image result dicts."""

    # Attempt 1: ddgs AsyncDDGS native async
    try:
        from ddgs import AsyncDDGS  # type: ignore
        async with AsyncDDGS() as ddgs:
            raw = await ddgs.aimages(
                query,
                max_results=max_results,
                safesearch="moderate",
            )
        if raw:
            results = [
                {
                    "url": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", r.get("image", "")),
                    "title": r.get("title", ""),
                    "source": r.get("url", ""),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                }
                for r in raw
                if r.get("image")
            ]
            print(f"[ImageSearch] DuckDuckGo (async) returned {len(results)} images")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[ImageSearch] DuckDuckGo async error: {e}")

    # Attempt 2: ddgs sync in thread pool
    try:
        from ddgs import DDGS  # type: ignore

        def _sync() -> list[dict]:
            with DDGS() as d:
                return list(d.images(query, max_results=max_results, safesearch="moderate"))

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _sync)
        if raw:
            results = [
                {
                    "url": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", r.get("image", "")),
                    "title": r.get("title", ""),
                    "source": r.get("url", ""),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                }
                for r in raw
                if r.get("image")
            ]
            print(f"[ImageSearch] DuckDuckGo (sync) returned {len(results)} images")
            return results
    except ImportError:
        print("[ImageSearch] `ddgs` package not installed. Run: pip install ddgs")
    except Exception as e:
        print(f"[ImageSearch] DuckDuckGo sync error: {e}")

    return []


# ─── Fallback: Unsplash API ───────────────────────────────────────────────────

async def _unsplash_search(query: str, max_results: int) -> list[dict]:
    """Use Unsplash's free public search (no key required for basic access)."""
    try:
        # Unsplash source provides random relevant images (free, no key needed)
        results = []
        for i in range(min(max_results, 6)):
            seed = f"{query.replace(' ', '-')}-{i}"
            url = f"https://source.unsplash.com/400x300/?{query.replace(' ', ',')}&sig={i}"
            results.append({
                "url": url,
                "thumbnail": url,
                "title": f"{query} - Image {i+1}",
                "source": "https://unsplash.com",
                "width": 400,
                "height": 300,
            })
        print(f"[ImageSearch] Unsplash fallback: generated {len(results)} image URLs")
        return results
    except Exception as e:
        print(f"[ImageSearch] Unsplash error: {e}")
    return []


# ─── Public entry point ───────────────────────────────────────────────────────

@cached("images", ttl=IMAGE_TTL, key_fn=lambda query, max_results=6: f"{query}:{max_results}")
async def search_images(query: str, max_results: int = 6) -> list[dict]:
    """
    Search for images matching `query`.
    1. Try DuckDuckGo (fast, structured, free)
    2. Fall back to Unsplash (free, curated)

    Each result dict has: url, thumbnail, title, source, width, height
    """
    results = await _ddg_image_search(query, max_results)
    if results:
        return results[:max_results]

    print("[ImageSearch] Falling back to Unsplash...")
    return await _unsplash_search(query, max_results)
