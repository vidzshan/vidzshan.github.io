# bulk_finder.py
import sys
import asyncio
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def harvest_jan_codes(base_url, category_name="Auto-Harvest", max_pages=1):
    """
    Smart Paginator: Extracts JAN codes across multiple search pages automatically.
    """
    print(f"🌍 Launching Multi-Page Harvester for: {category_name}")
    print(f"🔗 Target Base URL: {base_url}")
    print(f"📄 Scraping Depth: {max_pages} pages")
    
    jan_codes = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            geolocation={"longitude": 139.5732, "latitude": 36.3150},
            permissions=["geolocation"]
        )
        page = context.new_page()
        
        for current_page in range(1, max_pages + 1):
            # 🚨 DYNAMIC URL INJECTION: Safely append or update the &page= parameter
            if current_page == 1:
                target_url = base_url
            else:
                if re.search(r'([?&])page=\d+', base_url):
                    target_url = re.sub(r'([?&])page=\d+', rf'\g<1>page={current_page}', base_url)
                else:
                    connector = "&" if "?" in base_url else "?"
                    target_url = f"{base_url}{connector}page={current_page}"
            
            print(f"   -> Scraping Page {current_page}...")
            
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000) # Wait for JS to render the grid
            except Exception as e:
                print(f"❌ Failed to load page {current_page}: {e}")
                break # Stop paginating if connection fails

            soup = BeautifulSoup(page.content(), 'html.parser')
            
            # Find all product links on the current page
            links = soup.find_all('a', href=re.compile(r'/g/\d+\.html'))
            
            page_jans = 0
            for link in links:
                match = re.search(r'/g/(\d+)\.html', link['href'])
                if match:
                    jan = match.group(1)
                    if jan not in jan_codes:
                        jan_codes.add(jan)
                        page_jans += 1
                        
            print(f"      Found {page_jans} new items.")
            
            # If a page returns 0 items, we have hit the end of the category. Stop looping.
            if page_jans == 0 and current_page > 1:
                print("🛑 Reached the end of the product list. Stopping early.")
                break
                
            # Anti-Ban Sleep: Pause for 2 seconds before hitting the next page
            if current_page < max_pages:
                time.sleep(2)
                
        browser.close()
        
        print(f"\n✅ SUCCESS: Harvested {len(jan_codes)} TOTAL JAN codes across {max_pages} pages!")
        return list(jan_codes)
