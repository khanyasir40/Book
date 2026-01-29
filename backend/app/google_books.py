import os
import math
import requests
from typing import Dict, Any, List, Optional

API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
BASE_URL = "https://www.googleapis.com/books/v1/volumes"


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    vi = item.get("volumeInfo", {})
    item_id = item.get("id")
    title = vi.get("title")
    authors = vi.get("authors", [])
    description = vi.get("description")
    image_links = vi.get("imageLinks", {})
    
    # Use official image links if available
    thumbnail = image_links.get("thumbnail") or image_links.get("smallThumbnail")
        
    avg_rating = vi.get("averageRating")
    ratings_count = vi.get("ratingsCount")
    language = vi.get("language")
    categories = vi.get("categories", [])
    published_date = vi.get("publishedDate", "")
    year = None
    if isinstance(published_date, str) and len(published_date) >= 4:
        try:
            year = int(published_date[:4])
        except Exception:
            year = None
    page_count = vi.get("pageCount")
    
    access_info = item.get("accessInfo", {})
    read_link = access_info.get("webReaderLink")
    if not read_link:
        read_link = vi.get("previewLink")

    return {
        "id": item_id,
        "title": title,
        "authors": authors,
        "description": description,
        "thumbnail": thumbnail,
        "average_rating": avg_rating,
        "ratings_count": ratings_count,
        "language": language,
        "categories": categories,
        "published_year": year,
        "page_count": page_count,
        "read_link": read_link,
    }


def search_books(filters: Dict[str, Any], start_index: int = 0, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search for books with multi-stage fallback and FUZZY MATCHING support.
    """

# In-memory cache to prevent 429 Quota Exceeded errors
# Key: (query_string, language, start_index) -> Value: List[Dict]
from functools import lru_cache
import time

@lru_cache(maxsize=500)
def _cached_api_call(query: str, lang: str, start_index: int) -> List[Dict[str, Any]]:
    """Cached wrapper for Google Books API calls"""
    p = {
        "q": query,
        "startIndex": start_index,
        "maxResults": 40,  # Always fetch max to be efficient
        "orderBy": "relevance",
        "printType": "books",
    }
    if lang: p["langRestrict"] = lang
    if API_KEY: p["key"] = API_KEY
    
    try:
        r = requests.get(BASE_URL, params=p, timeout=10)
        
        # Handle Rate Limiting (429) gracefully
        if r.status_code == 429:
            print(f"[Google Books API] QUOTA EXCEEDED (429). Returning empty.")
            return []
            
        if r.status_code == 200:
            data = r.json()
            items = [_normalize_item(i) for i in (data.get("items") or [])]
            print(f"[Google Books API] Query: {query[:100]}... | Results: {len(items)}")
            return items
        else:
            print(f"[Google Books API] Error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[Google Books API] Exception: {str(e)[:200]}")
    return []

def search_books(filters: Dict[str, Any], start_index: int = 0, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search for books with multi-stage fallback and FUZZY MATCHING support.
    """
    # Initialize items to empty list to prevent UnboundLocalError
    items = []

    def perform_query(q_str: str, lang: str = None) -> List[Dict[str, Any]]:
        # SIMPLIFIED negative filters - only block obvious junk
        negative_filters = [
            'annual report',
            'proceedings',
            'white paper',
            'technical manual',
            'audiobook'
        ]
        
        clean_q = q_str
        # Only add negative filters if they're not part of the search query
        for nf in negative_filters:
            if nf.lower() not in q_str.lower():
                clean_q += f' -intitle:"{nf}"'
        
        # Use cached API call
        return _cached_api_call(clean_q, lang, start_index)

    query = (filters.get("query") or "").strip()
    author = (filters.get("author") or "").strip()
    genre = (filters.get("genre") or "").strip()
    language = filters.get("language")

    # Strategy 1: Exact match with all filters
    q_parts = []
    if query: q_parts.append(query)
    if author: q_parts.append(f"inauthor:{author}")
    if genre: q_parts.append(f"subject:{genre}")
    
    if q_parts:
        final_query = " ".join(q_parts)
        items = perform_query(final_query, language)
        if items:
            print(f"[Strategy 1] Found {len(items)} books with exact match")
            return items
    
    # Strategy 2: FUZZY MATCHING - Split multi-word queries
    if not items and query and len(query.split()) > 1:
        words = [w for w in query.split() if len(w) > 2]  # Skip short words
        fuzzy_query = " OR ".join(words[:5])  # Limit to 5 words
        if genre: fuzzy_query += f" subject:{genre}"
        if author: fuzzy_query += f" inauthor:{author}"
        items = perform_query(fuzzy_query, language)
        if items:
            print(f"[Strategy 2] Found {len(items)} books with fuzzy match")
            return items
    
    # Strategy 3: Relax constraints - remove inauthor/subject prefixes
    if not items and (genre or author):
        relaxed_parts = []
        if query: relaxed_parts.append(query)
        if genre: relaxed_parts.append(genre)
        if author: relaxed_parts.append(author)
        relaxed_query = " ".join(relaxed_parts)
        items = perform_query(relaxed_query, language)
        if items:
            print(f"[Strategy 3] Found {len(items)} books with relaxed match")
            return items
        
    # Strategy 4: Very broad fallback
    if not items:
        if genre:
            items = perform_query(genre, language)
        elif query:
            # Try just the first word of the query
            first_word = query.split()[0] if query.split() else "bestseller"
            items = perform_query(first_word, language)
        else:
            items = perform_query("bestseller", language)
        
        if items:
            print(f"[Strategy 4] Found {len(items)} books with broad fallback")

    return items or []



def get_book_details(book_id: str) -> Optional[Dict[str, Any]]:
    params = {"key": API_KEY} if API_KEY else {}
    resp = requests.get(f"{BASE_URL}/{book_id}", params=params, timeout=15)
    if resp.status_code != 200:
        return None
    return _normalize_item(resp.json())