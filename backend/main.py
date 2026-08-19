from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database.db import connect, disconnect
from routers.chats import router as chats_router
from routers.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB. Shutdown: disconnect."""
    await connect()
    yield
    await disconnect()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="InklingAI Backend",
        description="FastAPI backend for InklingAI chatbot — NVIDIA + MongoDB + DuckDuckGo",
        version="1.0.0",
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

    @app.get("/health")
    async def health():
        return {"status": "ok", "model": settings.nvidia_model}

    return app


app = create_app()
