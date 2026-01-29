from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..schemas import SearchFilters, ScoredBook, SimilarBooksOut
# Switch to Open Library for free unlimited API
from ..open_library import search_books, get_book_details
# from ..google_books import search_books, get_book_details
from ..curated_data import search_curated, curated_items_list
from ..recommendation import score_book
from ..models import SearchHistory, Preference
from ..auth import get_current_user, get_current_user_optional
import json

router = APIRouter()


import random

@router.get("/recommendations", response_model=List[ScoredBook])
def get_recommendations(db: Session = Depends(get_db), user=Depends(get_current_user_optional)):
    filters_dict = {}
    
    # Fetch user-specific data if logged in
    if user:
        from ..models import Favorite
        
        # Get user's favorites to extract preferences
        favorites = db.query(Favorite).filter(Favorite.user_id == user.id).limit(10).all()
        
        # Extract genres and authors from favorites
        fav_genres = set()
        fav_authors = set()
        for fav in favorites:
            try:
                book_data = json.loads(fav.book_json)
                if book_data.get("categories"):
                    fav_genres.update(book_data["categories"])
                if book_data.get("authors"):
                    fav_authors.update(book_data["authors"])
            except:
                pass
        
        # Get recent search history
        recent_searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == user.id
        ).order_by(SearchHistory.created_at.desc()).limit(5).all()
        
        # Extract search patterns
        search_genres = set()
        search_queries = []
        for search in recent_searches:
            try:
                search_filters = json.loads(search.filters_json) if search.filters_json else {}
                if search_filters.get("genre"):
                    search_genres.add(search_filters["genre"])
                if search.query and not search.query.startswith("view:"):
                    search_queries.append(search.query)
            except:
                pass
        
        # Build smart filters based on user behavior
        all_genres = list(fav_genres | search_genres)
        all_authors = list(fav_authors)
        
        if all_genres:
            # Prefer user's favorite genres
            filters_dict["genre"] = all_genres[0]  # Use most common genre
        
        if all_authors and len(all_authors) > 0:
            # Include author preference
            filters_dict["author"] = all_authors[0]
        
        # Add quality filter
        filters_dict["min_rating"] = 3.8
        
        # Check saved preferences
        pref = db.query(Preference).filter(Preference.user_id == user.id).first()
        if pref:
            try:
                saved_prefs = json.loads(pref.preferences_json)
                # Merge saved preferences
                if saved_prefs.get("language"):
                    filters_dict["language"] = saved_prefs["language"]
                if saved_prefs.get("min_rating"):
                    filters_dict["min_rating"] = float(saved_prefs["min_rating"])
            except:
                pass
    
    # Fallback for anonymous users or users with no history
    if not filters_dict or (not filters_dict.get("genre") and not filters_dict.get("author")):
        filters_dict = {"min_rating": 4.0}
    
    # Search using filters
    items = search_books(filters_dict, start_index=0, max_results=40)
    
    # Also include curated books
    curated = search_curated(
        genre=filters_dict.get("genre"),
        author=filters_dict.get("author"),
        language=filters_dict.get("language")
    )
    
    # Combine and deduplicate
    seen_ids = set()
    all_items = []
    for item in curated + items:
        if item["id"] not in seen_ids:
            all_items.append(item)
            seen_ids.add(item["id"])
    
    # Score and sort
    scored = []
    for b in all_items:
        s, conf, reasons = score_book(b, filters_dict)
        scored.append(ScoredBook(
            id=b["id"],
            title=b.get("title") or "Untitled",
            authors=b.get("authors") or [],
            description=b.get("description"),
            thumbnail=b.get("thumbnail"),
            average_rating=b.get("average_rating"),
            ratings_count=b.get("ratings_count"),
            language=b.get("language"),
            categories=b.get("categories"),
            published_year=b.get("published_year"),
            read_link=b.get("read_link"),
            score=s,
            confidence_pct=conf,
            reasons=reasons,
        ))
    
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:20]  # Return top 20


@router.get("/search", response_model=List[ScoredBook])
def search(
    query: Optional[str] = None,
    genre: Optional[str] = None,
    author: Optional[str] = None,
    language: Optional[str] = None,
    min_rating: Optional[float] = Query(default=None, ge=0, le=5),
    year: Optional[int] = None,
    mood: Optional[str] = None,
    reading_level: Optional[str] = None,
    length: Optional[str] = None,
    start_index: int = 0,
    max_results: int = 20,
    is_search: bool = Query(False),
    db: Session = Depends(get_db),
):
    filters = SearchFilters(
        query=query,
        genre=genre,
        author=author,
        language=language,
        min_rating=min_rating,
        year=year,
        mood=mood.split(",") if mood else None,
        reading_level=reading_level,
        length=length,
    ).model_dump()

    # Record anonymous history
    db.add(SearchHistory(user_id=None, query=query, filters_json=str(filters)))
    db.commit()

    # Fetch both curated and API books
    curated_items = search_curated(query=query, author=author, genre=genre, language=language)
    api_items = search_books(filters, start_index=start_index, max_results=max_results)
    
    # FALLBACK LOGIC: If strict search returns nothing, relax the constraints
    # This ensures "all combo of filter should at last work"
    if not api_items and not curated_items and is_search:
        # 1. Try removing Rating and Year constraints first
        relaxed_filters = filters.copy()
        if relaxed_filters.get('min_rating') or relaxed_filters.get('year'):
            relaxed_filters['min_rating'] = None
            relaxed_filters['year'] = None
            api_items = search_books(relaxed_filters, start_index=0, max_results=max_results)
            
        # 2. If still no results, try removing strict Genre but keep Query
        if not api_items and relaxed_filters.get('query') and relaxed_filters.get('genre'):
            relaxed_filters['genre'] = None
            api_items = search_books(relaxed_filters, start_index=0, max_results=max_results)
    
    # Combine results
    import random
    if not is_search:
        # Browsing mode (Homepage): Show ALL curated books that match
        # Don't artificially limit - let the frontend control pagination
        pass  # No limiting for homepage browsing

    # Deduplicate and merge
    seen_ids = set()
    all_items = []
    
    # Add curated items first (higher priority)
    for item in curated_items:
        if item["id"] not in seen_ids:
            all_items.append(item)
            seen_ids.add(item["id"])
    
    # Then add API items
    for item in api_items:
        if item["id"] not in seen_ids:
            all_items.append(item)
            seen_ids.add(item["id"])

    scored = []
    for b in all_items:
        is_curated = b["id"].startswith("curated")
        
        # === QUALITY FILTERS (ONLY FOR EXPLICIT SEARCH) ===
        # Homepage browsing shows all books, search applies quality filters
        if is_search and not is_curated:
            title = (b.get("title") or "").strip()
            desc = (b.get("description") or "").strip()
            authors = b.get("authors") or []
            
            # Basic validation only
            if not title or len(title) < 3:
                continue
            if not authors:
                continue
            
            # Minimal junk detection
            junk_keywords = ['annual report', 'proceedings', 'white paper', 'technical manual']
            title_lower = title.lower()
            desc_lower = desc.lower()
            if any(keyword in title_lower or keyword in desc_lower for keyword in junk_keywords):
                continue
        
        # === AUTHOR FILTER (always strict when specified) ===
        if author and author.strip():
            authors = b.get("authors") or []
            author_match = False
            author_parts = author.lower().strip().split()
            for book_author in authors:
                book_author_lower = book_author.lower()
                if all(part in book_author_lower for part in author_parts):
                    author_match = True
                    break
            if not author_match:
                continue

        s, conf, reasons = score_book(b, filters)
        
        # 1. Rating filter (relaxed)
        avg_r = b.get("average_rating")
        if min_rating and min_rating > 0:
            if avg_r is None:
                if min_rating > 4.0: continue
            else:
                if avg_r < min_rating: continue

        # 2. Length filter (soft)
        # short: < 200, medium: 200-400, long: > 400
        length_pref = filters.get("length")
        pages = b.get("page_count")
        if length_pref and pages:
            if length_pref == "short" and pages > 250: continue
            if length_pref == "medium" and (pages < 150 or pages > 500): continue
            if length_pref == "long" and pages < 400: continue
            
        # 3. Reading level filter (soft)
        # beginner: < 200, intermediate: 200-400, advanced: > 400 (corresponds to complexity)
        level_pref = filters.get("reading_level")
        if level_pref and pages:
            if level_pref == "beginner" and pages > 300: continue
            if level_pref == "advanced" and pages < 300: continue

        scored.append(ScoredBook(
            id=b["id"],
            title=b.get("title") or "Untitled",
            authors=b.get("authors") or [],
            description=b.get("description"),
            thumbnail=b.get("thumbnail"),
            average_rating=b.get("average_rating"),
            ratings_count=b.get("ratings_count"),
            language=b.get("language"),
            categories=b.get("categories"),
            published_year=b.get("published_year"),
            read_link=b.get("read_link"),
            score=s,
            confidence_pct=conf,
            reasons=reasons,
        ))

    # Final Sorting: Primary by published_year (newest first), secondary by recommendation score
    scored.sort(key=lambda x: (x.published_year or 0, x.score), reverse=True)
    return scored


@router.get("/{book_id}", response_model=ScoredBook)
def details(book_id: str, db: Session = Depends(get_db)):
    book = None
    if book_id.startswith("curated"):
        # Search curated explicitly by ID
        matches = [b for b in curated_items_list() if b["id"] == book_id]
        if matches:
            book = matches[0]
    
    if not book:
        book = get_book_details(book_id)
        
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    s, conf, reasons = score_book(book, {})
    # Record view in history
    db.add(SearchHistory(user_id=None, query=f"view:{book_id}", filters_json=str({})))
    db.commit()
    return ScoredBook(
        id=book["id"],
        title=book.get("title") or "Untitled",
        authors=book.get("authors") or [],
        description=book.get("description"),
        thumbnail=book.get("thumbnail"),
        average_rating=book.get("average_rating"),
        ratings_count=book.get("ratings_count"),
        language=book.get("language"),
        categories=book.get("categories"),
        published_year=book.get("published_year"),
        read_link=book.get("read_link"),
        score=s,
        confidence_pct=conf,
        reasons=reasons,
    )


@router.get("/{book_id}/similar", response_model=SimilarBooksOut)
def similar(book_id: str):
    # Handle curated books first
    book = None
    if book_id.startswith("curated"):
        matches = [b for b in curated_items_list() if b["id"] == book_id]
        if matches:
            book = matches[0]
    
    # Fallback to Google Books API
    if not book:
        book = get_book_details(book_id)
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    # Strategy 1: Strict match (Genre + Author)
    primary_genre = (book.get("categories") or [None])[0]
    primary_author = (book.get("authors") or [None])[0]
    
    candidates = {}
    
    def add_candidates(items):
        for r in items:
            if r["id"] != book_id and r["id"] not in candidates:
                candidates[r["id"]] = r

    # 0. Curated Match (High Priority)
    curated_matches = search_curated(author=primary_author, genre=primary_genre, language=book.get("language"))
    add_candidates(curated_matches)

    # 1. Author + Genre
    if len(candidates) < 10 and primary_author and primary_genre:
        f1 = {"author": primary_author, "genre": primary_genre, "language": book.get("language")}
        add_candidates(search_books(f1, max_results=20))
    
    # 2. Genre only (if needed)
    if len(candidates) < 20 and primary_genre:
        f2 = {"genre": primary_genre, "language": book.get("language")}
        add_candidates(search_books(f2, max_results=20))
        
    # 3. Author only (if needed)
    if len(candidates) < 25 and primary_author:
        f3 = {"author": primary_author, "language": book.get("language")}
        add_candidates(search_books(f3, max_results=20))

    # Convert to ScoredBook
    items = []
    # Make a dummy filter context for scoring
    score_ctx = {"genre": primary_genre, "author": primary_author}
    
    for r in candidates.values():
        s, conf, reasons = score_book(r, score_ctx)
        items.append(ScoredBook(
            id=r["id"],
            title=r.get("title") or "Untitled",
            authors=r.get("authors") or [],
            description=r.get("description"),
            thumbnail=r.get("thumbnail"),
            average_rating=r.get("average_rating"),
            ratings_count=r.get("ratings_count"),
            language=r.get("language"),
            categories=r.get("categories"),
            published_year=r.get("published_year"),
            read_link=r.get("read_link"),
            score=s,
            confidence_pct=conf,
            reasons=reasons,
        ))
    
    items.sort(key=lambda x: x.score, reverse=True)
    return SimilarBooksOut(items=items[:40])