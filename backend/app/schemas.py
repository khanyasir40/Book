from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any


class UserCreate(BaseModel):
    email: str  # Remove EmailStr requirement to accept any email format
    name: str
    password: str  # Remove min_length requirement


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: str  # Remove EmailStr requirement to accept any email format
    password: str  # Remove min_length requirement


class FavoriteIn(BaseModel):
    book_id: str
    book_json: Dict[str, Any]


class FavoriteOut(BaseModel):
    id: int
    book_id: str
    book_json: Dict[str, Any]

    class Config:
        from_attributes = True


class SearchFilters(BaseModel):
    genre: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    year: Optional[int] = None
    mood: Optional[List[str]] = None
    reading_level: Optional[str] = None
    length: Optional[str] = None  # short, medium, long
    query: Optional[str] = None


class ScoredBook(BaseModel):
    id: str
    title: str
    authors: List[str]
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    average_rating: Optional[float] = None
    ratings_count: Optional[int] = None
    language: Optional[str] = None
    categories: Optional[List[str]] = None
    published_year: Optional[int] = None
    read_link: Optional[str] = None

    score: float
    confidence_pct: float
    reasons: List[str]


class SimilarBooksOut(BaseModel):
    items: List[ScoredBook]