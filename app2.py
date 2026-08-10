import os
import re
import time
import requests
from dotenv import load_dotenv

# 1. .env から環境変数を読み込み
load_dotenv()

RAKUTEN_APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "").strip()
RAKUTEN_ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY", "").strip()

if not RAKUTEN_APPLICATION_ID or not RAKUTEN_ACCESS_KEY:
    raise ValueError(".env ファイルの RAKUTEN_APPLICATION_ID または RAKUTEN_ACCESS_KEY が設定されていません。")


# --- 設定: アレルギー・除外したい食材キーワードを指定 ---
EXCLUDE_KEYWORDS = ["エビ", "えび", "ピーナッツ", "ネギ", "ねぎ"]


# --- 2. recipeCost 文字列から数値 (int) を抽出する関数 ---
def extract_cost_int(cost_str):
    if not cost_str or cost_str == "指定なし":
        return 0
    cleaned_str = str(cost_str).replace(",", "")
    match = re.search(r'\d+', cleaned_str)
    return int(match.group()) if match else 0


# --- 3. 楽天レシピAPIからデータ取得関数 ---
def fetch_rakuten_recipes(category_id=None, count=5):
    url = "https://openapi.rakuten.co.jp/recipems/api/Recipe/CategoryRanking/20170426"
    
    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "format": "json",
        "formatVersion": "2"
    }
    
    if category_id:
        params["categoryId"] = str(category_id)
    
    print("楽天レシピAPIからデータを取得中...")
    response = requests.get(url, params=params)
    time.sleep(1.2)
    
    if response.status_code != 200:
        print(f"楽天APIエラー: Status Code {response.status_code}")
        print(f"詳細: {response.text}")
        return []

    data = response.json()
    recipes = data.get("result", [])[:count]
    
    extracted_recipes = []
    for r in recipes:
        cost_raw = r.get("recipeCost", "指定なし")
        cost_val = extract_cost_int(cost_raw)
        
        extracted_recipes.append({
            "title": r.get("recipeTitle"),
            "url": r.get("recipeUrl"),
            "materials": r.get("recipeMaterial", []),
            "cost_raw": cost_raw,
            "cost_int": cost_val
        })
    
    return extracted_recipes


# --- 4. 材料名の集計・アレルギーフィルタリング処理 ---
def generate_shopping_list(recipes, exclude_list):
    """
    指定した除外キーワードが含まれる材料を取り除き、残りの材料を集計する
    """
    ingredient_counts = {}
    excluded_items = set()  # 除外された材料の記録

    for recipe in recipes:
        materials = recipe.get("materials", [])
        for item in materials:
            name = item.strip()
            if not name:
                continue

            # 除外キーワードが含まれているかチェック
            is_excluded = any(ex_word in name for ex_word in exclude_list)

            if is_excluded:
                excluded_items.add(name)
            else:
                ingredient_counts[name] = ingredient_counts.get(name, 0) + 1

    shopping_list = [
        {"name": name, "count": count}
        for name, count in sorted(ingredient_counts.items())
    ]
    
    return shopping_list, list(excluded_items)


# --- 5. メイン処理 ---
def main():
    print("=== プログラムの実行を開始しました ===")
    print(f"【設定中の除外キーワード】: {', '.join(EXCLUDE_KEYWORDS)}\n")
    
    category_ids = [None]
    all_recipes = []

    for cat_id in category_ids:
        recipes = fetch_rakuten_recipes(category_id=cat_id, count=5)
        all_recipes.extend(recipes)

    if not all_recipes:
        print("レシピデータが取得できませんでした。")
        return

    print("\n--- 取得した楽天レシピ一覧と費用 ---")
    total_estimated_cost = 0

    for idx, r in enumerate(all_recipes, 1):
        cost_raw = r.get("cost_raw", "指定なし")
        cost_int = r.get("cost_int", 0)
        
        # アレルギー・除外食材が含まれるレシピかチェックして警告マークを表示
        contains_warning = any(
            any(ex_word in mat for ex_word in EXCLUDE_KEYWORDS) 
            for mat in r.get("materials", [])
        )
        warning_tag = " ⚠️ [除外対象が含まれます]" if contains_warning else ""
        
        print(f"{idx}. {r.get('title')}{warning_tag}")
        print(f"   費用の目安 (API返却値): {cost_raw}  ->  抽出数値: {cost_int}円")
        print(f"   材料: {', '.join(r.get('materials', []))}\n")
        
        total_estimated_cost += cost_int

    # 材料の集計とフィルタリングを実行
    shopping_list, excluded_materials = generate_shopping_list(all_recipes, EXCLUDE_KEYWORDS)

    print("=================== 統合・合算された買い物リスト (除外後) ===================")
    for idx, item in enumerate(shopping_list, 1):
        note = f" (★ {item['count']}個のレシピで使用)" if item['count'] > 1 else ""
        print(f"{idx}. {item['name']}{note}")

    if excluded_materials:
        print("\n------------------- 🚫 買い物リストから自動除外された材料 -------------------")
        for mat in excluded_materials:
            print(f"・{mat}")

    print("\n=================== 費用の合計目安 ===================")
    print(f"全{len(all_recipes)}件のレシピの目安費用合計: およそ {total_estimated_cost:,} 円")


if __name__ == "__main__":
    main()