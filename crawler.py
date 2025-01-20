import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import time  # timeモジュールをインポート
from typing import Dict, List
import random
import sys

import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
import re

# ログの設定
logger.remove()  # デフォルトのハンドラを削除
logger.add("logs/crawler.log", mode="w")  # 上書きモードでログファイルを作成

# 設定ファイルのパス
SETTINGS_FILE = 'crawled_data/settings.json'

# 設定を読み込む関数
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
        return {}

# OpenAI クライアントの初期化
settings = load_settings()
client = OpenAI(
    api_key=settings.get('api_key', '')
)

# プロンプトファイルのパス
PROMPT_FILE = 'prompt.txt'

# デフォルトの設定
DEFAULT_CONFIG = {
    "model": "4o-mini",
    "prompt": "予算が10,000以上のもののみピックする",
    "temperature": 0,
    "max_tokens": 100,
    "response_format": { "type": "json_object" }
}

# プロンプトと設定を読み込む関数
def load_config():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 必要なキーがすべて存在することを確認
            required_keys = ["model", "prompt", "temperature", "max_tokens"]
            if all(key in config for key in required_keys):
                # response_formatを追加
                config["response_format"] = { "type": "json_object" }
                # モデル名をそのまま使用（マッピング不要）
                return config
            else:
                print("Warning: Missing required keys in prompt.txt")
                return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

# GPTによる案件フィルタリング
def filter_jobs_by_gpt(jobs, config):
    # OpenAI クライアントの再初期化（最新の設定を使用）
    settings = load_settings()
    client = OpenAI(api_key=settings.get('api_key', ''))
    
    filtered_jobs = []
    total_jobs = len(jobs)
    
    print(f"GPTフィルタリングを開始します。対象案件数: {total_jobs}")
    print(f"使用モデル: {config['model']}")
    print(f"フィルター条件: {config['prompt']}")
    
    for i, job in enumerate(jobs, 1):
        print(f"案件 {i}/{total_jobs} を処理中...")
        # GPTに送信するメッセージを作成
        messages = [
            {"role": "system", "content": """あなたは案件の審査員です。与えられた条件に基づいて、案件を評価してください。
レスポンスは以下のJSON形式で返してください：
{
    "decision": "yes" or "no",
    "reason": "判断理由を1文で"
}"""},
            {"role": "user", "content": f"""
以下の案件が条件を満たすか判断してください。条件: {config['prompt']}

案件情報:
タイトル: {job['title']}
予算: {job['budget']}
クライアント: {job['client']}
            """}
        ]

        try:
            # GPTに問い合わせ（設定を使用）
            response = client.chat.completions.create(
                model=config['model'],
                messages=messages,
                temperature=config['temperature'],
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            # レスポンスを取得してJSONとしてパース
            result = json.loads(response.choices[0].message.content)
            
            # 'yes'の場合のみ案件を追加
            if result.get('decision', '').lower() == 'yes':
                # 判断理由を案件情報に追加
                job['gpt_reason'] = result.get('reason', '')
                filtered_jobs.append(job)
                print(f"✓ 案件が条件に適合: {job['title']}")
            else:
                print(f"✗ 案件が条件に不適合: {job['title']}")
                
        except Exception as e:
            print(f"Error in GPT filtering for job {job['title']}: {e}")
            # エラーの場合は安全のため、その案件を含める
            filtered_jobs.append(job)
    
    print(f"GPTフィルタリング完了。{len(filtered_jobs)}/{total_jobs} 件が条件に適合")
    return filtered_jobs

def save_filtered_jobs(jobs, base_filename):
    """フィルタリング済みの案件をJSONファイルに保存"""
    filtered_filename = base_filename.replace('.json', '_filtered.json')
    with open(filtered_filename, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"フィルタリング済み案件を保存: {filtered_filename}")
    return filtered_filename

# クローリング後の処理を修正
def process_crawled_data(jobs, crawler=None):
    """クロール済みデータの処理とGPTフィルタリング"""
    # 現在時刻を取得してファイル名を生成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f'crawled_data/jobs_{timestamp}.json'
    
    # 生のデータを保存
    with open(base_filename, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"生データを保存: {base_filename}")
    
    # GPTフィルタリングを実行
    config = load_config()
    filtered_jobs = filter_jobs_by_gpt(jobs, config)
    
    # フィルタリング済み案件の詳細情報を取得
    if crawler and filtered_jobs:
        print(f"フィルタリング済み案件の詳細情報を取得中...")
        for job in filtered_jobs:
            detail_data = crawler.scrape_job_detail(job['url'])
            job.update(detail_data)
    
    # フィルタリング済みデータを保存
    filtered_filename = base_filename.replace('.json', '_filtered.json')
    with open(filtered_filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_jobs, f, ensure_ascii=False, indent=2)
    print(f"フィルタリング済みデータを保存: {filtered_filename}")
    
    return base_filename, filtered_filename

class CrowdWorksCrawler:
    def __init__(self, email: str, password: str):
        """
        CrowdWorksクローラーの初期化
        
        Args:
            email (str): ログイン用メールアドレス
            password (str): ログインパスワード
        """
        self.base_url = "https://crowdworks.jp"
        self.search_url = f"{self.base_url}/public/jobs/search?order=new"
        self.login_url = f"{self.base_url}/login"
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.logger = logger  # loggerをインスタンス変数として設定
        self.setup_driver()

    def setup_driver(self):
        """Seleniumドライバーの設定"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # 新しいヘッドレスモードを使用
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # 通知を無効化
            "credentials_enable_service": False,  # パスワード保存のポップアップを無効化
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # JavaScript注入でWebDriverを検出されないようにする
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """
            })
            
            self.wait = WebDriverWait(self.driver, 20)  # 待機時間を20秒に延長
            logger.info("ChromeDriverの設定が完了しました")
        except Exception as e:
            logger.error(f"ChromeDriverの設定に失敗: {str(e)}")
            raise

    def wait_for_page_load(self):
        """ページの完全な読み込みを待機"""
        try:
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # sleepをtime.sleepに修正
        except Exception as e:
            logger.error(f"ページの読み込み待機に失敗: {str(e)}")

    def login(self) -> bool:
        """クラウドワークスにログイン"""
        try:
            logger.info("ログイン処理を開始")
            self.driver.get(self.login_url)
            logger.info(f"現在のURL: {self.driver.current_url}")
            
            # ページの完全な読み込みを待機
            self.wait_for_page_load()
            
            try:
                # メールアドレスとパスワードを入力
                logger.info("ログインフォームの要素を探索中...")
                
                # 新しいセレクタを使用
                form_elements = self.driver.execute_script("""
                    const result = {
                        email: document.querySelector('input[name="username"]'),
                        password: document.querySelector('input[name="password"]'),
                        submit: document.querySelector('button[type="submit"]')
                    };
                    return result;
                """)
                
                if not form_elements.get('email') or not form_elements.get('password'):
                    logger.error("ログインフォームの要素が見つかりません")
                    # ページソースを保存して調査
                    with open("error_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("エラー時のページソースを'error_page.html'に保存しました")
                    return False
                
                logger.info("ログインフォームの要素を発見")

                # JavaScriptを使用して入力
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, form_elements['email'], self.email)
                time.sleep(1)  # sleepをtime.sleepに修正
                
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, form_elements['password'], self.password)
                time.sleep(1)  # sleepをtime.sleepに修正

                if not form_elements.get('submit'):
                    logger.error("ログインボタンが見つかりません")
                    # フォーム自体を送信
                    self.driver.execute_script("""
                        document.querySelector('form').submit();
                    """)
                else:
                    logger.info("ログインボタンをクリック")
                    self.driver.execute_script("""
                        arguments[0].click();
                        arguments[0].dispatchEvent(new Event('click', { bubbles: true }));
                    """, form_elements['submit'])
                
                time.sleep(5)  # sleepをtime.sleepに修正

                # ログイン成功の確認（URLが変わったことを確認）
                logger.info(f"ログイン後のURL: {self.driver.current_url}")
                if "/login" not in self.driver.current_url:
                    logger.info("ログイン成功")
                    return True
                else:
                    logger.error("ログイン失敗: ログインページから移動できません")
                    return False
            except Exception as e:
                logger.error(f"ログインフォームの操作に失敗: {str(e)}")
                # ページソースを保存して調査
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info("エラー時のページソースを'error_page.html'に保存しました")
                return False
        except Exception as e:
            logger.error(f"ログイン処理でエラー発生: {str(e)}")
            return False

    def random_sleep(self, min_seconds=1, max_seconds=3):
        """ランダムな待機時間を設定"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)  # sleepをtime.sleepに修正

    def simulate_human_input(self, element, text):
        """人間らしい入力をシミュレート"""
        for char in text:
            element.send_keys(char)
            self.random_sleep(0.1, 0.3)

    def save_page_source(self, filename: str):
        """ページソースを保存"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            self.logger.info(f"ページソースを保存しました: {filename}")
        except Exception as e:
            self.logger.error(f"ページソースの保存に失敗: {str(e)}")

    def scrape_job_detail(self, url: str) -> Dict:
        """個別の仕事詳細ページから情報を取得"""
        try:
            self.logger.info(f"仕事詳細の取得を開始: {url}")
            self.driver.get(url)
            time.sleep(3)  # ページの読み込みを待つ
            
            # ページのHTMLを取得してBeautifulSoupで解析
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 仕事詳細テーブルを取得
            detail_table = soup.find('table', class_='job_offer_detail_table')
            if detail_table:
                # 改行を保持したまま取得
                # 1. 不要な空白行を削除
                # 2. 意味のある改行は保持
                lines = []
                for text in detail_table.stripped_strings:
                    lines.append(text)
                detail_text = '\n'.join(lines)
                
                return {
                    "detail_description": detail_text,
                    "crawled_detail_at": datetime.now().isoformat()
                }
            else:
                self.logger.warning(f"仕事詳細が見つかりませんでした: {url}")
                return {}
                
        except Exception as e:
            self.logger.error(f"仕事詳細の取得中にエラーが発生: {str(e)}")
            return {}

    def scrape_jobs(self):
        try:
            self.logger.info("案件情報の取得を開始")
            self.driver.get(self.search_url)
            time.sleep(5)  # ページの読み込みを待つ
            
            # ページのHTMLを取得してBeautifulSoupで解析
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 案件要素を取得
            job_elements = soup.find_all('div', class_='UNzN7')
            jobs_data = []
            
            for job_element in job_elements:
                try:
                    # タイトルとURL
                    title_element = job_element.find('h3', class_='iCeus').find('a')
                    title = title_element.text.strip()
                    url = f"https://crowdworks.jp{title_element['href']}"
                    
                    # 予算
                    budget_element = job_element.find('span', class_='Yh37y')
                    budget = budget_element.text.strip() if budget_element else "予算未設定"
                    
                    # クライアント名
                    client_element = job_element.find('a', class_='uxHdW')
                    client = client_element.text.strip() if client_element else "クライアント名非公開"
                    
                    # 投稿日
                    posted_date_element = job_element.find('time')
                    posted_date = posted_date_element['datetime'] if posted_date_element else None
                    
                    job_data = {
                        "title": title,
                        "url": url,
                        "budget": budget,
                        "client": client,
                        "posted_date": posted_date,
                        "crawled_at": datetime.now().isoformat()
                    }
                    
                    self.logger.info(f"求人情報を取得しました: {title}")
                    jobs_data.append(job_data)
                    
                except Exception as e:
                    self.logger.error(f"案件データの取得中にエラーが発生: {str(e)}")
                    continue
            
            self.logger.info(f"{len(jobs_data)}件の案件を取得")
            return jobs_data
            
        except Exception as e:
            self.logger.error(f"案件一覧の取得中にエラーが発生: {str(e)}")
            return []

    def save_jobs(self, jobs: List[Dict]):
        """取得した案件情報を保存"""
        if not jobs:
            logger.warning("保存する案件データがありません")
            return

        # 保存先ディレクトリの作成
        save_dir = Path("crawled_data")
        save_dir.mkdir(exist_ok=True)

        # 現在の日時をファイル名に使用
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSONとして保存
        json_path = save_dir / f"jobs_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        
        # CSVとして保存
        csv_path = save_dir / f"jobs_{timestamp}.csv"
        df = pd.DataFrame(jobs)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        logger.info(f"データを保存しました: {json_path}, {csv_path}")

    def load_previous_jobs(self) -> Dict[str, Dict]:
        """前回のクロール結果を読み込む"""
        save_dir = Path("crawled_data")
        if not save_dir.exists():
            return {}
        
        # 最新のJSONファイルを探す
        json_files = list(save_dir.glob("jobs_*.json"))
        if not json_files:
            return {}
        
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                jobs = json.load(f)
                # URL をキーとした辞書に変換
                return {job["url"]: job for job in jobs}
        except Exception as e:
            self.logger.error(f"前回のデータ読み込みに失敗: {str(e)}")
            return {}

    def check_duplicates(self, new_jobs: List[Dict]) -> List[Dict]:
        """重複チェックを行い、新規または更新が必要な案件のみを返す"""
        previous_jobs = self.load_previous_jobs()
        updated_jobs = []
        
        for new_job in new_jobs:
            url = new_job["url"]
            if url not in previous_jobs:
                # 新規案件
                self.logger.info(f"新規案件を追加: {new_job['title']}")
                updated_jobs.append(new_job)
            else:
                # 既存案件の場合、投稿日時を比較
                prev_date = datetime.fromisoformat(previous_jobs[url]["posted_date"])
                new_date = datetime.fromisoformat(new_job["posted_date"])
                
                if new_date > prev_date:
                    # 更新があった場合
                    self.logger.info(f"案件を更新: {new_job['title']}")
                    updated_jobs.append(new_job)
        
        self.logger.info(f"新規/更新案件: {len(updated_jobs)}件")
        return updated_jobs

    def run(self):
        """クローラーのメイン処理"""
        try:
            if self.login():
                jobs = self.scrape_jobs()
                if jobs:
                    # 重複チェックを実行
                    unique_jobs = self.check_duplicates(jobs)
                    if unique_jobs:
                        # GPTフィルタリングを含むデータ処理を実行（crawlerインスタンスを渡す）
                        base_filename, filtered_filename = process_crawled_data(unique_jobs, self)
                        self.logger.info(f"生データを保存: {base_filename}")
                        self.logger.info(f"フィルタリング済みデータを保存: {filtered_filename}")
                    else:
                        self.logger.info("新規または更新された案件はありません")
            else:
                self.logger.error("ログインに失敗したため、処理を中止します")
        finally:
            self.driver.quit()
            self.logger.info("クローラーを終了します")

if __name__ == "__main__":
    # 設定を読み込み
    settings = load_settings()
    email = settings.get('crowdworks_email')
    password = settings.get('crowdworks_password')
    
    if not email or not password:
        logger.error("CrowdWorksのメールアドレスまたはパスワードが設定されていません")
        sys.exit(1)
    
    # クローラーを実行
    crawler = CrowdWorksCrawler(email, password)
    crawler.run()
