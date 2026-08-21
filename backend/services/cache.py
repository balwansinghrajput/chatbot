"""
Redis cache service for M00 chatbot.

Provides a singleton async Redis client with:
  - get / set / delete helpers
  - A simple cached() decorator for async functions
  - JSON serialization for structured data
  - Graceful degradation: if Redis is unreachable, functions run without caching

TTL constants (seconds):
  INTENT_TTL      = 3600   (1 hr)   — intent routing is deterministic per query
  SEARCH_TTL      = 600    (10 min) — web search results
  IMAGE_TTL       = 1800   (30 min) — image search results
  SCRAPE_TTL      = 3600   (1 hr)   — scraped page content
  RAG_TTL         = 300    (5 min)  — RAG chunk retrieval
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Awaitable, TypeVar

import redis.asyncio as aioredis
from config import get_settings

logger = logging.getLogger(__name__)

# ─── TTL constants ────────────────────────────────────────────────────────────

INTENT_TTL  = 3_600   # 1 hour
SEARCH_TTL  =   600   # 10 minutes
IMAGE_TTL   = 1_800   # 30 minutes
SCRAPE_TTL  = 3_600   # 1 hour
RAG_TTL     =   300   # 5 minutes

# ─── Singleton client ──────────────────────────────────────────────────────────

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Connect to Redis at startup. Called from FastAPI lifespan."""
    global _redis
    settings = get_settings()
    url = settings.redis_url
    if not url:
        logger.warning("[Cache] REDIS_URL not set — caching disabled.")
        return
    try:
        _redis = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=3,
            health_check_interval=30,
        )
        await _redis.ping()
        logger.info("[Cache] Redis connected: %s", url.split("@")[-1])
        print(f"[Cache] Redis connected: {url.split('@')[-1]}")
    except Exception as e:
        logger.error("[Cache] Redis connection failed: %s — caching disabled.", e)
        print(f"[Cache] Redis connection failed: {e} — caching disabled.")
        _redis = None


async def close_redis() -> None:
    """Disconnect from Redis at shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        print("[Cache] Redis disconnected.")


def get_redis() -> aioredis.Redis | None:
    """Return the live Redis client, or None if unavailable."""
    return _redis


# ─── Low-level helpers ─────────────────────────────────────────────────────────

def _make_key(namespace: str, raw: str) -> str:
    """Create a namespaced, safe cache key from arbitrary input."""
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"m00:{namespace}:{digest}"


async def cache_get(namespace: str, key_raw: str) -> Any | None:
    """Retrieve a JSON-decoded value from cache, or None on miss/error."""
    r = get_redis()
    if r is None:
        return None
    try:
        key = _make_key(namespace, key_raw)
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("[Cache] get error (%s): %s", namespace, e)
        return None


async def cache_set(namespace: str, key_raw: str, value: Any, ttl: int) -> None:
    """JSON-encode and store a value in cache with the given TTL (seconds)."""
    r = get_redis()
    if r is None:
        return
    try:
        key = _make_key(namespace, key_raw)
        await r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception as e:
        logger.debug("[Cache] set error (%s): %s", namespace, e)


async def cache_delete(namespace: str, key_raw: str) -> None:
    """Remove a key from cache."""
    r = get_redis()
    if r is None:
        return
    try:
        await r.delete(_make_key(namespace, key_raw))
    except Exception as e:
        logger.debug("[Cache] delete error (%s): %s", namespace, e)


# ─── Decorator ────────────────────────────────────────────────────────────────

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def cached(namespace: str, ttl: int, key_fn: Callable[..., str] | None = None):
    """
    Async cache decorator.

    Usage:
        @cached("search", ttl=SEARCH_TTL, key_fn=lambda q, **_: q)
        async def search(query: str, max_results: int = 5) -> list[dict]: ...

    `key_fn` receives the same positional + keyword args as the wrapped function
    and must return a string used as the cache key.  If omitted, all args are
    joined into a string.
    """
    def decorator(fn: F) -> F:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            if key_fn is not None:
                raw_key = key_fn(*args, **kwargs)
            else:
                raw_key = str(args) + str(sorted(kwargs.items()))

            hit = await cache_get(namespace, raw_key)
            if hit is not None:
                print(f"[Cache] HIT  {namespace}:{raw_key[:60]!r}")
                return hit

            print(f"[Cache] MISS {namespace}:{raw_key[:60]!r}")
            result = await fn(*args, **kwargs)
            if result:  # only cache non-empty results
                await cache_set(namespace, raw_key, result, ttl)
            return result

        return wrapper  # type: ignore
    return decorator
