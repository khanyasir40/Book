import requests
from typing import Dict, Any, List, Optional
from functools import lru_cache

# Open Library APIs
SEARCH_URL = "https://openlibrary.org/search.json"
WORKS_URL = "https://openlibrary.org/works"
COVERS_URL = "https://covers.openlibrary.org/b/id"

def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Open Library data to our apps standard format.
    """
    # ID format: "/works/OL123W" -> "OL123W" (strip prefix if present, but usually we get key)
    key = item.get("key", "")
    item_id = key.split("/")[-1] if "/" in key else key
    
    title = item.get("title")
    
    # Authors
    author_names = item.get("author_name", [])
    if not author_names:
        # Sometimes authors is a list of dicts in works API
        authors_data = item.get("authors", [])
        if authors_data and isinstance(authors_data[0], dict):
            # We would need to fetch author names separately often, but search gives names
            pass 
        author_names = []
    
    # Description (Search API usually doesn't have it, Work API does)
    description = item.get("description", "")
    if isinstance(description, dict):
        description = description.get("value", "")
    if not description:
        # Fallback to first sentence if available
        first_sentence = item.get("first_sentence")
        if isinstance(first_sentence, list):
            description = first_sentence[0]
        elif isinstance(first_sentence, str):
            description = first_sentence
        else:
            description = "No description available."

    # Cover Image
    cover_i = item.get("cover_i")
    thumbnail = None
    if cover_i:
        thumbnail = f"{COVERS_URL}/{cover_i}-M.jpg"
    elif item.get("covers"):
        cover_id = item.get("covers")[0]
        thumbnail = f"{COVERS_URL}/{cover_id}-M.jpg"
        
    # Stats
    avg_rating = item.get("ratings_average")
    ratings_count = item.get("ratings_count")
    
    # Year
    publish_year = item.get("first_publish_year")
    if not publish_year and item.get("publish_date"):
        # Try to extract year from date string
        try:
            dates = item.get("publish_date")
            if isinstance(dates, list):
                pd = dates[0]
            else:
                pd = dates
            # Simple extraction strategy: find 4 digits
            import re
            match = re.search(r'\d{4}', str(pd))
            if match:
                publish_year = int(match.group(0))
        except:
            pass

    # Language
    languages = item.get("language", [])
    language = languages[0] if languages else "en"

    # Categories/Subjects
    subjects = item.get("subject", [])
    if not subjects and item.get("subjects"):
         subjects = item.get("subjects", [])
    
    return {
        "id": item_id,
        "title": title,
        "authors": author_names,
        "description": description,
        "thumbnail": thumbnail,
        "average_rating": avg_rating if avg_rating else 0.0,
        "ratings_count": ratings_count if ratings_count else 0,
        "language": language,
        "categories": subjects[:5], # Limit to 5 categories
        "published_year": publish_year,
        "page_count": item.get("number_of_pages_median", 0),
        "read_link": f"https://openlibrary.org{key}",
    }

@lru_cache(maxsize=500)
def _cached_search(query: str, author: str, genre: str, page: int = 1) -> List[Dict[str, Any]]:
    """Cached search request to Open Library"""
    params = {
        "limit": 40,
        "page": page,
        "fields": "key,title,author_name,cover_i,ratings_average,ratings_count,first_publish_year,language,subject,first_sentence,number_of_pages_median"
    }
    
    # Build query
    q_parts = []
    if query: q_parts.append(query)
    if author: q_parts.append(f"author:{author}")
    if genre: q_parts.append(f"subject:{genre}")
    
    if not q_parts:
        params["q"] = "bestsellers" # Fallback
    else:
        params["q"] = " ".join(q_parts)

    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            docs = data.get("docs", [])
            print(f"[OpenLibrary] Query: {params['q']} | Results: {len(docs)}")
            return [_normalize_item(d) for d in docs]
        else:
            print(f"[OpenLibrary] Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"[OpenLibrary] Exception: {e}")
    
    return []

def search_books(filters: Dict[str, Any], start_index: int = 0, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search books using Open Library API. 
    Notes: Open Library uses 'page' instead of 'startIndex'.
    We approximate page number from start_index.
    """
    query = (filters.get("query") or "").strip()
    author = (filters.get("author") or "").strip()
    genre = (filters.get("genre") or "").strip()
    
    # Calculate page number (assuming 40 items per page request inside _cached_search)
    # Open Library uses 1-based indexing for pages
    page = (start_index // 40) + 1
    
    return _cached_search(query, author, genre, page)

def get_book_details(book_id: str) -> Optional[Dict[str, Any]]:
    """Fetch specific book details from Open Library Work API"""
    url = f"{WORKS_URL}/{book_id}.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # The work API doesn't give everything (like author names directly as strings), 
            # so we often have to rely on what we got from search. 
            # But for details page, we might want the full description.
            
            # For author names, it gives /authors/OLxxx. We'd have to fetch them.
            # to remain fast, we might skip fetching author details if not strictly necessary 
            # or rely on the fact that the frontend might pass search data.
            # However, to be robust:
            data['key'] = f"/works/{book_id}"
            
            # Fetch authors if needed? (Skipping for speed for now, or just mapping ids)
            # A better approach for details might be to assume the main info is normalized
            return _normalize_item(data)
    except Exception as e:
        print(f"[OpenLibrary] Details Exception: {e}")
    return None
