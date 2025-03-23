import os
import sys
import json
import shutil
import tempfile
import logging
import requests
import zipfile
import semver
from pathlib import Path
import subprocess
from datetime import datetime

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 現在のアプリバージョン
CURRENT_VERSION = "0.5.1"

# GitHubリポジトリ情報
GITHUB_REPO_OWNER = "FoundD-oka"
GITHUB_REPO_NAME = "Selenium"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

# バックアップディレクトリ
BACKUP_DIR = Path("backups")

class Updater:
    def __init__(self):
        """アップデーターの初期化"""
        self.current_version = CURRENT_VERSION
        self.latest_version = None
        self.latest_download_url = None
        self.update_available = False
        self.progress = 0
        self.status = "準備完了"
        self.backup_path = None
        
        # バックアップディレクトリの作成
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True)
    
    def check_for_updates(self):
        """GitHubから最新バージョン情報を取得"""
        try:
            self.status = "更新を確認中..."
            self.progress = 10
            
            response = requests.get(GITHUB_API_URL)
            response.raise_for_status()
            
            release_info = response.json()
            self.latest_version = release_info["tag_name"].lstrip("v")
            
            # バージョン比較
            if semver.compare(self.latest_version, self.current_version) > 0:
                self.update_available = True
                self.latest_download_url = release_info["zipball_url"]
                self.status = f"新しいバージョン {self.latest_version} が利用可能です"
            else:
                self.update_available = False
                self.status = "最新バージョンを使用中です"
            
            self.progress = 20
            return self.update_available
            
        except Exception as e:
            logger.error(f"更新の確認中にエラーが発生しました: {str(e)}")
            self.status = f"エラー: {str(e)}"
            self.progress = 0
            return False
    
    def create_backup(self):
        """現在のアプリケーションのバックアップを作成"""
        try:
            self.status = "バックアップを作成中..."
            self.progress = 30
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = BACKUP_DIR / f"backup_{self.current_version}_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 重要なファイルとディレクトリをバックアップ
            # .git, __pycache__, logs, backups, crawled_dataを除外
            exclude_dirs = ['.git', '__pycache__', 'logs', 'backups', 'crawled_data']
            
            for item in Path('.').iterdir():
                if item.name in exclude_dirs or item.name.startswith('.'):
                    continue
                
                if item.is_file():
                    shutil.copy2(item, backup_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, backup_dir / item.name, 
                                   ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            
            self.backup_path = backup_dir
            self.progress = 40
            self.status = "バックアップ完了"
            return True
            
        except Exception as e:
            logger.error(f"バックアップ作成中にエラーが発生しました: {str(e)}")
            self.status = f"バックアップエラー: {str(e)}"
            self.progress = 30
            return False
    
    def download_update(self):
        """最新バージョンをダウンロード"""
        try:
            self.status = "更新をダウンロード中..."
            self.progress = 50
            
            # 一時ディレクトリを作成
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                zip_path = temp_dir_path / "update.zip"
                
                # ダウンロード
                response = requests.get(self.latest_download_url, stream=True)
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.progress = 60
                self.status = "ダウンロード完了、展開中..."
                
                # ZIPファイルを展開
                extract_dir = temp_dir_path / "extracted"
                extract_dir.mkdir()
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # 展開されたディレクトリを特定（通常は単一のディレクトリ）
                extracted_items = list(extract_dir.iterdir())
                if not extracted_items:
                    raise Exception("更新パッケージが空です")
                
                source_dir = extracted_items[0] if extracted_items[0].is_dir() else extract_dir
                
                self.progress = 70
                self.status = "ファイルを更新中..."
                
                # 現在のディレクトリにファイルをコピー
                # .git, __pycache__, logs, backups, crawled_dataを除外
                exclude_dirs = ['.git', '__pycache__', 'logs', 'backups', 'crawled_data']
                
                for item in source_dir.iterdir():
                    if item.name in exclude_dirs:
                        continue
                    
                    dest_path = Path('.') / item.name
                    
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                    elif item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path, 
                                       ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            
            self.progress = 80
            self.status = "更新ファイルのインストール完了"
            return True
            
        except Exception as e:
            logger.error(f"更新のダウンロード中にエラーが発生しました: {str(e)}")
            self.status = f"ダウンロードエラー: {str(e)}"
            self.progress = 50
            return False
    
    def install_dependencies(self):
        """依存関係をインストール"""
        try:
            self.status = "依存関係をインストール中..."
            self.progress = 85
            
            # requirements.txtが存在する場合、依存関係をインストール
            if Path("requirements.txt").exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              check=True, capture_output=True)
            
            self.progress = 90
            self.status = "依存関係のインストール完了"
            return True
            
        except Exception as e:
            logger.error(f"依存関係のインストール中にエラーが発生しました: {str(e)}")
            self.status = f"依存関係エラー: {str(e)}"
            self.progress = 85
            return False
    
    def rollback(self):
        """更新に失敗した場合、バックアップから復元"""
        try:
            if not self.backup_path or not self.backup_path.exists():
                raise Exception("バックアップが見つかりません")
            
            self.status = "ロールバック中..."
            self.progress = 95
            
            # バックアップから復元
            # .git, __pycache__, logs, backups, crawled_dataを除外
            exclude_dirs = ['.git', '__pycache__', 'logs', 'backups', 'crawled_data']
            
            for item in self.backup_path.iterdir():
                if item.name in exclude_dirs:
                    continue
                
                dest_path = Path('.') / item.name
                
                if item.is_file():
                    shutil.copy2(item, dest_path)
                elif item.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
            
            self.status = "ロールバック完了"
            self.progress = 100
            return True
            
        except Exception as e:
            logger.error(f"ロールバック中にエラーが発生しました: {str(e)}")
            self.status = f"ロールバックエラー: {str(e)}"
            return False
    
    def perform_update(self):
        """更新プロセス全体を実行"""
        try:
            # 更新の確認
            if not self.check_for_updates():
                return {"success": False, "message": self.status}
            
            # バックアップの作成
            if not self.create_backup():
                return {"success": False, "message": self.status}
            
            # 更新のダウンロードとインストール
            if not self.download_update():
                self.rollback()
                return {"success": False, "message": f"{self.status} - ロールバックしました"}
            
            # 依存関係のインストール
            if not self.install_dependencies():
                self.rollback()
                return {"success": False, "message": f"{self.status} - ロールバックしました"}
            
            self.progress = 100
            self.status = f"バージョン {self.latest_version} への更新が完了しました"
            return {"success": True, "message": self.status, "version": self.latest_version}
            
        except Exception as e:
            logger.error(f"更新プロセス中にエラーが発生しました: {str(e)}")
            self.status = f"更新エラー: {str(e)}"
            
            # エラーが発生した場合はロールバック
            try:
                self.rollback()
                return {"success": False, "message": f"{self.status} - ロールバックしました"}
            except:
                return {"success": False, "message": f"{self.status} - ロールバックにも失敗しました"}
    
    def get_status(self):
        """現在の更新ステータスを取得"""
        return {
            "progress": self.progress,
            "status": self.status,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available
        }

# グローバルインスタンス
updater = Updater()

# 更新の確認
def check_for_updates():
    return updater.check_for_updates()

# 更新の実行
def perform_update():
    return updater.perform_update()

# ステータスの取得
def get_update_status():
    return updater.get_status() 