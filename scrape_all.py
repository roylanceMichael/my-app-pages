import scrape_events
import scrape_movies
import sys

def main():
    print("=== Starting Update Process ===")
    
    # 1. Update Events
    print("\n--- Updating Gateway Events ---")
    try:
        events = scrape_events.scrape_calendar()
        scrape_events.save_json(events)
    except Exception as e:
        print(f"Error updating events: {e}", file=sys.stderr)

    # 2. Update Movies
    print("\n--- Updating Movies ---")
    try:
        movies = scrape_movies.scrape_movies()
        if movies:
            scrape_movies.save_json(movies)
        else:
            print("No movies found. Skipping JSON update.")
    except Exception as e:
        print(f"Error updating movies: {e}", file=sys.stderr)

    print("\n=== Update Complete ===")

if __name__ == "__main__":
    main()

