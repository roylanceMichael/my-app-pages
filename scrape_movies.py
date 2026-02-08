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
    if not img_url:
        return None
        
    if not os.path.exists(POSTER_DIR):
        os.makedirs(POSTER_DIR)
    
    filename = f"{slugify(title)}.jpg"
    filepath = os.path.join(POSTER_DIR, filename)
    
    # If file exists and is > 0 bytes, skip download (cache)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return filename

    try:
        print(f"Downloading poster for {title}...")
        # IMDB images might be resized; remove params for full size if needed, but default is fine
        r = requests.get(img_url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return filename
    except Exception as e:
        print(f"Failed to download poster for {title}: {e}")
    
    return None

def format_runtime(seconds):
    if not seconds:
        return ""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

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
    
    # Extract JSON blob from NEXT_DATA
    data_tag = soup.find("script", id="__NEXT_DATA__")
    if not data_tag:
        print("Error: Could not find __NEXT_DATA__ script tag.")
        return []

    try:
        json_data = json.loads(data_tag.string)
        # Navigate to the relevant data
        # props.pageProps.titleAndShowtimeData
        titles_data = json_data.get("props", {}).get("pageProps", {}).get("titleAndShowtimeData", [])
        
        print(f"Found {len(titles_data)} movies in JSON data.")

        for item in titles_data:
            node = item.get("node", {})
            title_obj = node.get("title", {})
            
            # Title
            title = title_obj.get("titleText", {}).get("text", "")
            if not title:
                continue

            # Rating
            rating_summary = title_obj.get("ratingsSummary", {})
            rating_val = rating_summary.get("aggregateRating", "")
            # Convert float to string if exists, else "NR"
            rating_score = str(rating_val) if rating_val else "NR"
            
            # Content Rating (MPAA)
            cert = title_obj.get("certificate", {}).get("rating", "NR")
            
            # Runtime
            runtime_secs = title_obj.get("runtime", {}).get("seconds")
            runtime = format_runtime(runtime_secs)
            
            # Genres
            genres_list = title_obj.get("titleGenres", {}).get("genres", [])
            genre_text = ""
            if genres_list:
                # Take the first genre
                genre_text = genres_list[0].get("genre", {}).get("text", "")

            # Poster
            poster_url = title_obj.get("primaryImage", {}).get("url", "")
            
            # Showtimes
            showtimes = []
            showtime_groups = title_obj.get("cinemaShowtimesByScreeningType", {}).get("edges", [])
            for group in showtime_groups:
                types = group.get("node", {}).get("showtimesByScreeningType", [])
                for t in types:
                    # We could distinguish "Standard", "3D" etc here if we wanted.
                    # t['screeningType']['text'] e.g. "Standard"
                    times = t.get("showtimes", [])
                    for st in times:
                        start_text = st.get("screeningStart", {}).get("text", "")
                        if start_text:
                            showtimes.append(start_text)
            
            # Sort showtimes? They usually come sorted.
            # Deduplicate just in case
            showtimes = sorted(list(set(showtimes)), key=lambda x: datetime_from_time_str(x))

            # Download Poster
            local_poster = ""
            if poster_url:
                local_poster = download_poster(poster_url, title)

            if title and showtimes:
                movies_data.append({
                    "title": title,
                    "rating": cert, # Using Content Rating (PG-13) instead of score (6.6) for the board
                    "score": rating_score, # Keeping score just in case we want it later
                    "runtime": runtime,
                    "genre": genre_text,
                    "times": showtimes[:5], # Limit to 5 times
                    "poster": f"posters/{local_poster}" if local_poster else ""
                })

    except Exception as e:
        print(f"Error parsing JSON data: {e}")
        return []

    # Cleanup Old Posters
    # Only run cleanup if we actually found movies (safety check)
    if len(movies_data) > 0:
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

def datetime_from_time_str(time_str):
    from datetime import datetime
    try:
        return datetime.strptime(time_str, "%I:%M %p")
    except:
        return datetime.min

def save_json(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} movies to {OUTPUT_FILE}")

if __name__ == "__main__":
    movies = scrape_movies()
    if not movies:
        print("Scrape returned 0 movies.")
    else:
        save_json(movies)
