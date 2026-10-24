"""
LinkedIn Profile Finder service.

Strategy (no LinkedIn API key required):
  1. Use Brave/DuckDuckGo web search for  site:linkedin.com/in/ "Person Name"
     → returns the profile URL, headline, and a bio snippet from the SERP
  2. Search DuckDuckGo images for "Person Name" linkedin
     → grabs the best candidate profile photo
  3. Optionally attempt a lightweight HTTP scrape of the LinkedIn public profile
     page to extract more structured data (name, headline, location, company).
     LinkedIn blocks most scrapers, but public preview data sometimes slips through.

Returns a LinkedInProfile dict:
  {
    "name":        str,
    "headline":    str,
    "location":    str,
    "company":     str,
    "profile_url": str,
    "photo_url":   str,
    "snippet":     str,
    "connections": str,
  }
"""

import re
import asyncio
import httpx
from services.cache import cached, SEARCH_TTL


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def _ddg_web_search(query: str, max_results: int = 5) -> list[dict]:
    """Quick DDG text search fallback."""
    try:
        from ddgs import AsyncDDGS  # type: ignore
        async with AsyncDDGS() as d:
            raw = await d.atext(query, max_results=max_results)
        if raw:
            return [{"title": r.get("title",""), "href": r.get("href",""), "body": r.get("body","")} for r in raw]
    except Exception as e:
        print(f"[LinkedIn] AsyncDDGS text search error: {e}")
        
    try:
        from ddgs import DDGS  # type: ignore
        def _sync():
            with DDGS() as d:
                return list(d.text(query, max_results=max_results))
        raw = await asyncio.get_event_loop().run_in_executor(None, _sync)
        if raw:
            return [{"title": r.get("title",""), "href": r.get("href",""), "body": r.get("body","")} for r in raw]
    except Exception as e:
        print(f"[LinkedIn] Sync DDGS text search error: {e}")
        
    return []


async def _ddg_image_search(query: str, max_results: int = 5) -> list[dict]:
    """Quick DDG image search for profile photo."""
    try:
        from ddgs import AsyncDDGS  # type: ignore
        async with AsyncDDGS() as d:
            raw = await d.aimages(query, max_results=max_results, safesearch="moderate")
        if raw:
            return [{"url": r.get("image",""), "thumbnail": r.get("thumbnail","")} for r in raw if r.get("image")]
    except Exception:
        pass
    try:
        from ddgs import DDGS  # type: ignore
        def _sync():
            with DDGS() as d:
                return list(d.images(query, max_results=max_results, safesearch="moderate"))
        raw = await asyncio.get_event_loop().run_in_executor(None, _sync)
        if raw:
            return [{"url": r.get("image",""), "thumbnail": r.get("thumbnail","")} for r in raw if r.get("image")]
    except Exception as e:
        print(f"[LinkedIn] DDG image search error: {e}")
    return []


def _extract_profile_url(results: list[dict]) -> str | None:
    """Find the first linkedin.com/in/ URL from search results."""
    for r in results:
        href = r.get("href", "")
        if "linkedin.com/in/" in href:
            # Normalize: strip query params / trailing slashes
            m = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_%-]+)", href)
            if m:
                return m.group(1).rstrip("/")
    return None


def _extract_name_from_title(title: str, query_name: str) -> str:
    """Try to extract the canonical name from the SERP title."""
    # LinkedIn SERP titles look like: "John Doe - Software Engineer at Google | LinkedIn"
    if " - " in title:
        candidate = title.split(" - ")[0].strip()
        if candidate and len(candidate) < 60:
            return candidate
    if " | LinkedIn" in title:
        candidate = title.split(" | LinkedIn")[0].strip()
        if " - " in candidate:
            candidate = candidate.split(" - ")[0].strip()
        if candidate and len(candidate) < 60:
            return candidate
    return query_name


def _extract_headline_from_title(title: str) -> str:
    """Extract headline/role from SERP title."""
    # "John Doe - Software Engineer at Google | LinkedIn"
    # "Jane Smith – Head of Product at Stripe | LinkedIn"
    for sep in [" - ", " – ", " | "]:
        parts = title.split(sep)
        if len(parts) >= 2:
            headline = parts[1].strip()
            # Remove trailing " | LinkedIn" etc.
            headline = re.sub(r"\s*\|.*$", "", headline).strip()
            if headline and len(headline) < 150:
                return headline
    return ""


async def _try_scrape_public_page(profile_url: str) -> dict:
    """
    Attempt a scrape of a LinkedIn public profile page using joeyism/linkedin_scraper.
    Requires a valid linkedin_session.json in the backend directory.
    """
    import os
    from linkedin_scraper.scrapers.person import PersonScraper
    from linkedin_scraper.core.browser import BrowserManager
    from linkedin_scraper.core.exceptions import AuthenticationError

    data = {}
    session_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "linkedin_session.json")
    
    if not os.path.exists(session_file):
        print(f"[LinkedIn] No session file found at {session_file}. Please run samples/create_session.py to generate one.")
        return data

    try:
        async with BrowserManager(headless=True) as browser:
            await browser.load_session(session_file)
            scraper = PersonScraper(browser.page)
            person = await scraper.scrape(profile_url)
            
            # Map Pydantic model to our dictionary format
            if person:
                data["og_name"] = person.name
                data["og_headline"] = person.headline
                data["snippet"] = person.about
                # It may be stored as photo or image, let's try both
                data["photo_url"] = getattr(person, 'photo', getattr(person, 'profile_pic_url', ''))
                
                # We can also get location, company, etc. if available
                data["location"] = getattr(person, 'location', '')
                if hasattr(person, 'experiences') and person.experiences:
                    data["company"] = person.experiences[0].company_name
    except AuthenticationError:
        print("[LinkedIn] linkedin_scraper Authentication Error: Not logged in or session expired.")
    except Exception as e:
        print(f"[LinkedIn] Profile scrape failed: {e}")
        
    return data


# ─── Public entry point ───────────────────────────────────────────────────────

@cached("linkedin", ttl=SEARCH_TTL * 6, key_fn=lambda name: name.lower().strip())
async def find_linkedin_profile(name: str) -> dict | None:
    """
    Find a LinkedIn profile for the given person name.

    Returns a dict with keys:
      name, headline, location, company, profile_url, photo_url, snippet
    or None if no profile was found.
    """
    print(f"[LinkedIn] Searching for profile: {name!r}")

    # ── Step 1: Web search for LinkedIn profile URL ───────────────────────────
    is_url = "linkedin.com/in/" in name
    web_results = []
    profile_url = None
    
    if is_url:
        m = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_%-]+)", name)
        if m:
            profile_url = m.group(1).rstrip("/")
            print(f"[LinkedIn] Direct URL provided: {profile_url}")
    
    if not profile_url:
        from services.search import search as robust_search
        search_query = f'site:linkedin.com/in/ "{name}"'
        web_results = await robust_search(search_query, max_results=5)
    
        if not web_results:
            web_results = await robust_search(f"{name} linkedin profile", max_results=5)
    
        profile_url = _extract_profile_url(web_results)
        print(f"[LinkedIn] Profile URL from search: {profile_url}")

    # ── Step 2: Extract info from SERP snippet ────────────────────────────────
    name_from_title = name
    headline = ""
    snippet  = ""

    for r in web_results:
        if "linkedin.com/in/" in r.get("href", ""):
            name_from_title = _extract_name_from_title(r.get("title", ""), name if not is_url else "")
            headline        = _extract_headline_from_title(r.get("title", ""))
            snippet         = _clean(r.get("body", ""))
            break

    # ── Step 3: Attempt lightweight scrape of public page ────────────────────
    scraped: dict = {}
    if profile_url:
        scraped = await _try_scrape_public_page(profile_url)

    # ── Step 4: Image search for profile photo ────────────────────────────────
    photo_url = scraped.get("photo_url", "")
    if not photo_url:
        image_query = f'{name} linkedin profile photo'
        img_results = await _ddg_image_search(image_query, max_results=8)
        # Filter for likely profile photos (square-ish, not banners)
        for img in img_results:
            url = img.get("url", "")
            if url and ("linkedin" in url or "licdn" in url or "media.licdn" in url):
                photo_url = url
                break
        # If no LinkedIn-hosted image, use the first result
        if not photo_url and img_results:
            photo_url = img_results[0].get("url", "")

    # ── Step 5: Merge and return ──────────────────────────────────────────────
    final_name     = scraped.get("og_name") or name_from_title or name
    final_headline = scraped.get("og_headline") or headline
    final_snippet  = scraped.get("snippet") or snippet

    if not profile_url:
        print(f"[LinkedIn] No profile URL found for {name!r}")
        return None

    result = {
        "name":        final_name,
        "headline":    final_headline,
        "snippet":     final_snippet,
        "profile_url": profile_url,
        "photo_url":   photo_url,
        "location":    "",   # requires deeper scrape / API
        "company":     "",
    }
    print(f"[LinkedIn] Result: {result['name']} | {result['headline'][:60]}")
    return result
