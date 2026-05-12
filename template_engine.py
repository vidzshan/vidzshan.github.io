# template_engine.py
import math

def calculate_price(source_price, dimensions_cm=120, packaging_cost=100, custom_profit=None):
    """
    Apply Financial Model & Mercari Shipping Guide logic (2026 Standards).
    """
    # Dynamic Shipping calculation based on Rakuraku Mercari Yamato Rates
    if dimensions_cm <= 30: 
        shipping_fee = 210  # Nekoposu (A4 size, under 3cm)
    elif dimensions_cm <= 45:
        shipping_fee = 520  # Takkyubin Compact (450 yen + 70 yen dedicated box cost)
    elif dimensions_cm <= 60: 
        shipping_fee = 750
    elif dimensions_cm <= 80: 
        shipping_fee = 850
    elif dimensions_cm <= 100: 
        shipping_fee = 1050
    elif dimensions_cm <= 120: 
        shipping_fee = 1200
    elif dimensions_cm <= 140: 
        shipping_fee = 1450
    elif dimensions_cm <= 160: 
        shipping_fee = 1700
    else: 
        shipping_fee = 2100 # 180 size
    
    target_profit = custom_profit if custom_profit is not None else int(source_price * 0.20)
    pre_fee_total = source_price + shipping_fee + packaging_cost + target_profit
    
    # Mercari 10% Fee Margin (Divide by 0.9)
    mercari_exact = pre_fee_total / 0.9
    
    # Psychological Pricing (Ends in 80 for highest CVR)
    hundreds = math.floor(mercari_exact / 100) * 100
    remainder = mercari_exact - hundreds
    final_price = int((hundreds + 80) if remainder <= 80 else (hundreds + 180))
        
    # EXACT Mercari Payout Math
    mercari_fee = math.floor(final_price * 0.1)
    seller_proceeds = final_price - mercari_fee
    actual_profit = int(seller_proceeds - source_price - shipping_fee - packaging_cost)
    
    return {
        "source_price": source_price,
        "shipping_fee": shipping_fee,
        "shipping_tier": dimensions_cm,
        "packaging_cost": packaging_cost,
        "target_profit": target_profit,
        "pre_fee_total": pre_fee_total,
        "mercari_exact": mercari_exact,
        "final_price": final_price,
        "actual_profit": actual_profit
    }


def generate_mercari_text(title, specs_text, features_text, problem_solution_text):
    """
    Generates the Mercari formatting. 
    (No English, No hardcoded prices, purely domestic corporate trust format).
    """
    
    # DYNAMIC HASHTAGS
    dynamic_tags = "#カインズ #CAINZ #新生活 #送料無料 "
    if "Kumimoku" in title or "工具" in title or "DIY" in specs_text:
        dynamic_tags += "#Kumimoku #DIY #工具箱 #ガレージ "
    if "キャンプ" in features_text or "アウトドア" in features_text:
        dynamic_tags += "#アウトドア #キャンプ #BBQ "
    if "犬" in title or "猫" in title or "ペット" in specs_text:
        dynamic_tags += "#ペット用品 #犬 #猫 "
    if "収納" in title or "収納" in features_text:
        dynamic_tags += "#収納 #インテリア #整理整頓 "

    # Force the title to strictly obey Mercari's 40-character limit
    clean_title = title[:40]

    return f"""【出品用タイトル】
{clean_title}

【カテゴリー】
インテリア・住まい・小物 > その他
（または 該当する適切なカテゴリー）

【商品の状態】
新品・未使用

【商品説明】
✨ご覧いただきありがとうございます✨

合同会社Jayani NEXUS（ジャヤニ ネクサス）です。
当店では、皆様の暮らしをより豊かにする、高品質なアイテムを厳選してお届けしております。安心・安全の法人運営ですので、どうぞご安心してお取引くださいませ。

◆ 【重要なお知らせ】
※大変人気の商品につき、他で在庫が切れた場合、予告なく出品を直ちに削除いたします。再出品できない場合がございますので、お早めにご検討ください。
※ギリギリの価格設定のため、誠に恐れ入りますが「お値下げ交渉」はご遠慮いただいております。

{problem_solution_text}

■ 商品の特徴
{features_text}

■ 商品仕様
{specs_text}

◆ 発送・梱包について
・送料無料（出品者負担）でお届けいたします。
・プライバシーと安全に完全に配慮した「らくらくメルカリ便（匿名配送）」を利用いたします。
・水濡れや衝撃を防止するため丁寧に梱包し、クリーンな環境から迅速に出荷いたします。
（※ペット飼育なし・喫煙者なしの環境です）

✅ 即購入大歓迎です！
事前のコメント等は不要ですので、そのままご購入にお進みください。
ご不明な点がございましたら、いつでもお気軽にコメントくださいませ。
皆様と素敵なご縁がありますように、よろしくお願いいたします。

▼ 検索用タグ
{dynamic_tags}
"""