from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KnowledgeChunkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Short descriptive title")
    content: str = Field(..., min_length=1, description="The knowledge text to store and embed")
    source: Optional[str] = Field(None, description="Optional URL or label for the source")
    category: Optional[str] = Field(None, description="Optional tag/category (e.g., 'faq', 'docs')")


class KnowledgeChunkOut(BaseModel):
    id: str
    title: str
    content: str
    source: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query to find relevant chunks")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class KnowledgeSearchResult(BaseModel):
    id: str
    title: str
    content: str
    source: Optional[str] = None
    category: Optional[str] = None
    score: float


class BulkKnowledgeCreate(BaseModel):
    chunks: list[KnowledgeChunkCreate] = Field(..., min_length=1, max_length=50)
