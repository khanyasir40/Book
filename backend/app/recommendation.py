from typing import Dict, Any, List
import math

WEIGHTS = {
    "genre": 0.30,
    "author": 0.15,
    "rating": 0.20,
    "popularity": 0.15,
    "year": 0.10,
    "language": 0.10,
}

MOOD_KEYWORDS = {
    "happy": ["happy", "joy", "uplifting", "optimistic"],
    "dark": ["dark", "grim", "noir", "morbid"],
    "inspirational": ["inspire", "motivation", "hope", "hero"],
    "thriller": ["thriller", "suspense", "tense", "mystery"],
}


def normalize_rating(avg_rating: float | None) -> float:
    if not avg_rating:
        return 0.0
    return max(0.0, min(1.0, avg_rating / 5.0))


def normalize_popularity(ratings_count: int | None) -> float:
    if not ratings_count or ratings_count <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log10(1 + ratings_count) / 3.0))


def match_genre(categories: List[str] | None, genre: str | None) -> float:
    if not genre:
        return 0.0
    cats = [c.lower() for c in (categories or [])]
    return 1.0 if genre.lower() in " ".join(cats) else 0.0


def match_author(authors: List[str] | None, author: str | None) -> float:
    if not author:
        return 0.0
    a = author.lower()
    book_authors = [x.lower() for x in (authors or [])]
    for ba in book_authors:
        if a in ba:
            return 1.0
    return 0.0


def match_language(language: str | None, desired: str | None) -> float:
    if not desired:
        return 0.0
    return 1.0 if language and language.lower() == desired.lower() else 0.0


def match_year(published_year: int | None, target_year: int | None) -> float:
    if not target_year or not published_year:
        return 0.0
    diff = abs(published_year - target_year)
    if diff == 0:
        return 1.0
    return max(0.0, 1.0 - min(diff, 50) / 50.0)


def mood_boost(title: str | None, description: str | None, moods: List[str] | str | None) -> float:
    """
    Calculate mood score boost based on keyword matching in title/description.
    Supports multiple moods as a list or comma-separated string.
    """
    if not moods:
        return 0.0
    
    # Handle moods as comma-separated string or list
    if isinstance(moods, str):
        mood_list = [m.strip() for m in moods.split(',') if m.strip()]
    else:
        mood_list = moods
    
    if not mood_list:
        return 0.0
    
    text = (title or "") + " " + (description or "")
    text_lower = text.lower()
    hits = 0
    
    for m in mood_list:
        for kw in MOOD_KEYWORDS.get(m.lower(), []):
            if kw in text_lower:
                hits += 1
                break
    
    return min(0.05 * hits, 0.15)  # small additive boost up to 0.15


def reading_level_match(page_count: int | None, level: str | None) -> float:
    if not level or not page_count:
        return 0.0
    if level == "beginner":
        return 1.0 if page_count <= 200 else 0.0
    if level == "intermediate":
        return 1.0 if 200 < page_count <= 400 else 0.0
    if level == "advanced":
        return 1.0 if page_count > 400 else 0.0
    return 0.0


def length_match(page_count: int | None, length: str | None) -> float:
    if not length or not page_count:
        return 0.0
    if length == "short":
        return 1.0 if page_count <= 200 else 0.0
    if length == "medium":
        return 1.0 if 200 < page_count <= 400 else 0.0
    if length == "long":
        return 1.0 if page_count > 400 else 0.0
    return 0.0


def score_book(book: Dict[str, Any], filters: Dict[str, Any]) -> tuple[float, float, list[str]]:
    genre_score = match_genre(book.get("categories"), filters.get("genre"))
    author_score = match_author(book.get("authors"), filters.get("author"))
    rating_score = normalize_rating(book.get("average_rating"))
    popularity_score = normalize_popularity(book.get("ratings_count"))
    year_score = match_year(book.get("published_year"), filters.get("year"))
    language_score = match_language(book.get("language"), filters.get("language"))

    base = (
        WEIGHTS["genre"] * genre_score
        + WEIGHTS["author"] * author_score
        + WEIGHTS["rating"] * rating_score
        + WEIGHTS["popularity"] * popularity_score
        + WEIGHTS["year"] * year_score
        + WEIGHTS["language"] * language_score
    )

    # Additional small boosts (not part of main weights)
    boost = 0.0
    boost += mood_boost(book.get("title"), book.get("description"), filters.get("mood"))
    boost += 0.05 * reading_level_match(book.get("page_count"), filters.get("reading_level"))
    boost += 0.05 * length_match(book.get("page_count"), filters.get("length"))

    score = min(1.0, base + boost)
    confidence_pct = round(score * 100, 2)

    reasons: list[str] = []
    if genre_score > 0: reasons.append("Genre match")
    if author_score > 0: reasons.append("Author match")
    if rating_score > 0.7: reasons.append("High rating")
    if popularity_score > 0.5: reasons.append("Popular")
    if year_score > 0.6: reasons.append("Year close to preference")
    if language_score > 0: reasons.append("Language match")
    if boost > 0: reasons.append("Mood/length/level bonus")

    return score, confidence_pct, reasons