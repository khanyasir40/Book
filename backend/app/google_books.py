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
    Search for books with multi-stage fallback for guaranteed results.
    """
    def perform_query(q_str: str, lang: str = None) -> List[Dict[str, Any]]:
        # Aggressively exclude non-book content
        negative_filters = [
            'report', 'annual', 'white paper', 'technical', 'survey', 
            'manual', 'handbook', 'standards', 'statutes', 'proceedings'
        ]
        
        clean_q = q_str
        for nf in negative_filters:
            if nf not in q_str.lower():
                clean_q += f' -intitle:"{nf}"'
        
        p = {
            "q": clean_q,
            "startIndex": start_index,
            "maxResults": min(max_results, 40),
            "orderBy": "relevance",
            "printType": "books",
        }
        if lang: p["langRestrict"] = lang
        if API_KEY: p["key"] = API_KEY
        
        try:
            r = requests.get(BASE_URL, params=p, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return [_normalize_item(i) for i in (data.get("items") or [])]
        except Exception:
            pass
        return []

    query = (filters.get("query") or "").strip()
    author = (filters.get("author") or "").strip()
    genre = (filters.get("genre") or "").strip()
    language = filters.get("language")

    # Strategy 1: All filters combined (Strict)
    q_parts = []
    if query: q_parts.append(query)
    
    # Map of short language codes to names to boost results
    lang_names = {"ur": "Urdu", "hi": "Hindi", "ar": "Arabic", "es": "Spanish", "fr": "French"}
    lang_name = lang_names.get(language)
    if lang_name: q_parts.append(lang_name)

    if author: q_parts.append(f"inauthor:{author}")
    if genre:
        # Treat all genres as keywords first for better discovery in combos
        q_parts.append(genre)
    
    final_query = " ".join(q_parts) if q_parts else "best books"
    items = perform_query(final_query, language)
    
    # Strategy 2: If no results, relax 'inauthor:' and 'subject:' prefixes
    if not items and (genre or author):
        relaxed_q = query
        if genre: relaxed_q += f" {genre}"
        if author: relaxed_q += f" {author}"
        items = perform_query(relaxed_q.strip(), language)
        
    # Strategy 3: Extreme fallback - just use keywords individually
    if not items:
        # Try words from the query if it's long, or just a very broad search
        fallback_terms = query.split() if len(query.split()) > 1 else [query, genre, author]
        extreme_q = " ".join([t for t in fallback_terms if t])
        if not extreme_q.strip():
            extreme_q = "best sellers"
        items = perform_query(extreme_q, language)

    return items



def get_book_details(book_id: str) -> Optional[Dict[str, Any]]:
    params = {"key": API_KEY} if API_KEY else {}
    resp = requests.get(f"{BASE_URL}/{book_id}", params=params, timeout=15)
    if resp.status_code != 200:
        return None
    return _normalize_item(resp.json())