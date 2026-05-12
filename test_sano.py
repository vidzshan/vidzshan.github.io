import sys
import asyncio
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def test_sano_stock(jan_code):
    print(f"🌍 Launching Playwright... Spoofing GPS to Sano City, Tochigi...")
    with sync_playwright() as p:
        # 🚨 CHANGED: headless=False so you can watch what happens!
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            geolocation={"longitude": 139.5732, "latitude": 36.3150}, # SANO GPS
            permissions=["geolocation"],
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        print(f"📦 Loading Cainz product page for JAN: {jan_code}...")
        try:
            # 🚨 CHANGED: Wait for basic HTML only (domcontentloaded), and give it 60 seconds!
            page.goto(f"https://www.cainz.com/g/{jan_code}.html", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            browser.close()
            return

        print("🖱️ Searching for 'Change Store' or 'Select Store' button to open modal...")
        clicked = False
        for btn_text in["店舗変更", "受取店舗を選択", "店舗を指定", "在庫を確認", "店舗受取"]:
            try:
                page.locator(f"text={btn_text}").first.click(timeout=5000)
                clicked = True
                print(f"✅ Successfully clicked '{btn_text}'!")
                break
            except:
                continue
                
        if not clicked:
            print("❌ Could not open store modal.")
            browser.close()
            return

        print("⏳ Waiting for '佐野' (Sano) to appear in the nearby stores list...")
        try:
            page.wait_for_selector("text=佐野", timeout=10000)
            page.wait_for_timeout(1500) # Let the Ajax text load fully
        except Exception as e:
            print("❌ Timed out waiting for Sano store to load in the modal.")
            browser.close()
            return
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        sano_blocks = soup.find_all(
            lambda t: t.name in ["label", "li", "div"] and 
            t.get_text() and 
            re.search(r'カインズ佐野|佐野店資材館', t.get_text())
        )
        
        print("\n--- 🎯 SANO STORE RESULTS ---")
        stock = 0
        for block in sano_blocks:
            txt = block.get_text()
            print(f"Raw Text Found: {txt.strip()[:60]}...") 
            
            if "商品をご用意できます" in txt or "在庫あり" in txt:
                stock = 15
                print("🟢 STATUS: PLENTY OF STOCK (Mapped to 15)")
                break
            elif "残りわずか" in txt:
                stock = 2
                print("🟡 STATUS: LOW STOCK (Mapped to 2)")
                break
            elif "お取り扱いがありません" in txt or "在庫なし" in txt:
                print("🔴 STATUS: OUT OF STOCK at this specific branch block.")
                stock = 0
                
        print(f"-----------------------------\nFINAL SANO STOCK NUMBER: {stock}\n")
        browser.close()

# Test with your Kumimoku 2WAY Fan
test_sano_stock("4549509353829")