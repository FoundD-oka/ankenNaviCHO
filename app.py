from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from functools import wraps
import json
import os
import glob
from datetime import datetime
from dotenv import load_dotenv, set_key
from pathlib import Path
import subprocess
import sys
from bulk_apply import register_bulk_apply_routes, init_bulk_apply
from supabase import create_client, Client

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
        if not current_user.is_authenticated or 'access_token' not in session:
            logout_user()
            session.clear()
            return redirect(url_for('login'))
        try:
            # セッションのアクセストークンを検証
            user_data = supabase.auth.get_user(session['access_token'])
            if not user_data:
                raise Exception("Invalid session")
        except Exception:
            logout_user()
            session.clear()
            return redirect(url_for('login'))
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
        try:
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({
                    'status': 'error',
                    'message': 'リクエストボディが無効です。JSONデータを送信してください。'
                }), 400
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'リクエストの解析に失敗しました: {str(e)}'
            }), 400
            
        settings = load_settings()
        
        # 更新する設定項目を処理
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
        
        save_settings(settings)
        return jsonify({
            'status': 'success',
            'message': '設定を更新しました'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/fetch_new_data', methods=['POST'])
@auth_required
def fetch_new_data():
    try:
        # リクエストボディを取得（空でも問題ない）
        try:
            data = request.get_json(silent=True) or {}
        except:
            data = {}
            
        # クローラーのパスを取得
        crawler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler.py')
        
        # Pythonインタープリタのパスを取得
        python_executable = sys.executable
        
        # サブプロセスとしてクローラーを実行
        process = subprocess.Popen(
            [python_executable, crawler_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 実行結果を取得
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # 最新のデータを読み込む
            jobs = get_latest_filtered_json()
            return jsonify({
                'status': 'success',
                'message': '新規データの取得が完了しました',
                'jobs': jobs
            })
        else:
            raise Exception(f"クローラーの実行に失敗しました: {stderr}")
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/check_auth', methods=['POST'])
@auth_required
def check_auth():
    try:
        data = request.get_json()
        service = data.get('service')
        settings = load_settings()
        
        # サービスごとの認証情報をチェック
        if service == 'crowdworks':
            authenticated = bool(settings.get('crowdworks_email')) and bool(settings.get('crowdworks_password'))
        elif service == 'coconala':
            authenticated = bool(settings.get('coconala_email')) and bool(settings.get('coconala_password'))
        else:
            authenticated = False
        
        return jsonify({
            'status': 'success',
            'authenticated': authenticated
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'authenticated': False
        }), 500

@app.route('/fetch_status')
@auth_required
def fetch_status():
    try:
        # クローラーのログファイルを読み取り
        log_files = glob.glob('logs/crawler_*.log')
        if not log_files:
            log_files = ['logs/crawler.log']
        
        latest_log = max(log_files, key=os.path.getctime)
        
        with open(latest_log, 'r', encoding='utf-8') as f:
            # 最後の10行を読み取り
            lines = f.readlines()[-10:]
            
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
        
        return jsonify({
            'status': 'unknown',
            'message': '処理中...'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)