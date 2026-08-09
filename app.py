import os
import time
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. .env から環境変数を読み込み
load_dotenv()

# .strip() を追加して前後の空白・改行コードを強制除去
RAKUTEN_APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "").strip()
RAKUTEN_ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

if not RAKUTEN_APPLICATION_ID:
    raise ValueError(".env ファイルに RAKUTEN_APPLICATION_ID が設定されていません。")
if not RAKUTEN_ACCESS_KEY:
    raise ValueError(".env ファイルに RAKUTEN_ACCESS_KEY が設定されていません。")
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
def fetch_rakuten_recipes(category_id=None, count=4):
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
    
    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "formatVersion": "2"
    }
    
    if category_id:
        params["categoryId"] = str(category_id)
    
    print(f"楽天レシピAPIからデータを取得中...")
    
    # 送信直前のリクエストを生成
    req = requests.Request('GET', url, params=params).prepare()
    print(f"[DEBUG] 送信URL: {req.url}")  # 送信される実際のURLを確認
    
    session = requests.Session()
    response = session.send(req)
    
    time.sleep(1.2)
    
    if response.status_code != 200:
        print(f"楽天APIエラー: Status Code {response.status_code}")
        print(f"詳細: {response.text}")
        return []

    data = response.json()
    recipes = data.get("result", [])[:count]
    
    extracted_recipes = []
    for r in recipes:
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
    
    all_raw_recipes = fetch_rakuten_recipes(category_id=None, count=4)

    if not all_raw_recipes:
        print("\n[確認] 楽天APIからエラーが返っています。")
        print("1. .env に余計な引用符(\")やスペースが入っていないか確認してください。")
        print("2. 楽天デベロッパーの管理画面でアプリID/Access Keyを発行し直してみてください。")
        return

    print("\n--- 取得した楽天レシピ一覧 ---")
    all_materials_text = ""
    for idx, r in enumerate(all_raw_recipes, 1):
        print(f"{idx}. {r['title']} ({r['url']})")
        materials_str = ", ".join(r['materials']) if isinstance(r['materials'], list) else str(r['materials'])
        all_materials_text += f"【レシピ{idx}: {r['title']}】\n材料: {materials_str}\n\n"

    print("\nGemini APIに材料データの抽出・集計・合算をリクエスト中...")
    
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
        model='gemini-1.5-flash',
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