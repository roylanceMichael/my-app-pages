import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time

# Configuration
# IMDB Showtimes URL for Megaplex Gateway (Zip 84101)
IMDB_URL = "https://www.imdb.com/showtimes/cinema/US/ci0011810/US/84062/"
OUTPUT_FILE = "movies.json"
POSTER_DIR = "posters"

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def clean_text(text):
    if text:
        return ' '.join(text.split())
    return ""

def slugify(text):
    """Converts 'The Iron Lung' to 'the-iron-lung' for filenames."""
    text = text.lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def download_poster(img_url, title):
    """Downloads poster image and saves to local directory."""
    if not os.path.exists(POSTER_DIR):
        os.makedirs(POSTER_DIR)
    
    filename = f"{slugify(title)}.jpg"
    filepath = os.path.join(POSTER_DIR, filename)
    
    # If file exists and is > 0 bytes, skip download (cache)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return filename

    try:
        print(f"Downloading poster for {title}...")
        # IMDB images might be resized; sometimes we can remove params for full size,
        # but for thumbnails, the default is often fine.
        r = requests.get(img_url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return filename
    except Exception as e:
        print(f"Failed to download poster for {title}: {e}")
    
    return None

def scrape_movies():
    print(f"Fetching showtimes from {IMDB_URL}...")
    try:
        response = requests.get(IMDB_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    movies_data = []
    
    # Select all movie containers
    # IMDB structure varies; looking for generic 'list-item' or specific showtime classes
    # Note: IMDB classes are often randomized/obfuscated (e.g., ipc-metadata-list).
    # We will look for semantic structure.
    
    # Strategy: Find the main list
    movie_list = soup.select(".ipc-metadata-list-summary-item")
    
    print(f"Found {len(movie_list)} movies.")

    for item in movie_list:
        try:
            # Title
            title_tag = item.select_one(".ipc-title__text")
            if not title_tag: continue
            title = clean_text(title_tag.get_text())
            
            # Metadata (Rating, Runtime, Genre)
            # Usually in a subtitle list
            metadata_items = item.select(".ipc-inline-list__item")
            rating = "NR"
            runtime = ""
            genre = ""
            
            # Simple heuristic parsing of metadata
            for meta in metadata_items:
                text = clean_text(meta.get_text())
                if text in ["R", "PG-13", "PG", "G", "NC-17"]:
                    rating = text
                elif "h" in text and "m" in text:
                    runtime = text
                elif not genre and len(text) > 3: # Assume first non-rating/non-time string is genre
                    genre = text

            # Poster
            poster_url = ""
            img_tag = item.select_one("img.ipc-image")
            if img_tag:
                poster_url = img_tag.get("src")
                # Handle IMDB dynamic resizing URLs if needed
                # URL often looks like: https://m.media-amazon.com/images/M/..._V1_QL75_UX140_CR0,0,140,207_.jpg
            
            # Showtimes
            # Look for time buttons
            showtime_tags = item.select(".showtime-button") # Class might vary, looking for button-like elements with times
            # Fallback search for times if specific class not found
            if not showtime_tags:
                # Text search for patterns like "12:00 pm"
                all_text = item.get_text()
                # Advanced regex for times could go here, but let's try a selector approach first
                # Often nested in a "showtimes" div
                times_container = item.select_one("[data-testid='showtimes-list']")
                if times_container:
                    # extract just the times
                    showtimes = [clean_text(t.get_text()) for t in times_container.find_all("span") if ":" in t.get_text()]
                else:
                    showtimes = []
            else:
                showtimes = [clean_text(t.get_text()) for t in showtime_tags]

            # Download Poster
            local_poster = ""
            if poster_url:
                local_poster = download_poster(poster_url, title)

            if title and showtimes:
                movies_data.append({
                    "title": title,
                    "rating": rating,
                    "runtime": runtime,
                    "genre": genre,
                    "times": showtimes[:5], # Limit to 5 times for space
                    "poster": f"posters/{local_poster}" if local_poster else ""
                })
        except Exception as e:
            print(f"Error parsing movie item: {e}")
            continue

    # Cleanup Old Posters
    # Get list of current poster filenames
    current_posters = [m["poster"].split('/')[-1] for m in movies_data if m["poster"]]
    
    if os.path.exists(POSTER_DIR):
        for f in os.listdir(POSTER_DIR):
            if f not in current_posters:
                try:
                    os.remove(os.path.join(POSTER_DIR, f))
                    print(f"Removed old poster: {f}")
                except:
                    pass

    return movies_data

def save_json(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} movies to {OUTPUT_FILE}")

if __name__ == "__main__":
    movies = scrape_movies()
    # Fallback data if scrape fails entirely (prevents empty board)
    if not movies:
        print("Scrape returned 0 movies. Keeping existing data or creating placeholder.")
        # Logic to handle empty scrape could go here
    else:
        save_json(movies)