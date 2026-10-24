from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Cookie, Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash

from config import get_settings
from database.db import get_db


COOKIE_NAME = "m00_session"
ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(password, hashed)
    except Exception:
        return False


def create_session_token(user_id: str, remember: bool = False) -> tuple[str, int]:
    settings = get_settings()
    seconds = 60 * 60 * (24 * 30 if remember else settings.auth_session_hours)
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(seconds=seconds)}
    return jwt.encode(payload, settings.auth_secret_key, algorithm=ALGORITHM), seconds


async def get_current_user(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
    if not session:
        raise unauthorized
    try:
        payload = jwt.decode(session, get_settings().auth_secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise unauthorized
        oid = ObjectId(user_id)
    except (InvalidTokenError, InvalidId, ValueError, TypeError):
        raise unauthorized
    user = await db["users"].find_one({"_id": oid, "disabled": {"$ne": True}})
    if not user:
        raise unauthorized
    return user
