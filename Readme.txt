Cainz to Mercari Management Dashboard

Cainz ➡️ Mercari Manager Walkthrough
The Mercari Management Dashboard has been fully implemented. Instead of manually copying and rewriting product descriptions, you can now use this local app as your command center.

What Was Built
scraper.py (The Engine) A Playwright automation script designed to navigate cainz.com invisibly. When given a JAN code, it visits the product page, extracts the Title, Price, Features, and attempts to pull Sano store inventory. It also downloads up to 3 high-quality product images into local project folders.

template_engine.py (The Brains) We converted your Mlft.txt logic into native Python algorithms. It mathematically calculates the Pre-Fee padding, your 20% target margins, size shipping variables, and performs the "Psychological Pricing" (rounding to standard ¥80 endings). It outputs the full Godo Gaisha professionally formatted descriptions.

models.py (The Memory) A local SQLite database storing your catalog of imported products along with their profit margins and their time-stamped inventory levels.

app.py (The Interface) A beautiful, interactive Streamlit local web page allowing you to add products visually, monitor your net profit on active listings, and view line-chart graphs of Sano-store inventory to avoid stockouts.

How to Run It
To launch your dashboard, run the following command in PowerShell:

powershell
cd c:\Users\praba\OneDrive\Documents\OnlineMarket\mercari_manager
& "C:\Users\praba\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py
This will automatically pop open a web browser tab with your dashboard.

How to Track 60-Minute Sano Inventory
To track stock passively every hour without leaving your browser dashboard open, I recommend running the automated scraper.py background function once an hour using Windows Task Scheduler:

Open Windows Task Scheduler
Create a Basic Task triggered "Every 1 Hour"
Action: Start a program
Program: C:\Users\praba\AppData\Local\Programs\Python\Python312\python.exe
Arguments: -c "from scraper import update_inventory_for_all; update_inventory_for_all()"
Start in: c:\Users\praba\OneDrive\Documents\OnlineMarket\mercari_manager
Or simply run the script manually whenever you want a fresh scan!