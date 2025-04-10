#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import socket
import subprocess
import webbrowser
import time
import logging
import threading
import json
import platform
import shutil
from pathlib import Path
from dotenv import load_dotenv, set_key
import traceback
import random

# ロギング設定
def setup_logging():
    """ロギングの設定を行う"""
    log_dir = Path('./logs')
    if not log_dir.exists():
        log_dir.mkdir(parents=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'launcher.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('app_launcher')

# グローバルなロガーを設定
logger = setup_logging()

class AppLauncher:
    """アプリケーション起動を管理するクラス"""
    
    def __init__(self):
        self.app_process = None
        self.port = 8000  # デフォルトポート
        self.bundle_dir = self._get_bundle_dir()
        self.env_file = self.bundle_dir / '.env'
        logger.info(f"アプリケーションを初期化しています。バンドルディレクトリ: {self.bundle_dir}")
        self.initialize_environment()
    
    def _get_bundle_dir(self):
        """アプリケーションバンドルのディレクトリを取得"""
        if getattr(sys, 'frozen', False):
            # .appとして実行されている場合
            if platform.system() == 'Darwin':
                # macOS
                if hasattr(sys, '_MEIPASS'):
                    # PyInstallerの場合
                    bundle_dir = Path(sys._MEIPASS)
                else:
                    # py2appの場合
                    bundle_dir = Path(os.path.dirname(os.path.dirname(sys.executable))) / 'Resources'
            else:
                # Windows/Linuxの場合
                bundle_dir = Path(os.path.dirname(sys.executable))
            logger.info(f"フローズンアプリケーションとして実行中: {bundle_dir}")
            return bundle_dir
        else:
            # 開発環境の場合
            bundle_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            logger.info(f"開発環境として実行中: {bundle_dir}")
            return bundle_dir
    
    def initialize_environment(self):
        """環境を初期化"""
        try:
            logger.info(f"環境を初期化しています。カレントディレクトリを変更: {self.bundle_dir}")
            
            # カレントディレクトリをバンドルディレクトリに設定
            os.chdir(self.bundle_dir)
            
            # .envファイルの読み込み
            self._load_env_file()
            
            # フォルダ構造の確認と作成
            self._ensure_directories()
            
            # ChromeDriverの設定確認
            self._setup_chromedriver()
            
            logger.info("環境の初期化が完了しました")
        except Exception as e:
            logger.error(f"環境の初期化中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            self._show_error_dialog("環境の初期化に失敗しました", str(e))
            sys.exit(1)
    
    def _load_env_file(self):
        """環境変数ファイルを読み込む"""
        try:
            # .envファイルが存在するか確認
            if not self.env_file.exists():
                logger.warning(".envファイルが見つかりません。デフォルト設定を使用します。")
                # デフォルトの.envファイルを作成
                with open(self.env_file, 'w', encoding='utf-8') as f:
                    f.write("# Flask設定\n")
                    f.write("FLASK_SECRET_KEY=default_secret_key\n\n")
                    f.write("# ポート設定\n")
                    f.write("PORT=8000\n")
                    f.write("FLASK_ENV=production\n")
                    f.write("FLASK_DEBUG=0\n")
            
            # .envファイルを読み込む
            load_dotenv(self.env_file)
            
            # ポート設定を取得
            env_port = os.getenv('PORT')
            if env_port:
                try:
                    self.port = int(env_port)
                    logger.info(f".envファイルから読み込んだポート: {self.port}")
                except ValueError:
                    logger.warning(f"ポート番号の解析に失敗しました: {env_port}。デフォルトポート {self.port} を使用します。")
            
            logger.info(f".envファイルを読み込みました。ポート: {self.port}")
        except Exception as e:
            logger.error(f".envファイルの読み込み中にエラーが発生しました: {str(e)}")
            raise
    
    def _ensure_directories(self):
        """必要なディレクトリが存在することを確認"""
        directories = [
            Path('./logs'),
            Path('./drivers'),
            Path('./backups'),
            Path('./crawled_data')
        ]
        
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True)
                logger.info(f"ディレクトリを作成しました: {directory}")
    
    def _setup_chromedriver(self):
        """ChromeDriverの設定を確認"""
        try:
            from chromedriver_manager import setup_driver
            
            driver_path = setup_driver()
            if not driver_path:
                raise Exception("ChromeDriverのセットアップに失敗しました")
            
            # .envファイルにSeleniumドライバーパスを設定
            selenium_driver_path = os.path.abspath(driver_path)
            current_path = os.getenv('SELENIUM_DRIVER_PATH', '')
            
            if current_path != selenium_driver_path:
                # .envファイルを更新
                set_key(self.env_file, 'SELENIUM_DRIVER_PATH', selenium_driver_path)
                logger.info(f"SELENIUM_DRIVER_PATHを更新しました: {selenium_driver_path}")
            
            logger.info("ChromeDriverのセットアップが完了しました")
        except Exception as e:
            logger.error(f"ChromeDriverのセットアップ中にエラーが発生しました: {str(e)}")
            raise
    
    def find_available_port(self):
        """使用可能なポートを見つける"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # 指定されたポートをチェック
            result = sock.connect_ex(('127.0.0.1', self.port))
            if result != 0:
                # ポートは使用可能
                logger.info(f"指定されたポート {self.port} は使用可能です")
                return self.port
            
            # ポートが使用中の場合、使用可能なポートを探す
            logger.warning(f"ポート {self.port} は既に使用されています。別のポートを探します。")
            
            # より広い範囲のポートを試す (3000-9000)
            # まず、元のポートの前後を試す
            start_port = max(3000, self.port - 100)
            end_port = min(9000, self.port + 100)
            
            for port in range(start_port, end_port):
                if port == self.port:
                    continue  # 既にチェック済み
                
                result = sock.connect_ex(('127.0.0.1', port))
                if result != 0:
                    logger.info(f"使用可能なポート {port} を見つけました")
                    return port
            
            # より広範囲で探す
            candidate_ports = list(range(3000, 9000))
            random.shuffle(candidate_ports)  # ランダムな順序で試す
            
            for port in candidate_ports:
                if port >= start_port and port <= end_port:
                    continue  # 既にチェック済み
                
                result = sock.connect_ex(('127.0.0.1', port))
                if result != 0:
                    logger.info(f"使用可能なポート {port} を見つけました")
                    return port
            
            # 使用可能なポートが見つからない場合
            logger.error("使用可能なポートが見つかりませんでした")
            return None
        finally:
            sock.close()
    
    def update_port_in_env(self, port):
        """環境変数ファイルのポート設定を更新"""
        if self.port != port:
            self.port = port
            set_key(self.env_file, 'PORT', str(port))
            logger.info(f".envファイルのポート設定を {port} に更新しました")
    
    def start_app(self):
        """アプリケーションを起動"""
        try:
            # 環境変数から直接ポートを取得（シェルスクリプトからの設定を優先）
            env_port = os.environ.get('PORT')
            if env_port:
                try:
                    port = int(env_port)
                    logger.info(f"環境変数から直接ポートを取得しました: {port}")
                except ValueError:
                    logger.warning(f"環境変数のポート番号が無効です: {env_port}")
                    port = self.find_available_port()
            else:
                # 使用可能なポートを見つける
                port = self.find_available_port()
            
            if not port:
                raise Exception("使用可能なポートが見つかりませんでした")
            
            # .envファイルのポート設定を更新
            self.update_port_in_env(port)
            
            # アプリケーションの起動コマンド
            app_path = self.bundle_dir / 'app.py'
            logger.info(f"アプリケーションパス: {app_path}")
            
            # 環境変数を設定
            env = os.environ.copy()
            env['PORT'] = str(port)
            env['FLASK_ENV'] = 'production'  # 開発モードを無効化
            env['FLASK_DEBUG'] = '0'         # デバッグモードを無効化
            env['PYTHONWARNINGS'] = 'ignore::urllib3.exceptions.NotOpenSSLWarning'  # urllib3の警告を抑制
            
            cmd = [
                sys.executable,
                str(app_path)
            ]
            
            # アプリケーションを起動
            logger.info(f"アプリケーションを起動します: {' '.join(cmd)}")
            self.app_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.bundle_dir)
            )
            
            # サーバー起動を待機
            self._wait_for_server(port)
            
            # ブラウザでアプリケーションを開く
            self._open_browser(port)
            
            # 標準出力とエラー出力をログに記録するスレッドを開始
            threading.Thread(target=self._log_output, args=(self.app_process.stdout, "stdout")).start()
            threading.Thread(target=self._log_output, args=(self.app_process.stderr, "stderr")).start()
            
            # プロセスの完了を待機
            self.app_process.wait()
            
        except Exception as e:
            logger.error(f"アプリケーションの起動中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            self._show_error_dialog("アプリケーションの起動に失敗しました", str(e))
            if self.app_process:
                self.app_process.terminate()
            sys.exit(1)
    
    def _wait_for_server(self, port, timeout=30):
        """サーバーが起動するのを待機"""
        logger.info(f"サーバーの起動を待機しています（ポート: {port}）...")
        for _ in range(timeout):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                logger.info(f"サーバーが起動しました（ポート: {port}）")
                return True
            time.sleep(1)
        
        raise Exception(f"サーバーの起動がタイムアウトしました（ポート: {port}）")
    
    def _open_browser(self, port):
        """ブラウザでアプリケーションを開く"""
        url = f"http://localhost:{port}"
        logger.info(f"ブラウザでアプリケーションを開きます: {url}")
        
        # Chromeで開く
        chrome_path = ''
        if platform.system() == 'Darwin':  # macOS
            chrome_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
        elif platform.system() == 'Windows':
            chrome_paths = [
                os.path.expandvars('%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe'),
                os.path.expandvars('%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe'),
                os.path.expandvars('%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe')
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
        elif platform.system() == 'Linux':
            chrome_paths = ['google-chrome', 'google-chrome-stable']
            for path in chrome_paths:
                if shutil.which(path):
                    chrome_path = path
                    break
        
        if chrome_path:
            try:
                # 新しいウィンドウで開く
                subprocess.Popen([chrome_path, '--new-window', url])
                logger.info(f"Chromeで開きました: {chrome_path}")
                return
            except Exception as e:
                logger.error(f"Chromeでの起動に失敗: {str(e)}")
        
        # Chromeが見つからない場合はデフォルトブラウザで開く
        logger.warning("Chromeが見つからないため、デフォルトブラウザで開きます")
        webbrowser.open(url)
    
    def _log_output(self, pipe, name):
        """プロセスの出力をログに記録"""
        for line in pipe:
            logger.info(f"[{name}] {line.strip()}")
    
    def _show_error_dialog(self, title, message):
        """エラーダイアログを表示"""
        try:
            if platform.system() == 'Darwin':
                # macOSの場合、osascriptを使用
                script = f'''
                tell application "System Events"
                    display dialog "{message}" buttons {{"OK"}} default button "OK" with title "{title}" with icon stop
                end tell
                '''
                subprocess.run(['osascript', '-e', script])
            else:
                # その他のプラットフォームの場合、標準出力にメッセージを出力
                print(f"エラー: {title}\n{message}")
        except Exception as e:
            logger.error(f"エラーダイアログの表示に失敗しました: {str(e)}")

    def cleanup(self):
        """アプリケーションのクリーンアップ"""
        if self.app_process:
            logger.info("アプリケーションを終了します...")
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
            logger.info("アプリケーションが終了しました")

def main():
    """メイン関数"""
    launcher = AppLauncher()
    
    try:
        # アプリケーションを起動
        launcher.start_app()
    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
    finally:
        # クリーンアップ
        launcher.cleanup()

if __name__ == "__main__":
    main() 