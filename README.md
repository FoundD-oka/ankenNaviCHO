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
```

# macOS アプリ (.app → ZIP) ビルド手順

macOS でダブルクリックして起動できる `ankenNaviCHO_mac.app` を生成し、
Google Drive へ配布可能な `dist/ankenNaviCHO_mac.zip` を作成する手順です。

### 前提
* macOS Ventura / Sonoma（arm64）
* Xcode Command Line Tools がインストール済み
* Python 3.11+ がシステムに存在

### 1. 仮想環境の自動生成 & PyInstaller インストール
`mac_build/build_app.sh` はプロジェクト直下に `.venv` が無い場合、
自動で `python3 -m venv .venv` を実行し Pip / PyInstaller / Pillow を導入します。

### 2. ビルド実行

```bash
# 任意: 初回のみ venv を手動で作成しても OK
# python3 -m venv .venv && source .venv/bin/activate && pip install pyinstaller pillow

# ビルド
source .venv/bin/activate  # 既存 venv があれば有効化
bash mac_build/build_app.sh
```

スクリプトが行うこと
1. `.venv` を検出／作成し PyInstaller を準備
2. `mac_build/ank_nav.spec` を使い PyInstaller で
   `dist/ankenNaviCHO_mac.app` を生成
3. 初回セットアップスクリプト `setup` を `.app` 内へ同梱
4. 事前に venv を `Contents/Resources/venv` に構築し `.setup_done` を作成
5. `ditto` で `dist/ankenNaviCHO_mac.zip` を作成

> 注: notarize ステップはコメントアウトしています。<br>
> オンライン初回起動で問題なければ Staple なしで配布可能です。

### 3. 配布

生成された `dist/ankenNaviCHO_mac.zip` を Google Drive へアップロードし、
リンク共有すれば完了です。

利用者手順は下記のとおりです。
1. ZIP をダウンロードしてダブルクリックで展開
2. `ankenNaviCHO_mac.app` を **Applications** へコピー
3. 初回起動時はインターネット接続必須（Gatekeeper がチケット照会）
4. 起動するだけ（初回でもセットアップ不要）

---
これで「ダブルクリックでインストール＆起動」形式の配布が可能になります。
# Windows アプリ (.exe) ビルド手順

Windows 環境で実行可能な `ankenNaviCHO_win.exe` を生成する手順です。

### 前提
* Windows 10/11
* Python 3.11+ がインストール済み

### 1. ビルド実行
```cmd
cd win_build
.\build_app.bat
```
スクリプトが行うこと
1. `.venv` を自動作成し依存パッケージをインストール
2. `original_icon.png` を `.ico` 形式へ変換
3. `win_build/ank_nav.spec` を使い PyInstaller で `dist/ankenNaviCHO_win.exe` を生成

ビルド完了後、`dist` ディレクトリ内の `ankenNaviCHO_win.exe` を配布してください。

