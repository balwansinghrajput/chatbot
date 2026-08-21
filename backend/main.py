import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from config import get_settings
from database.db import connect, disconnect
from services.cache import init_redis, close_redis
from routers.chats import router as chats_router
from routers.stream import router as stream_router
from routers.knowledge import router as knowledge_router
from routers.scrape import router as scrape_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB + Redis. Shutdown: disconnect both."""
    await connect()
    await init_redis()
    yield
    await close_redis()
    await disconnect()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="M00 AI Backend",
        description="FastAPI backend for M00 chatbot — NVIDIA NIM + MongoDB Atlas + Brave/DDG Search + RAG",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS — allow the Vite dev server origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(chats_router)
    app.include_router(stream_router)
    app.include_router(knowledge_router)
    app.include_router(scrape_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "model": settings.nvidia_model}

    return app


app = create_app()
