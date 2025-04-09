import os
import sys
import platform
import subprocess
import re
import requests
import zipfile
import shutil
import logging
import time
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict
import json
from datetime import datetime, timedelta

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/chromedriver.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ChromeDriverの保存ディレクトリ
DRIVER_DIR = Path('./drivers')
# 設定ファイルのパス
CONFIG_FILE = Path('./drivers/config.json')
# 更新チェック間隔（秒）
UPDATE_CHECK_INTERVAL = 86400  # 24時間

class ChromeDriverManager:
    """ChromeDriverの自動管理クラス"""
    
    def __init__(self):
        """初期化"""
        self._ensure_driver_dir()
        self.config = self._load_config()
        self.update_thread = None
        self.stop_update_thread = False
    
    def _ensure_driver_dir(self):
        """ドライバーディレクトリの存在確認と作成"""
        if not DRIVER_DIR.exists():
            DRIVER_DIR.mkdir(parents=True)
            logger.info(f"ドライバーディレクトリを作成しました: {DRIVER_DIR}")
    
    def _load_config(self) -> Dict:
        """設定ファイルの読み込み"""
        if not CONFIG_FILE.exists():
            default_config = {
                "chrome_version": "",
                "driver_version": "",
                "driver_path": "",
                "last_check": "",
                "last_update": ""
            }
            self._save_config(default_config)
            return default_config
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
            return {
                "chrome_version": "",
                "driver_version": "",
                "driver_path": "",
                "last_check": "",
                "last_update": ""
            }
    
    def _save_config(self, config: Dict):
        """設定ファイルの保存"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定ファイルの保存に失敗: {str(e)}")
    
    def get_chrome_version(self) -> Optional[str]:
        """Chromeのバージョンを取得"""
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                # M1/M2 Macの場合
                if platform.machine() in ["arm64", "aarch64"]:
                    cmd = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"]
                else:  # Intel Mac
                    cmd = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"]
            elif system == "Windows":
                # Windowsの場合
                cmd = ["reg", "query", "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon", "/v", "version"]
            elif system == "Linux":
                # Linuxの場合
                cmd = ["google-chrome", "--version"]
            else:
                logger.error(f"未対応のOS: {system}")
                return None
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if system == "Windows":
                # Windowsの場合、レジストリから値を抽出
                match = re.search(r"version\s+REG_SZ\s+([\d\.]+)", result.stdout)
                if match:
                    version = match.group(1)
                else:
                    logger.error("Windowsでのバージョン抽出に失敗")
                    return None
            else:
                # macOSとLinuxの場合
                match = re.search(r"Chrome\s+([\d\.]+)", result.stdout)
                if match:
                    version = match.group(1)
                else:
                    logger.error("バージョン抽出に失敗")
                    return None
            
            logger.info(f"検出されたChromeバージョン: {version}")
            return version
        except Exception as e:
            logger.error(f"Chromeバージョンの取得に失敗: {str(e)}")
            return None
    
    def get_compatible_driver_version(self, chrome_version: str) -> Optional[str]:
        """Chromeバージョンに対応するChromeDriverバージョンを取得"""
        try:
            # メジャーバージョンを抽出（例: 120.0.6099.109 -> 120）
            major_version = chrome_version.split('.')[0]
            
            # Chrome 134以降は新しいURLフォーマットを使用
            if int(major_version) >= 134:
                # Chrome for Testingの最新バージョンを使用
                # 完全なバージョン番号を使用
                driver_version = chrome_version
                logger.info(f"Chrome 134以降のため、Chrome for Testingを使用: {driver_version}")
                return driver_version
            
            # 従来のChromeDriverのバージョン情報を取得
            url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            response = requests.get(url)
            
            if response.status_code == 200:
                driver_version = response.text.strip()
                logger.info(f"対応するChromeDriverバージョン: {driver_version}")
                return driver_version
            else:
                logger.error(f"ChromeDriverバージョンの取得に失敗: ステータスコード {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"対応するChromeDriverバージョンの取得に失敗: {str(e)}")
            return None
    
    def download_driver(self, driver_version: str) -> Optional[str]:
        """指定されたバージョンのChromeDriverをダウンロード"""
        try:
            system = platform.system()
            chrome_version = self.config.get("chrome_version", "")
            major_version = chrome_version.split('.')[0] if chrome_version else "0"
            
            # プラットフォーム名の決定
            if system == "Darwin":  # macOS
                if platform.machine() in ["arm64", "aarch64"]:
                    platform_name = "mac_arm64" if int(major_version) < 134 else "mac-arm64"
                else:
                    platform_name = "mac64" if int(major_version) < 134 else "mac-x64"
            elif system == "Windows":
                platform_name = "win32" if int(major_version) < 134 else "win32"
            elif system == "Linux":
                platform_name = "linux64" if int(major_version) < 134 else "linux64"
            else:
                logger.error(f"未対応のOS: {system}")
                return None
            
            # ダウンロードURL
            if int(major_version) >= 134:
                # Chrome for Testing用のURL
                download_url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{driver_version}/{platform_name}/chromedriver-{platform_name}.zip"
            else:
                # 従来のChromeDriver用のURL
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform_name}.zip"
            
            # 一時ファイルパス
            zip_path = DRIVER_DIR / f"chromedriver_{driver_version}.zip"
            
            # ダウンロード
            logger.info(f"ChromeDriverをダウンロード中: {download_url}")
            response = requests.get(download_url, stream=True)
            
            if response.status_code != 200:
                logger.error(f"ダウンロードに失敗: ステータスコード {response.status_code}")
                return None
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 解凍先ディレクトリ
            extract_dir = DRIVER_DIR / f"chromedriver_{driver_version}"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir()
            
            # ZIPファイルを解凍
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # ZIPファイルを削除
            zip_path.unlink()
            
            # ChromeDriverのパスを取得
            if int(major_version) >= 134:
                # Chrome for Testingの場合、ディレクトリ構造が異なる
                if system == "Windows":
                    driver_path = next(extract_dir.glob("**/chromedriver.exe"))
                else:
                    driver_path = next(extract_dir.glob("**/chromedriver"))
            else:
                # 従来のChromeDriverの場合
                if system == "Windows":
                    driver_path = extract_dir / "chromedriver.exe"
                else:
                    driver_path = extract_dir / "chromedriver"
            
            # 実行権限を付与
            if system != "Windows":
                os.chmod(driver_path, 0o755)
            
            logger.info(f"ChromeDriverのダウンロードと解凍が完了: {driver_path}")
            return str(driver_path)
        except Exception as e:
            logger.error(f"ChromeDriverのダウンロードに失敗: {str(e)}")
            return None
    
    def setup_driver(self) -> Optional[str]:
        """ChromeDriverのセットアップ"""
        try:
            # Chromeバージョンを取得
            chrome_version = self.get_chrome_version()
            if not chrome_version:
                return self._handle_error("Chromeバージョンの取得に失敗しました")
            
            # 設定を更新
            self.config["chrome_version"] = chrome_version
            self.config["last_check"] = datetime.now().isoformat()
            
            # 既存のドライバーが存在し、バージョンが一致する場合は再利用
            if (self.config["driver_version"] and 
                self.config["driver_path"] and 
                Path(self.config["driver_path"]).exists() and
                chrome_version.split('.')[0] == self.config["chrome_version"].split('.')[0]):
                
                logger.info(f"既存のChromeDriverを使用: {self.config['driver_path']}")
                return self.config["driver_path"]
            
            # 対応するドライバーバージョンを取得
            driver_version = self.get_compatible_driver_version(chrome_version)
            if not driver_version:
                return self._handle_error("対応するChromeDriverバージョンの取得に失敗しました")
            
            # ドライバーをダウンロード
            driver_path = self.download_driver(driver_version)
            if not driver_path:
                return self._handle_error("ChromeDriverのダウンロードに失敗しました")
            
            # 設定を更新
            self.config["driver_version"] = driver_version
            self.config["driver_path"] = driver_path
            self.config["last_update"] = datetime.now().isoformat()
            self._save_config(self.config)
            
            # シンボリックリンクまたはコピーを作成（プロジェクトルートの./chromedriverへ）
            root_driver_path = Path('./chromedriver')
            if root_driver_path.exists():
                if root_driver_path.is_symlink() or root_driver_path.is_file():
                    root_driver_path.unlink()
            
            try:
                # シンボリックリンクを作成
                os.symlink(driver_path, root_driver_path)
                logger.info(f"シンボリックリンクを作成: {root_driver_path} -> {driver_path}")
            except Exception as e:
                # シンボリックリンクの作成に失敗した場合はコピー
                logger.warning(f"シンボリックリンクの作成に失敗: {str(e)}")
                shutil.copy2(driver_path, root_driver_path)
                os.chmod(root_driver_path, 0o755)
                logger.info(f"ファイルをコピー: {driver_path} -> {root_driver_path}")
            
            return driver_path
        except Exception as e:
            return self._handle_error(f"ChromeDriverのセットアップに失敗: {str(e)}")
    
    def _handle_error(self, message: str) -> Optional[str]:
        """エラーハンドリング"""
        logger.error(message)
        
        # 既存のドライバーパスがあれば、それを返す
        if self.config["driver_path"] and Path(self.config["driver_path"]).exists():
            logger.info(f"既存のChromeDriverを使用: {self.config['driver_path']}")
            return self.config["driver_path"]
        
        # プロジェクトルートのchromedriver
        root_driver = Path('./chromedriver')
        if root_driver.exists():
            logger.info(f"プロジェクトルートのChromeDriverを使用: {root_driver}")
            return str(root_driver)
        
        return None
    
    def start_background_update(self):
        """バックグラウンド更新スレッドを開始"""
        if self.update_thread and self.update_thread.is_alive():
            logger.info("バックグラウンド更新スレッドは既に実行中です")
            return
        
        self.stop_update_thread = False
        self.update_thread = threading.Thread(target=self._background_update_task, daemon=True)
        self.update_thread.start()
        logger.info("バックグラウンド更新スレッドを開始しました")
    
    def stop_background_update(self):
        """バックグラウンド更新スレッドを停止"""
        if self.update_thread and self.update_thread.is_alive():
            self.stop_update_thread = True
            self.update_thread.join(timeout=1.0)
            logger.info("バックグラウンド更新スレッドを停止しました")
    
    def _background_update_task(self):
        """バックグラウンド更新タスク"""
        logger.info("バックグラウンド更新タスクを開始")
        
        while not self.stop_update_thread:
            try:
                # 最終チェック時刻を確認
                last_check = self.config.get("last_check", "")
                if last_check:
                    last_check_time = datetime.fromisoformat(last_check)
                    now = datetime.now()
                    
                    # 前回のチェックから24時間経過していない場合はスキップ
                    if now - last_check_time < timedelta(seconds=UPDATE_CHECK_INTERVAL):
                        time_to_next = (last_check_time + timedelta(seconds=UPDATE_CHECK_INTERVAL) - now).total_seconds()
                        logger.info(f"次回の更新チェックまで {time_to_next:.1f} 秒")
                        
                        # 1時間ごとにチェック
                        for _ in range(int(min(time_to_next, 3600) / 10)):
                            if self.stop_update_thread:
                                break
                            time.sleep(10)
                        continue
                
                # Chromeバージョンを取得
                chrome_version = self.get_chrome_version()
                if not chrome_version:
                    logger.error("バックグラウンド更新: Chromeバージョンの取得に失敗")
                    time.sleep(3600)  # 1時間後に再試行
                    continue
                
                # 現在のバージョンと比較
                if chrome_version == self.config.get("chrome_version", ""):
                    logger.info(f"バックグラウンド更新: Chromeバージョンに変更なし ({chrome_version})")
                    
                    # 最終チェック時刻を更新
                    self.config["last_check"] = datetime.now().isoformat()
                    self._save_config(self.config)
                    
                    # 次回のチェックまで待機
                    for _ in range(int(UPDATE_CHECK_INTERVAL / 10)):
                        if self.stop_update_thread:
                            break
                        time.sleep(10)
                    continue
                
                # バージョンが変更された場合、ドライバーを更新
                logger.info(f"バックグラウンド更新: Chromeバージョンが変更されました ({self.config.get('chrome_version', '')} -> {chrome_version})")
                driver_path = self.setup_driver()
                
                if driver_path:
                    logger.info(f"バックグラウンド更新: ChromeDriverを更新しました ({driver_path})")
                else:
                    logger.error("バックグラウンド更新: ChromeDriverの更新に失敗")
                
                # 次回のチェックまで待機
                for _ in range(int(UPDATE_CHECK_INTERVAL / 10)):
                    if self.stop_update_thread:
                        break
                    time.sleep(10)
            
            except Exception as e:
                logger.error(f"バックグラウンド更新タスクでエラーが発生: {str(e)}")
                time.sleep(3600)  # エラー発生時は1時間後に再試行

# シングルトンインスタンス
_instance = None

def get_instance() -> ChromeDriverManager:
    """ChromeDriverManagerのシングルトンインスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = ChromeDriverManager()
    return _instance

def setup_driver() -> Optional[str]:
    """ChromeDriverをセットアップし、パスを返す"""
    return get_instance().setup_driver()

def start_background_update():
    """バックグラウンド更新を開始"""
    get_instance().start_background_update()

def stop_background_update():
    """バックグラウンド更新を停止"""
    get_instance().stop_background_update() 