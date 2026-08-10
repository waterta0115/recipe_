# 楽天レシピ 買い物リスト＆費用集計ツール

[![Python Application CI](https://github.com/waterta0115/recipe_/actions/workflows/ci.yml/badge.svg)](https://github.com/waterta0115/recipe_/actions/workflows/ci.yml)

## 📌 概要（目的）
本ソフトウェアは、楽天レシピAPIから人気レシピデータを取得し、複数レシピ間で**重複する材料の自動集計**、**費用の目安合計の算出**、および**アレルギー・不要食材の自動除外**を行うCLIツールです。毎日の献立計画と買い物リスト作成の効率化を目的としています。

---

## 📸 使用例

ターミナルで実行すると、取得したレシピ一覧、フィルタリング後の買い物リスト、合計費用目安が即座に出力されます。

```text
=== プログラムの実行を開始しました ===
【設定中の除外キーワード】: エビ, えび, ピーナッツ, ネギ, ねぎ

--- 取得した楽天レシピ一覧と費用 ---
1. 簡単絶品ポークソテー
   費用の目安 (API返却値): 500円前後  ->  抽出数値: 500円
   材料: 豚ロース肉, 塩コショウ, ガリバタしょうゆ

2. 節約もやし炒め ⚠️ [除外対象が含まれます]
   費用の目安 (API返却値): 100円以下  ->  抽出数値: 100円
   材料: もやし, 豚バラ肉, 長ネギ

=================== 統合・合算された買い物リスト (除外後) ===================
1. キャベツ
2. 豚ロース肉
3. もやし (★ 2個のレシピで使用)

------------------- 🚫 買い物リストから自動除外された材料 -------------------
・長ネギ

=================== 費用の合計目安 ===================
全5件のレシピの目安費用合計: およそ 1,200 円
```
## 👀インストール方法
```bash
# リポジトリのクローン
git clone [https://github.com/waterta0115/recipe_.git](https://github.com/waterta0115/recipe_.git)
cd recipe_

# 依存パッケージのインストール
pip install -r requirements.txt
```
## 簡単な使い方
1. プロジェクト直下に`.env`ファイルを作成し、APIキーを設定する。
```text
RAKUTEN_APPLICATION_ID=your_application_id
RAKUTEN_ACCESS_KEY=your_access_key
```
2. 以下のコマンドを実行する。
```bash
python3 app2.py
```

## 開発環境の設定方法
- 動作要件：python3.10以上
- 仮想環境の構築
```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

## テストの実行方法
`pytest`を使用して単体テストを実行する。
```bash
pytest
```
