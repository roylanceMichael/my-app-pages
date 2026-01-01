import requests
from bs4 import BeautifulSoup
import json
import time

# Configuration
URL = "https://atthegateway.com/calendar/"
OUTPUT_FILE = "gateway_events.json"

# Enhanced Headers to mimic a real modern browser
# These headers help bypass 403 Forbidden errors by looking like a real user
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def clean_text(text):
    """Removes extra whitespace and newlines."""
    if text:
        return ' '.join(text.split())
    return ""

def scrape_calendar():
    print(f"Fetching calendar from {URL}...")
    
    # Add a small delay to seem more human (optional, but good practice)
    time.sleep(1)

    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        # Return a fallback event so the script doesn't fail silently
        return [{
            "title": "Visit The Gateway Website",
            "date": "Check Website",
            "description": "Unable to fetch latest events automatically. Scan QR code for details."
        }]

    soup = BeautifulSoup(response.content, "html.parser")
    events_data = []

    # 1. Try modern Tribe Events View
    event_cards = soup.select(".tribe-events-calendar-list__event-details")
    
    # 2. Fallback to older Tribe Events View if 1 is empty
    if not event_cards:
        event_cards = soup.select(".type-tribe_events")

    print(f"Found {len(event_cards)} event entries.")

    count = 0
    for card in event_cards:
        if count >= 4: # Limit to top 4 upcoming events to fit on TV
            break

        # EXTRACT TITLE
        title_tag = card.select_one(".tribe-events-calendar-list__event-title, .tribe-events-list-event-title")
        if not title_tag: 
            continue # Skip if no title
        
        title = clean_text(title_tag.get_text())

        # EXTRACT DATE/TIME
        time_tag = card.select_one("time")
        if time_tag:
            date_text = clean_text(time_tag.get_text())
        else:
            meta_tag = card.select_one(".tribe-event-schedule-details")
            date_text = clean_text(meta_tag.get_text()) if meta_tag else "Check website for time"

        # EXTRACT DESCRIPTION
        desc_tag = card.select_one(".tribe-events-calendar-list__event-description, .tribe-events-list-event-description")
        description = clean_text(desc_tag.get_text()) if desc_tag else ""
        if len(description) > 120:
            description = description[:117] + "..."

        events_data.append({
            "title": title,
            "date": date_text,
            "description": description
        })
        count += 1

    if not events_data:
        print("Warning: No specific events found. Creating placeholder.")
        events_data.append({
            "title": "Visit The Gateway Website",
            "date": "Daily",
            "description": "Scan the QR code to see the full calendar of events, concerts, and markets."
        })

    return events_data

def save_json(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} events to {OUTPUT_FILE}")

if __name__ == "__main__":
    events = scrape_calendar()
    save_json(events)