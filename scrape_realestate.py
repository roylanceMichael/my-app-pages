import json
import re
import time
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "forsale.json"
# Search entire 84101 zip code
URL = "https://www.utahrealestate.com/search/public.search?type=1&zip=84101"

def clean_text(text):
    if text:
        return ' '.join(text.split())
    return ""

def scrape_listings():
    print(f"Launching browser to scrape: {URL}")
    listings = []
    
    # Track unique units to avoid duplicates across pages
    seen_units = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            page.goto(URL, timeout=60000)
            page.wait_for_timeout(5000) # Initial hydrate
            
            max_pages = 5
            current_page = 1
            
            while current_page <= max_pages:
                print(f"--- Scanning Page {current_page} ---")
                
                # Grab all listing cards on current page
                listing_tables = page.locator(".public-detail-quickview").all()
                print(f"Found {len(listing_tables)} listings on this page.")
                
                for table in listing_tables:
                    try:
                        text_content = table.inner_text().upper()
                        
                        # Address Check
                        address_loc = table.locator("h2.public")
                        if address_loc.count() == 0: continue
                        
                        full_address = clean_text(address_loc.inner_text())
                        check_addr = full_address.upper()
                        
                        # Match Logic
                        is_match = False
                        if "5 S 500 W" in check_addr or "5 SOUTH 500 WEST" in check_addr:
                            is_match = True
                        elif "165 S RIO GRANDE" in check_addr or "165 SOUTH RIO GRANDE" in check_addr:
                            is_match = True
                        elif "PARC" in check_addr and "GATEWAY" in check_addr:
                            is_match = True
                        
                        if not is_match:
                            continue

                        # Extract Data
                        # Price
                        price_match = re.search(r'\$[\d,]+', text_content)
                        price = price_match.group(0) if price_match else "Call for Price"
                        
                        # Unit
                        unit = ""
                        if "#" in full_address:
                            # Split by # and take the part after
                            parts = full_address.split("#")
                            if len(parts) > 1:
                                # "1060 S Main St #74, Brigham City..." -> "74"
                                unit = parts[-1].split(",")[0].strip()
                        
                        if not unit:
                            # Fallback: sometimes address is "5 S 500 W 402"
                            parts = full_address.split(" ")
                            if parts[-1].isdigit(): # potentially unit number at end?
                                # risky, but let's stick to # for now
                                pass

                        if unit in seen_units:
                            continue
                        
                        # Details
                        overview = "Details not found"
                        overview_loc = table.locator(".public-detail-overview")
                        if overview_loc.count() > 0:
                            overview = clean_text(overview_loc.inner_text())
                        
                        # Link
                        full_link = ""
                        try:
                            link_locator = table.locator("li.view-prop-details a").first
                            if link_locator.count() > 0:
                                 link_suffix = link_locator.get_attribute("href", timeout=500)
                                 full_link = f"https://www.utahrealestate.com{link_suffix}"
                        except:
                            pass

                        listings.append({
                            "unit": unit,
                            "price": price,
                            "details": overview,
                            "link": full_link
                        })
                        seen_units.add(unit)
                        print(f"MATCH: Unit {unit} - {price}")

                    except Exception as e:
                        print(f"Error parsing listing: {e}")

                # Pagination Logic
                # Look for a "Next" button.
                # URE pagination usually has class 'pagination' and next arrow
                # We can try finding a link with text ">" or class "next"
                next_btn = page.locator("ul.pagination li a[rel='next']").first
                
                if next_btn.count() > 0 and next_btn.is_visible():
                    print("Navigating to next page...")
                    next_btn.click()
                    page.wait_for_timeout(4000) # Wait for reload
                    current_page += 1
                else:
                    print("No 'Next' button found or end of results.")
                    break

        except Exception as e:
            print(f"Browser error: {e}")
            # Take screenshot on error
            page.screenshot(path="error_screenshot.png")
        finally:
            browser.close()

    # Sort listings by unit number naturally (104, 402, 1001)
    def natural_keys(text):
        return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]
    
    listings.sort(key=lambda x: natural_keys(x['unit']))
    return listings

def save_json(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} listings to {OUTPUT_FILE}")

if __name__ == "__main__":
    data = scrape_listings()
    save_json(data)