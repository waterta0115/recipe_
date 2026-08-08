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
    shopping_list: list[Ingredient] = Field(description="買い物リスト")


# --- 3. 楽天レシピAPIからデータ取得関数 ---
def fetch_rakuten_recipes(category_id="30", count=4):
    """
    楽天レシピAPI（人気ピックアップ）からレシピ情報を取得する
    ※デフォルト category_id="30" は人気メニューカテゴリ（肉・魚・野菜など適宜指定可能）
    """
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "categoryId": category_id,
    }
    
    print(f"楽天レシピAPIからデータを取得中... (Category ID: {category_id})")
    response = requests.get(url, params=params)
    
    # 楽天APIの利用制限制限（1sec/req）を遵守するためのウェイト処理
    time.sleep(1.2)
    
    if response.status_code != 200:
        print(f"楽天APIエラー: Status Code {response.status_code}")
        return []

    data = response.json()
    recipes = data.get("result", [])[:count]
    
    extracted_recipes = []
    for r in recipes:
        extracted_recipes.append({
            "title": r.get("recipeTitle"),
            "url": r.get("recipeUrl"),
            "materials": r.get("recipeMaterial")  # 例: ["玉ねぎ 1/2個", "豚肉 200g", "塩コショウ 少々"]
        })
    
    return extracted_recipes


# --- 4. メイン処理 ---
def main():
    print("=== プログラムの実行を開始しました ===")
    # A. 楽天レシピAPIから複数レシピと材料を取得
    # 例として「人気カテゴリ(30)」「肉(10)」「野菜(12)」からレシピを取得
    category_ids = ["30", "10", "12"]
    all_raw_recipes = []
    
    for cat_id in category_ids:
        recipes = fetch_rakuten_recipes(category_id=cat_id, count=2)
        all_raw_recipes.extend(recipes)

    print("\n--- 取得した楽天レシピ一覧 ---")
    all_materials_text = ""
    for idx, r in enumerate(all_raw_recipes, 1):
        print(f"{idx}. {r['title']} ({r['url']})")
        materials_str = ", ".join(r['materials'])
        all_materials_text += f"【レシピ{idx}: {r['title']}】\n材料: {materials_str}\n\n"

    # B. 取得した全材料データを Gemini API に渡して解析・整理
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
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShoppingListResponse,
            temperature=0.2, # データ解析なので低めの値に設定
        ),
    )

    print("\n=================== 統合・合算された買い物リスト (JSON) ===================")
    print(response.text)


if __name__ == "__main__":
    main()