"""
Web Scraping Service using Playwright + GitHub API.

URL types handled:
  - GitHub repos / files / dirs  → GitHub REST API (structured, fast, no auth needed)
  - Regular webpages             → Playwright (Chromium, headless)
  - Direct text/code URLs        → httpx (lightweight fallback)

Scraped content is returned as a ScrapedPage dict and injected into the
system prompt as URL context for the AI to answer questions about.
"""

import re
import asyncio
import base64
from urllib.parse import urlparse
from typing import Optional

import httpx

from config import get_settings

# ─── Types ────────────────────────────────────────────────────────────────────

class ScrapedPage:
    def __init__(
        self,
        url: str,
        title: str,
        content: str,
        page_type: str = "webpage",
        metadata: Optional[dict] = None,
    ):
        self.url = url
        self.title = title
        self.content = content
        self.page_type = page_type       # "webpage" | "github_repo" | "github_file" | "github_dir"
        self.metadata = metadata or {}
        self.internal_links = []

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "page_type": self.page_type,
            "metadata": self.metadata,
            "internal_links": self.internal_links,
            "char_count": len(self.content),
        }


# ─── GitHub URL detection ──────────────────────────────────────────────────────

GITHUB_REPO_RE    = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
GITHUB_FILE_RE    = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$")
GITHUB_DIR_RE     = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)$")
GITHUB_ROOT_RE    = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:/.*)?$")


def _is_github(url: str) -> bool:
    return "github.com" in url


def _parse_github_url(url: str) -> dict:
    """Return info dict about a GitHub URL."""
    m = GITHUB_REPO_RE.match(url)
    if m:
        return {"kind": "repo", "owner": m.group(1), "repo": m.group(2)}
    m = GITHUB_FILE_RE.match(url)
    if m:
        return {"kind": "file", "owner": m.group(1), "repo": m.group(2), "ref": m.group(3), "path": m.group(4)}
    m = GITHUB_DIR_RE.match(url)
    if m:
        return {"kind": "dir", "owner": m.group(1), "repo": m.group(2), "ref": m.group(3), "path": m.group(4)}
    m = GITHUB_ROOT_RE.match(url)
    if m:
        return {"kind": "repo", "owner": m.group(1), "repo": m.group(2).split("/")[0]}
    return {"kind": "unknown"}


# ─── GitHub API scraper ────────────────────────────────────────────────────────

GH_API = "https://api.github.com"
COMMON_FILES = ["README.md", "README.rst", "README.txt", "README",
                "package.json", "requirements.txt", "pyproject.toml",
                "Cargo.toml", "go.mod", "setup.py", "setup.cfg",
                "CONTRIBUTING.md", "LICENSE"]


async def _gh_get(client: httpx.AsyncClient, path: str) -> dict | list | None:
    """Make a GitHub API request. Returns None on error."""
    try:
        r = await client.get(f"{GH_API}{path}", timeout=15,
                             headers={"Accept": "application/vnd.github+json",
                                      "X-GitHub-Api-Version": "2022-11-28"})
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Scraper] GitHub API error for {path}: {e}")
    return None


async def scrape_github(url: str, max_chars: int = 12000) -> ScrapedPage:
    """Scrape a GitHub URL using the GitHub REST API."""
    info = _parse_github_url(url)
    owner = info.get("owner", "")
    repo  = info.get("repo", "")
    kind  = info.get("kind", "unknown")

    async with httpx.AsyncClient() as client:

        # ── Specific file ────────────────────────────────────────────────────
        if kind == "file":
            path = info.get("path", "")
            ref  = info.get("ref", "main")
            data = await _gh_get(client, f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
            if data and isinstance(data, dict) and data.get("content"):
                try:
                    decoded = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                    return ScrapedPage(
                        url=url, title=f"{owner}/{repo}: {path}",
                        content=decoded[:max_chars],
                        page_type="github_file",
                        metadata={"owner": owner, "repo": repo, "path": path, "ref": ref},
                    )
                except Exception:
                    pass

        # ── Directory listing ───────────────────────────────────────────────
        if kind == "dir":
            path = info.get("path", "")
            ref  = info.get("ref", "main")
            data = await _gh_get(client, f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
            if data and isinstance(data, list):
                entries = "\n".join(
                    f"{'[DIR] ' if e['type']=='dir' else '[FILE]'} {e['name']}"
                    for e in data[:80]
                )
                return ScrapedPage(
                    url=url, title=f"{owner}/{repo}/{path} (directory)",
                    content=f"Directory listing for /{path}:\n\n{entries}",
                    page_type="github_dir",
                    metadata={"owner": owner, "repo": repo, "path": path},
                )

        # ── Full repo ─────────────────────────────────────────────────────
        # 1. Repo metadata
        repo_data = await _gh_get(client, f"/repos/{owner}/{repo}")
        # 2. README
        readme_data = await _gh_get(client, f"/repos/{owner}/{repo}/readme")
        # 3. File tree (top-level)
        tree_data = await _gh_get(client, f"/repos/{owner}/{repo}/contents")

        parts: list[str] = []

        if repo_data and isinstance(repo_data, dict):
            parts.append(f"# {repo_data.get('full_name', f'{owner}/{repo}')}")
            if repo_data.get("description"):
                parts.append(f"**Description:** {repo_data['description']}")
            lang = repo_data.get("language")
            stars = repo_data.get("stargazers_count", 0)
            forks = repo_data.get("forks_count", 0)
            topics = ", ".join(repo_data.get("topics", []))
            parts.append(f"**Language:** {lang} | **Stars:** {stars:,} | **Forks:** {forks:,}")
            if topics:
                parts.append(f"**Topics:** {topics}")
            parts.append("")

        if tree_data and isinstance(tree_data, list):
            file_names = [e["name"] for e in tree_data[:60]]
            parts.append("## Repository Files (top-level)\n" + "\n".join(f"- {f}" for f in file_names))
            parts.append("")

        if readme_data and isinstance(readme_data, dict) and readme_data.get("content"):
            try:
                readme_text = base64.b64decode(readme_data["content"]).decode("utf-8", errors="replace")
                parts.append("## README\n")
                parts.append(readme_text[:6000])
            except Exception:
                pass

        title = f"{owner}/{repo}" + (f" — {repo_data.get('description','')}" if repo_data and repo_data.get("description") else "")
        content = "\n".join(parts)[:max_chars]

        return ScrapedPage(
            url=url, title=title, content=content,
            page_type="github_repo",
            metadata={"owner": owner, "repo": repo,
                      "stars": repo_data.get("stargazers_count") if repo_data else None,
                      "language": repo_data.get("language") if repo_data else None},
        )


# ─── Playwright web scraper ────────────────────────────────────────────────────

_JS_EXTRACT = """
() => {
    // Remove noise elements
    ['script','style','noscript','nav','footer','header','aside',
     '[role="navigation"]','[role="banner"]','[role="complementary"]',
     '.cookie-banner','.ad','.advertisement','#cookie','.popup'
    ].forEach(sel => {
        try { document.querySelectorAll(sel).forEach(el => el.remove()); } catch(_) {}
    });

    // Get page title
    const title = document.title || '';

    // Prefer article/main content areas
    const selectors = [
        'article', 'main', '[role="main"]',
        '.post-content','.entry-content','.article-content',
        '.markdown-body','.prose','#content','.content',
        '#main','.main-content','.page-content',
    ];
    let mainEl = null;
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 200) { mainEl = el; break; }
    }
    const text = (mainEl || document.body).innerText.trim();

    // Extract links
    const internalLinks = [];
    const seenUrls = new Set();
    const currentDomain = window.location.hostname;
    
    document.querySelectorAll('a[href]').forEach(a => {
        try {
            const href = a.href;
            const text = a.innerText.trim();
            if (href && text && text.length > 2 && text.length < 50) {
                const urlObj = new URL(href);
                // Only keep internal links to same domain, ignoring hashes/mailtos
                if (urlObj.hostname === currentDomain && !href.includes('#') && urlObj.protocol.startsWith('http')) {
                    const cleanUrl = urlObj.origin + urlObj.pathname + urlObj.search;
                    if (!seenUrls.has(cleanUrl)) {
                        seenUrls.add(cleanUrl);
                        internalLinks.push({ text: text, href: cleanUrl });
                    }
                }
            }
        } catch(_) {}
    });

    return { title, text, internalLinks: internalLinks.slice(0, 50) };
}
"""


def _run_playwright_sync(url: str, max_chars: int) -> dict:
    """Run playwright in a new event loop on a separate thread to avoid Windows SelectorEventLoop issues."""
    import asyncio
    import sys
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def _do_scrape():
        from playwright.async_api import async_playwright
        title = url
        content = ""
        internal_links = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    ctx = await browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1280, "height": 900},
                    )
                    page = await ctx.new_page()
                    # Block images/fonts/media to speed up
                    await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot,mp4,mp3}",
                                     lambda r: r.abort())
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)   # allow JS to settle

                    result = await page.evaluate(_JS_EXTRACT)
                    title = result.get("title") or url
                    content = result.get("text", "")[:max_chars]
                    internal_links = result.get("internalLinks", [])
                finally:
                    await browser.close()
        except Exception as e:
            print(f"[Scraper] Playwright error scraping {url}: {e}")
            content = f"[Scraping failed: {e}]"
            
        return {"title": title, "content": content, "internal_links": internal_links}

    return asyncio.run(_do_scrape())


async def scrape_with_playwright(url: str, max_chars: int = 10000) -> ScrapedPage:
    """Scrape a webpage using Playwright's headless Chromium in a safe thread."""
    import asyncio
    
    result = await asyncio.to_thread(_run_playwright_sync, url, max_chars)
    
    page = ScrapedPage(url=url, title=result["title"], content=result["content"], page_type="webpage")
    page.internal_links = result["internal_links"]
    return page


# ─── httpx fast-path ──────────────────────────────────────────────────────────

async def _scrape_with_httpx(url: str, max_chars: int = 10000) -> ScrapedPage | None:
    """
    Fast fallback: fetch plain HTML and extract text using BeautifulSoup.
    Returns None if the response is not parseable text/html.
    """
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        headers = {"User-Agent": "Mozilla/5.0 (compatible; M00Bot/1.0)"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            r = await client.get(url, headers=headers)
            content_type = r.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return None

        soup = BeautifulSoup(r.text, "lxml")
        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        # Prefer main content areas
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"content|main|article", re.I))
            or soup.body
        )
        text = main.get_text(separator="\n", strip=True) if main else ""
        text = re.sub(r"\n{3,}", "\n\n", text)

        if len(text) < 100:
            return None   # not enough content → fall through to Playwright

        # Extract links
        internal_links = []
        seen_urls = set()
        base_domain = urlparse(url).netloc
        
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            link_text = a.get_text(strip=True)
            if href and link_text and 2 < len(link_text) < 50:
                full_url = urljoin(url, href)
                parsed_full = urlparse(full_url)
                if parsed_full.netloc == base_domain and not full_url.endswith("#") and parsed_full.scheme.startswith("http"):
                    clean_url = f"{parsed_full.scheme}://{parsed_full.netloc}{parsed_full.path}"
                    if parsed_full.query:
                        clean_url += f"?{parsed_full.query}"
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        internal_links.append({"text": link_text, "href": clean_url})
                        if len(internal_links) >= 50:
                            break

        page = ScrapedPage(url=url, title=title, content=text[:max_chars], page_type="webpage")
        page.internal_links = internal_links
        return page

    except Exception as e:
        print(f"[Scraper] httpx fallback error for {url}: {e}")
        return None


# ─── Public entry point ───────────────────────────────────────────────────────

async def scrape(url: str, max_chars: int = 10000) -> ScrapedPage:
    """
    Scrape a URL and return a ScrapedPage.

    Routing:
      - github.com/*   → GitHub API (structured, fast, no auth)
      - other URLs     → httpx fast-path → Playwright (JS-heavy fallback)
    """
    print(f"[Scraper] Scraping: {url}")

    if _is_github(url):
        page = await scrape_github(url, max_chars=max_chars)
        print(f"[Scraper] GitHub: {page.title[:60]}")
        return page

    # Try fast httpx path first
    page = await _scrape_with_httpx(url, max_chars=max_chars)
    if page and len(page.content) >= 100:
        print(f"[Scraper] httpx OK: {page.title[:60]}")
        return page

    # Full Playwright path
    print(f"[Scraper] Falling back to Playwright for: {url}")
    page = await scrape_with_playwright(url, max_chars=max_chars)
    print(f"[Scraper] Playwright: {page.title[:60]}")
    return page


# ─── Context formatter for system prompt ─────────────────────────────────────

def format_url_context(pages: list[dict]) -> str:
    """Format scraped pages into a system prompt context block."""
    if not pages:
        return ""

    lines = [
        "## Scraped URL Contexts\n",
        "The following content was scraped live from user-provided URLs. "
        "Use it to accurately answer the user's questions about these sources.\n",
    ]

    for i, page in enumerate(pages, 1):
        title = page.get("title", page.get("url", f"Source {i}"))
        url = page.get("url", "")
        page_type = page.get("page_type", "webpage")
        content = page.get("content", "")
        lines.append(f"\n### [{i}] {title}")
        lines.append(f"URL: {url}  (type: {page_type})")
        lines.append("```")
        lines.append(content[:8000])
        lines.append("```")

    return "\n".join(lines)
