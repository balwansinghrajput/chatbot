"""
Image search service.

Primary:  DuckDuckGo Image Search (free, no key needed)
Fallback: Wikimedia Commons API (free, stable direct image URLs)
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
        # Projects created before the package rename may still install
        # `duckduckgo-search`, whose public client has the same sync API.
        try:
            from duckduckgo_search import DDGS  # type: ignore

            def _legacy_sync() -> list[dict]:
                with DDGS() as d:
                    return list(d.images(query, max_results=max_results, safesearch="moderate"))

            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, _legacy_sync)
            if raw:
                return [
                    {
                        "url": r.get("image", ""),
                        "thumbnail": r.get("thumbnail", r.get("image", "")),
                        "title": r.get("title", ""),
                        "source": r.get("url", ""),
                        "width": r.get("width", 0),
                        "height": r.get("height", 0),
                    }
                    for r in raw if r.get("image")
                ][:max_results]
        except Exception as e:
            print(f"[ImageSearch] DuckDuckGo legacy client error: {e}")
    except Exception as e:
        print(f"[ImageSearch] DuckDuckGo sync error: {e}")

    return []


# ─── Fallback: Unsplash API ───────────────────────────────────────────────────

async def _commons_search(query: str, max_results: int) -> list[dict]:
    """Search Wikimedia Commons for stable, directly renderable image URLs."""
    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": min(max_results, 10),
            "prop": "imageinfo",
            "iiprop": "url|size",
            "iiurlwidth": 640,
            "format": "json",
            "origin": "*",
        }
        headers = {"User-Agent": "M00-AI-Assistant/1.0 (image search)"}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
            response = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
            response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("url")
            if not url:
                continue
            results.append({
                "url": url,
                "thumbnail": info.get("thumburl", url),
                "title": page.get("title", "").removeprefix("File:"),
                "source": info.get("descriptionurl", "https://commons.wikimedia.org"),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
            })
        print(f"[ImageSearch] Wikimedia Commons returned {len(results)} images")
        return results
    except Exception as e:
        print(f"[ImageSearch] Wikimedia Commons error: {e}")
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

    print("[ImageSearch] Falling back to Wikimedia Commons...")
    return await _commons_search(query, max_results)
