from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap
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
from bulk_apply import register_bulk_apply_routes, init_bulk_apply
from supabase import create_client, Client
import logging
import re
from openai import OpenAI
from updater import check_for_updates, perform_update, get_update_status
import atexit

# ChromeDriver自動管理モジュールをインポート
import chromedriver_manager

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
Bootstrap(app)
csrf = CSRFProtect(app)

# CSRFトークンをAjaxリクエストでも検証するように設定
csrf.exempt_views = []

# アップデート関連のエンドポイントをCSRF保護から除外（バックアップとして）
csrf.exempt('/api/check_updates')
csrf.exempt('/api/perform_update')
csrf.exempt('/api/update_status')
csrf.exempt('/bulk_apply')

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

# 一括応募機能の初期化
init_bulk_apply()
# 一括応募ルートの登録
register_bulk_apply_routes(app)

# 最新のフィルタリング済みJSONファイルを取得する関数
def get_latest_filtered_json():
    json_files = glob.glob('crawled_data/*_filtered.json')
    if not json_files:
        return []
    latest_file = max(json_files, key=os.path.getctime)
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# 全てのフィルタリング済みJSONファイルの一覧を取得する関数
def get_all_filtered_json_files():
    json_files = glob.glob('crawled_data/*_filtered.json')
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
            for file_path in glob.glob('crawled_data/*.json'):
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
        # 現在の日時から指定日数前の日時を計算
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"{days}日以前（{cutoff_date.strftime('%Y-%m-%d')}より前）の案件データを削除します")
        
        # 削除対象のファイルを検索
        count = 0
        for file_path in glob.glob('crawled_data/jobs_*.json'):
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
        # 全ての非フィルタリングJSONファイルを取得
        raw_files = glob.glob('crawled_data/jobs_*.json')
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
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# 設定を読み込む
def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    
    # 設定ファイルから読み込み
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings.update(json.load(f))
    
    # prompt.txtからフィルター設定を読み込み
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompt_config = json.load(f)
            settings['filter_prompt'] = prompt_config.get('prompt', '')
    
    # SelfIntroduction.txtから自己紹介文を読み込み
    if os.path.exists('SelfIntroduction.txt'):
        try:
            with open('SelfIntroduction.txt', 'r', encoding='utf-8') as f:
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
        redirect_url = 'http://localhost:3000/auth/callback'
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
                return redirect(url_for('index'))
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
    jobs = get_latest_filtered_json()
    checks = load_checks()
    settings = load_settings()
    # 詳細テキストの改行をHTMLの<br>タグに変換
    for job in jobs:
        if 'detail_description' in job:
            job['detail_description'] = job['detail_description'].replace('\n', '<br>')
    return render_template('index.html', jobs=jobs, checks=checks, settings=settings)

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
                    with open('SelfIntroduction.txt', 'w', encoding='utf-8') as f:
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
            process = subprocess.Popen(
                [python_executable, crawler_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 実行結果を取得
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"クローラーの実行に失敗: {stderr}")
                return handle_error(
                    Exception(f"クローラーの実行に失敗しました"),
                    error_type="クローラーエラー",
                    user_message="データの取得に失敗しました。詳細はログを確認してください。",
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
            jobs = get_latest_filtered_json()
            logger.info(f"新規データの取得が完了: {len(jobs)}件の案件を取得")
            return jsonify({
                'status': 'success',
                'message': '新規データの取得が完了しました',
                'jobs': jobs
            })
        except Exception as e:
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
        # クローラーのログファイルを検索
        try:
            log_files = glob.glob('logs/crawler_*.log')
            if not log_files:
                log_files = ['logs/crawler.log']
                
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
        
        # パスインジェクション対策
        if not file_path or '..' in file_path or not file_path.startswith('crawled_data/') or not file_path.endswith('_filtered.json'):
            return jsonify({
                'success': False,
                'message': '無効な案件ファイルパスです。'
            }), 400
            
        # ファイルの存在確認
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '案件ファイルが見つかりません。'
            }), 404
            
        # ファイルから案件を読み込む
        jobs = load_filtered_json(file_path)
        
        # ファイル情報を取得
        file_name = os.path.basename(file_path)
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
            if '..' in file_path or not file_path.startswith('crawled_data/') or not file_path.endswith('_filtered.json'):
                return jsonify({
                    'success': False,
                    'message': '無効な案件ファイルパスです。'
                }), 400
                
            # ファイルの存在確認
            if not os.path.exists(file_path):
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
        result = perform_update()
        return jsonify(result)
    except Exception as e:
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

if __name__ == '__main__':
    # 起動時に古いデータを削除
    clear_old_job_data()
    
    # .envファイルから環境変数PORTを取得
    port = int(os.getenv('PORT', 8000))
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)