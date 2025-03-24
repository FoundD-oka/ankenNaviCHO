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
│   ├── templates/               # HTMLテンプレート
│   └── util/                    # ユーティリティ関数
│       ├── logging.py           # ロギング設定
│       ├── auth.py              # 認証ユーティリティ
│       └── chromedriver.py      # ChromeDriver管理
├── backups/                     # バックアップファイル
├── config/                      # グローバル設定ファイル
├── crawled_data/                # クロール済みデータ
├── data/                        # データ保存ディレクトリ
│   ├── settings.json            # アプリケーション設定
│   └── jobs/                    # 案件データ
├── Docs/                        # ドキュメント
├── drivers/                     # WebDrivers
├── logs/                        # ログファイル
├── templates/                   # 外部テンプレート
├── venv/                        # 仮想環境
├── app.py                       # メインアプリケーション
├── app_launcher.py              # アプリケーション起動スクリプト
├── bulk_apply.py                # 一括応募スクリプト
├── build_app.sh                 # アプリケーションビルドスクリプト
├── chromedriver                 # ChromeDriverバイナリ
├── chromedriver_manager.py      # ChromeDriver管理スクリプト
├── crawler.py                   # クローラースクリプト
├── create_icon.py               # アイコン作成スクリプト
├── icon.icns                    # アプリケーションアイコン
├── install_standalone.sh        # スタンドアロンインストーラースクリプト
├── requirements.txt             # 依存パッケージリスト
├── run_standalone.sh            # スタンドアロン実行スクリプト
├── setup.py                     # セットアップスクリプト
├── simple_installer.sh          # シンプルインストーラースクリプト
├── standalone_app.py            # スタンドアロンアプリケーション
├── supabase_stripe_handler.py   # Supabase/Stripe連携処理
├── updater.py                   # アップデータースクリプト
├── .env                         # 環境変数設定
└── .gitignore                   # Gitの無視設定