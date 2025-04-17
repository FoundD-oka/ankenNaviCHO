from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap4
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from functools import wraps
import json
import os
import glob
from datetime import datetime, timedelta
import traceback
from dotenv import load_dotenv, set_key
from pathlib import Path
import subprocess
import sys
import signal
import threading
import time
from bulk_apply import register_bulk_apply_routes, init_bulk_apply
from supabase import create_client, Client
import logging
import re
from openai import OpenAI
from updater import check_for_updates, perform_update, get_update_status
import atexit
from fix_settings_patch import get_app_paths, get_data_dir_from_env
import socket
import fcntl
import errno
import webbrowser
import tempfile

# アプリケーションパスを取得
app_paths = get_app_paths()
data_dir = app_paths['data_dir']

# 設定ファイルのパス
SETTINGS_FILE = str(app_paths['settings_file'])
PROMPT_FILE = str(data_dir / 'crawled_data' / 'prompt.txt')

# デフォルト設定
DEFAULT_SETTINGS = {
    'model': 'gpt-4o-mini',
    'api_key': '',
    'deepseek_api_key': '',
    'max_items': 100,
    'filter_prompt': '',
    'self_introduction': '',
    'crowdworks_email': '',
    'crowdworks_password': ''
}

# アプリケーション環境の初期化関数
def initialize_app_environment():
    """アプリケーションの初期環境を設定する"""
    logger.info("アプリケーション環境の初期化を開始")
    
    # 必要なディレクトリの作成（fix_settings_patch.pyですでに作成済み）
    # app_pathsから直接必要なディレクトリを取得
    data_dir = app_paths['data_dir']
    
    # 設定ファイルの初期化
    settings_file = app_paths['settings_file']
    if not os.path.exists(settings_file):
        default_settings = DEFAULT_SETTINGS.copy()
        logger.info(f"デフォルト設定ファイルを作成します: {settings_file}")
        # 設定ファイルのディレクトリが存在することを確認
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)
    
    # checked_jobs.jsonの初期化
    checks_file = data_dir / 'crawled_data' / 'checked_jobs.json'
    if not os.path.exists(checks_file):
        logger.info(f"チェック状態ファイルを作成します: {checks_file}")
        # ファイルのディレクトリが存在することを確認
        checks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checks_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    
    # prompt.txtの初期化
    prompt_file = data_dir / 'crawled_data' / 'prompt.txt'
    if not os.path.exists(prompt_file):
        logger.info(f"フィルタープロンプトファイルを初期化します: {prompt_file}")
        # ファイルのディレクトリが存在することを確認
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_config = {
            'model': 'gpt-4o-mini',
            'prompt': '',
            'temperature': 0,
            'max_tokens': 100
        }
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompt_config, f, ensure_ascii=False, indent=2)
    
    logger.info("アプリケーション環境の初期化が完了しました")

# ChromeDriver自動管理モジュールをインポート
import chromedriver_manager

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(data_dir / 'logs' / 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Nodeサーバーのサブプロセスを保持する変数
node_process = None

# エラーハンドリングのためのユーティリティ関数
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
    
    # JSONレスポンスを返す
    return jsonify({
        'status': 'error',
        'error_type': error_type,
        'message': user_message,
        'detail': str(e) if not app.config.get('PRODUCTION', False) else None
    }), status_code

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
Bootstrap4(app)
csrf = CSRFProtect(app)

# CSRFトークンをAjaxリクエストでも検証するように設定
csrf.exempt_views = []

# アップデート関連のエンドポイントをCSRF保護から除外（バックアップとして）
csrf.exempt('/api/check_updates')
csrf.exempt('/api/perform_update')
csrf.exempt('/api/update_status')
csrf.exempt('/bulk_apply')
csrf.exempt('/api/browser_close')  # ブラウザ終了通知のエンドポイントも除外

# Supabaseクライアントの初期化
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_ANON_KEY')
)

# ログイン管理の初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'

# ChromeDriver自動管理の初期化
try:
    # ChromeDriverのセットアップ
    driver_path = chromedriver_manager.setup_driver()
    if driver_path:
        logger.info(f"ChromeDriverを自動設定しました: {driver_path}")
    else:
        logger.warning("ChromeDriverの自動設定に失敗しました。手動での設定が必要な場合があります。")
    
    # バックグラウンド更新を開始
    chromedriver_manager.start_background_update()
    logger.info("ChromeDriverのバックグラウンド更新を開始しました")
    
    # アプリケーション終了時にバックグラウンド更新を停止
    def stop_chromedriver_update():
        chromedriver_manager.stop_background_update()
        logger.info("ChromeDriverのバックグラウンド更新を停止しました")
    
    atexit.register(stop_chromedriver_update)
except Exception as e:
    logger.error(f"ChromeDriver自動管理の初期化に失敗: {str(e)}")

# ユーザーモデル
class User(UserMixin):
    def __init__(self, user_id, email, avatar_url=None):
        self.id = user_id
        self.email = email
        self.avatar_url = avatar_url or f"https://www.gravatar.com/avatar/{user_id}?d=mp"

@login_manager.user_loader
def load_user(user_id):
    try:
        if 'access_token' in session:
            # セッションに保存されているトークンを使用
            user = supabase.auth.get_user(session['access_token']).user
            if user:
                # Get user metadata which includes avatar_url
                user_metadata = user.user_metadata
                avatar_url = user_metadata.get('avatar_url') if user_metadata else None
                return User(user.id, user.email, avatar_url)
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# 認証必須のデコレータ
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 認証状態のチェック
        if not current_user.is_authenticated or 'access_token' not in session:
            logger.warning("認証されていないアクセス: ユーザーが認証されていないか、アクセストークンがありません")
            
            # APIリクエストの場合はJSONレスポンスを返す
            if request.is_json or request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return handle_error(
                    Exception("認証が必要です"),
                    error_type="認証エラー",
                    user_message="この操作を実行するにはログインが必要です",
                    status_code=401
                )
            
            # 通常のリクエストの場合はリダイレクト
            logout_user()
            session.clear()
            flash("セッションが無効になりました。再度ログインしてください。", "warning")
            return redirect(url_for('login'))
        
        # アクセストークンの検証
        try:
            # セッションのアクセストークンを検証
            user_data = supabase.auth.get_user(session['access_token'])
            if not user_data:
                raise Exception("無効なセッションです")
        except Exception as e:
            logger.warning(f"セッション検証エラー: {str(e)}")
            
            # APIリクエストの場合はJSONレスポンスを返す
            if request.is_json or request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return handle_error(
                    e,
                    error_type="セッションエラー",
                    user_message="セッションが無効になりました。再度ログインしてください",
                    status_code=401
                )
            
            # 通常のリクエストの場合はリダイレクト
            logout_user()
            session.clear()
            flash("セッションが無効になりました。再度ログインしてください。", "warning")
            return redirect(url_for('login'))
        
        # 認証が成功した場合は元の関数を実行
        return f(*args, **kwargs)
    
    return decorated_function

# 最新のフィルタリング済みJSONファイルを取得する関数
def get_latest_filtered_json():
    data_dir = app_paths['data_dir']
    json_files = glob.glob(str(data_dir / 'crawled_data' / '*_filtered.json'))
    if not json_files:
        return []
    latest_file = max(json_files, key=os.path.getctime)
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# 全てのフィルタリング済みJSONファイルの一覧を取得する関数
def get_all_filtered_json_files():
    data_dir = app_paths['data_dir']
    crawled_data_dir = data_dir / 'crawled_data'
    json_files = glob.glob(str(crawled_data_dir / '*_filtered.json'))
    if not json_files:
        return []
    
    # ファイル情報を取得
    file_info = []
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        # ファイル名からタイムスタンプを抽出（jobs_YYYYMMDD_HHMMSS_filtered.json）
        match = re.search(r'jobs_(\d{8})_(\d{6})_filtered\.json', file_name)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            # 日付フォーマットを変換
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

# 特定のフィルタリング済みJSONファイルを読み込む関数
def load_filtered_json(file_path):
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

# 案件データをクリアする関数
def clear_job_data(file_path=None):
    """
    案件データをクリアする
    
    Args:
        file_path: クリアする特定のファイルパス。Noneの場合は全てのファイルをクリア
    
    Returns:
        削除されたファイル数
    """
    try:
        data_dir = app_paths['data_dir']
        crawled_data_dir = data_dir / 'crawled_data'
        
        if file_path:
            # 特定のファイルのみ削除
            if os.path.exists(file_path):
                os.remove(file_path)
                # 対応する非フィルタリングファイルも削除
                raw_file = file_path.replace('_filtered.json', '.json')
                if os.path.exists(raw_file):
                    os.remove(raw_file)
                return 1
            return 0
        else:
            # 全てのファイルを削除（settings.jsonとchecked_jobs.jsonは除く）
            count = 0
            for file_path in glob.glob(str(crawled_data_dir / '*.json')):
                if not file_path.endswith('settings.json') and not file_path.endswith('checked_jobs.json'):
                    os.remove(file_path)
                    count += 1
            return count
    except Exception as e:
        logger.error(f"案件データのクリアに失敗: {str(e)}")
        raise

# 古い案件データを削除する関数
def clear_old_job_data(days=14):
    """
    指定した日数より古い案件データを削除する
    
    Args:
        days: 保持する日数（デフォルト: 14日）
    
    Returns:
        削除されたファイル数
    """
    try:
        # アプリケーションパスを取得
        data_dir = app_paths['data_dir']
        crawled_data_dir = data_dir / 'crawled_data'
        
        # 現在の日時から指定日数前の日時を計算
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"{days}日以前（{cutoff_date.strftime('%Y-%m-%d')}より前）の案件データを削除します")
        
        # 削除対象のファイルを検索
        count = 0
        for file_path in glob.glob(str(crawled_data_dir / 'jobs_*.json')):
            # ファイル名からタイムスタンプを抽出（jobs_YYYYMMDD_HHMMSS.json または jobs_YYYYMMDD_HHMMSS_filtered.json）
            file_name = os.path.basename(file_path)
            match = re.search(r'jobs_(\d{8})_(\d{6})', file_name)
            
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                
                # ファイルの日時を解析
                try:
                    file_date = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    
                    # 指定日数より古い場合は削除
                    if file_date < cutoff_date:
                        logger.info(f"古いファイルを削除: {file_path} ({file_date.strftime('%Y-%m-%d %H:%M:%S')})")
                        os.remove(file_path)
                        count += 1
                except ValueError:
                    # 日付解析エラーの場合はスキップ
                    logger.warning(f"ファイル名の日付解析に失敗: {file_path}")
                    continue
        
        logger.info(f"合計 {count} 件の古い案件データファイルを削除しました")
        return count
    except Exception as e:
        logger.error(f"古い案件データの削除に失敗: {str(e)}\n{traceback.format_exc()}")
        return 0

# 過去の案件を再フィルタリングする関数
def refilter_jobs(filter_prompt, model="gpt-4o-mini"):
    """
    保存されている全ての案件データに対して再フィルタリングを実行
    
    Args:
        filter_prompt: フィルタリング条件
        model: 使用するAIモデル
    
    Returns:
        再フィルタリングされた案件数
    """
    try:
        # アプリケーションパスを取得
        data_dir = app_paths['data_dir']
        crawled_data_dir = data_dir / 'crawled_data'
        
        # 全ての非フィルタリングJSONファイルを取得
        raw_files = glob.glob(str(crawled_data_dir / 'jobs_*.json'))
        raw_files = [f for f in raw_files if not f.endswith('_filtered.json')]
        
        if not raw_files:
            return 0
            
        # OpenAI クライアントの初期化
        settings = load_settings()
        client = OpenAI(
            api_key=settings.get('api_key', '')
        )
        
        # 各ファイルに対して再フィルタリングを実行
        total_filtered = 0
        
        for raw_file in raw_files:
            try:
                # 元データを読み込み
                with open(raw_file, 'r', encoding='utf-8') as f:
                    jobs = json.load(f)
                
                # フィルタリング設定
                config = {
                    'model': model,
                    'prompt': filter_prompt,
                    'temperature': 0,
                    'max_tokens': 100
                }
                
                # フィルタリング実行
                filtered_jobs = []
                for job in jobs:
                    try:
                        # 案件情報をテキスト形式に変換
                        job_text = f"""
                        タイトル: {job.get('title', 'N/A')}
                        予算: {job.get('budget', 'N/A')}
                        クライアント: {job.get('client', 'N/A')}
                        投稿日: {job.get('posted_date', 'N/A')}
                        説明: {job.get('description', 'N/A')}
                        """
                        
                        # GPTにフィルタリングを依頼
                        response = client.chat.completions.create(
                            model=config['model'],
                            messages=[
                                {"role": "system", "content": "あなたは案件フィルタリングを行うアシスタントです。与えられた条件に基づいて案件を評価し、条件に合致するかどうかを判断してください。"},
                                {"role": "user", "content": f"以下の案件が条件「{config['prompt']}」に合致するか判断してください。\n\n{job_text}\n\nJSON形式で回答してください: {{\"match\": true/false, \"reason\": \"理由\"}}"}
                            ],
                            temperature=config['temperature'],
                            max_tokens=config['max_tokens']
                        )
                        
                        # レスポンスからJSONを抽出
                        result_text = response.choices[0].message.content
                        result_json = re.search(r'\{.*\}', result_text, re.DOTALL)
                        if result_json:
                            result = json.loads(result_json.group(0))
                        else:
                            result = {"match": True, "reason": "フォーマットエラー（安全のため含める）"}
                        
                        # 条件に合致する場合のみ追加
                        if result.get('match', True):
                            job['gpt_reason'] = result.get('reason', '')
                            filtered_jobs.append(job)
                    except Exception as e:
                        logger.error(f"案件フィルタリング中にエラー: {str(e)}")
                        # エラーの場合は安全のため含める
                        filtered_jobs.append(job)
                
                # フィルタリング結果を保存
                filtered_file = raw_file.replace('.json', '_filtered.json')
                with open(filtered_file, 'w', encoding='utf-8') as f:
                    json.dump(filtered_jobs, f, ensure_ascii=False, indent=2)
                
                total_filtered += len(filtered_jobs)
                
            except Exception as e:
                logger.error(f"ファイル {raw_file} の再フィルタリング中にエラー: {str(e)}")
                continue
        
        return total_filtered
        
    except Exception as e:
        logger.error(f"再フィルタリング処理中にエラー: {str(e)}")
        raise

# チェック状態を保存するファイル
CHECKS_FILE = 'crawled_data/checked_jobs.json'

# チェック状態を読み込む
def load_checks():
    if os.path.exists(CHECKS_FILE):
        with open(CHECKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# チェック状態を保存
def save_checks(checks):
    os.makedirs(os.path.dirname(CHECKS_FILE), exist_ok=True)
    with open(CHECKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(checks, f, ensure_ascii=False, indent=2)

# 設定ファイルのパス
SETTINGS_FILE = 'crawled_data/settings.json'

# prompt.txtのパス
PROMPT_FILE = 'prompt.txt'

# デフォルト設定
DEFAULT_SETTINGS = {
    'model': 'gpt-4o',
    'api_key': '',
    'deepseek_api_key': '',
    'max_items': 50,
    'filter_prompt': '',
    'self_introduction': '',
    'crowdworks_email': '',
    'crowdworks_password': '',
    'coconala_email': '',
    'coconala_password': ''
}

# 設定を保存
def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    # プロンプトが更新された場合、prompt.txtも更新
    if 'filter_prompt' in settings:
        prompt_config = {
            'model': settings.get('model', '4o-mini'),
            'prompt': settings['filter_prompt'],
            'temperature': 0,
            'max_tokens': 100
        }
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompt_config, f, ensure_ascii=False, indent=2)
    
    # デバッグ情報を追加
    logger.info(f"設定を保存します: {SETTINGS_FILE}")
    logger.debug(f"保存する設定: {settings}")
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    
    logger.info("設定を保存しました")

# 設定を読み込む
def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    
    # 設定ファイルから読み込み
    if os.path.exists(SETTINGS_FILE):
        logger.info(f"設定ファイルを読み込みます: {SETTINGS_FILE}")
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                settings.update(loaded_settings)
                logger.debug(f"読み込んだ設定: {settings}")
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
    else:
        logger.warning(f"設定ファイルが見つかりません: {SETTINGS_FILE}")
    
    # prompt.txtからフィルター設定を読み込み
    if os.path.exists(PROMPT_FILE):
        try:
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt_config = json.load(f)
                settings['filter_prompt'] = prompt_config.get('prompt', '')
        except Exception as e:
            logger.error(f"prompt.txtの読み込みに失敗: {str(e)}")
    
    # SelfIntroduction.txtから自己紹介文を読み込み
    self_intro_file = app_paths['data_dir'] / 'crawled_data' / 'SelfIntroduction.txt'
    if os.path.exists(self_intro_file):
        try:
            with open(self_intro_file, 'r', encoding='utf-8') as f:
                settings['self_introduction'] = f.read()
        except Exception as e:
            logger.error(f"自己紹介文の読み込みに失敗: {str(e)}")
            settings['self_introduction'] = ''
    else:
        # SelfIntroduction.txtがない場合はデフォルトの自己紹介文を設定
        settings['self_introduction'] = ''
    
    return settings

# 認証関連のルート
@app.route('/login')
def login():
    # ログイン後のリダイレクト先をセッションに保存
    if not current_user.is_authenticated:
        return render_template('login.html')
    return redirect(url_for('index'))

@app.route('/login/google')
def login_with_google():
    try:
        # 実行中のポート番号を取得
        port = int(os.environ.get('PORT', 8080))
        redirect_url = f'http://localhost:{port}/auth/callback'
        
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
                "scopes": "email profile"
            }
        })
        if not response.url:
            raise Exception("認証URLが取得できませんでした")
        return redirect(response.url)
    except Exception as e:
        flash(f'ログインエラー: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/callback')
def auth_callback():
    try:
        access_token = request.args.get('access_token')
        if access_token:
            try:
                # アクセストークンをセッションに保存
                session['access_token'] = access_token
                # ユーザー情報を取得
                user_response = supabase.auth.get_user(access_token)
                user_metadata = user_response.user.user_metadata
                avatar_url = user_metadata.get('avatar_url') if user_metadata else None
                user = User(user_response.user.id, user_response.user.email, avatar_url)
                login_user(user)
                flash('ログインしました', 'success')
                return redirect(url_for('top'))
            except Exception as e:
                print(f"Auth error: {str(e)}")
                flash('認証エラーが発生しました', 'error')
                return redirect(url_for('login'))
    except Exception as e:
        flash(f'認証エラー: {str(e)}', 'error')
    return redirect(url_for('login'))

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    try:
        # Supabaseのセッションを終了
        if 'access_token' in session:
            try:
                supabase.auth.sign_out(session['access_token'])
            except:
                pass  # Supabaseのエラーは無視
            
        # Flaskのセッションとログイン状態をクリア
        logout_user()
        session.clear()
        
        # 新しいCSRFトークンを生成
        csrf = CSRFProtect(app)
        csrf.generate_token()
        
        flash('ログアウトしました', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        # エラー時も確実にセッションをクリア
        logout_user()
        session.clear()
        flash(f'ログアウトエラー: {str(e)}', 'error')
        return redirect(url_for('login'))

# メインのルート（認証必須）
@app.route('/')
@auth_required
def index():
    # トップページにリダイレクト
    return redirect(url_for('top'))

# トップページ（認証必須）
@app.route('/top')
@auth_required
def top():
    # トップページを表示
    return render_template('top.html')

# サービス別案件一覧ページ（認証必須）
@app.route('/jobs/<service>')
@auth_required
def service_jobs(service):
    if service not in ['crowdworks', 'coconala']:
        flash('無効なサービスが指定されました', 'error')
        return redirect(url_for('top'))
    
    # 現在はココナラは未対応
    if service == 'coconala':
        flash('ココナラの案件一覧は現在準備中です', 'warning')
        return redirect(url_for('top'))
    
    # クラウドワークスの場合は従来の案件一覧を表示
    jobs = get_latest_filtered_json()
    checks = load_checks()
    settings = load_settings()
    # 詳細テキストの改行をHTMLの<br>タグに変換
    for job in jobs:
        if 'detail_description' in job:
            job['detail_description'] = job['detail_description'].replace('\n', '<br>')
    return render_template('index.html', jobs=jobs, checks=checks, settings=settings, service=service)

@app.route('/update_check', methods=['POST'])
@auth_required
def update_check():
    try:
        data = request.get_json()
        job_url = data.get('url')
        is_checked = data.get('checked')
        
        logger.info(f"チェック状態の更新リクエスト: URL={job_url}, checked={is_checked}")
        
        checks = load_checks()
        checks[job_url] = {
            'checked': is_checked,
            'updated_at': datetime.now().isoformat()
        }
        save_checks(checks)
        
        logger.info(f"チェック状態を更新しました: URL={job_url}, checked={is_checked}")
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"チェック状態の更新に失敗: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_settings', methods=['POST'])
@auth_required
def update_settings():
    try:
        # JSONデータの解析
        try:
            data = request.get_json(silent=True)
            if data is None:
                return handle_error(
                    Exception("JSONデータが見つかりません"),
                    error_type="リクエストエラー",
                    user_message="リクエストボディが無効です。JSONデータを送信してください。",
                    status_code=400
                )
        except Exception as e:
            return handle_error(
                e,
                error_type="リクエストエラー",
                user_message="リクエストの解析に失敗しました。正しいJSON形式で送信してください。",
                status_code=400
            )
            
        # 設定の読み込み
        try:
            settings = load_settings()
        except Exception as e:
            return handle_error(
                e,
                error_type="設定読み込みエラー",
                user_message="設定の読み込みに失敗しました。",
                status_code=500
            )
        
        # 更新する設定項目を処理
        try:
            if 'model' in data:
                settings['model'] = data['model']
            if 'max_items' in data:
                settings['max_items'] = int(data['max_items'])
            if 'api_key' in data:
                settings['api_key'] = data['api_key']
            if 'deepseek_api_key' in data:
                settings['deepseek_api_key'] = data['deepseek_api_key']
            if 'filter_prompt' in data:
                settings['filter_prompt'] = data['filter_prompt']
            if 'self_introduction' in data:
                settings['self_introduction'] = data['self_introduction']
                # SelfIntroduction.txtファイルに保存
                try:
                    self_intro_file = app_paths['data_dir'] / 'crawled_data' / 'SelfIntroduction.txt'
                    with open(self_intro_file, 'w', encoding='utf-8') as f:
                        f.write(data['self_introduction'])
                except Exception as e:
                    logger.error(f"自己紹介文の保存に失敗: {str(e)}")
                    return jsonify({'status': 'error', 'message': '自己紹介文の保存に失敗しました'}), 500
            
            # サービス認証情報の更新
            if 'crowdworks_email' in data:
                settings['crowdworks_email'] = data['crowdworks_email']
            if 'crowdworks_password' in data:
                settings['crowdworks_password'] = data['crowdworks_password']
            if 'coconala_email' in data:
                settings['coconala_email'] = data['coconala_email']
            if 'coconala_password' in data:
                settings['coconala_password'] = data['coconala_password']
        except ValueError as e:
            return handle_error(
                e,
                error_type="値エラー",
                user_message="設定値の形式が正しくありません。",
                status_code=400
            )
        
        # 設定の保存
        try:
            save_settings(settings)
        except Exception as e:
            return handle_error(
                e,
                error_type="設定保存エラー",
                user_message="設定の保存に失敗しました。",
                status_code=500
            )
            
        # 成功レスポンス
        logger.info("設定が正常に更新されました")
        return jsonify({
            'status': 'success',
            'message': '設定を更新しました'
        })
    except Exception as e:
        return handle_error(
            e,
            error_type="設定更新エラー",
            user_message="設定の更新中に予期しないエラーが発生しました。",
            status_code=500
        )

@app.route('/fetch_new_data', methods=['POST'])
@auth_required
def fetch_new_data():
    try:
        # リクエストボディを取得（空でも問題ない）
        try:
            data = request.get_json(silent=True) or {}
        except Exception as e:
            logger.warning(f"リクエストの解析に失敗: {str(e)}")
            data = {}
            
        # クローラーのパスを取得
        try:
            crawler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler.py')
            if not os.path.exists(crawler_path):
                return handle_error(
                    Exception(f"クローラーファイルが見つかりません: {crawler_path}"),
                    error_type="ファイルエラー",
                    user_message="クローラーファイルが見つかりません。",
                    status_code=500
                )
        except Exception as e:
            return handle_error(
                e,
                error_type="パスエラー",
                user_message="クローラーファイルのパス取得に失敗しました。",
                status_code=500
            )
        
        # Pythonインタープリタのパスを取得
        python_executable = sys.executable
        
        # サブプロセスとしてクローラーを実行
        try:
            logger.info(f"クローラーを実行: {python_executable} {crawler_path}")
            process = subprocess.Popen(
                [python_executable, crawler_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 実行結果を取得
            stdout, stderr = process.communicate()
            
            # 出力内容をログに記録
            logger.info(f"クローラー標準出力: {stdout}")
            if stderr:
                logger.warning(f"クローラー標準エラー出力: {stderr}")
            
            if process.returncode != 0:
                logger.error(f"クローラーの実行に失敗: 戻り値={process.returncode}, エラー={stderr}")
                return handle_error(
                    Exception(f"クローラーの実行に失敗しました: {stderr}"),
                    error_type="クローラーエラー",
                    user_message=f"データの取得に失敗しました: {stderr}",
                    status_code=500
                )
        except subprocess.SubprocessError as e:
            return handle_error(
                e,
                error_type="プロセスエラー",
                user_message="クローラープロセスの実行に失敗しました。",
                status_code=500
            )
        
        # 最新のデータを読み込む
        try:
            data_dir = app_paths['data_dir']
            crawled_data_dir = data_dir / 'crawled_data'
            os.makedirs(crawled_data_dir, exist_ok=True)
            
            json_files = glob.glob(str(crawled_data_dir / '*_filtered.json'))
            if not json_files:
                logger.warning("フィルタリング済みJSONファイルが見つかりません")
                return jsonify({
                    'status': 'error',
                    'message': '新規データが見つかりませんでした。ログインエラーや設定の問題が考えられます。',
                    'crawler_output': stdout,
                    'crawler_error': stderr
                }), 404
                
            # 最新のファイルを選択
            latest_file = max(json_files, key=os.path.getctime)
            logger.info(f"最新のフィルタリング済みJSONファイル: {latest_file}")
            
            # ファイルが存在するか確認
            if not os.path.exists(latest_file) or os.path.getsize(latest_file) == 0:
                logger.error(f"ファイルが存在しないか空です: {latest_file}")
                return jsonify({
                    'status': 'error',
                    'message': 'データファイルが存在しないか空です。',
                    'crawler_output': stdout,
                    'crawler_error': stderr
                }), 500
            
            # ファイルを読み込む
            with open(latest_file, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
                
            logger.info(f"新規データの取得が完了: {len(jobs)}件の案件を取得")
            return jsonify({
                'status': 'success',
                'message': f'新規データの取得が完了しました（{len(jobs)}件）',
                'jobs': jobs
            })
        except json.JSONDecodeError as e:
            logger.error(f"JSONの解析に失敗: {str(e)}, ファイル: {latest_file}")
            return handle_error(
                e,
                error_type="JSONデータエラー",
                user_message="新規データの解析に失敗しました。データが破損している可能性があります。",
                status_code=500
            )
        except Exception as e:
            logger.error(f"データ読み込みに失敗: {str(e)}\n{traceback.format_exc()}")
            return handle_error(
                e,
                error_type="データ読み込みエラー",
                user_message="新規データの読み込みに失敗しました。",
                status_code=500
            )
            
    except Exception as e:
        return handle_error(
            e,
            error_type="データ取得エラー",
            user_message="データの取得中に予期しないエラーが発生しました。",
            status_code=500
        )

@app.route('/api/check_auth', methods=['POST'])
@auth_required
def api_check_auth():
    # 既存の check_auth 関数を呼び出す
    return check_auth()

@app.route('/check_auth', methods=['POST'])
@auth_required
def check_auth():
    try:
        # リクエストデータの取得
        try:
            data = request.get_json()
            if not data:
                return handle_error(
                    Exception("リクエストデータが空です"),
                    error_type="リクエストエラー",
                    user_message="リクエストデータが空です。サービス名を指定してください。",
                    status_code=400
                )
        except Exception as e:
            return handle_error(
                e,
                error_type="リクエストエラー",
                user_message="リクエストの解析に失敗しました。正しいJSON形式で送信してください。",
                status_code=400
            )
        
        # サービス名の取得
        service = data.get('service')
        if not service:
            return handle_error(
                Exception("サービス名が指定されていません"),
                error_type="パラメータエラー",
                user_message="サービス名を指定してください。",
                status_code=400
            )
        
        # 設定の読み込み
        try:
            settings = load_settings()
        except Exception as e:
            return handle_error(
                e,
                error_type="設定読み込みエラー",
                user_message="設定の読み込みに失敗しました。",
                status_code=500
            )
        
        # サービスごとの認証情報をチェック
        if service == 'crowdworks':
            authenticated = bool(settings.get('crowdworks_email')) and bool(settings.get('crowdworks_password'))
        elif service == 'coconala':
            authenticated = bool(settings.get('coconala_email')) and bool(settings.get('coconala_password'))
        else:
            return handle_error(
                Exception(f"不明なサービス: {service}"),
                error_type="パラメータエラー",
                user_message=f"不明なサービスです: {service}",
                status_code=400
            )
        
        # 結果を返す
        logger.info(f"認証情報チェック: サービス={service}, 認証状態={authenticated}")
        return jsonify({
            'status': 'success',
            'authenticated': authenticated
        })
    except Exception as e:
        return handle_error(
            e,
            error_type="認証チェックエラー",
            user_message="認証情報の確認中に予期しないエラーが発生しました。",
            status_code=500
        )

@app.route('/fetch_status')
@auth_required
def fetch_status():
    try:
        # アプリケーションパスを取得
        data_dir = app_paths['data_dir']
        log_dir = data_dir / 'logs'
        
        # クローラーのログファイルを検索
        try:
            log_files = glob.glob(str(log_dir / 'crawler_*.log'))
            if not log_files:
                log_files = [str(log_dir / 'crawler.log')]
                
            # ログファイルが存在するか確認
            if not os.path.exists(log_files[0]):
                logger.warning(f"ログファイルが見つかりません: {log_files[0]}")
                return jsonify({
                    'status': 'unknown',
                    'message': 'ログファイルが見つかりません'
                })
        except Exception as e:
            return handle_error(
                e,
                error_type="ログファイル検索エラー",
                user_message="ログファイルの検索に失敗しました。",
                status_code=500
            )
        
        # 最新のログファイルを取得
        try:
            latest_log = max(log_files, key=os.path.getctime)
        except Exception as e:
            return handle_error(
                e,
                error_type="ログファイル選択エラー",
                user_message="最新のログファイルの選択に失敗しました。",
                status_code=500
            )
        
        # ログファイルを読み取り
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                # 最後の10行を読み取り
                lines = f.readlines()[-10:]
        except FileNotFoundError:
            logger.warning(f"ログファイルが見つかりません: {latest_log}")
            return jsonify({
                'status': 'unknown',
                'message': 'ログファイルが見つかりません'
            })
        except Exception as e:
            return handle_error(
                e,
                error_type="ログファイル読み取りエラー",
                user_message="ログファイルの読み取りに失敗しました。",
                status_code=500
            )
            
        # ログから進捗状況を解析
        for line in reversed(lines):
            if '案件を取得' in line:
                return jsonify({
                    'status': 'running',
                    'message': f'案件情報を取得中...'
                })
            elif 'GPTフィルタリング' in line:
                return jsonify({
                    'status': 'running',
                    'message': 'GPTによるフィルタリング中...'
                })
        
        # 進捗状況が不明な場合
        return jsonify({
            'status': 'unknown',
            'message': '処理中...'
        })
        
    except Exception as e:
        return handle_error(
            e,
            error_type="ステータス取得エラー",
            user_message="処理状況の取得中に予期しないエラーが発生しました。",
            status_code=500
        )

@app.route('/job_history')
@auth_required
def job_history_page():
    """案件履歴管理ページを表示"""
    try:
        # 利用可能な案件履歴ファイル一覧を取得
        job_files = get_all_filtered_json_files()
        
        # 最新のファイルから案件を読み込む
        jobs = []
        if job_files:
            jobs = load_filtered_json(job_files[0]['path'])
            
        checks = load_checks()
        settings = load_settings()
        
        return render_template('job_history.html', 
                              job_files=job_files, 
                              jobs=jobs, 
                              current_file=job_files[0] if job_files else None,
                              checks=checks, 
                              settings=settings)
    except Exception as e:
        flash('案件履歴ページの表示中にエラーが発生しました。', 'danger')
        logger.error(f"案件履歴ページ表示エラー: {str(e)}\n{traceback.format_exc()}")
        return redirect(url_for('index'))

@app.route('/api/job_history/files')
@auth_required
def get_job_history_files_api():
    """利用可能な案件履歴ファイル一覧を取得するAPI"""
    try:
        job_files = get_all_filtered_json_files()
        return jsonify({
            'success': True,
            'job_files': job_files
        })
    except Exception as e:
        return handle_error(
            e,
            error_type="案件履歴ファイル一覧取得エラー",
            user_message="案件履歴ファイル一覧の取得に失敗しました。",
            status_code=500
        )

@app.route('/api/job_history/content')
@auth_required
def get_job_history_content():
    """特定の案件履歴ファイルの内容を取得するAPI"""
    try:
        file_path = request.args.get('file')
        
        # 安全なパス構築
        data_dir = app_paths['data_dir']
        crawled_data_dir = data_dir / 'crawled_data'
        file_name = os.path.basename(file_path) if file_path else ""
        safe_file_path = str(crawled_data_dir / file_name)
        
        # パスインジェクション対策
        if not file_path or not file_name.endswith('_filtered.json'):
            return jsonify({
                'success': False,
                'message': '無効な案件ファイルパスです。'
            }), 400
            
        # ファイルの存在確認
        if not os.path.exists(safe_file_path):
            return jsonify({
                'success': False,
                'message': '案件ファイルが見つかりません。'
            }), 404
            
        # ファイルから案件を読み込む
        jobs = load_filtered_json(safe_file_path)
        
        # ファイル情報を取得
        file_name = os.path.basename(safe_file_path)
        match = re.search(r'jobs_(\d{8})_(\d{6})_filtered\.json', file_name)
        date_str = ""
        if match:
            date_str = f"{match.group(1)[:4]}-{match.group(1)[4:6]}-{match.group(1)[6:8]} {match.group(2)[:2]}:{match.group(2)[2:4]}:{match.group(2)[4:6]}"
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'file_name': file_name,
            'date': date_str,
            'job_count': len(jobs)
        })
        
    except Exception as e:
        return handle_error(
            e,
            error_type="案件履歴取得エラー",
            user_message="案件履歴の取得に失敗しました。",
            status_code=500
        )

@app.route('/api/job_history/clear', methods=['POST'])
@auth_required
def clear_job_history():
    """案件履歴をクリアするAPI"""
    try:
        file_path = request.json.get('file')
        
        if file_path:
            # パスインジェクション対策
            file_name = os.path.basename(file_path)
            # ファイルパスを安全に再構築
            data_dir = app_paths['data_dir']
            crawled_data_dir = data_dir / 'crawled_data'
            safe_file_path = str(crawled_data_dir / file_name)
            
            # ファイルの存在確認
            if not os.path.exists(safe_file_path):
                return jsonify({
                    'success': False,
                    'message': '案件ファイルが見つかりません。'
                }), 404
                
            # 特定のファイルをクリア
            clear_job_data(file_path)
            message = '指定された案件履歴をクリアしました。'
        else:
            # 全てのファイルをクリア
            count = clear_job_data()
            message = f'{count}件の案件履歴ファイルをクリアしました。'
            
        # 操作をログに記録
        logger.info(f"案件履歴がクリアされました: {file_path if file_path else '全て'}")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return handle_error(
            e,
            error_type="案件履歴クリアエラー",
            user_message="案件履歴のクリアに失敗しました。",
            status_code=500
        )

@app.route('/api/job_history/refilter', methods=['POST'])
@auth_required
def refilter_job_history():
    """案件履歴を再フィルタリングするAPI"""
    try:
        data = request.get_json()
        filter_prompt = data.get('filter_prompt', '')
        model = data.get('model', 'gpt-4o-mini')
        
        if not filter_prompt:
            return jsonify({
                'success': False,
                'message': 'フィルター条件が指定されていません。'
            }), 400
            
        # 再フィルタリングを実行
        total_filtered = refilter_jobs(filter_prompt, model)
        
        # 設定を更新
        settings = load_settings()
        settings['filter_prompt'] = filter_prompt
        if model != settings.get('model'):
            settings['model'] = model
        save_settings(settings)
        
        # 操作をログに記録
        logger.info(f"案件の再フィルタリングが完了しました: {total_filtered}件")
        
        return jsonify({
            'success': True,
            'message': f'再フィルタリングが完了しました。{total_filtered}件の案件がフィルタリングされました。',
            'total_filtered': total_filtered
        })
        
    except Exception as e:
        return handle_error(
            e,
            error_type="再フィルタリングエラー",
            user_message="案件の再フィルタリングに失敗しました。",
            status_code=500
        )

@app.route('/api/get_checks')
@auth_required
def get_checks_api():
    """チェック状態を取得するAPI"""
    try:
        checks = load_checks()
        return jsonify({
            'success': True,
            'checks': checks
        })
    except Exception as e:
        return handle_error(
            e,
            error_type="チェック状態取得エラー",
            user_message="チェック状態の取得に失敗しました。",
            status_code=500
        )

@app.route('/api/clear_old_data', methods=['POST'])
@auth_required
def clear_old_data_api():
    """古い案件データを削除するAPI"""
    try:
        data = request.get_json()
        days = data.get('days', 14)  # デフォルトは14日
        
        # 日数の検証
        try:
            days = int(days)
            if days < 1:
                return jsonify({
                    'success': False,
                    'message': '日数は1以上の整数を指定してください。'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': '日数は整数で指定してください。'
            }), 400
            
        # 古いデータを削除
        count = clear_old_job_data(days)
        
        return jsonify({
            'success': True,
            'message': f'{days}日以前の案件データを削除しました。合計 {count} 件のファイルを削除しました。',
            'deleted_count': count
        })
    except Exception as e:
        return handle_error(
            e,
            error_type="古いデータ削除エラー",
            user_message="古い案件データの削除に失敗しました。",
            status_code=500
        )

# アップデート確認エンドポイント
@app.route('/api/check_updates', methods=['POST'])
@auth_required
def check_updates_api():
    """
    最新バージョンの確認を行うAPI
    """
    try:
        update_available = check_for_updates()
        return jsonify(get_update_status())
    except Exception as e:
        return handle_error(e, "アップデート確認エラー", "更新の確認中にエラーが発生しました。")

# アップデート実行エンドポイント
@app.route('/api/perform_update', methods=['POST'])
@auth_required
def perform_update_api():
    """
    アップデートを実行するAPI
    """
    try:
        # アップデート中の自動再起動を防止するために環境変数を設定
        os.environ['UPDATING'] = '1'
        # 環境変数ファイルにも書き込み、再起動時にも適用されるようにする
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(dotenv_path):
            set_key(dotenv_path, 'UPDATING', '1')
        
        logger.info("アップデート処理を開始します（自動再起動は無効）")
        result = perform_update()
        
        # アップデート完了後、次回起動時のためにフラグをリセット
        if result.get('success', False):
            os.environ['UPDATING'] = '0'
            if os.path.exists(dotenv_path):
                set_key(dotenv_path, 'UPDATING', '0')
            logger.info("アップデート処理が完了し、環境変数をリセットしました")
        
        return jsonify(result)
    except Exception as e:
        # エラー発生時も環境変数をリセット
        os.environ['UPDATING'] = '0'
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(dotenv_path):
            set_key(dotenv_path, 'UPDATING', '0')
        logger.error(f"アップデート処理中にエラーが発生し、環境変数をリセットしました: {str(e)}")
        return handle_error(e, "アップデート実行エラー", "更新の実行中にエラーが発生しました。")

# アップデートステータス取得エンドポイント
@app.route('/api/update_status', methods=['GET'])
@auth_required
def update_status_api():
    """
    アップデートの進捗状況を取得するAPI
    """
    try:
        return jsonify(get_update_status())
    except Exception as e:
        return handle_error(e, "ステータス取得エラー", "更新状態の取得中にエラーが発生しました。")

# 案件詳細取得エンドポイント
@app.route('/api/job_details', methods=['GET'])
@auth_required
def get_job_details_api():
    """
    指定されたURLの案件詳細を取得するAPI
    """
    try:
        # URLパラメータを取得
        job_url = request.args.get('url')
        if not job_url:
            return jsonify({
                'success': False,
                'message': '案件URLが指定されていません'
            }), 400
        
        # 全ての案件データをチェック
        all_jobs = []
        json_files = glob.glob('crawled_data/*_filtered.json')
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    jobs = json.load(f)
                    all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"ファイル {file_path} の読み込み中にエラー: {str(e)}")
                continue
        
        # URLに一致する案件を探す
        for job in all_jobs:
            if job.get('url') == job_url:
                # 詳細情報の整形
                if 'detail_description' in job:
                    job['detail_description'] = job['detail_description'].replace('\n', '<br>')
                return jsonify({
                    'success': True,
                    'job': job
                })
        
        # 案件が見つからない場合
        return jsonify({
            'success': False,
            'message': '指定されたURLの案件が見つかりません'
        }), 404
        
    except Exception as e:
        logger.error(f"案件詳細の取得中にエラー: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'案件詳細の取得中にエラーが発生しました: {str(e)}'
        }), 500

# ChromeDriverの状態を確認するAPIエンドポイントを追加
@app.route('/api/chromedriver/status', methods=['GET'])
@auth_required
def chromedriver_status_api():
    """ChromeDriverの状態を取得するAPI"""
    try:
        # ChromeDriverManagerのインスタンスを取得
        manager = chromedriver_manager.get_instance()
        config = manager.config
        
        # 状態情報を作成
        status = {
            "chrome_version": config.get("chrome_version", "不明"),
            "driver_version": config.get("driver_version", "不明"),
            "driver_path": config.get("driver_path", "不明"),
            "last_check": config.get("last_check", "なし"),
            "last_update": config.get("last_update", "なし"),
            "is_update_running": manager.update_thread is not None and manager.update_thread.is_alive()
        }
        
        return jsonify({"status": "success", "data": status})
    except Exception as e:
        logger.error(f"ChromeDriverの状態取得に失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ChromeDriverを手動で更新するAPIエンドポイントを追加
@app.route('/api/chromedriver/update', methods=['POST'])
@auth_required
def chromedriver_update_api():
    """ChromeDriverを手動で更新するAPI"""
    try:
        # ChromeDriverを再セットアップ
        driver_path = chromedriver_manager.setup_driver()
        
        if driver_path:
            # 環境変数にドライバーパスを設定
            os.environ["SELENIUM_DRIVER_PATH"] = driver_path
            
            # .envファイルにも保存（再起動時のため）
            dotenv_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(dotenv_path):
                set_key(dotenv_path, 'SELENIUM_DRIVER_PATH', driver_path)
            
            return jsonify({
                "status": "success", 
                "message": "ChromeDriverを更新しました", 
                "driver_path": driver_path
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "ChromeDriverの更新に失敗しました"
            }), 500
    except Exception as e:
        logger.error(f"ChromeDriverの手動更新に失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ChromeDriverエラーページを表示するルート
@app.route('/chromedriver_error')
def chromedriver_error():
    """ChromeDriverエラーページを表示"""
    error_message = request.args.get('message', 'ChromeDriverの設定に問題が発生しました。')
    return render_template('error.html', error_message=error_message)

# アプリケーション終了時の処理
def cleanup_resources():
    # ChromeDriverのバックグラウンド更新を停止
    chromedriver_manager.stop_background_update()
    logger.info("ChromeDriverのバックグラウンド更新を停止しました")
    
    # Nodeサーバーも終了させる
    stop_node_server()

# Nodeサーバーを停止する関数
def stop_node_server():
    global node_process
    if node_process:
        try:
            logger.info(f"Nodeサーバーを終了します (PID={node_process.pid})")
            node_process.terminate()
            
            # 終了を確認し、必要に応じて強制終了
            time.sleep(1)
            if node_process.poll() is None:
                logger.info(f"Nodeサーバーを強制終了します (PID={node_process.pid})")
                if sys.platform == 'win32':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(node_process.pid)])
                else:
                    os.kill(node_process.pid, signal.SIGKILL)
            
            node_process = None
            logger.info("Nodeサーバーを終了しました")
        except Exception as e:
            logger.error(f"Nodeサーバー終了処理中にエラー: {str(e)}")

# Nodeサーバーを起動する関数
def start_node_server():
    global node_process
    
    if node_process is not None:
        logger.info("Nodeサーバーは既に起動しています")
        return
    
    try:
        # npmコマンドのパスを動的に検出
        npm_path = "npm"  # デフォルト値
        try:
            # which/whereコマンドでnpmの場所を特定
            if sys.platform == 'win32':
                process = subprocess.run(["where", "npm"], capture_output=True, text=True, check=True)
            else:
                process = subprocess.run(["which", "npm"], capture_output=True, text=True, check=True)
            
            if process.stdout.strip():
                npm_path = process.stdout.strip().split('\n')[0]  # 最初の行を取得
                logger.info(f"検出されたnpmパス: {npm_path}")
        except Exception as npm_error:
            logger.warning(f"npmパスの自動検出に失敗しました: {str(npm_error)}")
            # 既知のパスを試す
            known_paths = [
                "/Users/m1_mini/.nvm/versions/node/v22.14.0/bin/npm",
                "/usr/local/bin/npm",
                "/opt/homebrew/bin/npm"
            ]
            for path in known_paths:
                if os.path.exists(path):
                    npm_path = path
                    logger.info(f"既知のパスからnpmを見つけました: {npm_path}")
                    break
        
        # 環境変数から起動コマンドを取得（デフォルトは「npm run dev」）
        node_cmd_str = os.getenv('NODE_SERVER_CMD', 'npm run dev')
        # npmをフルパスに置き換え
        if node_cmd_str.startswith('npm'):
            node_cmd_str = node_cmd_str.replace('npm', npm_path, 1)
        
        node_cmd = node_cmd_str.split()
        
        # カレントディレクトリからNodeサーバーのディレクトリを取得（デフォルトはカレントディレクトリ）
        node_dir = os.getenv('NODE_SERVER_DIR', '.')
        
        logger.info(f"Nodeサーバーを起動します: {' '.join(node_cmd)} in {node_dir}")
        
        # 環境変数を設定してPATHを通す
        env = os.environ.copy()
        npm_dir = os.path.dirname(npm_path)
        if npm_dir not in env.get('PATH', ''):
            env['PATH'] = f"{npm_dir}:{env.get('PATH', '')}"
        
        # Nodeサーバーを起動
        node_process = subprocess.Popen(
            node_cmd,
            cwd=node_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        logger.info(f"Nodeサーバーを起動しました (PID={node_process.pid})")
    except Exception as e:
        logger.error(f"Nodeサーバーの起動に失敗: {str(e)}\n{traceback.format_exc()}")

# アプリケーション終了時に実行する関数を登録
atexit.register(cleanup_resources)

# 初期化関数を定義
def init_app():
    """アプリケーションの初期化"""
    # 環境初期化
    initialize_app_environment()
    
    # バルク応募機能の初期化
    init_bulk_apply()
    
    # バルク応募ルートの登録
    register_bulk_apply_routes(app)
    
    return app

# ブラウザ終了通知を受け取るAPIエンドポイント
@app.route('/api/browser_close', methods=['POST'])
@csrf.exempt  # CSRFトークン検証を除外
def browser_close():
    """ブラウザが閉じられたときに呼び出されるAPI"""
    try:
        # ブラウザからのデータを取得
        data = request.get_json(silent=True) or {}
        
        # Nodeサーバーを終了
        stop_node_server()
        
        logger.info("ブラウザ終了通知を受信しました。Nodeサーバーを終了しました。")
        
        return jsonify({
            'status': 'success',
            'message': 'Nodeサーバーを終了しました'
        })
    except Exception as e:
        logger.error(f"ブラウザ終了処理中にエラー: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# グローバル変数としてロックファイルパスとロックファイルハンドルを定義
LOCK_FILE = None
LOCK_FD = None

def is_port_in_use(port):
    """指定したポートが使用中かどうかをチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_lock_file():
    """ロックファイルのパスを取得"""
    global LOCK_FILE
    if LOCK_FILE is None:
        # アプリケーションパスを取得
        app_paths = get_app_paths()
        data_dir = app_paths['data_dir']
        LOCK_FILE = data_dir / "anken_navi.lock"
    return LOCK_FILE

def acquire_lock(lock_file):
    """ロックファイルをロック (macOS用実装)"""
    global LOCK_FD
    
    try:
        # ロックファイルパスの親ディレクトリが存在することを確認
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # ロックファイルをオープン
        lock_fd = open(lock_file, 'w')
        
        try:
            # 排他ロックを取得
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # ロック成功
            LOCK_FD = lock_fd
            return True
        except IOError:
            # ロック失敗（ファイルが既にロックされている）
            try:
                if lock_fd:
                    lock_fd.close()
            except:
                pass
            return False
    except Exception as e:
        logger.error(f"ロック取得中にエラー: {str(e)}")
        return False

def release_lock():
    """ロックファイルのロック解除 (macOS用実装)"""
    global LOCK_FD, LOCK_FILE
    
    if LOCK_FD:
        try:
            # ロック解除
            fcntl.flock(LOCK_FD, fcntl.LOCK_UN)
            
            # ファイルを閉じる
            LOCK_FD.close()
            
            # ロックファイルを削除
            try:
                if LOCK_FILE and LOCK_FILE.exists():
                    LOCK_FILE.unlink()
            except:
                pass
                
            logger.info("アプリケーションロックを解除しました")
        except Exception as e:
            logger.error(f"ロック解除中にエラー: {str(e)}")
        finally:
            LOCK_FD = None

def check_already_running(port):
    """
    アプリケーションが既に実行中かどうかをチェック
    既に実行中の場合は終了する

    Args:
        port: アプリケーションのポート番号

    Returns:
        True: 既に実行中
        False: 実行中ではない
    """
    # ポートが使用中かチェック
    if is_port_in_use(port):
        logger.info(f"ポート {port} は既に使用中です。アプリケーションは既に実行中です。")
        # ブラウザは自動で開かない
        return True

    # ロックファイルのパスを取得
    lock_file = get_lock_file()
    
    # ロックを取得を試行
    if acquire_lock(lock_file):
        # ロック成功 - PIDとポート情報をロックファイルに書き込む
        if LOCK_FD:
            LOCK_FD.write(f"{os.getpid()},{port}")
            LOCK_FD.flush()
            
        # 終了時にロックを解除するよう登録
        atexit.register(release_lock)
        
        logger.info(f"アプリケーションロックを取得しました: {lock_file}")
        return False
    else:
        # ロック取得失敗 - 既に別のインスタンスが実行中
        
        # ロックファイルから情報を読み取り
        try:
            with open(lock_file, 'r') as f:
                content = f.read().strip()
                if content:
                    parts = content.split(',')
                    if len(parts) == 2:
                        pid, existing_port = parts
                        
                        # PIDをチェックしてプロセスが実行中か確認
                        try:
                            pid = int(pid)
                            # プロセスが存在するか確認
                            try:
                                os.kill(pid, 0)
                                # プロセスが実行中の場合は既に実行中と表示するのみ
                                logger.info(f"既存のインスタンスを検出: PID={pid}, ポート={existing_port}")
                                return True
                            except OSError:
                                # プロセスが存在しない場合
                                logger.warning(f"ロックファイルのプロセスが既に終了しています: {pid}")
                                
                                # ロックファイルを強制削除し、再試行
                                try:
                                    if lock_file.exists():
                                        lock_file.unlink()
                                    time.sleep(1)  # 少し待機
                                    return check_already_running(port)  # 再試行
                                except Exception as e:
                                    logger.error(f"古いロックファイル削除中にエラー: {str(e)}")
                        except (ValueError, TypeError) as e:
                            logger.error(f"無効なPID: {str(e)}")
        except Exception as e:
            logger.error(f"ロックファイル読み取り中にエラー: {str(e)}")
        
        # ポートが使用中の場合も既に実行中と表示するのみ
        if is_port_in_use(port):
            logger.info(f"ポート {port} は既に使用中です。アプリケーションは既に実行中です。")
            
        return True

# ブラウザのセッション管理のための関数
def check_and_reopen_browser(port):
    """
    定期的にサーバーの状態をチェックして必要に応じてブラウザを再度開く
    """
    def browser_checker():
        # 最初はブラウザが開かれたと仮定
        browser_opened = True
        last_check_time = time.time()
        
        while True:
            try:
                # 30秒ごとにチェック
                time.sleep(30)
                
                # ユーザーがブラウザを閉じた後で一定時間以上経過した場合、ブラウザを再度開く
                # （最初の1分は除外、セットアップ中の場合があるため）
                current_time = time.time()
                if current_time - last_check_time > 60 and not browser_opened:
                    logger.info("ブラウザセッションが見つかりません。ブラウザを再度開きます。")
                    webbrowser.open(f"http://localhost:{port}/login")
                    browser_opened = True
                
                # ブラウザ終了通知があったことがわかるフラグをリセット
                last_check_time = current_time
                browser_opened = False
                
            except Exception as e:
                logger.error(f"ブラウザチェック中にエラー: {str(e)}")
    
    # バックグラウンドスレッドとして実行
    checker_thread = threading.Thread(target=browser_checker, daemon=True)
    checker_thread.start()

# アプリケーションの起動
if __name__ == "__main__":
    try:
        # アプリケーションの初期化
        init_app()
        
        # ポート番号を取得
        port = int(os.environ.get('PORT', 8080))
        
        # 既に実行中かチェック
        if check_already_running(port):
            logger.info("アプリケーションは既に実行中です。終了します。")
            sys.exit(0)
        
        # Nodeサーバーを起動（必要な場合）
        if not os.environ.get('SKIP_NODE_SERVER', False):
            start_node_server()
        
        # サーバーを起動
        app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')
    except Exception as e:
        logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        sys.exit(1)