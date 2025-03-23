# Selenium プロジェクト リファクタリング実行計画書

## プロジェクト概要と目的

このプロジェクトは、Selenium WebDriverを使用したクローリングと案件情報管理のためのFlaskアプリケーションです。現在はフラットな構造で実装されており、機能拡張や保守が難しくなっています。このリファクタリングでは、コードを責務ごとにモジュール化し、保守性と拡張性を向上させることを目的とします。

### 現状の課題
1. 肥大化したapp.py（1300行以上）に複数の責務が混在
2. 設定情報が複数の場所に散在
3. ユーティリティ関数と業務ロジックの混在
4. テスト容易性の欠如
5. パッケージング手順の標準化不足

### リファクタリングのゴール
1. モジュラーな構造による機能分離と責務の明確化
2. 設定管理の一元化
3. コード再利用性の向上
4. テスト容易性の向上
5. デプロイプロセスの改善

## Claude向け実行手順

### 前提条件
- Python 3.9以上がインストールされていること
- pip, virtualenvがインストールされていること
- Gitが構成されていること

### フェーズ1: 環境準備

#### タスク1.1: プロジェクト構造分析
**入力**: 
- 現在のプロジェクトファイル一式

**プロセス**:
1. 以下のコマンドを実行してプロジェクト構造を把握:
   ```
   find . -type f -name "*.py" | sort
   ```
2. 主要ファイルの依存関係を分析:
   - app.pyが依存している外部モジュールの特定
   - app.pyが提供しているルート/機能の一覧化
   - 設定読み込みの流れの特定
   - データ保存パターンの特定

**出力**:
- プロジェクト構造の分析結果
- 主要な依存関係の図式化
- リファクタリングの優先順位付きリスト

#### タスク1.2: 新ディレクトリ構造の作成
**入力**: 
- 分析結果
- `.cursor/rules/directorystructure.md`に定義されたディレクトリ構成

**プロセス**:
1. ベースディレクトリの作成:
   ```bash
   mkdir -p app/{routes,models,services,util,templates,static}
   mkdir -p app/routes
   mkdir -p app/models
   mkdir -p app/services
   mkdir -p app/util
   mkdir -p config
   mkdir -p data/{jobs,settings}
   mkdir -p tests
   mkdir -p packaging/{macos,windows}
   mkdir -p docs
   ```
   
2. 必要な`__init__.py`ファイルを作成:
   ```bash
   touch app/__init__.py
   touch app/routes/__init__.py
   touch app/models/__init__.py
   touch app/services/__init__.py
   touch app/util/__init__.py
   touch config/__init__.py
   touch tests/__init__.py
   ```

**出力**:
- 新しいディレクトリ構造（ファイルはまだ移動していない状態）

### フェーズ2: 共通基盤の実装

#### タスク2.1: 設定管理の実装
**要件**:
- 環境（開発/本番）に応じた設定の切り替え
- 設定値の一元管理
- 環境変数とのシームレスな統合
- シークレット情報の安全な取り扱い

**入力**: 
- 現在の設定管理コード（app.pyの設定関連部分）
- .envファイル

**プロセス**:
1. `config/default.py`を作成し、デフォルト設定を定義:
   ```python
   """アプリケーションのデフォルト設定"""
   import os
   from pathlib import Path

   # ベースディレクトリ
   BASE_DIR = Path(__file__).parent.parent

   # アプリケーション設定
   FLASK_APP = 'run.py'
   SECRET_KEY = 'development-key'
   PERMANENT_SESSION_LIFETIME = 86400 * 30  # 30日
   
   # データ保存設定
   DATA_DIR = BASE_DIR / 'data'
   LOG_DIR = BASE_DIR / 'logs'
   
   # API設定
   DEFAULT_MODEL = 'gpt-4o-mini'
   MAX_ITEMS = 50
   
   # 認証設定
   SUPABASE_URL = ''
   SUPABASE_ANON_KEY = ''
   ```

2. `config/development.py`と`config/production.py`を作成:
   ```python
   """開発環境設定"""
   from config.default import *

   DEBUG = True
   TESTING = False
   ```

3. `config/__init__.py`に設定ロード機能を実装:
   ```python
   """設定管理モジュール"""
   import os
   from pathlib import Path
   from dotenv import load_dotenv

   # .envファイルの読み込み
   load_dotenv()

   # 環境の取得
   ENV = os.getenv('FLASK_ENV', 'development')

   # 環境に応じた設定の読み込み
   if ENV == 'production':
       from config.production import *
   else:
       from config.development import *
   ```

4. `.env.example`ファイルを作成:
   ```
   FLASK_ENV=development
   FLASK_SECRET_KEY=your-secret-key-here
   PORT=8000
   FLASK_DEBUG=0
   
   # Supabase認証情報
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-supabase-anon-key
   
   # OpenAI API設定
   OPENAI_API_KEY=your-openai-api-key
   
   # CrowdWorks認証情報
   CROWDWORKS_EMAIL=your-email
   CROWDWORKS_PASSWORD=your-password
   ```

**出力**:
- 設定管理モジュール
- 環境別設定ファイル
- .env.exampleファイル

#### タスク2.2: ログユーティリティの実装
**要件**:
- 一貫したロギング形式
- ログレベルの環境別設定
- ファイルとコンソール出力の両方に対応
- ログローテーション対応

**入力**: 
- 現在のロギング設定（app.py内）

**プロセス**:
1. `app/util/logging.py`を作成:
   ```python
   """ロギングユーティリティ"""
   import logging
   import sys
   from pathlib import Path
   from logging.handlers import RotatingFileHandler
   from config import LOG_DIR

   def setup_logger(name, log_file=None, level=logging.INFO):
       """
       アプリケーションのロガーをセットアップする
       
       Args:
           name: ロガー名
           log_file: ログファイル名（Noneの場合は{name}.logを使用）
           level: ロギングレベル
           
       Returns:
           設定済みのロガーインスタンス
       """
       # ロガーの取得
       logger = logging.getLogger(name)
       logger.setLevel(level)
       
       # フォーマッターの作成
       formatter = logging.Formatter(
           '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
       )
       
       # コンソールハンドラーの追加
       console_handler = logging.StreamHandler(sys.stdout)
       console_handler.setFormatter(formatter)
       logger.addHandler(console_handler)
       
       # ファイルハンドラーの追加（指定がある場合）
       if log_file is None:
           log_file = f"{name}.log"
           
       log_path = LOG_DIR / log_file
       
       # ログディレクトリの作成
       LOG_DIR.mkdir(parents=True, exist_ok=True)
       
       # ローテーティングファイルハンドラーの追加
       file_handler = RotatingFileHandler(
           log_path, 
           maxBytes=10*1024*1024,  # 10MB
           backupCount=5,
           encoding='utf-8'
       )
       file_handler.setFormatter(formatter)
       logger.addHandler(file_handler)
       
       return logger
   ```

**出力**:
- ロギングユーティリティモジュール

#### タスク2.3: エラーハンドリングユーティリティの実装
**要件**:
- 一貫したエラーレスポンス形式
- デバッグ情報の環境別制御
- ログへのエラー記録
- API/ウェブ両方に対応したエラーハンドリング

**入力**: 
- app.pyのエラーハンドリング関連コード

**プロセス**:
1. `app/util/error_handler.py`を作成:
   ```python
   """エラーハンドリングユーティリティ"""
   import traceback
   from flask import jsonify, redirect, url_for, flash
   from app.util.logging import setup_logger

   # ロガーの設定
   logger = setup_logger('error_handler')

   def handle_error(e, error_type="一般エラー", user_message=None, status_code=500):
       """
       例外を処理し、適切なJSONレスポンスを返す
       
       Args:
           e: 発生した例外
           error_type: エラーの種類を示す文字列
           user_message: ユーザーに表示するメッセージ（Noneの場合は汎用メッセージ）
           status_code: HTTPステータスコード
       
       Returns:
           JSONレスポンスとステータスコード
       """
       # スタックトレースを取得
       stack_trace = traceback.format_exc()
       
       # エラーをログに記録
       logger.error(f"{error_type}: {str(e)}\n{stack_trace}")
       
       # ユーザー向けメッセージを設定
       if user_message is None:
           if status_code == 401:
               user_message = "認証が必要です。再度ログインしてください。"
           elif status_code == 403:
               user_message = "この操作を実行する権限がありません。"
           elif status_code == 404:
               user_message = "リクエストされたリソースが見つかりません。"
           elif status_code >= 500:
               user_message = "サーバーエラーが発生しました。しばらく経ってからもう一度お試しください。"
           else:
               user_message = "エラーが発生しました。"
       
       # 本番環境では詳細エラーを表示しない
       from config import ENV
       show_details = ENV != 'production'
       
       # JSONレスポンスを返す
       return jsonify({
           'status': 'error',
           'error_type': error_type,
           'message': user_message,
           'detail': str(e) if show_details else None
       }), status_code
   ```

**出力**:
- エラーハンドリングユーティリティモジュール

### フェーズ3: モデル層の実装

#### タスク3.1: ユーザーモデルの実装
**要件**:
- Supabaseとの連携
- Flask-Loginとの互換性
- セッション管理

**入力**: 
- app.pyのUserクラス定義と関連コード

**プロセス**:
1. `app/models/user.py`を作成:
   ```python
   """ユーザーモデル"""
   from flask_login import UserMixin
   
   class User(UserMixin):
       """アプリケーションのユーザーモデル"""
       
       def __init__(self, user_id, email, avatar_url=None):
           """
           ユーザーモデルの初期化
           
           Args:
               user_id: ユーザーID（Supabase）
               email: ユーザーメールアドレス
               avatar_url: アバター画像URL（オプション）
           """
           self.id = user_id
           self.email = email
           self.avatar_url = avatar_url or f"https://www.gravatar.com/avatar/{user_id}?d=mp"
       
       @classmethod
       def from_supabase_user(cls, supabase_user):
           """
           Supabaseユーザーオブジェクトからユーザーモデルを作成
           
           Args:
               supabase_user: Supabaseのユーザーオブジェクト
               
           Returns:
               ユーザーモデルのインスタンス
           """
           if not supabase_user:
               return None
               
           # ユーザーメタデータの取得
           user_metadata = supabase_user.user_metadata
           avatar_url = user_metadata.get('avatar_url') if user_metadata else None
           
           return cls(
               user_id=supabase_user.id,
               email=supabase_user.email,
               avatar_url=avatar_url
           )
   ```

**出力**:
- ユーザーモデルモジュール

#### タスク3.2: 案件モデルの実装
**要件**:
- JSONデータの読み書き
- フィルタリング機能
- チェック状態管理

**入力**: 
- 案件関連の関数とデータ管理コード

**プロセス**:
1. `app/models/job.py`を作成:
   ```python
   """案件モデルとデータアクセス"""
   import json
   import glob
   import os
   import re
   from datetime import datetime
   from pathlib import Path
   from config import DATA_DIR
   from app.util.logging import setup_logger

   # ロガーの設定
   logger = setup_logger('job_model')

   # データファイルのパス
   JOBS_DIR = DATA_DIR / 'jobs'
   CHECKS_FILE = DATA_DIR / 'settings' / 'checked_jobs.json'

   # ディレクトリの作成
   JOBS_DIR.mkdir(parents=True, exist_ok=True)
   (DATA_DIR / 'settings').mkdir(parents=True, exist_ok=True)

   class JobRepository:
       """案件データの永続化を担当するリポジトリクラス"""
       
       @staticmethod
       def get_latest_filtered_jobs():
           """
           最新のフィルタリング済み案件を取得
           
           Returns:
               フィルタリング済み案件のリスト
           """
           json_files = glob.glob(str(JOBS_DIR / '*_filtered.json'))
           if not json_files:
               return []
               
           latest_file = max(json_files, key=os.path.getctime)
           try:
               with open(latest_file, 'r', encoding='utf-8') as f:
                   jobs = json.load(f)
                   
               # 詳細テキストの改行をHTMLの<br>タグに変換
               for job in jobs:
                   if 'detail_description' in job:
                       job['detail_description'] = job['detail_description'].replace('\n', '<br>')
                       
               return jobs
           except Exception as e:
               logger.error(f"ファイルの読み込みに失敗: {str(e)}")
               return []
       
       @staticmethod
       def get_all_filtered_files():
           """
           全てのフィルタリング済みファイル情報を取得
           
           Returns:
               ファイル情報のリスト（パス、日付、案件数など）
           """
           json_files = glob.glob(str(JOBS_DIR / '*_filtered.json'))
           if not json_files:
               return []
           
           file_info = []
           for file_path in json_files:
               file_name = os.path.basename(file_path)
               match = re.search(r'jobs_(\d{8})_(\d{6})_filtered\.json', file_name)
               
               if match:
                   date_str = match.group(1)
                   time_str = match.group(2)
                   formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                   
                   # 案件数を取得
                   try:
                       with open(file_path, 'r', encoding='utf-8') as f:
                           jobs = json.load(f)
                           job_count = len(jobs)
                   except:
                       job_count = 0
                   
                   file_info.append({
                       'path': file_path,
                       'name': file_name,
                       'date': formatted_date,
                       'timestamp': f"{date_str}_{time_str}",
                       'job_count': job_count
                   })
           
           # 日付の降順でソート
           file_info.sort(key=lambda x: x['timestamp'], reverse=True)
           return file_info
       
       @staticmethod
       def load_filtered_jobs(file_path):
           """
           特定のフィルタリング済みJSONファイルを読み込む
           
           Args:
               file_path: 読み込むファイルのパス
               
           Returns:
               案件のリスト
           """
           if not os.path.exists(file_path):
               return []
           
           try:
               with open(file_path, 'r', encoding='utf-8') as f:
                   jobs = json.load(f)
                   
               # 詳細テキストの改行をHTMLの<br>タグに変換
               for job in jobs:
                   if 'detail_description' in job:
                       job['detail_description'] = job['detail_description'].replace('\n', '<br>')
                       
               return jobs
           except Exception as e:
               logger.error(f"ファイルの読み込みに失敗: {str(e)}")
               return []
       
       @staticmethod
       def load_checks():
           """
           チェック状態を読み込む
           
           Returns:
               チェック状態の辞書
           """
           if os.path.exists(CHECKS_FILE):
               try:
                   with open(CHECKS_FILE, 'r', encoding='utf-8') as f:
                       return json.load(f)
               except Exception as e:
                   logger.error(f"チェックファイルの読み込みに失敗: {str(e)}")
           
           return {}
       
       @staticmethod
       def save_checks(checks):
           """
           チェック状態を保存
           
           Args:
               checks: チェック状態の辞書
           """
           try:
               with open(CHECKS_FILE, 'w', encoding='utf-8') as f:
                   json.dump(checks, f, ensure_ascii=False, indent=2)
           except Exception as e:
               logger.error(f"チェックファイルの保存に失敗: {str(e)}")
   ```

**出力**:
- 案件モデルモジュールと永続化クラス

### フェーズ4: サービス層の実装

#### タスク4.1: クローラーサービスの実装
**要件**:
- Seleniumによるクローリング機能
- 設定に基づく動作制御
- エラーハンドリング
- ログ出力

**入力**: 
- crawler.pyの内容

**プロセス**:
1. `app/services/crawler.py`を実装（詳細を省略）

**出力**:
- クローラーサービスモジュール

#### タスク4.2-4.4: その他のサービス実装
...（同様の形式で他のサービスも実装）

### フェーズ5: ルーティングと初期化

#### タスク5.1: アプリケーション初期化の実装
**要件**:
- Flask, Blueprint, 拡張機能の設定
- エラーハンドラー登録
- データディレクトリの初期化
- サービスの初期化

**入力**: 
- app.pyの初期化関連コード

**プロセス**:
1. `app/__init__.py`を実装:
   ```python
   """アプリケーション初期化"""
   import os
   import atexit
   from flask import Flask
   from flask_bootstrap import Bootstrap
   from flask_login import LoginManager
   from flask_wtf.csrf import CSRFProtect
   from supabase import create_client
   from .util.logging import setup_logger
   from .util.chromedriver import ChromeDriverManager
   from config import *

   # ロガーの設定
   logger = setup_logger('app')

   def create_app(test_config=None):
       """アプリケーションファクトリ"""
       # Flaskインスタンスの作成
       app = Flask(__name__)
       
       # 設定の読み込み
       if test_config is None:
           # 通常の設定を読み込む
           app.config.from_object('config')
       else:
           # テスト用の設定を読み込む
           app.config.from_mapping(test_config)
       
       # CSRFトークン
       csrf = CSRFProtect(app)
       
       # アップデート関連のエンドポイントをCSRF保護から除外（バックアップとして）
       csrf.exempt('/api/check_updates')
       csrf.exempt('/api/perform_update')
       csrf.exempt('/api/update_status')
       csrf.exempt('/bulk_apply')
       
       # Bootstrap
       Bootstrap(app)
       
       # ログイン管理の初期化
       login_manager = LoginManager()
       login_manager.init_app(app)
       login_manager.login_view = 'auth.login'
       login_manager.login_message = 'このページにアクセスするにはログインが必要です。'
       
       # Supabaseクライアントの初期化
       supabase_client = create_client(
           os.getenv('SUPABASE_URL'),
           os.getenv('SUPABASE_ANON_KEY')
       )
       
       # アプリケーションコンテキストにSupabaseクライアントを追加
       app.supabase = supabase_client
       
       # ChromeDriver自動管理の初期化
       try:
           # ChromeDriverのセットアップ
           driver_manager = ChromeDriverManager()
           driver_path = driver_manager.setup_driver()
           if driver_path:
               logger.info(f"ChromeDriverを自動設定しました: {driver_path}")
           else:
               logger.warning("ChromeDriverの自動設定に失敗しました。手動での設定が必要な場合があります。")
           
           # バックグラウンド更新を開始
           driver_manager.start_background_update()
           logger.info("ChromeDriverのバックグラウンド更新を開始しました")
           
           # アプリケーションコンテキストにドライバーマネージャーを追加
           app.driver_manager = driver_manager
           
           # アプリケーション終了時にバックグラウンド更新を停止
           def stop_chromedriver_update():
               driver_manager.stop_background_update()
               logger.info("ChromeDriverのバックグラウンド更新を停止しました")
           
           atexit.register(stop_chromedriver_update)
       except Exception as e:
           logger.error(f"ChromeDriver自動管理の初期化に失敗: {str(e)}")
       
       # Blueprintの登録
       from .routes import main, auth, api, job
       app.register_blueprint(main.bp)
       app.register_blueprint(auth.bp, url_prefix='/auth')
       app.register_blueprint(api.bp, url_prefix='/api')
       app.register_blueprint(job.bp, url_prefix='/job')
       
       # 一括応募機能の初期化
       from .services.bulk_apply import init_bulk_apply
       init_bulk_apply(app)
       
       # 起動時に古いデータを削除
       from .services.job_service import clean_old_job_data
       try:
           clean_old_job_data()
       except Exception as e:
           logger.error(f"古いデータの削除中にエラー発生: {str(e)}")
       
       return app
   ```

**出力**:
- アプリケーション初期化モジュール

#### タスク5.2-5.5: ルートの実装
...（メイン、認証、API、ジョブ管理のルーティングを実装）

### フェーズ6-7: フロントエンド、テスト、パッケージング
...（簡略化のため省略）

## 実装時の判断基準

1. **コード移行時の優先順位**:
   - 依存関係の少ないものから実装（共通ユーティリティ、設定など）
   - 依存関係のあるものを次に実装（モデル層、サービス層）
   - UIに関連するものを最後に実装（ルート、テンプレートなど）

2. **リファクタリングの判断基準**:
   - 単一責任の原則: 各クラス/関数は1つの責任を持つ
   - 開放/閉鎖の原則: 拡張には開かれ、修正には閉じる
   - リスコフの置換原則: 派生クラスは基底クラスの代わりに使用可能
   - インターフェイス分離の原則: 特化したインターフェイスが単一の大きなものより良い
   - 依存関係逆転の原則: 高レベルモジュールは低レベルモジュールに依存すべきでない

3. **テスト追加の判断基準**:
   - 重要なビジネスロジックには単体テスト必須
   - 複雑なデータ変換には入出力テスト必須
   - エッジケースの特定と対応
   - 異常系のエラーハンドリングテスト

## まとめ

このリファクタリングにより、以下の成果が期待されます：

1. **保守性の向上**: コードの責務が明確に分離され、変更が容易になる
2. **拡張性の向上**: 新機能の追加が構造的に容易になる
3. **テスト容易性**: 各コンポーネントが独立しているため、単体テストが容易
4. **コード理解の容易さ**: 明確な構造により、新規開発者の学習曲線が緩やかに
5. **エラー処理の改善**: 一貫したエラー処理メカニズムによる堅牢性の向上

このリファクタリング計画はClaude向けに構造化されており、各ステップの入力と出力、判断基準が明確に示されています。これにより、AIによる自動コード生成とリファクタリングが効率的に実行できます。 