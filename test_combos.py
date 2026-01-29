import requests

def test_combo(genre, lang, query=""):
    url = f"http://127.0.0.1:8000/api/books/search?genre={genre}&language={lang}&query={query}"
    print(f"Testing: Genre={genre}, Lang={lang}, Query='{query}'")
    r = requests.get(url)
    if r.status_code == 200:
        books = r.json()
        print(f"Found {len(books)} results")
        for b in books[:3]:
            print(f" - {b['title']} ({b['language']})")
    else:
        print(f"Error {r.status_code}: {r.text}")
    print("-" * 30)

if __name__ == "__main__":
    test_combo("History", "ur")
    test_combo("Fiction", "hi")
    test_combo("Mystery", "en")
    test_combo("Religious", "en", "quran")
