import os
import re
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# 1. 環境変数の読み込み
load_dotenv()

RAKUTEN_APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "").strip()
RAKUTEN_ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY", "").strip()

# ページ基本設定
st.set_page_config(
    page_title="楽天レシピ 買い物リスト生成アプリ",
    page_icon="🍳",
    layout="wide"
)


# --- 2. 費用の数値抽出関数 ---
def extract_cost_int(cost_str):
    if not cost_str or cost_str == "指定なし":
        return 0
    cleaned_str = str(cost_str).replace(",", "")
    match = re.search(r'\d+', cleaned_str)
    return int(match.group()) if match else 0


# --- 3. 楽天API取得関数 ---
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
        
    try:
        response = requests.get(url, params=params)
        time.sleep(1.0)
        if response.status_code == 200:
            data = response.json()
            recipes = data.get("result", [])[:count]
            extracted = []
            for r in recipes:
                cost_raw = r.get("recipeCost", "指定なし")
                extracted.append({
                    "title": r.get("recipeTitle"),
                    "url": r.get("recipeUrl"),
                    "materials": r.get("recipeMaterial", []),
                    "cost_raw": cost_raw,
                    "cost_int": extract_cost_int(cost_raw)
                })
            return extracted
        else:
            st.error(f"APIエラー: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")
        return []


# --- 4. 買い物リスト集計関数 ---
def generate_shopping_list(recipes):
    ingredient_counts = {}
    for recipe in recipes:
        for item in recipe.get("materials", []):
            name = item.strip()
            if name:
                ingredient_counts[name] = ingredient_counts.get(name, 0) + 1

    shopping_list = [
        {"材料名": name, "使用レシピ数": count}
        for name, count in sorted(ingredient_counts.items())
    ]
    return shopping_list


# --- 5. Streamlit メインUI画面 ---
def main():
    st.title("🍳 楽天レシピ 買い物リスト生成ダッシュボード")
    st.caption("人気レシピから材料の重複と費用の目安を自動集計します")

    # APIキーの存在チェック
    if not RAKUTEN_APPLICATION_ID or not RAKUTEN_ACCESS_KEY:
        st.warning(".env ファイルに RAKUTEN_APPLICATION_ID と RAKUTEN_ACCESS_KEY を設定してください。")
        st.stop()

    # サイドバー（操作パネル）
    st.sidebar.header("🔍 検索設定")
    
    # 楽天の大カテゴリマップ（主要ジャンル）
    categories = {
        "総合人気ランキング": None,
        "肉": "10",
        "魚介": "11",
        "野菜": "12",
        "パスタ・麺類": "15",
        "ご飯もの": "14",
        "汁物・スープ": "17"
    }
    
    selected_category_name = st.sidebar.selectbox("カテゴリを選択", list(categories.keys()))
    selected_category_id = categories[selected_category_name]
    recipe_count = st.sidebar.slider("取得件数", min_value=1, max_value=5, value=5)

    # 実行ボタン
    if st.sidebar.button("レシピ・買い物リストを取得", type="primary"):
        with st.spinner("楽天レシピAPIからデータを取得中..."):
            recipes = fetch_rakuten_recipes(category_id=selected_category_id, count=recipe_count)

        if not recipes:
            st.info("レシピが見つかりませんでした。")
            return

        # 画面を2つのカラム（列）に分割
        col1, col2 = st.columns([1, 1])

        # --- 左カラム：取得したレシピ一覧 ---
        with col1:
            st.subheader("📖 取得したレシピ一覧")
            total_cost = 0
            
            for idx, r in enumerate(recipes, 1):
                total_cost += r["cost_int"]
                with st.expander(f"{idx}. {r['title']}"):
                    st.write(f"**費用の目安:** {r['cost_raw']}")
                    st.write(f"**材料:** {', '.join(r['materials'])}")
                    st.markdown(f"[👉 レシピページを開く]({r['url']})")

            # メトリクス表示（合計金額）
            st.metric(
                label="全レシピの目安費用合計",
                value=f"約 {total_cost:,} 円"
            )

        # --- 右カラム：買い物リスト ---
        with col2:
            st.subheader("🛒 まとめ買い物リスト")
            shopping_list = generate_shopping_list(recipes)
            df_shopping = pd.DataFrame(shopping_list)

            # データフレーム（表形式）で表示
            st.dataframe(
                df_shopping,
                use_container_width=True,
                hide_index=True
            )

            # CSVダウンロードボタンの設置
            csv_data = df_shopping.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 買い物リストをCSVでダウンロード",
                data=csv_data,
                file_name="shopping_list.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()