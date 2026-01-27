# SmartShelf – Filter-Based Book Recommendation System

SmartShelf is a full-stack, deployable book recommendation platform that fetches live data from public book APIs and ranks results using a weighted scoring engine. It features a modern responsive UI with dark/light mode, real user accounts, favorites, history, and actionable filters.

## Features
- Filter by genre, author, language, rating, year, mood, reading level, book length
- Real-time data via Google Books API (optional: Open Library, Gutendex)
- Weighted recommendation scoring and confidence percentage
- Favorites, recently viewed, and recommendation history
- Similar books per title
- Modern responsive UI, dark/light mode, hover effects, smooth animations
- SQLite database for users, favorites, history, preferences

## Architecture
- Frontend: HTML + CSS + JavaScript (responsive SPA-style)
- Backend: FastAPI (Python) + SQLite via SQLAlchemy
- Recommendation Engine: Weighted scoring based on match quality, rating, popularity, year, language

## Scoring Weights
- Genre match: 30%
- Author match: 15%
- Rating: 20%
- Popularity: 15%
- Year: 10%
- Language: 10%

Final score = weighted sum of normalized features. Books are sorted by highest score and include a confidence percentage with a “why recommended” breakdown.

## Project Structure
```
bookprojecet/
  backend/
    app/
      main.py
      database.py
      models.py
      schemas.py
      auth.py
      recommendation.py
      google_books.py
      routes/
        auth.py
        books.py
        favorites.py
        history.py
    tests/
      test_filters.py
      test_api_response.py
      test_empty_results.py
      test_invalid_input.py
    requirements.txt
  frontend/
    index.html
    styles.css
    script.js
    assets/
      logo.svg
  README.md
``` 

## How to Run (Local)
1. Install Python 3.10+.
2. Create a virtual environment and install dependencies:
   - `python -m venv .venv`
   - Windows: `.\.venv\\Scripts\\activate`
   - `pip install -r backend/requirements.txt`
3. Optional: set environment variables:
   - `GOOGLE_BOOKS_API_KEY` (increases quota; not required for basic usage)
4. Start the backend:
   - `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
5. Open the app:
   - Visit `http://localhost:8000/` (frontend served by FastAPI).

## How It Works
- Frontend sends filter params to backend routes.
- Backend fetches live data from Google Books API, normalizes fields, and computes recommendation scores.
- Results are ranked, annotated with confidence and reasons, and returned to frontend.
- Users can register/login, save favorites, view history, and fetch similar books.

## APIs Used
- Google Books API (mandatory)
- Optional: Open Library API, Gutendex API (expansion ready)

## Deployment
- Render/Railway: Run `uvicorn backend.app.main:app` with Python build
- Vercel: Host the frontend, point to a deployed backend URL
- Environment: configure `GOOGLE_BOOKS_API_KEY` if desired

## Testing
- Run backend tests: `pytest`
- Tests cover filters, API response handling, empty results, invalid input

## License
- For educational deployment demos.