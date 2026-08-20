"""
Web search service.

Primary:  Brave Search API (https://api.search.brave.com)
Fallback: DuckDuckGo via `ddgs` package (no API key needed)

Set BRAVE_SEARCH_API_KEY in backend/.env to enable Brave.
If the key is missing or the Brave request fails, DuckDuckGo is used automatically.
"""

import httpx
import re
from urllib.parse import urlparse

from config import get_settings


BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    """Extract clean domain from URL, e.g. 'https://www.example.com/page' -> 'example.com'"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = re.sub(r"^www\.", "", domain)
        return domain
    except Exception:
        return url


def _enrich(title: str, href: str, body: str) -> dict:
    """Build a standard result dict with domain field."""
    domain = _extract_domain(href)
    return {
        "title": title.strip(),
        "href": href,
        "body": body.strip(),
        "domain": domain,
    }


# ─── Primary: Brave Search ────────────────────────────────────────────────────

async def _brave_search(query: str, max_results: int) -> list[dict]:
    """Call Brave Search API. Returns [] on any error or missing key."""
    api_key = get_settings().brave_search_api_key
    if not api_key or api_key == "your_brave_api_key_here":
        print("[Search] Brave API key not set, skipping Brave.")
        return []

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": max_results,
        "search_lang": "en",
        "text_decorations": False,
        "result_filter": "web",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(BRAVE_SEARCH_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        raw = data.get("web", {}).get("results", [])[:max_results]
        results = [
            _enrich(r.get("title", ""), r.get("url", ""), r.get("description", ""))
            for r in raw
        ]
        print(f"[Search] Brave returned {len(results)} results")
        return results

    except httpx.HTTPStatusError as e:
        print(f"[Search] Brave HTTP {e.response.status_code}: {e.response.text[:120]}")
    except Exception as e:
        print(f"[Search] Brave error: {e}")

    return []


# ─── Fallback: DuckDuckGo ─────────────────────────────────────────────────────

async def _ddg_search(query: str, max_results: int) -> list[dict]:
    """
    DuckDuckGo fallback using the `ddgs` package.
    Tries async API first, falls back to sync in thread pool.
    """
    # Attempt 1: ddgs AsyncDDGS (native async, ddgs v9+)
    try:
        from ddgs import AsyncDDGS  # type: ignore
        async with AsyncDDGS() as ddgs:
            raw = await ddgs.atext(query, max_results=max_results)
        if raw:
            results = [
                _enrich(r.get("title", ""), r.get("href", ""), r.get("body", ""))
                for r in raw
            ]
            print(f"[Search] DuckDuckGo (async) returned {len(results)} results")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[Search] DuckDuckGo async error: {e}")

    # Attempt 2: ddgs sync DDGS in thread pool
    try:
        import asyncio
        from ddgs import DDGS  # type: ignore

        def _sync() -> list[dict]:
            with DDGS() as d:
                return list(d.text(query, max_results=max_results))

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _sync)
        if raw:
            results = [
                _enrich(r.get("title", ""), r.get("href", ""), r.get("body", ""))
                for r in raw
            ]
            print(f"[Search] DuckDuckGo (sync) returned {len(results)} results")
            return results
    except ImportError:
        print("[Search] `ddgs` package not installed. Run: pip install ddgs")
    except Exception as e:
        print(f"[Search] DuckDuckGo sync error: {e}")

    return []


# ─── Public entry point ───────────────────────────────────────────────────────

async def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for `query`.
    1. Try Brave Search (fast, structured, requires API key)
    2. Fall back to DuckDuckGo (free, no key needed)
    """
    # Primary: Brave
    results = await _brave_search(query, max_results)
    if results:
        return results

    # Fallback: DuckDuckGo
    print("[Search] Falling back to DuckDuckGo...")
    return await _ddg_search(query, max_results)


# ─── Prompt builder ───────────────────────────────────────────────────────────

def format_search_context(results: list[dict], query: str = "") -> str:
    """Format results into a system context block for the AI prompt."""
    if not results:
        return ""

    header = f'## Web Search Results for: "{query}"\n\n' if query else "## Web Search Results\n\n"
    parts = [
        header,
        "The following information was retrieved live from the web. "
        "Use it as context to give an accurate, up-to-date answer and cite sources.\n\n",
    ]

    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] **{r.get('title', 'Result')}**")
        if r.get("href"):
            parts.append(f"    URL: {r['href']}")
        if r.get("body"):
            parts.append(f"    {r['body']}")
        parts.append("")

    return "\n".join(parts)


async def build_search_system_prompt(user_query: str) -> tuple[str, list[dict]]:
    """
    Search the web and return (system_prompt_with_context, enriched_results).
    Always tries Brave first; silently falls back to DuckDuckGo if needed.
    """
    print(f"[Search] Query: {user_query!r}")
    results = await search(user_query)
    context = format_search_context(results, query=user_query)

    base = (
        "You are a helpful AI assistant with deep reasoning capabilities. "
        "Answer questions thoughtfully and precisely. "
        "When using information from the web search results, cite the source number like [1], [2] etc. "
        "and also explicitly include the full URL of the source in your response."
    )

    if context:
        prompt = f"{base}\n\n{context}"
    else:
        prompt = (
            f"{base}\n\n"
            "## Web Search Note\n"
            "A web search was attempted but returned no results. "
            "Answer based on your training knowledge."
        )

    return prompt, results
