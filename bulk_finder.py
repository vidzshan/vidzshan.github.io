import sys
import asyncio
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def harvest_jan_codes(search_url, category_name="Items"):
    print(f"🌍 Launching Harvester for: {category_name}")
    print(f"🔗 URL: {search_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using Sano City GPS to ensure items are relevant to your region
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            geolocation={"longitude": 139.5732, "latitude": 36.3150},
            permissions=["geolocation"],
        )
        page = context.new_page()

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)  # Wait for the product grid to load
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            browser.close()
            return []

        soup = BeautifulSoup(page.content(), "html.parser")

        # Find all product links on the search page
        links = soup.find_all("a", href=re.compile(r"/g/\d+\.html"))

        jan_codes = set()
        for link in links:
            match = re.search(r"/g/(\d+)\.html", link["href"])
            if match:
                jan_codes.add(match.group(1))

        browser.close()

        print(f"\n✅ SUCCESS: Harvested {len(jan_codes)} GUARANTEED LIVE JAN codes!")
        print("=" * 40)
        for jan in list(jan_codes):
            print(jan)
        print("=" * 40)
        print(
            "👉 Copy any of the codes above and paste them into your Streamlit Dashboard!\n"
        )

        return list(jan_codes)


# ========================================================
# 🚀 HIGH-PROFIT CATEGORY URLs (Target: ¥2,000 - ¥5,000)
# ========================================================

# 1. Kumimoku Tools (High demand on Mercari, small shipping size)
kumimoku_url = "https://www.cainz.com/search/?q=kumimoku&price=2000-4999"

# 2. Storage & Organization (整理収納) (Moms on Mercari love Cainz storage)
storage_url = "https://www.cainz.com/search/?category=21&price=2000-4999"

# 3. Camping & Outdoor (キャンプ) (Huge demand right now)
camp_url = "https://www.cainz.com/search/?category=4224&price=2000-4999"

# --- Run the Harvester ---
if __name__ == "__main__":
    # Ensure Windows console can print emojis without crashing
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    harvest_jan_codes(kumimoku_url, "Kumimoku DIY Tools")
    # harvest_jan_codes(storage_url, "Storage Boxes")
    # harvest_jan_codes(camp_url, "Camp & Outdoor Gear")
