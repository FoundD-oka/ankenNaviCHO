# ディレクトリ構成

以下はプロジェクトの現在のディレクトリ構造です：

```
Selenium/
├── app/                         # アプリケーションのコアパッケージ
│   ├── config/                  # アプリケーション設定
│   ├── models/                  # データモデル
│   ├── repositories/            # データアクセス層
│   ├── routes/                  # ルーティング処理
│   ├── services/                # ビジネスロジック
│   │   ├── crawler.py           # クローリングサービス
│   │   ├── filter.py            # フィルタリングサービス
│   │   ├── bulk_apply.py        # 一括応募サービス
│   │   └── updater.py           # アップデートサービス
│   ├── static/                  # 静的ファイル
│   │   └── css/                 # CSSファイル
│   │   └── js/                  # JavaScriptファイル
│   ├── templates/               # HTMLテンプレート
│   │   ├── filter/              # フィルタリングテンプレート
│   │   └── layout/              # レイアウトテンプレート
│   └── util/                    # ユーティリティ関数
│       ├── logging.py           # ロギング設定
│       ├── auth.py              # 認証ユーティリティ
│       └── chromedriver_manager.py # ChromeDriver管理
├── backups/                     # バックアップファイル
├── config/                      # グローバル設定ファイル
├── crawled_data/                # クロール済みデータ
├── data/                        # データ保存ディレクトリ
│   ├── settings.json            # アプリケーション設定
│   └── jobs/                    # 案件データ
├── Docs/                        # ドキュメント
├── drivers/                     # WebDrivers
│   └── config.json              # WebDriver設定
├── logs/                        # ログファイル
├── templates/                   # 外部テンプレート
│   ├── error.html               # エラーページ
│   ├── index.html               # インデックスページ
│   ├── job_history.html         # ジョブ履歴ページ
│   └── login.html               # ログインページ
├── app.py                       # メインアプリケーション
├── app_launcher.py              # アプリケーション起動スクリプト
├── bulk_apply.py                # 一括応募スクリプト
├── simple_installer.sh          # アプリケーションビルドスクリプト
├── chromedriver                 # ChromeDriverバイナリ
├── chromedriver_manager.py      # ChromeDriver管理スクリプト
├── crawler.py                   # クローラースクリプト
├── create_icon.py               # アイコン作成スクリプト
├── env.txt                      # 環境変数設定
├── icon.icns                    # アプリケーションアイコン
├── requirements.txt             # 依存パッケージリスト
├── SelfIntroduction.txt         # 自己紹介テキスト
├── setup.py                     # セットアップスクリプト
├── supabase_stripe_handler.py   # Supabase/Stripe連携処理
└── .gitignore                   # Gitの無視設定