"""
DuckDuckGo search service using the `ddgs` package (v9+).
Returns structured results with title, href, body, domain, and favicon URL.
"""

import asyncio
import re
from urllib.parse import urlparse


def _extract_domain(url: str) -> str:
    """Extract clean domain from a URL, e.g. 'https://example.com/page' -> 'example.com'"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Strip www.
        domain = re.sub(r"^www\.", "", domain)
        return domain
    except Exception:
        return url


def _enrich_result(r: dict) -> dict:
    """Add domain field to a raw search result dict."""
    href = r.get("href", "") or r.get("url", "")
    domain = _extract_domain(href)
    return {
        "title": (r.get("title") or "").strip(),
        "href": href,
        "body": (r.get("body") or r.get("snippet") or "").strip(),
        "domain": domain,
    }


async def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Async DuckDuckGo search.
    Tries AsyncDDGS (ddgs v9+) first, falls back to sync DDGS in thread pool,
    then falls back to httpx HTML scraping.
    """

    # ── Attempt 1: ddgs AsyncDDGS (native async) ─────────────────────────────
    try:
        from ddgs import AsyncDDGS  # type: ignore
        async with AsyncDDGS() as ddgs:
            raw = await ddgs.atext(query, max_results=max_results)
        if raw:
            results = [_enrich_result(r) for r in raw]
            print(f"[Search] ddgs AsyncDDGS returned {len(results)} results")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[Search] AsyncDDGS error: {e}")

    # ── Attempt 2: ddgs sync DDGS in thread pool ──────────────────────────────
    try:
        from ddgs import DDGS  # type: ignore

        def _sync():
            with DDGS() as d:
                return list(d.text(query, max_results=max_results))

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _sync)
        if raw:
            results = [_enrich_result(r) for r in raw]
            print(f"[Search] ddgs sync returned {len(results)} results")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[Search] ddgs sync error: {e}")

    # ── Attempt 3: httpx HTML scraping fallback ───────────────────────────────
    try:
        import httpx
        from html import unescape

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(headers=headers, timeout=12, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
            )
            resp.raise_for_status()
            html = resp.text

        # Parse title/url/snippet with regex
        title_pat = re.compile(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
        )
        snippet_pat = re.compile(
            r'class="result__snippet">(.*?)</a>', re.DOTALL
        )

        titles_urls = title_pat.findall(html)
        snippets_raw = snippet_pat.findall(html)

        results = []
        for i, (href, title_html) in enumerate(titles_urls[:max_results]):
            title = unescape(re.sub(r"<[^>]+>", "", title_html)).strip()
            snippet = unescape(re.sub(r"<[^>]+>", "", snippets_raw[i])).strip() if i < len(snippets_raw) else ""
            if title:
                results.append(_enrich_result({"title": title, "href": href, "body": snippet}))

        print(f"[Search] httpx fallback returned {len(results)} results")
        return results[:max_results]

    except Exception as e:
        print(f"[Search] httpx fallback error: {e}")

    print("[Search] All search methods failed, returning empty results")
    return []


def format_search_context(results: list[dict], query: str = "") -> str:
    """Format search results into a system context block for the AI prompt."""
    if not results:
        return ""

    header = f'## Web Search Results for: "{query}"\n\n' if query else "## Web Search Results\n\n"
    parts = [
        header,
        "The following information was retrieved live from the web. "
        "Use it as context to give an accurate, up-to-date answer and cite sources.\n\n",
    ]

    for i, r in enumerate(results, 1):
        title = r.get("title") or "Result"
        href = r.get("href", "")
        body = r.get("body", "")
        parts.append(f"[{i}] **{title}**")
        if href:
            parts.append(f"    URL: {href}")
        if body:
            parts.append(f"    {body}")
        parts.append("")

    return "\n".join(parts)


async def build_search_system_prompt(user_query: str) -> tuple[str, list[dict]]:
    """
    Search DuckDuckGo and return (system_prompt, sources_list).
    The sources list contains enriched result dicts.
    """
    print(f"[Search] Querying DuckDuckGo for: {user_query!r}")
    results = await search(user_query)
    print(f"[Search] Got {len(results)} results")

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
