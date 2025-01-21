from flask import Flask, render_template, request, jsonify
from flask_bootstrap import Bootstrap
import json
import os
import glob
from datetime import datetime
from dotenv import load_dotenv, set_key
from pathlib import Path
import subprocess
import sys

app = Flask(__name__)
Bootstrap(app)

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

@app.route('/')
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
def update_settings():
    try:
        data = request.get_json()
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
def fetch_new_data():
    try:
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
    app.run(debug=True) 