import os
import math
import requests
from typing import Dict, Any, List, Optional

API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
BASE_URL = "https://www.googleapis.com/books/v1/volumes"


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    vi = item.get("volumeInfo", {})
    title = vi.get("title")
    authors = vi.get("authors", [])
    description = vi.get("description")
    image_links = vi.get("imageLinks", {})
    thumbnail = image_links.get("thumbnail")
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
        "id": item.get("id"),
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
    Search for books using Google Books API with comprehensive filter support.
    Combines all filters into a single optimized query for better results.
    """
    q_parts: List[str] = []
    
    # Main search query
    query = filters.get("query")
    if query:
        q_parts.append(query)
    
    # Author filter
    author = filters.get("author")
    if author:
        q_parts.append(f"inauthor:{author}")
    
    # Genre/Subject filter
    genre = filters.get("genre")
    if genre:
        q_parts.append(f"subject:{genre}")
    
    # Year filter
    year = filters.get("year")
    if year:
        try:
            year_int = int(year)
            # Search for books published in that specific year
            q_parts.append(f"publishedDate:{year_int}")
        except (ValueError, TypeError):
            pass
    
    # Reading level filter (maps to subject categories)
    reading_level = filters.get("reading_level")
    if reading_level:
        level_mapping = {
            "beginner": "juvenile",
            "intermediate": "young adult",
            "advanced": "adult"
        }
        mapped_level = level_mapping.get(reading_level.lower(), reading_level)
        q_parts.append(f"subject:{mapped_level}")
    
    # Build the final query string
    # If no filters are provided, search for generic "book"
    final_query = " ".join(q_parts) if q_parts else "book"
    
    params = {
        "q": final_query,
        "startIndex": start_index,
        "maxResults": min(max_results, 40),  # Google Books API max is 40
        "orderBy": "relevance",  # Sort by relevance for better results
    }
    
    # Language restriction
    language = filters.get("language")
    if language:
        params["langRestrict"] = language
    
    # Add API key if available
    if API_KEY:
        params["key"] = API_KEY
    
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return [_normalize_item(i) for i in items]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching books from Google Books API: {e}")
        return []



def get_book_details(book_id: str) -> Optional[Dict[str, Any]]:
    params = {"key": API_KEY} if API_KEY else {}
    resp = requests.get(f"{BASE_URL}/{book_id}", params=params, timeout=15)
    if resp.status_code != 200:
        return None
    return _normalize_item(resp.json())