import sys
import os
sys.path.append('c:\\Users\\praba\\Documents\\OnlineMarket\\mercari_manager')
from models import SessionLocal, Product, InventoryLog, TrackedJan
import pandas as pd
import plotly.express as px

db = SessionLocal()
active_prods = db.query(Product).all()

scatter_data = []
for p in active_prods:
    logs = (
        db.query(InventoryLog)
        .filter_by(jan_code=p.jan_code)
        .order_by(InventoryLog.timestamp)
        .all()
    )
    real_stock = int(logs[-1].stock_quantity) if logs else 0
    
    try:
        source_price = float(p.price) if p.price else 0.0
        net_profit = float(p.expected_profit) if p.expected_profit else 0.0
        margin_pct = (
            float(round((net_profit / source_price) * 100, 1))
            if source_price > 0
            else 0.0
        )
    except:
        source_price, net_profit, margin_pct = 0.0, 0.0, 0.0
    
    scatter_data.append(
        {
            "Title": str(p.title[:30]) + "..." if p.title else "Unknown",
            "Source Price": source_price,
            "Net Profit": net_profit,
            "Margin (%)": margin_pct,
            "Visual Size": max(real_stock, 1),
            "Actual Stock": real_stock,
            "Category": (
                str(p.category).split(">")[-1].strip()
                if p.category
                else "Uncategorized"
            ),
            "Status": str(p.mercari_status),
        }
    )

df_scatter = pd.DataFrame(scatter_data)
df_scatter["Source Price"] = pd.to_numeric(df_scatter["Source Price"], errors="coerce").fillna(0)
df_scatter["Net Profit"] = pd.to_numeric(df_scatter["Net Profit"], errors="coerce").fillna(0)
df_scatter["Margin (%)"] = pd.to_numeric(df_scatter["Margin (%)"], errors="coerce").fillna(0)
df_scatter["Visual Size"] = pd.to_numeric(df_scatter["Visual Size"], errors="coerce").fillna(1)

print("Dataframe shape:", df_scatter.shape)

if not df_scatter.empty:
    try:
        fig_scatter = px.scatter(
            df_scatter,
            x="Source Price",
            y="Net Profit",
            size="Visual Size",
            color="Margin (%)",
            hover_name="Title",
            color_continuous_scale="Turbo",
            size_max=35,
            hover_data={
                "Visual Size": False,
                "Actual Stock": True,
                "Status": True,
            },
        )
        # Try to render it to json to see if Plotly crashes
        fig_json = fig_scatter.to_json()
        print("Scatter plot created successfully.")
    except Exception as e:
        print("Error creating scatter plot:", e)
        
    try:
        df_cat_grouped = df_scatter.groupby("Category")["Net Profit"].sum().reset_index()
        fig_bar = px.bar(
            df_cat_grouped,
            x="Net Profit",
            y="Category",
            orientation="h",
            color="Net Profit",
            color_continuous_scale="Greens",
        )
        fig_json = fig_bar.to_json()
        print("Bar plot created successfully.")
    except Exception as e:
        print("Error creating bar plot:", e)
else:
    print("Dataframe is empty.")
