from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["Software Engineer", "AI Researcher", "Founder / Lead"] | None = None
    accepted_terms: bool
    remember: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    remember: bool = False


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
