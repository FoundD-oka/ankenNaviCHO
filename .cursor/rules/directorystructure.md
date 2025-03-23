# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
selenium-project/
├── app/                   # アプリケーションのコアパッケージ
│   ├── __init__.py        # アプリケーション初期化
│   ├── routes/            # ルーティング処理
│   │   ├── __init__.py
│   │   ├── main.py        # メインページのルート
│   │   ├── auth.py        # 認証関連のルート
│   │   ├── api.py         # API関連のルート
│   │   └── job.py         # 案件管理のルート
│   ├── models/            # データモデル
│   │   ├── __init__.py
│   │   └── user.py        # ユーザーモデル
│   ├── services/          # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── crawler.py     # クローリングサービス
│   │   ├── filter.py      # フィルタリングサービス
│   │   ├── bulk_apply.py  # 一括応募サービス
│   │   └── updater.py     # アップデートサービス
│   ├── util/              # ユーティリティ関数
│   │   ├── __init__.py
│   │   ├── logging.py     # ロギング設定
│   │   ├── auth.py        # 認証ユーティリティ
│   │   └── chromedriver.py # ChromeDriver管理
│   ├── static/            # 静的ファイル
│   └── templates/         # HTMLテンプレート
├── config/                # 設定ファイル
│   ├── __init__.py
│   ├── default.py         # デフォルト設定
│   ├── development.py     # 開発環境設定
│   └── production.py      # 本番環境設定
├── data/                  # データ保存ディレクトリ
│   ├── settings.json      # アプリケーション設定
│   └── jobs/              # 案件データ
├── logs/                  # ログファイル
├── tests/                 # テストコード
│   ├── __init__.py
│   ├── test_crawler.py
│   └── test_filter.py
├── packaging/             # パッケージング
│   ├── macos/             # macOS用
│   └── windows/           # Windows用
├── docs/                  # ドキュメント
├── run.py                 # 開発用起動スクリプト
├── wsgi.py                # 本番用WSGI起動スクリプト  
├── .env.example           # 環境変数サンプル
├── .gitignore             # Gitの無視設定
└── requirements.txt       # 依存パッケージリスト