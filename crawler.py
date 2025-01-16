import os
import json
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, List
import random
import sys

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ログの設定
logger.add("logs/crawler_{time}.log", rotation="500 MB")

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
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.logger = logger  # loggerをインスタンス変数として設定
        self.setup_driver()

    def setup_driver(self):
        """Seleniumドライバーの設定"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # ヘッドレスモードは一時的に無効化
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
            sleep(2)  # 追加の待機時間
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
                sleep(1)
                
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, form_elements['password'], self.password)
                sleep(1)

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
                
                sleep(5)  # ログイン処理待機時間を延長

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
        sleep(sleep_time)

    def simulate_human_input(self, element, text):
        """人間らしい入力をシミュレート"""
        for char in text:
            element.send_keys(char)
            self.random_sleep(0.1, 0.3)

    def scrape_jobs(self) -> List[Dict]:
        """案件情報を取得する"""
        self.logger.info("案件情報の取得を開始")
        
        # 検索ページに移動
        self.driver.get(self.search_url)
        time.sleep(random.uniform(2, 4))
        
        # ページが完全に読み込まれるまで待機
        self.wait_for_page_load()
        
        # 案件一覧を取得
        jobs = []
        try:
            # 案件要素を待機
            job_elements = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.item_body"))
            )
            
            for job in job_elements:
                try:
                    # タイトルと URL を取得
                    title_element = job.find_element(By.CSS_SELECTOR, "h3.item_title a")
                    title = title_element.text.strip()
                    url = title_element.get_attribute("href")
                    
                    # 予算を取得
                    try:
                        budget = job.find_element(By.CSS_SELECTOR, "b.amount").text.strip()
                    except NoSuchElementException:
                        budget = ""
                    
                    # クライアント名を取得
                    try:
                        client = job.find_element(By.CSS_SELECTOR, "div.client_name").text.strip()
                    except NoSuchElementException:
                        client = ""
                    
                    # 投稿日を取得
                    try:
                        posted_date = job.find_element(By.CSS_SELECTOR, "span.post_date").text.strip()
                    except NoSuchElementException:
                        posted_date = ""
                    
                    # 本文を取得
                    try:
                        description = job.find_element(By.CSS_SELECTOR, "p.item_description").text.strip()
                        # 「...続きを見る」を削除
                        description = description.replace("...続きを見る", "")
                    except NoSuchElementException:
                        description = ""
                    
                    self.logger.info(f"案件を取得: {title}")
                    self.logger.debug(f"本文: {description[:100]}...")
                    
                    jobs.append({
                        "title": title,
                        "url": url,
                        "budget": budget,
                        "client": client,
                        "description": description,
                        "posted_date": posted_date,
                        "crawled_at": datetime.datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"案件情報の取得中にエラーが発生: {str(e)}")
                    continue
            
            self.logger.info(f"{len(jobs)}件の案件を取得")
            return jobs
            
        except Exception as e:
            self.logger.error(f"案件一覧の取得中にエラーが発生: {str(e)}")
            # ページソースを保存
            self.save_page_source("error_jobs_list.html")
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

    def run(self):
        """クローラーのメイン処理"""
        try:
            if self.login():
                jobs = self.scrape_jobs()
                self.save_jobs(jobs)
            else:
                logger.error("ログインに失敗したため、処理を中止します")
        finally:
            self.driver.quit()
            logger.info("クローラーを終了します")

if __name__ == "__main__":
    # 環境変数を読み込み
    load_dotenv()
    email = os.getenv("CROWDWORKS_EMAIL")
    password = os.getenv("CROWDWORKS_PASSWORD")
    
    if not email or not password:
        logger.error("環境変数 CROWDWORKS_EMAIL または CROWDWORKS_PASSWORD が設定されていません")
        sys.exit(1)
    
    # クローラーを実行
    crawler = CrowdWorksCrawler(email, password)
    crawler.run()
