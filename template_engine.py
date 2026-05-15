# template_engine.py
import math

def calculate_price(source_price, dimensions_cm=120, weight_kg=0.0, packaging_cost=100, custom_profit=None):
    """
    Applies the EXACT Yamato Rakuraku Mercari Matrix (Size AND Weight) up to Size 200.
    """
    # 1. Determine Tier by physical Dimensions
    if dimensions_cm <= 30: dim_tier = 210  
    elif dimensions_cm <= 45: dim_tier = 520  
    elif dimensions_cm <= 60: dim_tier = 750
    elif dimensions_cm <= 80: dim_tier = 850
    elif dimensions_cm <= 100: dim_tier = 1050
    elif dimensions_cm <= 120: dim_tier = 1200
    elif dimensions_cm <= 140: dim_tier = 1450
    elif dimensions_cm <= 160: dim_tier = 1700
    elif dimensions_cm <= 180: dim_tier = 2100
    else: dim_tier = 2500 # 🚨 PATCHED: Size 200 Max Limit

    # 2. Determine Tier by Weight (Yamato Rules)
    weight_tier = 0
    if weight_kg > 0:
        if weight_kg <= 1.0 and dim_tier == 210: weight_tier = 210
        elif weight_kg <= 2.0: weight_tier = 750
        elif weight_kg <= 5.0: weight_tier = 850
        elif weight_kg <= 10.0: weight_tier = 1050
        elif weight_kg <= 15.0: weight_tier = 1200
        elif weight_kg <= 20.0: weight_tier = 1450
        elif weight_kg <= 25.0: weight_tier = 1700
        elif weight_kg <= 30.0: weight_tier = 2500 # 180 and 200 sizes cap at 30kg
        else: weight_tier = 2500

    shipping_fee = max(dim_tier, weight_tier)
    
    if shipping_fee >= 1450 or weight_kg >= 15.0:
        shipping_fee += 100 # Pick-up fee
        
    if shipping_fee <= 520: packaging_cost = 50
    elif shipping_fee >= 1450: packaging_cost = 200
    else: packaging_cost = 100

    # 🚨 PATCHED: Absolute Floor of ¥400 Minimum Profit
    target_profit = custom_profit if custom_profit is not None else max(int(source_price * 0.20), 400)
    
    pre_fee_total = source_price + shipping_fee + packaging_cost + target_profit
    mercari_exact = pre_fee_total / 0.9
    
    hundreds = math.floor(mercari_exact / 100) * 100
    remainder = mercari_exact - hundreds
    final_price = int((hundreds + 80) if remainder <= 80 else (hundreds + 180))
        
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
    
    # 🚨 PATCHED: Removed all Cainz branding. Added FOMO tags.
    dynamic_tags = "#特売 #送料無料 #匿名配送 #新生活 "
    if "Kumimoku" in title or "工具" in title or "DIY" in specs_text:
        dynamic_tags += "#DIY #工具箱 #ガレージ #日曜大工 "
    if "キャンプ" in features_text or "アウトドア" in features_text or "バーベキュー" in title:
        dynamic_tags += "#アウトドア #キャンプ #BBQ #レジャー "
    if "犬" in title or "猫" in title or "ペット用品" in specs_text or "ペット用" in features_text:
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

def simulate_discount(target_price, source_price, shipping_fee, packaging_cost=100):
    """
    Simulates profit for a requested discount and generates a negotiation response.
    """
    # 1. Calculate simulated profit
    mercari_fee = math.floor(target_price * 0.1)
    seller_proceeds = target_price - mercari_fee
    simulated_profit = int(seller_proceeds - source_price - shipping_fee - packaging_cost)
    
    # 2. Minimum Floor
    FLOOR_PROFIT = 400
    
    if simulated_profit >= FLOOR_PROFIT:
        status = "ACCEPT"
        message = f"コメントありがとうございます！\nせっかくお声がけいただきましたので、ご希望の【{target_price}円】にてお譲りさせていただきます。\n価格を変更いたしましたので、よろしければそのままご購入へお進みくださいませ。\nよろしくお願いいたします。"
    elif simulated_profit >= 0:
        status = "COUNTER_OFFER"
        # Calculate lowest acceptable price to hit the floor
        required_pre_fee = source_price + shipping_fee + packaging_cost + FLOOR_PROFIT
        exact_target = required_pre_fee / 0.9
        
        hundreds = math.floor(exact_target / 100) * 100
        remainder = exact_target - hundreds
        counter_price = int((hundreds + 80) if remainder <= 80 else (hundreds + 180))
        
        message = f"コメントいただきありがとうございます！\n大変恐縮なのですが、こちらの商品は大型で送料（{shipping_fee}円）がかかってしまうため、ご提示いただいた金額までのお値下げが少し厳しい状況です。\nですが、せっかくご検討いただいておりますので、ギリギリまで頑張らせていただき【{counter_price:,}円】でしたらお譲り可能ですが、いかがでしょうか？\nご希望に添えず申し訳ございませんが、ご検討いただけますと幸いです。"
    else:
        status = "REJECT"
        message = "コメントいただきありがとうございます！\n大変申し訳ございませんが、こちらの商品は送料・手数料の関係上、現在の価格がギリギリの設定となっております。そのため、これ以上のお値下げは難しい状況です。\nご希望に添えず誠に申し訳ございませんが、現在の価格にてご検討いただけますと幸いです。"

    return {
        "simulated_profit": simulated_profit,
        "status": status,
        "message": message
    }