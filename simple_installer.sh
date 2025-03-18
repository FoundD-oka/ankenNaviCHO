#!/bin/bash

# エラーが発生したら終了
set -e

# アプリケーション名
APP_NAME="SeleniumAutomation"

# アプリケーションのインストール先
INSTALL_DIR="$HOME/Applications/$APP_NAME.app"
CONTENTS_DIR="$INSTALL_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# カレントディレクトリを取得
CURRENT_DIR=$(pwd)

# カラー表示の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘッダーを表示
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}      ${APP_NAME} ワンクリックインストーラー      ${NC}"
echo -e "${BLUE}====================================================${NC}"
echo ""

# インストール先ディレクトリが既に存在する場合の確認
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${RED}警告: $INSTALL_DIR は既に存在します。${NC}"
    read -p "上書きしますか？ (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "インストールを中止しました。"
        exit 1
    fi
    echo "既存のインストールを削除しています..."
    rm -rf "$INSTALL_DIR"
fi

echo "アプリケーションをインストールしています..."

# ディレクトリ構造を作成
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# 必要なファイルをコピー
echo "ファイルをコピーしています..."

# リソースファイルをコピー
cp -R app.py "$RESOURCES_DIR/"
cp -R chromedriver_manager.py "$RESOURCES_DIR/"
cp -R bulk_apply.py "$RESOURCES_DIR/"
cp -R crawler.py "$RESOURCES_DIR/"
cp -R updater.py "$RESOURCES_DIR/"
cp -R supabase_stripe_handler.py "$RESOURCES_DIR/"
cp -R .env "$RESOURCES_DIR/"
cp -R requirements.txt "$RESOURCES_DIR/"
cp -R templates "$RESOURCES_DIR/"
cp -R static "$RESOURCES_DIR/"

# ディレクトリを作成
mkdir -p "$RESOURCES_DIR/logs"
mkdir -p "$RESOURCES_DIR/drivers"
mkdir -p "$RESOURCES_DIR/backups"
mkdir -p "$RESOURCES_DIR/crawled_data"

# ChromeDriverをコピー
if [ -f "chromedriver" ]; then
    cp chromedriver "$RESOURCES_DIR/"
    chmod +x "$RESOURCES_DIR/chromedriver"
fi

# 簡易的なアイコンファイルを作成
echo "アイコンを作成しています..."
mkdir -p "$RESOURCES_DIR/AppIcon.iconset"

# Iconutil用のディレクトリが存在しない場合は作成
if [ ! -d "temp_icons" ]; then
    mkdir -p "temp_icons/AppIcon.iconset"
fi

# シンプルなアイコンを作成（ImageMagickがインストールされている場合）
if command -v convert &> /dev/null; then
    echo "ImageMagickを使用してアイコンを作成しています..."
    
    # 各サイズのアイコンを生成
    for size in 16 32 128 256 512 1024; do
        convert -size "${size}x${size}" xc:none -fill royalblue -draw "circle $((size/2)),$((size/2)) $((size/2)),1" -fill white -font Arial -pointsize $((size/2)) -gravity center -annotate 0 "S" "temp_icons/AppIcon.iconset/icon_${size}x${size}.png"
        
        # Retina用アイコン（サイズが適切な場合）
        if [ $size -gt 16 ]; then
            cp "temp_icons/AppIcon.iconset/icon_${size}x${size}.png" "temp_icons/AppIcon.iconset/icon_$((size/2))x$((size/2))@2x.png"
        fi
    done
    
    # iconutilでicnsファイルを作成
    if command -v iconutil &> /dev/null; then
        iconutil -c icns "temp_icons/AppIcon.iconset" -o "$RESOURCES_DIR/AppIcon.icns"
        echo "アイコンファイルを作成しました: $RESOURCES_DIR/AppIcon.icns"
    else
        echo "iconutilがインストールされていないため、アイコンファイルの作成をスキップします。"
    fi
else
    echo "ImageMagickがインストールされていないため、アイコンの作成をスキップします。"
    echo "デフォルトアイコンを使用します。"
fi

# app_launcher.pyをコピー
cat > "$RESOURCES_DIR/app_launcher.py" << 'EOF'
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

# ロギング設定
log_dir = Path('./logs')
if not log_dir.exists():
    log_dir.mkdir(parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/launcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('app_launcher')

class AppLauncher:
    """アプリケーション起動を管理するクラス"""
    
    def __init__(self):
        self.app_process = None
        self.port = 8000  # デフォルトポート
        self.env_file = Path('.env')
        self.bundle_dir = self._get_bundle_dir()
        self.initialize_environment()
    
    def _get_bundle_dir(self):
        """アプリケーションバンドルのディレクトリを取得"""
        if getattr(sys, 'frozen', False):
            # .appとして実行されている場合
            bundle_dir = Path(os.path.dirname(os.path.dirname(sys.executable)))
            return bundle_dir / 'Resources'
        else:
            # 開発環境の場合
            return Path(os.path.dirname(os.path.abspath(__file__)))
    
    def initialize_environment(self):
        """環境を初期化"""
        try:
            logger.info(f"アプリケーションの初期化を開始します。バンドルディレクトリ: {self.bundle_dir}")
            
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
            
            # ポート8000から8100までを試す
            for port in range(8000, 8100):
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
            # 使用可能なポートを見つける
            port = self.find_available_port()
            if not port:
                raise Exception("使用可能なポートが見つかりませんでした")
            
            # .envファイルのポート設定を更新
            self.update_port_in_env(port)
            
            # アプリケーションの起動コマンド
            cmd = [
                sys.executable,
                os.path.join(self.bundle_dir, 'app.py')
            ]
            
            # 環境変数を設定
            env = os.environ.copy()
            env['PORT'] = str(port)
            
            # アプリケーションを起動
            logger.info(f"アプリケーションを起動します: {' '.join(cmd)}")
            self.app_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
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
EOF

# 起動スクリプトを作成
cat > "$MACOS_DIR/run" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

cd "$RESOURCES_DIR"
python3 app_launcher.py
EOF

# 起動スクリプトに実行権限を付与
chmod +x "$MACOS_DIR/run"

# Info.plistを作成
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>run</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.$APP_NAME</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 YourCompany. All rights reserved.</string>
</dict>
</plist>
EOF

# シンボリックリンクを作成（任意）
ln -sf "$INSTALL_DIR" "/Applications/$APP_NAME.app"

echo -e "${GREEN}インストールが完了しました！${NC}"
echo -e "アプリケーションは以下の場所にインストールされました:"
echo -e "${BLUE}$INSTALL_DIR${NC}"

echo -e "\n${GREEN}アプリケーションの起動方法:${NC}"
echo -e "Finderから ${BLUE}/Applications/$APP_NAME.app${NC} をダブルクリックします。"

echo -e "\n${GREEN}ログファイルの場所:${NC}"
echo -e "${BLUE}$RESOURCES_DIR/logs/${NC}"

echo ""
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}インストールが正常に完了しました！${NC}"
echo -e "${BLUE}====================================================${NC}"

# アプリケーションを今すぐ起動するか確認
read -p "アプリケーションを今すぐ起動しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "アプリケーションを起動しています..."
    open -a "/Applications/$APP_NAME.app"
fi 