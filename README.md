# 案件管理アプリケーション

## 概要
このアプリケーションは、フリーランス案件のクローリングとAIフィルタリングを行うFlaskベースのWebアプリケーションです。

## 主な機能

### 1. ユーザー認証
- Supabaseを使用したGoogle認証
- セッション管理
- ユーザープロファイル管理

### 2. 案件クローリング
- 複数のフリーランスプラットフォームからの案件収集
- 自動クローリングスケジュール機能
- ChromeDriver自動管理システム

### 3. AIフィルタリング
- OpenAI GPTを使用した案件フィルタリング
- カスタマイズ可能なフィルタリング条件
- 案件の自動評価と分類

### 4. データ管理
- 案件履歴の保存と管理
- 古いデータの自動クリーニング
- バックアップ機能

### 5. その他の機能
- アプリケーションの自動アップデート
- システムステータス監視
- エラー処理とログ管理

## 技術仕様

### 使用技術
- Backend: Python (Flask)
- Frontend: HTML/CSS/JavaScript
- Database: Supabase
- AI: OpenAI GPT
- Browser Automation: Selenium (ChromeDriver)

### 依存関係
- Flask
- Flask-Bootstrap
- Flask-Login
- OpenAI
- Selenium
- python-dotenv
- Supabase Client

## セットアップ

1. 必要な環境変数の設定
```
FLASK_SECRET_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
```

2. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

3. アプリケーションの起動
```bash
python app_launcher.py
```

## ディレクトリ構造
```
.
├── app_launcher.py      # アプリケーション起動スクリプト
├── app.py              # メインアプリケーション
├── bulk_apply.py       # 一括応募機能
├── crawler.py          # クローリング機能
├── chromedriver_manager.py  # ChromeDriver管理
└── static/
    ├── css/
    ├── js/
    └── images/