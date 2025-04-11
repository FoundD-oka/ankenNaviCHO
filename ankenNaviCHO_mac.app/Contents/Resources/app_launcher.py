import os
import sys
import time
import logging
import subprocess
import signal
import socket
import webbrowser
import threading
import re
from pathlib import Path
from dotenv import load_dotenv

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'launcher.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('app_launcher')

# ディレクトリの作成
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)

# グローバル変数
flask_process = None
chrome_process = None

def signal_handler(sig, frame):
    logger.info("終了シグナルを受信しました。アプリケーションを終了します。")
    cleanup()
    sys.exit(0)

def cleanup():
    global flask_process, chrome_process
    
    # Flaskプロセスの終了
    if flask_process:
        logger.info("Flaskサーバーを終了します。")
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=5)
        except:
            try:
                os.killpg(os.getpgid(flask_process.pid), signal.SIGKILL)
            except:
                pass
    
    # Chromeプロセスの終了
    if chrome_process:
        logger.info("Chromeブラウザを終了します。")
        try:
            chrome_process.terminate()
            chrome_process.wait(timeout=5)
        except:
            try:
                chrome_process.kill()
            except:
                pass

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def wait_for_port(port, timeout=60):
    """指定されたポートが利用可能になるまで待機"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.5)
    return False

def get_chrome_version():
    """現在のChromeバージョンを取得"""
    try:
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if not os.path.exists(chrome_path):
            chrome_path = os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        
        if os.path.exists(chrome_path):
            version = subprocess.check_output([chrome_path, "--version"], stderr=subprocess.STDOUT)
            match = re.search(r"Google Chrome ([\d.]+)", version.decode("utf-8"))
            if match:
                return match.group(1)
    except Exception as e:
        logger.error(f"Chromeバージョン取得エラー: {e}")
    return None

def load_env_file():
    """環境変数をロードしてPORTを取得"""
    # 実行環境パスを取得
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"アプリケーションを初期化しています。バンドルディレクトリ: {bundle_dir}")
    
    # カレントディレクトリを変更
    logger.info(f"環境を初期化しています。カレントディレクトリを変更: {bundle_dir}")
    os.chdir(bundle_dir)
    
    # .envファイルをロード
    env_path = os.path.join(bundle_dir, ".env")
    port = 8080  # デフォルトポート
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
        if "PORT" in os.environ:
            try:
                port = int(os.environ["PORT"])
                logger.info(f".envファイルから読み込んだポート: {port}")
            except ValueError:
                logger.warning(f"PORT環境変数の値が無効です: {os.environ['PORT']}、デフォルト値を使用します: {port}")
        logger.info(f".envファイルを読み込みました。ポート: {port}")
    else:
        logger.warning(".envファイルが見つかりません。デフォルト設定を使用します。")
    
    return port

def setup_chromedriver():
    """ChromeDriverのセットアップと環境変数設定"""
    # ChromeDriverのキャッシュ情報を確認
    cache_info_path = os.path.join(os.getcwd(), ".chromedriver_cache_info")
    driver_path = None
    
    # 現在のChromeバージョンを取得
    chrome_version = get_chrome_version()
    logger.info(f"検出されたChromeバージョン: {chrome_version}")
    
    if os.path.exists(cache_info_path):
        try:
            cache_info = {}
            with open(cache_info_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        cache_info[key] = value
            
            # Chromeバージョンチェック - 変更があれば再取得
            if chrome_version and "CHROME_VERSION" in cache_info:
                if chrome_version != cache_info["CHROME_VERSION"]:
                    logger.info(f"Chromeバージョンが変更されました（{cache_info['CHROME_VERSION']} → {chrome_version}）。ChromeDriverを再取得します。")
                    # キャッシュを使わずに再取得
                    from chromedriver_manager import setup_driver
                    driver_path = setup_driver()
                    # 更新したキャッシュ情報を保存
                    with open(cache_info_path, "w") as f:
                        f.write(f"PATH={driver_path}\n")
                        f.write(f"TIMESTAMP={int(time.time())}\n")
                        f.write(f"CHROME_VERSION={chrome_version}\n")
                    logger.info(f"ChromeDriverを更新しました: {driver_path}")
                    os.environ["SELENIUM_DRIVER_PATH"] = driver_path
                    return True
            
            # Chromeバージョンが同じか未設定の場合はキャッシュを使用
            if "PATH" in cache_info and os.path.exists(os.path.join(os.getcwd(), cache_info["PATH"])):
                driver_path = os.path.join(os.getcwd(), cache_info["PATH"])
                logger.info(f"キャッシュされたChromeDriverを使用します: {driver_path}")
                os.environ["SELENIUM_DRIVER_PATH"] = driver_path
                logger.info(f"SELENIUM_DRIVER_PATHを更新しました: {driver_path}")
                return True
        except Exception as e:
            logger.warning(f"キャッシュ情報の読み込み中にエラーが発生しました: {e}")
    
    # キャッシュがない場合やエラーの場合は通常のセットアップを実行
    try:
        from chromedriver_manager import setup_driver
        driver_path = setup_driver()
        
        if not driver_path:
            raise Exception("ChromeDriverのセットアップが失敗しました")
            
        logger.info(f"SELENIUM_DRIVER_PATHを更新しました: {driver_path}")
        os.environ["SELENIUM_DRIVER_PATH"] = driver_path
        
        # 新しくセットアップした情報をキャッシュに保存
        try:
            with open(cache_info_path, "w") as f:
                f.write(f"PATH={driver_path}\n")
                f.write(f"TIMESTAMP={int(time.time())}\n")
                if chrome_version:
                    f.write(f"CHROME_VERSION={chrome_version}\n")
            logger.info(f"ChromeDriverキャッシュ情報を更新しました")
        except Exception as e:
            logger.warning(f"キャッシュ情報の保存中にエラーが発生しました: {e}")
        
        logger.info("ChromeDriverのセットアップが完了しました")
        return True
    except Exception as e:
        logger.error(f"ChromeDriverのセットアップ中にエラーが発生しました: {e}")
        return False

def run_app():
    """アプリケーションを実行"""
    global flask_process
    
    # 環境を初期化
    port = load_env_file()
    
    # ChromeDriverをセットアップ
    if not setup_chromedriver():
        logger.error("ChromeDriverのセットアップに失敗しました。アプリケーションを終了します。")
        return
    
    logger.info("環境の初期化が完了しました")
    
    # 環境変数からポートを直接取得（.envが読み込まれた後）
    port = int(os.environ.get("PORT", port))
    logger.info(f"環境変数から直接ポートを取得しました: {port}")
    
    # アプリケーションパス
    app_path = os.path.join(os.getcwd(), "app.py")
    logger.info(f"アプリケーションパス: {app_path}")
    
    # 実行する Python インタプリタパスを取得
    venv_dir = os.path.expanduser("~/Library/Application Support/ankenNaviCHO/venv")
    python_path = os.path.join(venv_dir, "bin", "python3")
    
    # アプリケーションを起動
    command = [python_path, app_path]
    logger.info(f"アプリケーションを起動します: {' '.join(command)}")
    
    # サブプロセスとして起動
    flask_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid
    )
    
    # 標準出力と標準エラー出力を読み取るスレッド
    def read_output(stream, prefix):
        for line in stream:
            logger.info(f"[{prefix}] {line.rstrip()}")
    
    threading.Thread(target=read_output, args=(flask_process.stdout, "stdout"), daemon=True).start()
    threading.Thread(target=read_output, args=(flask_process.stderr, "stderr"), daemon=True).start()
    
    # サーバーの起動を待機
    logger.info(f"サーバーの起動を待機しています（ポート: {port}）...")
    if wait_for_port(port, timeout=15):
        logger.info(f"サーバーが起動しました（ポート: {port}）")
        # ブラウザでアプリケーションを開く
        url = f"http://localhost:{port}"
        logger.info(f"ブラウザでアプリケーションを開きます: {url}")
        webbrowser.open(url)
    else:
        logger.error(f"サーバーの起動タイムアウト（ポート: {port}）")

if __name__ == "__main__":
    # シグナルハンドラを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 開発環境かどうかを確認
        if os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) == "Resources":
            logger.info(f"開発環境として実行中: {os.path.abspath(os.path.dirname(__file__))}")
        
        # アプリケーションを実行
        run_app()
        
        # メインスレッドを維持（Ctrl+Cを受け取れるように）
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("キーボード割り込みを受信しました。アプリケーションを終了します。")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
    finally:
        cleanup()
