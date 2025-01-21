import json
import os
from datetime import datetime
from typing import Dict, List
import time
from queue import Queue
from threading import Thread

from flask import Flask, Response, jsonify, request, stream_with_context
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from openai import OpenAI

# グローバル変数で進捗状況を管理
progress_queue = Queue()
current_progress = {
    "current": 0,
    "total": 0,
    "status": "待機中",
    "completed": False
}

def load_settings():
    """設定ファイルを読み込む"""
    try:
        with open('crawled_data/settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
        return {}

def setup_driver():
    """Seleniumドライバーの設定"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument("--suppress-message-center-popups")  # ポップアップを抑制
    chrome_options.add_argument("--disable-notifications")  # 通知を無効化
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("detach", True)  # スクリプト終了後もブラウザを開いたままにする
    
    try:
        driver_path = "./chromedriver"
        if not os.path.exists(driver_path):
            raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")
        
        os.chmod(driver_path, 0o755)
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # JavaScript注入
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
            """
        })
        
        return driver
    except Exception as e:
        logger.error(f"ChromeDriverの設定に失敗: {str(e)}")
        raise

def login_to_crowdworks(driver, email: str, password: str) -> bool:
    """クラウドワークスにログイン"""
    try:
        logger.info("ログイン処理を開始")
        driver.get("https://crowdworks.jp/login")
        wait = WebDriverWait(driver, 20)
        
        # メールアドレスとパスワードを入力
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']")))
        
        email_input.send_keys(email)
        time.sleep(1)
        password_input.send_keys(password)
        time.sleep(1)
        submit_button.click()
        
        time.sleep(5)
        
        # ログイン成功の確認
        return "/login" not in driver.current_url
        
    except Exception as e:
        logger.error(f"ログイン処理でエラー発生: {str(e)}")
        return False

def generate_application_content(job_detail: str, self_intro: str) -> Dict[str, str]:
    """LLMを使用して応募内容を生成"""
    try:
        settings = load_settings()
        
        # モデルに応じてクライアントを選択
        if settings.get('model') == 'deepseek-chat':
            client = OpenAI(
                api_key=settings.get('deepseek_api_key', ''),
                base_url="https://api.deepseek.com"
            )
        else:
            client = OpenAI(api_key=settings.get('api_key'))
        
        prompt = f"""
以下の案件に対する応募メッセージと契約金額を生成してください。
応募者の自己紹介も参考にしてください。

【案件詳細】
{job_detail}

【応募者の自己紹介】
{self_intro}

以下のJSON形式で出力してください：
{{
    "contract_amount": "契約金額（数値のみ）",
    "application_message": "応募メッセージ"
}}
"""
        
        response = client.chat.completions.create(
            model=settings.get('model', 'gpt-4'),
            messages=[
                {"role": "system", "content": "あなたはフリーランスエンジニアの応募メッセージを作成する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"応募内容の生成に失敗: {str(e)}")
        return {
            "contract_amount": "要相談",
            "application_message": "申し訳ありませんが、応募内容の生成に失敗しました。"
        }

def apply_to_job(driver, url: str, self_intro: str):
    """個別の案件に応募"""
    try:
        logger.info(f"案件への応募を開始: {url}")
        # 新しいタブで開いて、そのタブに切り替える
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        wait = WebDriverWait(driver, 20)
        
        # 案件詳細を取得（複数の要素を試行）
        detail_selectors = [
            "job_offer_detail_table",  # クラス名
            "detail_description",      # 可能性のある別のクラス名
            "//table[contains(@class, 'detail')]",  # XPath
            "//div[contains(@class, 'detail')]"     # 別のXPath
        ]
        
        job_detail = ""
        for selector in detail_selectors:
            try:
                if selector.startswith("//"):
                    element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                else:
                    element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, selector)))
                job_detail = element.text
                break
            except:
                continue
        
        if not job_detail:
            logger.warning("案件詳細の取得に失敗しましたが、処理を継続します")
            job_detail = "案件詳細の取得に失敗しました"
        
        # 「作業を開始する」ボタンの確認
        try:
            start_work_button = driver.find_element(
                By.XPATH, '//*[@id="job_offer_detail"]/div/div[1]/div[1]/div/div/form/input[4]'
            )
            logger.info("この案件は「作業を開始する」タイプです")
            return {
                "status": "work_start",
                "message": "この案件は「作業を開始する」タイプのため、応募処理をスキップしました"
            }
        except NoSuchElementException:
            pass
        
        # 応募ボタンをクリック
        try:
            apply_button = wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@id="job_offer_detail"]/div/div[1]/div[2]/div/p/a'
            )))
            apply_button.click()
            time.sleep(3)
        except TimeoutException:
            return {
                "status": "error",
                "message": "応募ボタンが見つかりませんでした"
            }
        
        # 応募内容を生成
        content = generate_application_content(job_detail, self_intro)
        
        # 契約金額を入力
        try:
            amount_input = wait.until(EC.presence_of_element_located((
                By.XPATH, '//*[@id="amount_dummy_"]'
            )))
            amount_input.clear()
            amount_input.send_keys(content["contract_amount"])
        except TimeoutException:
            return {
                "status": "error",
                "message": "契約金額の入力フィールドが見つかりませんでした"
            }
        
        # 応募メッセージを入力
        try:
            message_input = wait.until(EC.presence_of_element_located((
                By.XPATH, '//*[@id="proposal_conditions_attributes_0_message_attributes_body"]'
            )))
            message_input.clear()
            message_input.send_keys(content["application_message"])
        except TimeoutException:
            return {
                "status": "error",
                "message": "応募メッセージの入力フィールドが見つかりませんでした"
            }
        
        return {
            "status": "success",
            "message": "応募情報の入力が完了しました"
        }
        
    except Exception as e:
        logger.error(f"案件応募中にエラーが発生: {str(e)}")
        return {
            "status": "error",
            "message": f"予期せぬエラーが発生しました: {str(e)}"
        }

def bulk_apply_process(urls: List[str]):
    """一括応募のメイン処理"""
    try:
        settings = load_settings()
        email = settings.get('crowdworks_email')
        password = settings.get('crowdworks_password')
        
        if not email or not password:
            raise ValueError("認証情報が設定されていません")
        
        # 自己紹介文を読み込み
        try:
            with open('SelfIntroduction.txt', 'r', encoding='utf-8') as f:
                self_intro = f.read()
        except FileNotFoundError:
            raise ValueError("SelfIntroduction.txtが見つかりません")
        
        driver = setup_driver()
        
        try:
            # ログイン
            if not login_to_crowdworks(driver, email, password):
                raise Exception("ログインに失敗しました")
            
            total = len(urls)
            current_progress.update({
                "total": total,
                "current": 0,
                "status": "応募処理を開始します",
                "completed": False
            })
            progress_queue.put(current_progress.copy())
            
            # 結果を集計するための変数
            results = {
                "success": 0,
                "work_start": 0,
                "error": 0,
                "messages": []
            }
            
            # 各案件に応募
            for i, url in enumerate(urls, 1):
                current_progress.update({
                    "current": i,
                    "status": f"案件 {i}/{total} を処理中...",
                })
                progress_queue.put(current_progress.copy())
                
                result = apply_to_job(driver, url, self_intro)
                results[result["status"]] += 1
                results["messages"].append(f"案件 {i}: {result['message']}")
                
                # 進捗状況を更新
                current_progress.update({
                    "status": f"案件 {i}/{total}: {result['message']}"
                })
                progress_queue.put(current_progress.copy())
                
                time.sleep(2)
            
            # 最終結果を生成
            summary = (
                f"処理完了: 全{total}件\n"
                f"- 応募完了: {results['success']}件\n"
                f"- 作業開始タイプ: {results['work_start']}件\n"
                f"- エラー: {results['error']}件"
            )
            
            current_progress.update({
                "current": total,
                "status": summary,
                "completed": True,
                "details": results["messages"]
            })
            progress_queue.put(current_progress.copy())
            
        except Exception as e:
            logger.error(f"一括応募処理でエラーが発生: {str(e)}")
            current_progress.update({
                "status": f"エラーが発生しました: {str(e)}",
                "completed": True
            })
            progress_queue.put(current_progress.copy())
            raise
            
    except Exception as e:
        logger.error(f"一括応募処理でエラーが発生: {str(e)}")
        current_progress.update({
            "status": f"エラーが発生しました: {str(e)}",
            "completed": True
        })
        progress_queue.put(current_progress.copy())

def create_self_introduction():
    """自己紹介文が存在しない場合に作成"""
    if not os.path.exists('SelfIntroduction.txt'):
        default_intro = """私は5年以上のWeb開発経験を持つフリーランスエンジニアです。
フロントエンド（React, Vue.js）からバックエンド（Node.js, Python）まで、
幅広い技術スタックを活用した開発が可能です。

これまでの経験：
- ECサイトのフルスタック開発
- 業務効率化ツールの設計・実装
- チーム開発でのプロジェクトリード

迅速な対応と質の高い成果物の提供を心がけています。
ご要望に応じて柔軟に対応させていただきますので、
ぜひご検討いただけますと幸いです。"""
        
        with open('SelfIntroduction.txt', 'w', encoding='utf-8') as f:
            f.write(default_intro)
        logger.info("デフォルトの自己紹介文を作成しました")

def init_bulk_apply():
    """一括応募機能の初期化"""
    create_self_introduction()
    
# Flaskルート関数（app.pyに統合予定）
def register_bulk_apply_routes(app: Flask):
    @app.route('/bulk_apply', methods=['POST'])
    def bulk_apply():
        try:
            data = request.get_json()
            urls = data.get('urls', [])
            
            if not urls:
                return jsonify({
                    'status': 'error',
                    'message': '応募する案件が選択されていません'
                }), 400
            
            # 別スレッドで処理を開始
            Thread(target=bulk_apply_process, args=(urls,), daemon=True).start()
            
            return jsonify({
                'status': 'success',
                'message': '一括応募を開始しました'
            })
            
        except Exception as e:
            logger.error(f"一括応募の開始に失敗: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/bulk_apply_progress')
    def bulk_apply_progress():
        def generate():
            while True:
                progress = progress_queue.get()
                yield f"data: {json.dumps(progress)}\n\n"
                if progress["completed"]:
                    break
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )