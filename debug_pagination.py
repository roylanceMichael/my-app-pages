from playwright.sync_api import sync_playwright

URL = "https://www.utahrealestate.com/search/public.search?type=1&zip=84101"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    print(f"Navigating to {URL}...")
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(5000)
    
    # 1. Check for Pagination HTML
    pagination = page.locator("ul.pagination").first
    if pagination.count() > 0:
        print("Found pagination container:")
        print(pagination.inner_html())
    else:
        print("No 'ul.pagination' found.")
        # Try generic search for "Next" text
        next_links = page.get_by_text("Next", exact=False).all()
        print(f"Found {len(next_links)} elements with text 'Next':")
        for link in next_links:
            print(f"- Tag: {link.evaluate('el => el.tagName')}, HTML: {link.inner_html()}")

    # 2. Check for Page Size dropdown
    # Sometimes it's a select box
    page_size = page.locator("select[name='limit']").first
    if page_size.count() > 0:
        print("Found page size selector!")

    browser.close()
