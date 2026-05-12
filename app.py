# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from models import SessionLocal, Product, InventoryLog, TrackedJan, init_db
from scraper import scrape_cainz_product
from template_engine import calculate_price, generate_mercari_text
from bulk_finder import harvest_jan_codes


st.set_page_config(page_title="Mercari Nexus Engine", layout="wide", page_icon="📦")

st.title("📦 Jayani NEXUS Mercari Engine")
st.markdown("Automated Bulk Sourcing, Pricing, and Sano Store Inventory Analytics.")

init_db()
db = SessionLocal()

tab_dash, tab_bulk, tab_bundles, tab_analytics, tab_crm = st.tabs([
    "📊 Dashboard", "⚡ Bulk Add", "🛍️ Smart Bundles", "📈 Analytics", "💬 CRM & Support"
])
# ==========================================
# TAB 1: DASHBOARD (Active Listings)
# ==========================================
with tab_dash:
    products = db.query(Product).all()

    # Calculate advanced metrics
    low_stock_count = 0
    active_profit = 0
    realized_profit = 0  # Money in the bank!

    for p in products:
        logs = (
            db.query(InventoryLog)
            .filter_by(jan_code=p.jan_code)
            .order_by(InventoryLog.timestamp)
            .all()
        )
        if logs and logs[-1].stock_quantity <= 2:
            low_stock_count += 1

        if p.mercari_status == "Active":
            active_profit += p.expected_profit
        elif p.mercari_status == "Sold":
            realized_profit += p.expected_profit

    st.markdown("### 📊 Business Overview & Account Health")
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Tracked Items", len(products))
    c2.metric("Projected Profit (Active)", f"¥{active_profit:,.0f}")
    c3.metric(
        "🏆 Realized Profit (Sold)",
        f"¥{realized_profit:,.0f}",
        delta="Money in the bank!",
    )
    c4.metric(
        "🚨 Low Stock Alerts",
        low_stock_count,
        delta="-Action Required" if low_stock_count > 0 else "Safe",
        delta_color="inverse",
    )

    st.markdown("---")
    st.markdown("#### ⚠️ Mercari Account Safety Status")
    health_col1, health_col2 = st.columns(2)
    health_col1.warning("Current Status: **24-Hour Restriction (Fertilizer)**")
    health_col2.error(
        "Cancellation Warning: Do NOT cancel any more transactions manually this week. Use Support Mediation."
    )
    st.divider()

    # 🚨 NEW: Dashboard Filters so you don't lose track of items!
    st.markdown("### 📋 Manage Listings")
    filter_status = st.radio(
        "Filter by Mercari Status:",
        ["All", "Not Listed", "Active", "Paused", "Sold"],
        horizontal=True,
    )

    # Apply the filter to create the current view
    filtered_products = [
        p
        for p in products
        if filter_status == "All" or p.mercari_status == filter_status
    ]

    # ==========================================
    # 🚨 10X COMFORT: MASTER PAYLOAD ZIP GENERATOR
    # ==========================================
    with st.expander("📦 Generate Mercari Shops Master Payload (CSV + Images)"):
        st.markdown("Download a single ZIP file containing the bulk-upload CSV **and** all associated product images, perfectly mapped for 1-click Mercari Shops deployment.")
        export_items =[p for p in products if p.mercari_status == "Active"]
        
        if export_items:
            if st.button("🚀 Compile Master Payload (.ZIP)", type="primary"):
                with st.spinner("Compiling CSV and packaging images..."):
                    import zipfile
                    import io
                    import os
                    
                    # 1. Create in-memory ZIP buffer
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        csv_data =[]
                        
                        # 2. Process each item
                        for p in export_items:
                            # 🚨 NEW: Strict Mercari Shops CSV Schema Mapping
                            row = {
                                "商品名": p.title[:40],
                                "商品説明": p.mercari_text.replace("\n", "\r\n"),
                                "在庫数": 1,
                                "販売価格": p.mercari_price,
                                "商品の状態": "新品、未使用",
                                "配送料の負担": "送料込み(出品者負担)",
                                "配送の方法": "らくらくメルカリ便",
                                "発送元の地域": "栃木県", # Sano location
                                "発送までの日数": "1~2日で発送",
                                "種類": "その他", # Default fallback category
                                "JANコード": p.jan_code
                            }
                            
                            # Map up to 6 images to the strict CSV columns
                            if p.image_folder and os.path.exists(p.image_folder):
                                img_files = [f for f in os.listdir(p.image_folder) if f.endswith('.jpg')]
                                for i in range(10): # Mercari allows up to 10 images
                                    col_name = f"画像{i+1}"
                                    if i < len(img_files):
                                        # Write exact filename so Mercari ZIP upload links them
                                        row[col_name] = f"{p.jan_code}_{i}.jpg" 
                                    else:
                                        row[col_name] = ""
                            
                            csv_data.append(row)
                            
                            # 3. Inject Images into the ZIP directory
                            if p.image_folder and os.path.exists(p.image_folder):
                                for img_name in os.listdir(p.image_folder):
                                    if img_name.endswith('.jpg'):
                                        img_path = os.path.join(p.image_folder, img_name)
                                        # Store inside an 'images/' folder in the zip
                                        zip_file.write(img_path, arcname=f"images/{p.jan_code}/{img_name}")
                        
                        # 4. Generate the CSV file and inject it into the ZIP
                        df_export = pd.DataFrame(csv_data)
                        csv_string = df_export.to_csv(index=False, encoding='utf-8-sig')
                        zip_file.writestr("mercari_bulk_upload.csv", csv_string)
                    
                    # 5. Serve the ZIP file to the user
                    st.download_button(
                        label="⬇️ Download Completed Payload",
                        data=zip_buffer.getvalue(),
                        file_name=f"Jayani_Nexus_Payload_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        type="primary"
                    )
        else:
            st.warning("No 'Active' items to export. Change some items to 'Active' first!")

    # ==========================================
    # 🚨 BULK DELETE ENGINE (DB + Local Images)
    # ==========================================
    with st.expander("🗑️ Bulk Delete Items (Database & Local Images)"):
        st.error(
            "⚠️ Warning: This will permanently delete the items from the database AND wipe their image folders from your computer."
        )

        # Multi-select dropdown to pick many items at once
        delete_list = st.multiselect(
            "Select items to delete:",
            options=[p.jan_code for p in filtered_products],
            format_func=lambda jan: next(
                (
                    f"{p.title} (JAN: {p.jan_code})"
                    for p in filtered_products
                    if p.jan_code == jan
                ),
                jan,
            ),
        )

        if st.button(
            "🚨 Delete Selected Items", type="primary", disabled=len(delete_list) == 0
        ):
            import shutil
            import os

            deleted_count = 0
            for jan in delete_list:
                prod_to_delete = db.query(Product).filter_by(jan_code=jan).first()
                if prod_to_delete:
                    # 1. Wipe the images from the local hard drive
                    img_path = os.path.abspath(prod_to_delete.image_folder)
                    if os.path.exists(img_path):
                        try:
                            shutil.rmtree(
                                img_path
                            )  # Recursively deletes the folder and all images inside
                        except Exception as e:
                            st.error(f"Failed to delete folder for {jan}: {e}")

                    # 2. Update Analytics Tracker so it is logged as manually deleted
                    track = db.query(TrackedJan).filter_by(jan_code=jan).first()
                    if track:
                        track.status = "Deleted Manually (Bulk)"

                    # 3. Delete from the Database (SQLAlchemy automatically deletes Inventory Logs)
                    db.delete(prod_to_delete)
                    deleted_count += 1

            db.commit()
            st.toast(
                f"Successfully wiped {deleted_count} items and their images!", icon="🗑️"
            )
            st.rerun()  # Instantly refreshes the UI

    st.markdown("---")

    if not filtered_products:
        st.info(
            "No products match this filter. Go to the 'Bulk Add' tab to source items!"
        )
    else:
        for prod in filtered_products:
            # Apply Filter
            if filter_status != "All" and prod.mercari_status != filter_status:
                continue

            logs = (
                db.query(InventoryLog)
                .filter_by(jan_code=prod.jan_code)
                .order_by(InventoryLog.timestamp)
                .all()
            )
            current_stock = logs[-1].stock_quantity if logs else 0
            stock_warning = (
                " 🚨 LOW STOCK/OUT OF STOCK" if current_stock <= 2 else " 🟢 IN STOCK"
            )

            status_icon = (
                "⚪"
                if prod.mercari_status == "Not Listed"
                else (
                    "🔵"
                    if prod.mercari_status == "Active"
                    else ("🟡" if prod.mercari_status == "Paused" else "🔴")
                )
            )

            # 🚨 NEW: Stale Inventory Alert (The 100-Yen Drop Trick)
            days_since_update = (datetime.utcnow() - prod.updated_at).days
            stale_warning = ""
            if prod.mercari_status == "Active" and days_since_update >= 2:
                stale_warning = " 📉 TIME FOR 100-YEN DROP!"

            with st.expander(
                f"{status_icon} [{prod.mercari_status}] {prod.title[:20]}... | Profit: ¥{prod.expected_profit} | Sano: {current_stock} {stock_warning} {stale_warning}"
            ):
                col1, col2, col3 = st.columns([1, 1.5, 1.5])

                with col1:
                    st.markdown("**💰 Financials**")
                    st.metric("Source Price", f"¥{prod.price:,.0f}")
                    st.metric(
                        f"Shipping (Size {prod.shipping_tier})",
                        f"¥{prod.shipping_fee:,.0f}",
                    )
                    st.metric("Mercari Sale Price", f"¥{prod.mercari_price:,.0f}")
                    import math
                    mercari_fee = math.floor(prod.mercari_price * 0.1)
                    st.metric("Mercari Fee (10%)", f"-¥{mercari_fee:,.0f}")
                    st.metric("Net Profit", f"¥{prod.expected_profit:,.0f}")

                    st.markdown("**🛒 Operations**")
                    st.markdown(f"[🔗 Buy on Cainz]({prod.cainz_url})")

                    # 🚨 UPGRADED: Live Verify Button (Syncs to Database)
                    if st.button("⚡ Live Stock Verify", key=f"verify_{prod.jan_code}"):
                        with st.spinner("Checking live Sano store stock..."):
                            try:
                                live_info = scrape_cainz_product(prod.jan_code)
                                live_stock = live_info["stock_quantity"]

                                # 1. Save the newly verified stock to the database!
                                new_log = InventoryLog(
                                    jan_code=prod.jan_code, stock_quantity=live_stock
                                )
                                db.add(new_log)
                                db.commit()

                                # 2. Show the result
                                if live_stock > 0:
                                    st.toast(
                                        f"SAFE! Sano has {live_stock} in stock.",
                                        icon="✅",
                                    )
                                else:
                                    st.toast("DANGER! Sano is out of stock.", icon="🚨")

                                # 3. Instantly refresh the screen so the Header and Chart update!
                                import time

                                time.sleep(1)  # Give the toast a second to display
                                st.rerun()

                            except Exception as e:
                                st.error(f"Verification failed: {e}")

                    if st.button("📂 Open Image Folder", key=f"folder_{prod.jan_code}"):
                        import os

                        img_path = os.path.abspath(prod.image_folder)
                        if os.path.exists(img_path):
                            os.startfile(img_path)
                        else:
                            st.error("Image folder not found.")
                            
                    if st.button("🖼️ Generate Premium Image", key=f"gen_single_{prod.jan_code}"):
                        with st.spinner("Generating Mercari-optimized image..."):
                            from PIL import Image, ImageDraw, ImageFont
                            import os

                            def get_first_image(folder_path):
                                if not folder_path or not os.path.exists(folder_path):
                                    return None
                                files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                                return os.path.join(folder_path, files[0]) if files else None
                                
                            img_path_src = get_first_image(prod.image_folder)
                            
                            if not img_path_src:
                                st.error("Missing original images. Cannot generate.")
                            else:
                                try:
                                    canvas = Image.new("RGB", (1000, 1000), "white")
                                    img = Image.open(img_path_src).convert("RGB")
                                    
                                    img.thumbnail((900, 900), Image.Resampling.LANCZOS)
                                    canvas.paste(img, ((1000 - img.width) // 2, (1000 - img.height) // 2))
                                    
                                    font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "meiryo.ttc")
                                    try:
                                        font_large = ImageFont.truetype(font_path, 60)
                                        font_medium = ImageFont.truetype(font_path, 50)
                                    except:
                                        font_large = ImageFont.load_default()
                                        font_medium = ImageFont.load_default()
                                    
                                    draw = ImageDraw.Draw(canvas)
                                    
                                    draw.rectangle([0, 0, 350, 100], fill="#E60012")
                                    draw.text((25, 15), "送料無料", fill="white", font=font_large)
                                    
                                    draw.rectangle([0, 880, 1000, 1000], fill="#FFD700")
                                    promo_text = f"✨ 新品・高品質 / スピード発送 ✨"
                                    text_bbox = draw.textbbox((0, 0), promo_text, font=font_medium)
                                    text_x = (1000 - (text_bbox[2] - text_bbox[0])) / 2
                                    draw.text((text_x, 905), promo_text, fill="red", font=font_medium)
                                    
                                    bundle_dir = os.path.join(os.path.dirname(__file__), "data", "bundles")
                                    os.makedirs(bundle_dir, exist_ok=True)
                                    save_path = os.path.join(bundle_dir, f"single_{prod.jan_code}.jpg")
                                    canvas.save(save_path, quality=95)
                                    
                                    st.success("✅ Image Generated! Right-click and 'Copy Image'.")
                                    st.image(save_path)
                                except Exception as e:
                                    st.error(f"Image generation failed: {e}")

                    new_status = st.selectbox(
                        "Mercari Status",
                        ["Not Listed", "Active", "Paused", "Sold"],
                        index=["Not Listed", "Active", "Paused", "Sold"].index(
                            prod.mercari_status
                        ),
                        key=f"status_{prod.jan_code}",
                    )
                    if new_status != prod.mercari_status:
                        prod.mercari_status = new_status
                        db.commit()
                        st.rerun()

                    # ==========================================
                    # 🚨 NEW: PHASE 4 - MARKET MATCHER (NEGOTIATOR)
                    # ==========================================
                    st.markdown("---")
                    st.markdown("**🤝 Market Matcher (Discount Simulator)**")
                    col_sim1, col_sim2 = st.columns([1, 1.5])
                    
                    with col_sim1:
                        target_price = st.number_input("Target/Requested Price (¥)", 
                                                       min_value=0, 
                                                       value=prod.mercari_price, 
                                                       step=100, 
                                                       key=f"target_{prod.jan_code}")
                    
                    if target_price != prod.mercari_price:
                        from template_engine import simulate_discount
                        sim = simulate_discount(target_price, prod.price, prod.shipping_fee, 100) # Assumes base packaging=100
                        
                        with col_sim2:
                            if sim["status"] == "ACCEPT":
                                st.success(f"🟢 **Safe!** Profit: ¥{sim['simulated_profit']:,}")
                            elif sim["status"] == "COUNTER_OFFER":
                                st.warning(f"🟡 **Low Profit!** Profit: ¥{sim['simulated_profit']:,} (Below ¥400 Floor)")
                            else:
                                st.error(f"🔴 **LOSS ALERT!** Profit: ¥{sim['simulated_profit']:,}")
                        
                        st.code(sim["message"], language="markdown")
                        
                        # 1-Click Update Button if you accept the price
                        if sim["status"] == "ACCEPT" and st.button("✅ Apply New Price to Database", key=f"apply_{prod.jan_code}"):
                            prod.mercari_price = target_price
                            prod.expected_profit = sim["simulated_profit"]
                            prod.updated_at = datetime.utcnow() # Resets the 100-yen drop timer!
                            db.commit()
                            st.toast(f"Price updated to ¥{target_price:,}!", icon="🎉")
                            st.rerun()

                    # ==========================================
                    # 🚨 NEW: DELETE ITEM BUTTON
                    # ==========================================
                    st.markdown("---")
                    if st.button(
                        "🗑️ Delete from Database", key=f"delete_{prod.jan_code}"
                    ):
                        import shutil
                        import os

                        # 1. Plug the Storage Leak: Wipe local images first
                        if prod.image_folder:
                            img_path = os.path.abspath(prod.image_folder)
                            if os.path.exists(img_path) and os.path.isdir(img_path):
                                try:
                                    shutil.rmtree(img_path)
                                except Exception as e:
                                    st.error(f"Failed to delete local images: {e}")

                        # 2. Update the Analytics Tracker
                        track = (
                            db.query(TrackedJan)
                            .filter_by(jan_code=prod.jan_code)
                            .first()
                        )
                        if track:
                            track.status = "Deleted Manually"

                        # 3. Delete from Database
                        db.delete(prod)
                        db.commit()
                        st.rerun()

                with col2:
                    if logs:
                        df = pd.DataFrame(
                            [
                                {"Time": l.timestamp, "Stock": l.stock_quantity}
                                for l in logs[-24:]
                            ]
                        )
                        df.set_index("Time", inplace=True)
                        st.line_chart(df, height=200)
                with col3:
                    st.code(prod.mercari_text, language="markdown")

# ==========================================
# TAB 2: BULK ADD & AUTO-HARVESTER
# ==========================================
with tab_bulk:
    st.markdown("### 🤖 Add Multiple Items to your Database")
    col_a, col_b = st.columns(2)
    jan_list_to_process = []

    with col_a:
        st.markdown("**Option 1: Paste Multiple JAN Codes**")
        raw_jans = st.text_area("Paste JAN codes", height=150)
        if st.button("Process Pasted JANs", type="primary"):
            import re

            jan_list_to_process = re.findall(r"\d{13}", raw_jans)

    with col_b:
        st.markdown("**Option 2: Auto-Harvest from Cainz URL**")
        cainz_url = st.text_input("Enter Cainz Category/Search URL")
        if st.button("Harvest URL & Process", type="primary"):
            with st.spinner("Scraping URL for JAN codes..."):
                jan_list_to_process = harvest_jan_codes(cainz_url, "Auto-Harvest")
                st.success(f"Harvested {len(jan_list_to_process)} JANs!")

# --- 🚨 10X BATCH PROCESSING ENGINE (MULTI-THREADED) ---
    if jan_list_to_process:
        st.markdown(f"### ⚡ Concurrent Processing: {len(jan_list_to_process)} Items...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # 1. Define the isolated worker function (Network only, NO Database calls here!)
        def fetch_cainz_data(jan_code):
            try:
                info = scrape_cainz_product(jan_code)
                price_calc = calculate_price(info['price'], dimensions_cm=info['dimensions_cm'], weight_kg=info.get('weight_kg', 0.0))
                return {"jan": jan_code, "info": info, "calc": price_calc, "error": None}
            except Exception as e:
                return {"jan": jan_code, "info": None, "calc": None, "error": str(e)}

        added = 0
        processed = 0
        
        # 2. Launch 3 concurrent browsers (Max 3 to avoid Cainz Cloudflare DDoS blocks)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(fetch_cainz_data, jan): jan for jan in jan_list_to_process}
            
            for future in as_completed(futures):
                result = future.result()
                jan = result["jan"]
                processed += 1
                status_text.text(f"Processing ({processed}/{len(jan_list_to_process)}): Resolving JAN {jan}...")
                
                # 3. Main Thread Database Commit (100% Safe from SQL Locks)
                if result["error"]:
                    err_str = result["error"]
                    status_msg = "TOS Banned" if "TOS VIOLATION" in err_str else ("404 Discontinued" if "404" in err_str else "Error")
                    track = TrackedJan(jan_code=jan, status=status_msg, notes=err_str, last_checked=datetime.now())
                    db.merge(track)
                else:
                    info = result["info"]
                    price_calc = result["calc"]
                    
                    if info['price'] < 1800:
                        track = TrackedJan(jan_code=jan, status="Skipped: Price too low", notes=f"Price: ¥{info['price']}", last_checked=datetime.now())
                        db.merge(track)
                    # 🚨 PATCHED: Enforced the ¥400 minimum profit floor
                    elif price_calc['actual_profit'] < 400:
                        track = TrackedJan(jan_code=jan, status="Skipped: Low Profit", notes=f"Profit: ¥{price_calc['actual_profit']}", last_checked=datetime.now())
                        db.merge(track)
                    else:
                        existing_prod = db.query(Product).filter_by(jan_code=jan).first()
                        
                        # 🚨 PATCHED: Operator Friction Fix (Auto-Route to Active)
                        if not existing_prod:
                            # Brand new item? If it has stock, make it Active instantly. 
                            preserved_status = "Active" if info['stock_quantity'] > 0 else "Paused"
                        else:
                            # Existing item? Preserve the user's manual choice, but auto-pause if OOS.
                            preserved_status = existing_prod.mercari_status
                            if info['stock_quantity'] == 0 and preserved_status == "Active":
                                preserved_status = "Paused"
                                st.toast(f"Auto-Paused {jan} (Out of Stock!)", icon="🚨")

                        m_text = generate_mercari_text(
                            title=f"【特売】{info['title'][:25]} 新品",
                            specs_text=info['specs'],
                            features_text=info['features'],
                            problem_solution_text="日々の作業を快適にする素晴らしいアイテムです！"
                        )
                        
                        prod = Product(
                            jan_code=info['jan_code'], title=info['title'], price=info['price'],
                            category=info['category'], features=info['features'], specs=info['specs'], 
                            mercari_text=m_text, image_folder=info['image_folder'], 
                            weight_kg=info.get('weight_kg', 0.0),
                            mercari_price=price_calc['final_price'], expected_profit=price_calc['actual_profit'],
                            cainz_url=f"https://www.cainz.com/g/{info['jan_code']}.html",
                            shipping_tier=price_calc['shipping_tier'], shipping_fee=price_calc['shipping_fee'],
                            mercari_status=preserved_status 
                        )
                        db.merge(prod)
                        db.add(InventoryLog(jan_code=info['jan_code'], stock_quantity=info['stock_quantity']))
                        
                        status_msg = "Active & Listed" if info['stock_quantity'] > 0 else "Out of Stock at Sano"
                        db.merge(TrackedJan(jan_code=jan, status=status_msg, last_checked=datetime.now()))
                        added += 1
                
                # Commit exactly once per item
                db.commit()
                progress_bar.progress(processed / len(jan_list_to_process))
                
        status_text.success(f"✅ 10x Batch Complete! {added} High-Profit items secured in record time.")
# ==========================================
# TAB 3: SMART BUNDLE GENERATOR (まとめ売り)
# ==========================================
with tab_bundles:
    st.markdown("### 🛍️ Smart Bundle Generator")
    st.markdown("Build premium thematic solutions and complete starter kits.")

    # Extract only valid Active items
    active_items = db.query(Product).filter_by(mercari_status="Active").all()

    if len(active_items) < 2:
        st.warning(
            "Insufficient Active inventory to calculate bundles (Minimum 2 required)."
        )
    else:
        import math
        import re
        import os
        from PIL import Image, ImageDraw, ImageFont

        st.markdown("#### 🛠️ Custom Solution Builder")
        
        # 1. Multi-select for 2-4 items
        selected_jans = st.multiselect(
            "Select 2 to 4 items to bundle:",
            options=[p.jan_code for p in active_items],
            format_func=lambda jan: next((f"{p.title[:30]}... (¥{p.price})" for p in active_items if p.jan_code == jan), jan),
            max_selections=4
        )
        
        # 2. Custom Title Input
        custom_title = st.text_input(
            "Custom Bundle Theme / Title", 
            placeholder="e.g., 【送料無料】Complete Weekend BBQ Starter Kit"
        )
        
        if len(selected_jans) >= 2:
            selected_items = [p for p in active_items if p.jan_code in selected_jans]
            num_items = len(selected_items)
            
            # Logic to strip brand names
            def strip_brands(title):
                return re.sub(
                    r"カインズ|CAINZ|Kumimoku|kumimoku|ブラック|ホワイト|レッド|ブルー|グリーン|グレー|ブラウン",
                    "",
                    title,
                ).strip()
            
            # Safely extract first meaningful line of features
            def get_clean_feature(text):
                if not text:
                    return "アウトドアや日々の作業を快適にサポートします。"
                text = re.sub(r"✅ 【.*?】", "", text)
                lines = re.split(r"●|■|・|\n", text)
                for line in lines:
                    clean_line = line.strip()
                    if len(clean_line) > 8 and not re.search(
                        r"注意|本来|禁止|危険|保管|しないで|ください|下さい|必ず",
                        clean_line,
                    ):
                        return clean_line[:35] + "…" if len(clean_line) > 35 else clean_line
                return "アウトドアや日々の作業を快適にサポートします。"

            # 🚨 2. YAMATO HARD-CAP CRASH FIX
            bundle_dim = max([item.shipping_tier for item in selected_items]) + (15 * (num_items - 1))
            if bundle_dim > 160:
                st.error(f"🚨 Yamato Hard-Cap Warning: This bundle size is {bundle_dim}cm. You cannot drop this off at PUDO or Convenience Stores! It must be taken directly to a Yamato Sales Office.")
            
            # 🚨 3. STREAMLIT MULTI-SELECT LAG FIX
            if st.button("Calculate Custom Bundle & Generate Image", type="primary"):
                if bundle_dim <= 60:
                    combined_shipping = 750
                elif bundle_dim <= 80:
                    combined_shipping = 850
                elif bundle_dim <= 100:
                    combined_shipping = 1050
                elif bundle_dim <= 120:
                    combined_shipping = 1200
                elif bundle_dim <= 140:
                    combined_shipping = 1450
                elif bundle_dim <= 160:
                    combined_shipping = 1700
                else:
                    combined_shipping = 2100 # Default to max 180 size if over 160
                
                combined_source = sum(item.price for item in selected_items)
                separate_profit = sum(item.expected_profit for item in selected_items)
                separate_shipping = sum(item.shipping_fee for item in selected_items)
                separate_retail = sum(item.mercari_price for item in selected_items)
                
                shipping_savings = separate_shipping - combined_shipping
                
                # 🚨 PREMIUM PRICING: Capture savings + ¥500 curation fee
                bundle_target_profit = separate_profit + shipping_savings + 500
                
                # Assume 150 packaging cost
                pre_fee_total = combined_source + combined_shipping + 150 + bundle_target_profit
                mercari_exact = pre_fee_total / 0.9
                
                # Psychological Pricing (Ends in 80)
                hundreds = math.floor(mercari_exact / 100) * 100
                remainder = mercari_exact - hundreds
                bundle_final_price = int((hundreds + 80) if remainder <= 80 else (hundreds + 180))
                
                bundle_actual_profit = int(
                    (bundle_final_price * 0.9) - combined_source - combined_shipping - 150
                )
                
                # If the calculated premium price somehow makes it more expensive than separate retail
                # The buyer pays the exact same amount or slightly more for the curation
                buyer_savings = separate_retail - bundle_final_price
                
                # Generate fallback title if custom is empty
                if not custom_title:
                    clean_t1 = strip_brands(selected_items[0].title)
                    clean_t2 = strip_brands(selected_items[1].title)
                    safe_title = f"【特別セット】{clean_t1[:15]} ＆ {clean_t2[:15]}"
                else:
                    safe_title = custom_title
                    
                st.markdown("---")
                c1, c2, c3 = st.columns([1, 1, 1.5])
                
                with c1:
                    st.markdown("**💰 Financials**")
                    st.write(f"**Source Cost:** ¥{combined_source:,}")
                    st.write(f"**Bundle Shipping (Size {bundle_dim}):** ¥{combined_shipping:,}")
                    st.metric("Mercari Bundle Price", f"¥{bundle_final_price:,}")
                    
                    st.markdown("---")
                    st.markdown("**🛒 Logistics Actions**")
                    
                    bundle_key_suffix = "_".join([item.jan_code for item in selected_items])
                    
                    if st.button("📂 Open Image Folders", key=f"img_bundle_{bundle_key_suffix}"):
                        success_count = 0
                        for item in selected_items:
                            if not item.image_folder:
                                continue
                            img_path = os.path.normpath(os.path.abspath(item.image_folder))
                            if os.path.exists(img_path) and os.path.isdir(img_path):
                                try:
                                    os.startfile(img_path)
                                    success_count += 1
                                except OSError as e:
                                    st.error(f"OS Error opening {img_path}: {e}")
                        if success_count > 0:
                            st.success(f"{success_count} Folders opened.")
                            
                    # ==========================================
                    # 🚨 MULTI-ITEM COLLAGE GENERATOR
                    # ==========================================
                    with st.spinner("Generating Mercari-optimized collage..."):
                        def get_first_image(folder_path):
                            if not folder_path or not os.path.exists(folder_path):
                                return None
                            # Sort to try and grab _0 or _1 predictably
                            files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                            return os.path.join(folder_path, files[0]) if files else None

                        img_paths = [get_first_image(item.image_folder) for item in selected_items]
                        
                        if any(p is None for p in img_paths):
                            st.error("Missing original images for one or more items. Cannot generate collage.")
                        else:
                            try:
                                from PIL import ImageOps
                                canvas = Image.new("RGB", (1000, 1000), "white")
                                imgs = [Image.open(p).convert("RGB") for p in img_paths]
                                
                                # 🚨 1. THE ASPECT RATIO DISTORTION TRAP FIX
                                if num_items == 2:
                                    # Split vertically (500x1000 each)
                                    padded_img0 = ImageOps.pad(imgs[0], (500, 1000), color='white')
                                    canvas.paste(padded_img0, (0, 0))
                                    padded_img1 = ImageOps.pad(imgs[1], (500, 1000), color='white')
                                    canvas.paste(padded_img1, (500, 0))
                                elif num_items == 3:
                                    # Item 1 top half (1000x500), Items 2 & 3 bottom half (500x500 each)
                                    padded_img0 = ImageOps.pad(imgs[0], (1000, 500), color='white')
                                    canvas.paste(padded_img0, (0, 0))
                                    
                                    padded_img1 = ImageOps.pad(imgs[1], (500, 500), color='white')
                                    canvas.paste(padded_img1, (0, 500))
                                    
                                    padded_img2 = ImageOps.pad(imgs[2], (500, 500), color='white')
                                    canvas.paste(padded_img2, (500, 500))
                                elif num_items == 4:
                                    # 4 equal quadrants (500x500 each)
                                    coords = [(0, 0), (500, 0), (0, 500), (500, 500)]
                                    for idx, img in enumerate(imgs):
                                        padded_img = ImageOps.pad(img, (500, 500), color='white')
                                        canvas.paste(padded_img, coords[idx])
                                
                                # Setup Fonts
                                font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "meiryo.ttc")
                                try:
                                    font_large = ImageFont.truetype(font_path, 60)
                                    font_medium = ImageFont.truetype(font_path, 50)
                                except:
                                    font_large = ImageFont.load_default()
                                    font_medium = ImageFont.load_default()
                                
                                draw = ImageDraw.Draw(canvas)
                                
                                # Draw Red "Free Shipping" Badge
                                draw.rectangle([0, 0, 350, 100], fill="#E60012")
                                draw.text((25, 15), "送料無料", fill="white", font=font_large)
                                
                                # Draw Gold "Discount" Badge
                                draw.rectangle([0, 880, 1000, 1000], fill="#FFD700")
                                discount_text = f"✨ 特別セット：個別購入よりお買い得！ ✨"
                                text_bbox = draw.textbbox((0, 0), discount_text, font=font_medium)
                                text_x = (1000 - (text_bbox[2] - text_bbox[0])) / 2
                                draw.text((text_x, 905), discount_text, fill="red", font=font_medium)
                                
                                bundle_dir = os.path.join(os.path.dirname(__file__), "data", "bundles")
                                os.makedirs(bundle_dir, exist_ok=True)
                                save_path = os.path.join(bundle_dir, f"bundle_{bundle_key_suffix}.jpg")
                                canvas.save(save_path, quality=95)
                                
                                st.success("✅ Image Generated! Right-click the image below and select 'Copy Image', then paste into Mercari.")
                                st.image(save_path)
                            except Exception as e:
                                st.error(f"Image generation failed: {e}")

                with c2:
                    st.markdown("**📈 Arbitrage Stats**")
                    st.metric("Profit if sold separately", f"¥{separate_profit:,}")
                    st.metric(
                        "New Profit (Bundled)",
                        f"¥{bundle_actual_profit:,}",
                        delta=f"+¥{bundle_actual_profit - separate_profit:,} Bonus",
                    )
                    if buyer_savings > 0:
                        st.info(f"🎁 **Buyer Saves vs Retail:** ¥{buyer_savings:,}")
                    else:
                        st.info(f"💎 **Premium Value:** ¥{-buyer_savings:,}")

                with c3:
                    st.markdown("**📋 Bundle Listing Copy**")
                    
                    # Build Item Features List
                    items_text = ""
                    for i, item in enumerate(selected_items):
                        clean_title = strip_brands(item.title)
                        safe_text = f"{item.features or ''} {item.specs or ''}"
                        feat = get_clean_feature(safe_text)
                        items_text += f"{(i+1)} {clean_title}\n・{feat}\n\n"

                    bundle_text = f"""{safe_title}

【商品の状態】
新品・未使用

【商品説明】
✨ご覧いただきありがとうございます✨
合同会社Jayani NEXUSです。

相性抜群の大人気アイテムを組み合わせた【特別セット】のご案内です！
日々の作業やアウトドアを快適にする充実のセット内容となっております。

◆ セット内容
{items_text.strip()}

◆ 【重要なお知らせ】
※大変人気の商品セットにつき、いずれかが他で売り切れた場合、予告なくこちらのセット出品も削除いたします。
※限界までお安くしたセット特別価格のため「お値下げ交渉」ならびに「バラ売り」はご遠慮いただいております。

✅ 即購入大歓迎です！
水濡れ・衝撃対策を徹底し、安全な「らくらくメルカリ便（匿名配送）」にて丁寧におまとめして発送いたします。
"""
                    st.code(bundle_text, language="markdown")

# ==========================================
# TAB 4: VISUAL COMMAND CENTER
# ==========================================
with tab_analytics:
    st.markdown("### 📈 Visual Command Center")
    st.markdown("Analytics using Streamlit's native rendering engine for stability.")

    tracked = db.query(TrackedJan).all()
    active_prods = db.query(Product).all()

    if not tracked and not active_prods:
        st.info("No data available yet. Run the Auto-Harvester first!")
    else:
        # --- ROW 1: Sourcing Health & Mercari Funnel ---
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**Scraping Engine Health**")
            if tracked:
                df_track = pd.DataFrame([{"Status": t.status} for t in tracked])
                # Using native Streamlit Bar Chart for stability
                status_counts = df_track["Status"].value_counts()
                st.bar_chart(status_counts)

        with chart_col2:
            st.markdown("**Mercari Listing Funnel**")
            if active_prods:
                df_funnel = pd.DataFrame(
                    [{"Mercari Status": p.mercari_status} for p in active_prods]
                )
                funnel_counts = df_funnel["Mercari Status"].value_counts()
                st.bar_chart(funnel_counts)

        st.divider()

        # --- ROW 2: Category Performance & ROI ---
        if active_prods:
            bar_col1, bar_col2 = st.columns([1.5, 1])

            # Prepare clean data
            scatter_data = []
            for p in active_prods:
                logs = (
                    db.query(InventoryLog)
                    .filter_by(jan_code=p.jan_code)
                    .order_by(InventoryLog.timestamp)
                    .all()
                )
                real_stock = int(logs[-1].stock_quantity) if logs else 0

                # Safely convert to float
                source_price = float(p.price) if p.price else 0.0
                net_profit = float(p.expected_profit) if p.expected_profit else 0.0

                scatter_data.append(
                    {
                        "Title": str(p.title[:30]),
                        "Source Price": source_price,
                        "Net Profit": net_profit,
                        "Stock": real_stock,
                        "Category": (
                            str(p.category).split(">")[-1].strip()
                            if p.category
                            else "Uncategorized"
                        ),
                    }
                )

            df_scatter = pd.DataFrame(scatter_data)

            with bar_col1:
                st.markdown("#### 🎯 Net Profit vs. Source Price")

                if not df_scatter.empty:
                    # 🚨 NATIVE STREAMLIT SCATTER CHART (No Plotly needed)
                    st.scatter_chart(
                        df_scatter,
                        x="Source Price",
                        y="Net Profit",
                        size="Stock",
                        color="Category",
                        use_container_width=True,
                    )
                else:
                    st.warning("No pricing data available to draw chart.")

            with bar_col2:
                st.markdown("#### 🏆 Profit by Category")
                if not df_scatter.empty:
                    # Group by category and sum the profit
                    df_cat_grouped = df_scatter.groupby("Category")["Net Profit"].sum()
                    st.bar_chart(df_cat_grouped, use_container_width=True)

            # Basic Insight Generation
            st.markdown("---")
            if not df_scatter.empty and df_scatter["Net Profit"].max() > 0:
                best_item = df_scatter.loc[df_scatter["Net Profit"].idxmax()]
                st.success(
                    f"🤖 **Insight:** Your highest potential earner is **{best_item['Title']}** with a profit of **¥{best_item['Net Profit']:,.0f}**. Ensure this item's Mercari status is set to 'Active'."
                )

# ==========================================
# TAB 5: CRM & MESSAGE TEMPLATES
# ==========================================
with tab_crm:
    from crm_engine import generate_crm_response
    
    st.markdown("### 💬 Customer Relationship Management (CRM)")
    st.markdown("Generate Mercari-safe, highly professional Japanese responses to instantly resolve buyer issues and prevent account strikes.")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.markdown("#### 1. Transaction Details")
        buyer_name = st.text_input("Buyer Name (購入者名)", placeholder="例: リン")
        item_name = st.text_input("Item Name (商品名)", placeholder="例: Kumimoku ツールボックス")
        
        st.markdown("#### 2. Select Scenario")
        scenario = st.selectbox("What happened?",[
            "1. 御礼・発送予定 (Thank You & Shipping Update)",
            "2. 発送完了 (Shipping Completed)",
            "3. 欠品キャンセル (Out of Stock / Defect Cancellation)",
            "4. 配送中の破損・トラブル (Damaged in Transit)",
            "5. 部品不足・商品不備 (Missing Parts - Full Refund)"
        ])
        
    with col2:
        st.markdown("#### 📋 Generated Response")
        response_text = generate_crm_response(scenario, buyer_name, item_name)
        
        # Display the text in a code block for 1-click copying
        st.code(response_text, language="markdown")
        
        if "キャンセル" in scenario or "不足" in scenario:
            st.error("⚠️ **Safety Warning:** Do not click 'Cancel' yourself. Ask the buyer to contact support or use this template to let support handle it. This protects your account from automated cancellation strikes.")

db.close()
