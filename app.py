from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from functools import wraps
import json
import os
import glob
from datetime import datetime
import traceback
from dotenv import load_dotenv, set_key
from pathlib import Path
import subprocess
import sys
from bulk_apply import register_bulk_apply_routes, init_bulk_apply
from supabase import create_client, Client
import logging

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
Bootstrap(app)
csrf = CSRFProtect(app)

# CSRFトークンをAjaxリクエストでも検証するように設定
csrf.exempt_views = []

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
    'model': 'gpt-4o-mini',
    'max_items': 50,
    'api_key': '',
    'deepseek_api_key': '',
    'deepseek_model': 'deepseek-chat',
    'filter_prompt': '',
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
    data = request.get_json()
    job_url = data.get('url')
    is_checked = data.get('checked')
    
    checks = load_checks()
    checks[job_url] = {
        'checked': is_checked,
        'updated_at': datetime.now().isoformat()
    }
    save_checks(checks)
    return jsonify({'status': 'success'})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)