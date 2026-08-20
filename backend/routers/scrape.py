"""
Scrape Router — /api/scrape

Accepts a URL and returns scraped content that the frontend can attach as
context to a conversation. Handles webpages and GitHub repos/files/dirs.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from services.scraper import scrape

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: str
    max_chars: int = 10000


class ScrapeResponse(BaseModel):
    url: str
    title: str
    content: str
    page_type: str
    metadata: dict = {}
    char_count: int


@router.post("", response_model=ScrapeResponse)
async def scrape_url(body: ScrapeRequest):
    """
    Scrape a URL and return its extracted text content.
    - GitHub repos/files/dirs → GitHub REST API (fast, structured)
    - Regular webpages → httpx fast-path → Playwright (JS-heavy fallback)
    """
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        page = await scrape(body.url, max_chars=body.max_chars)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraping failed: {e}")

    if not page.content or page.content.startswith("[Scraping failed"):
        raise HTTPException(status_code=422, detail="Could not extract content from this URL.")

    return ScrapeResponse(
        url=page.url,
        title=page.title,
        content=page.content,
        page_type=page.page_type,
        metadata=page.metadata,
        char_count=len(page.content),
    )
