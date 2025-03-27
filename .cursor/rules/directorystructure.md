# ディレクトリ構成

以下はプロジェクトの現在のディレクトリ構造です：

```
Selenium/
├── ankenNaviCHO.app/               # アプリケーションバンドル
├── backups/                        # バックアップファイル
├── crawled_data/                   # クロール済みデータ
├── Docs/                           # ドキュメント
├── drivers/                        # WebDrivers
│   ├── config.json                 # WebDriver設定
│   └── chromedriver_134.0.6998.89/
│       └── chromedriver-mac-arm64/
│           ├── LICENSE.chromedriver
│           └── THIRD_PARTY_NOTICES.chromedriver
├── logs/                           # ログファイル
├── static/                         # 静的ファイル
│   ├── css/                        # CSSファイル
│   ├── images/                     # 画像ファイル
│   │   ├── coconala_logo.png
│   │   └── crowdworks_logo.png
│   └── js/                         # JavaScriptファイル
│       └── fixes.js
├── temp_icons/                     # 一時的なアイコンファイル
│   └── AppIcon.iconset/
│       ├── icon_16x16.png
│       ├── icon_16x16@2x.png
│       ├── icon_32x32.png
│       ├── icon_64x64@2x.png
│       ├── icon_128x128.png
│       ├── icon_128x128@2x.png
│       ├── icon_256x256.png
│       ├── icon_256x256@2x.png
│       ├── icon_512x512.png
│       ├── icon_512x512@2x.png
│       └── icon_1024x1024.png
├── templates/                      # HTMLテンプレート
│   ├── error.html                  # エラーページ
│   ├── index.html                  # インデックスページ
│   ├── job_history.html           # ジョブ履歴ページ
│   ├── login.html                 # ログインページ
│   └── top.html                   # トップページ
├── .gitignore                     # Gitの無視設定
├── app_launcher.py                # アプリケーション起動スクリプト
├── app.py                         # メインアプリケーション
├── bulk_apply.py                  # 一括応募スクリプト
├── chromedriver_manager.py        # ChromeDriver管理スクリプト
├── crawler.py                     # クローラースクリプト
├── create_icon.py                 # アイコン作成スクリプト
├── env.txt                        # 環境変数設定
├── icon.icns                      # アプリケーションアイコン
├── prompt.txt                     # プロンプト設定
├── requirements.txt               # 依存パッケージリスト
├── SelfIntroduction.txt          # 自己紹介テキスト
├── simple_installer.sh            # インストーラースクリプト
├── supabase_stripe_handler.py     # Supabase/Stripe連携処理
├── updater.py                     # アップデートスクリプト
└── 依頼.md                        # 依頼内容