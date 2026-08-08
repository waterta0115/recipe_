import os
import time
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. .env から環境変数を読み込み
load_dotenv()

RAKUTEN_APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not RAKUTEN_APPLICATION_ID:
    raise ValueError(".env ファイルに RAKUTEN_APPLICATION_ID が設定されていません。")
if not GOOGLE_API_KEY:
    raise ValueError(".env ファイルに GOOGLE_API_KEY が設定されていません。")

# --- 2. 出力データ構造の定義 (Pydantic) ---
class Ingredient(BaseModel):
    name: str = Field(description="食材名（例: 玉ねぎ、豚バラ肉）")
    amount: str = Field(description="全体に必要な合計数量（例: 2個、300g）")
    category: str = Field(description="分類（例: 野菜、肉類、魚介類、調味料、加工食品、その他）")

class ShoppingListResponse(BaseModel):
    shopping_list: list[Ingredient] = Field(description="重複をまとめ合算した買い物リスト")


# --- 3. 楽天レシピAPIからデータ取得関数 ---
def fetch_rakuten_recipes(category_id="10", count=2):
    """
    楽天レシピAPI（カテゴリランキング）からレシピ情報を取得する
    ※ category_id: 10(肉), 11(魚), 12(野菜), 30(人気メニュー) など
    """
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "categoryId": category_id,
        "formatVersion": "2"  # レスポンス形式を標準化
    }
    
    print(f"楽天レシピAPIからデータを取得中... (Category ID: {category_id})")
    response = requests.get(url, params=params)
    
    # 楽天APIの利用制限（1sec/req）を考慮したウェイト
    time.sleep(1.2)
    
    if response.status_code != 200:
        print(f"楽天APIエラー: Status Code {response.status_code}")
        print(f"詳細: {response.text}")
        return []

    data = response.json()
    recipes = data.get("result", [])[:count]
    
    extracted_recipes = []
    for r in recipes:
        # 食材リスト（配列または文字列）を抽出
        materials = r.get("recipeMaterial", [])
        extracted_recipes.append({
            "title": r.get("recipeTitle"),
            "url": r.get("recipeUrl"),
            "materials": materials
        })
    
    return extracted_recipes


# --- 4. メイン処理 ---
def main():
    print("=== プログラムの実行を開始しました ===")
    print(f"[DEBUG] 読み込まれた楽天アプリID: '{RAKUTEN_APPLICATION_ID}'")
    print(f"[DEBUG] 文字数: {len(RAKUTEN_APPLICATION_ID) if RAKUTEN_APPLICATION_ID else 0}")
    # 肉(10)、魚(11)、野菜(12)の大カテゴリIDからレシピを取得
    category_ids = ["10", "11", "12"]
    all_raw_recipes = []
    
    for cat_id in category_ids:
        recipes = fetch_rakuten_recipes(category_id=cat_id, count=2)
        all_raw_recipes.extend(recipes)

    if not all_raw_recipes:
        print("レシピデータが取得できませんでした。.env の RAKUTEN_APPLICATION_ID を確認してください。")
        return

    print("\n--- 取得した楽天レシピ一覧 ---")
    all_materials_text = ""
    for idx, r in enumerate(all_raw_recipes, 1):
        print(f"{idx}. {r['title']} ({r['url']})")
        materials_str = ", ".join(r['materials']) if isinstance(r['materials'], list) else str(r['materials'])
        all_materials_text += f"【レシピ{idx}: {r['title']}】\n材料: {materials_str}\n\n"

    # Gemini API に材料データを渡して解析・集計
    print("Gemini APIに材料データの抽出・集計・合算をリクエスト中...")
    
    client = genai.Client()
    
    prompt = f"""
以下は楽天レシピAPIから取得した複数のレシピとそれぞれの材料リストです。
これらの材料を解析し、重複している食材を合算して1つの「買い物リスト」としてまとめてください。

【生の材料データ】
{all_materials_text}

【条件】
- 「玉ねぎ 1/2個」と「玉ねぎ 1個」のように重複しているものは「玉ねぎ 1.5個」や「玉ねぎ 2個」のように合算・整理してください。
- 数量が「少々」や「お好みで」といった曖昧な表現の場合は、適量としてまとめてください。
- 食材ごとに適切なカテゴリ（野菜、肉類、魚介類、調味料、その他）を付与してください。
"""

    response = client.models.generate_content(
        model='gemini-1.5-flash',  # 最新の標準モデル名に修正
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShoppingListResponse,
            temperature=0.2,
        ),
    )

    print("\n=================== 統合・合算された買い物リスト (JSON) ===================")
    print(response.text)


if __name__ == "__main__":
    main()