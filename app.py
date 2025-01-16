from flask import Flask, render_template, request, jsonify
from flask_bootstrap import Bootstrap
import json
import os
import glob
from datetime import datetime

app = Flask(__name__)
Bootstrap(app)

# 最新のJSONファイルを取得する関数
def get_latest_json():
    json_files = glob.glob('crawled_data/jobs_*.json')
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

@app.route('/')
def index():
    jobs = get_latest_json()
    checks = load_checks()
    return render_template('index.html', jobs=jobs, checks=checks)

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

if __name__ == '__main__':
    app.run(debug=True) 