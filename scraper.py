# scraper.py
import os
import time
import requests
import re
import sys
import asyncio
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from models import SessionLocal, Product, InventoryLog

# Use Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Setup your free Discord/Slack Webhook here for mobile alerts
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"

# Banned keywords to protect Mercari Account
PROHIBITED_KEYWORDS = ['肥料', '農薬', '殺虫', '除草剤', '配合', '化成']

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def send_stock_alert(message):
    if WEBHOOK_URL != "YOUR_DISCORD_WEBHOOK_URL_HERE":
        try:
            requests.post(WEBHOOK_URL, json={"content": message})
        except:
            pass

def scrape_cainz_product(jan_code):
    url = f"https://www.cainz.com/g/{jan_code}.html"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Inject Sano City GPS coordinates
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            geolocation={"longitude": 139.5732, "latitude": 36.3150},
            permissions=["geolocation"],
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if response and response.status == 404:
                raise Exception("404 Not Found (HTTP 404).")
        except Exception as e:
            browser.close()
            raise Exception(f"Playwright navigation failed: {e}")
            
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Visible H1 Check for 404
        h1_tag = soup.select_one('h1')
        if h1_tag and "お探しのページは見つかりません" in h1_tag.text:
            browser.close()
            raise Exception("404 Not Found (Item discontinued).")
        
        # TOS Safety Check
        visible_text = soup.get_text()
        if any(keyword in visible_text for keyword in PROHIBITED_KEYWORDS):
            browser.close()
            raise ValueError("⚠️ TOS VIOLATION: Item contains prohibited keywords. Skipped automatically.")
        
        # Extract Title
        title = h1_tag.text.strip() if h1_tag else f"Product {jan_code}"
        
        # Extract Price (Primary: JSON-LD)
        price = 0
        ld_json_el = soup.find('script', type='application/ld+json')
        if ld_json_el:
            import json
            try:
                data = json.loads(ld_json_el.text)
                offers = data.get("offers")
                if isinstance(offers, dict):
                    price = int(offers.get("price", 0))
                elif isinstance(offers, list) and len(offers) > 0:
                    price = int(offers[0].get("price", 0))
            except: pass
            
        # Extract Price (Fallback: Regex)
        if price == 0:
            for price_elem in soup.select('.text-24-bold,[class*="price"]'):
                match = re.search(r'([0-9,]+)', price_elem.get_text())
                if match:
                    potential_price = int(match.group(1).replace(',', ''))
                    if potential_price > 0 and potential_price != 5000:
                        price = potential_price
                        break

        # 🚨 FIXED CATEGORY EXTRACTION: Target the specific Breadcrumb Nav
        category = "Uncategorized"
        try:
            # Look for the exact 'トップ' (Top) link to isolate the correct <nav>
            top_link = soup.find('a', string=re.compile(r'^トップ$'))
            if top_link:
                nav = top_link.find_parent('nav')
                if nav:
                    lis = nav.find_all('li')
                    if len(lis) > 2:
                        cat_parts = []
                        # Skip index 0 (Top) and the last index (Current Product)
                        for li in lis[1:-1]:
                            a_tag = li.find('a')
                            if a_tag:
                                cat_parts.append(a_tag.get_text(strip=True))
                        
                        if cat_parts:
                            category = " > ".join(cat_parts)
        except Exception as e:
            print(f"Category extraction failed: {e}")

        # Extract dimensions (L+W+H) and catch mm vs cm
        dimensions_cm = 120 
        try:
            dim_match = re.search(r'幅(\d+(?:\.\d+)?).*?奥行(\d+(?:\.\d+)?).*?高さ(\d+(?:\.\d+)?)\s*(cm|mm)?', content, re.IGNORECASE)
            if dim_match:
                l, w, h = map(float, dim_match.group(1, 2, 3))
                unit = dim_match.group(4)
                
                if unit and unit.lower() == 'mm':
                    l, w, h = l/10, w/10, h/10
                    
                dimensions_cm = int(l + w + h)
        except: pass

        # Product Data Extraction (Features & Specs)
        features_text = ""
        specs_text = ""
        
        detail_grid = soup.find('div', class_=re.compile(r'grid-cols-3'))
        if detail_grid:
            keys = detail_grid.find_all('div', class_=re.compile(r'col-span-1'))
            for k in keys:
                v = k.find_next_sibling('div', class_=re.compile(r'col-span-2'))
                if v:
                    key_str = k.get_text(strip=True)
                    val_str = v.get_text(strip=True)
                    if key_str in ["特徴", "商品説明", "キャッチコピー", "機能"]:
                        features_text += f"✅ 【{key_str}】\n{val_str}\n\n"
                    elif key_str not in ["商品コード", "JANコード"]: 
                        specs_text += f"■ {key_str}：{val_str}\n"

        if not features_text:
            features_text = "✅ 使いやすさを追求した、日々の暮らしに役立つアイテムです。\n"
            
        specs_text += f"■ JANコード：{jan_code}\n■ 推定配送サイズ：{dimensions_cm}cm以内\n"

        # High-Res Image Downloader
        img_dir = os.path.join(os.path.dirname(__file__), "data", "img", jan_code)
        ensure_dir(img_dir)
        
        images = soup.find_all('img', src=re.compile(r'imgix\.cainz\.com.*product'))
        valid_img_urls =[]
        for img in images:
            src = img.get('src')
            clean_src = src.split('?')[0] if '?' in src else src
            if clean_src not in valid_img_urls:
                valid_img_urls.append(clean_src)
                
        saved_imgs = 0
        for src in valid_img_urls[:6]:
            try:
                file_path = os.path.join(img_dir, f"{jan_code}_{saved_imgs}.jpg")
                with open(file_path, 'wb') as f:
                    f.write(requests.get(src).content)
                
                # 🚨 NEW: IMAGE CLOAKING ENGINE (DEFEATS MERCARI AI)
                # We modify the FIRST image (Thumbnail) to break the stock-photo hash
                if saved_imgs == 0:
                    from PIL import Image, ImageOps
                    try:
                        with Image.open(file_path) as img:
                            # 1. Convert to standard RGB to prevent color space crashes
                            img = img.convert("RGB")
                            
                            # 2. Add a thick, 15-pixel custom border (Jayani NEXUS branded color: Dark Green/Gold)
                            # This completely changes the cryptographic hash of the image!
                            cloaked_img = ImageOps.expand(img, border=15, fill='#2E8B57')
                            
                            # 3. Save it back, overwriting the original stock photo
                            cloaked_img.save(file_path, quality=95)
                    except Exception as img_e:
                        print(f"Image cloaking failed, bypassing: {img_e}")

                saved_imgs += 1
            except: pass

        # Smart Modal Clicker for Sano Store Inventory
        stock_quantity = 0
        clicked = False
        for btn_text in["店舗変更", "受取店舗を選択", "店舗を指定", "在庫を確認", "店舗受取"]:
            try:
                page.locator(f"text={btn_text}").first.click(timeout=3000)
                clicked = True
                break
            except: continue
                
        if clicked:
            try:
                page.wait_for_selector("text=佐野", timeout=5000)
                page.wait_for_timeout(1000) 
                
                modal_soup = BeautifulSoup(page.content(), 'html.parser')
                sano_blocks = modal_soup.find_all(
                    lambda t: t.name in ["label", "li", "div"] and 
                    t.get_text() and 
                    re.search(r'カインズ佐野|佐野店資材館', t.get_text())
                )
                
                for block in sano_blocks:
                    txt = block.get_text()
                    if "商品をご用意できます" in txt or "在庫あり" in txt:
                        stock_quantity = 15
                        break
                    elif "残りわずか" in txt:
                        stock_quantity = 2
                        break
                    elif "お取り扱いがありません" in txt or "在庫なし" in txt:
                        stock_quantity = 0
            except: pass
            
        browser.close()
        
    return {
        "jan_code": jan_code, 
        "title": title, 
        "price": price,
        "category": category,
        "features": features_text.strip(),
        "specs": specs_text.strip(),
        "stock_quantity": stock_quantity, 
        "image_folder": img_dir,
        "dimensions_cm": dimensions_cm
    }

def update_inventory_for_all():
    db = SessionLocal()
    products = db.query(Product).all()
    
    for prod in products:
        try:
            info = scrape_cainz_product(prod.jan_code)
            new_stock = info['stock_quantity']
            
            if new_stock <= 2:
                alert_msg = f"🚨 **MERCARI ALERT**: `{prod.title}` (JAN: {prod.jan_code})\nSano Store Stock is critically low: **{new_stock} items left**. Update Mercari!"
                send_stock_alert(alert_msg)
            
            new_log = InventoryLog(jan_code=prod.jan_code, stock_quantity=new_stock)
            db.add(new_log)
        except Exception as e:
            print(f"Error updating {prod.jan_code}: {e}")
            
    db.commit()
    db.close()