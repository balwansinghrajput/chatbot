from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.db_name]


async def connect():
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    # Verify connection
    await _client.admin.command("ping")
    print(f"[DB] Connected to MongoDB at {settings.mongodb_uri}")


async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
        print("[DB] Disconnected from MongoDB")
