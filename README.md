# 医薬品不良在庫管理システム

## 概要
医薬品の不良在庫を効率的に管理するためのStreamlitウェブアプリケーションです。
複数の医療機関間での在庫データの共有と分析を可能にし、不良在庫の削減に貢献します。

## 主な機能
- ユーザー認証システム
- 指定フォーマットのファイルアップロード
  - OMEC他院所データ (XLSX)
  - 在庫金額データ (CSV)
- CSVダウンロード機能
- PDFファイル生成・ダウンロード
- データベース連携
- 日本語対応UI
- 不良在庫データ管理・分析
- エラーハンドリングとログ出力システム

## セットアップ手順

1. リポジトリのクローン:
```bash
git clone https://github.com/[your-username]/medical-inventory-management.git
cd medical-inventory-management
```

2. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

3. 環境変数の設定:
以下の環境変数を設定してください：
- DATABASE_URL: PostgreSQLデータベースの接続URL

4. アプリケーションの起動:
```bash
streamlit run main.py
```

## 使用方法

1. ログイン/新規登録
   - システムにアクセスするにはユーザー登録が必要です

2. ファイルのアップロード
   - 「OMEC他院所(XLSX)」ファイルをアップロード
   - 「在庫金額(CSV)」ファイルをアップロード

3. データの処理
   - アップロードされたファイルは自動的に処理され、結果が表示されます
   - 処理結果はExcel形式でダウンロード可能です

4. PDFレポート
   - 処理結果をPDF形式でダウンロードすることができます

## 開発環境
- Python 3.11
- Streamlit
- PostgreSQL
- pandas
- openpyxl

## ライセンス
このプロジェクトはMITライセンスの下で公開されています。
