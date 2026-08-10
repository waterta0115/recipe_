import pytest
import os
from unittest.mock import patch
from app2 import extract_cost_int, generate_shopping_list, fetch_rakuten_recipes

# CI環境用にダミーの環境変数をセット
os.environ["RAKUTEN_APPLICATION_ID"] = "dummy_id"
os.environ["RAKUTEN_ACCESS_KEY"] = "dummy_key"

# --- 1. 数値抽出機能 (extract_cost_int) のテスト ---
def test_extract_cost_int_valid_strings():
    """様々な文字列から数値が正しく抽出できるか検証"""
    assert extract_cost_int("300円前後") == 300
    assert extract_cost_int("1,000円前後") == 1000
    assert extract_cost_int("100円以下") == 100


def test_extract_cost_int_invalid_strings():
    """数値が含まれない場合や None / 指定なし の場合に 0 が返るか検証"""
    assert extract_cost_int("指定なし") == 0
    assert extract_cost_int("") == 0
    assert extract_cost_int(None) == 0


# --- 2. 買い物リスト集計・除外機能 (generate_shopping_list) のテスト ---
def test_generate_shopping_list_aggregation_and_exclusion():
    """材料の重複カウントおよび指定キーワードの除外処理を検証"""
    mock_recipes = [
        {"materials": ["豚肉", "玉ねぎ", "ネギ"]},
        {"materials": ["豚肉", "キャベツ", "エビ"]}
    ]
    exclude_keywords = ["エビ", "ネギ"]

    shopping_list, excluded = generate_shopping_list(mock_recipes, exclude_keywords)

    # 買い物リストの検証
    shopping_dict = {item["name"]: item["count"] for item in shopping_list}
    assert shopping_dict["豚肉"] == 2
    assert shopping_dict["玉ねぎ"] == 1
    assert shopping_dict["キャベツ"] == 1

    # 除外された材料の検証
    assert "ネギ" in excluded
    assert "エビ" in excluded
    assert "豚肉" not in excluded


# --- 3. 外部API取得処理 (fetch_rakuten_recipes) のモックテスト ---
@patch("app2.requests.get")
def test_fetch_rakuten_recipes_success(mock_get):
    """APIからのレスポンスが正常な場合のデータ抽出を検証"""
    # 楽天APIの擬似レスポンスデータ
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "result": [
            {
                "recipeTitle": "テスト豚の生姜焼き",
                "recipeUrl": "https://recipe.rakuten.co.jp/test",
                "recipeMaterial": ["豚肉", "玉ねぎ"],
                "recipeCost": "300円前後"
            }
        ]
    }

    recipes = fetch_rakuten_recipes(category_id=None, count=1)

    assert len(recipes) == 1
    assert recipes[0]["title"] == "テスト豚の生姜焼き"
    assert recipes[0]["cost_int"] == 300
    assert "豚肉" in recipes[0]["materials"]


@patch("app2.requests.get")
def test_fetch_rakuten_recipes_api_error(mock_get):
    """APIエラー（Status Code 403 や 500等）発生時に空リストが返るか検証"""
    mock_get.return_value.status_code = 403

    recipes = fetch_rakuten_recipes(category_id=None, count=1)
    assert recipes == []