from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from config import get_settings
from database.db import get_db
from models.auth import AuthResponse, LoginRequest, SignupRequest, UserOut
from services.auth import COOKIE_NAME, create_session_token, get_current_user, hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: dict) -> UserOut:
    return UserOut(
        id=str(user["_id"]), name=user["name"], email=user["email"],
        role=user.get("role"), created_at=user["created_at"],
    )


def _set_cookie(response: Response, token: str, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME, value=token, max_age=max_age, httponly=True,
        secure=settings.auth_cookie_secure, samesite="lax", path="/",
    )


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(body: SignupRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not body.accepted_terms:
        raise HTTPException(status_code=400, detail="Terms must be accepted")
    now = datetime.now(timezone.utc)
    user = {
        "name": body.name.strip(), "email": str(body.email).lower(),
        "password_hash": hash_password(body.password), "role": body.role,
        "accepted_terms_at": now, "created_at": now, "updated_at": now,
    }
    try:
        result = await db["users"].insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user["_id"] = result.inserted_id
    token, max_age = create_session_token(str(result.inserted_id), body.remember)
    _set_cookie(response, token, max_age)
    return AuthResponse(user=_user_out(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db["users"].find_one({"email": str(body.email).lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token, max_age = create_session_token(str(user["_id"]), body.remember)
    _set_cookie(response, token, max_age)
    return AuthResponse(user=_user_out(user))


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


@router.get("/me", response_model=AuthResponse)
async def me(user: dict = Depends(get_current_user)):
    return AuthResponse(user=_user_out(user))
