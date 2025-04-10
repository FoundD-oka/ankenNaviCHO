#!/bin/bash

# エラーが発生したら終了
set -e

# アプリケーション名
APP_NAME="ankenNaviCHO"

# カレントディレクトリを取得
CURRENT_DIR=$(pwd)

# アプリケーションのインストール先をカレントディレクトリに変更
INSTALL_DIR="$CURRENT_DIR/${APP_NAME}_mac.app"
CONTENTS_DIR="$INSTALL_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# カラー表示の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘッダーを表示
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}      ${APP_NAME} 修正スクリプト      ${NC}"
echo -e "${BLUE}====================================================${NC}"
echo ""

# インストール先ディレクトリが既に存在する場合の確認
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${RED}警告: $INSTALL_DIR は既に存在します。${NC}"
    read -p "上書きしますか？ (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "修正を中止しました。"
        exit 1
    fi
    echo "既存のアプリケーションをバックアップしています..."
    BACKUP_DIR="$CURRENT_DIR/backups/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -R "$INSTALL_DIR" "$BACKUP_DIR/"
    echo "バックアップが完了しました: $BACKUP_DIR"
else
    echo "新規にアプリケーションを作成します..."
    mkdir -p "$INSTALL_DIR"
fi

echo "アプリケーションを修正しています..."

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
if [ -f ".env" ]; then
    cp -R .env "$RESOURCES_DIR/"
fi
if [ -f "requirements.txt" ]; then
    cp -R requirements.txt "$RESOURCES_DIR/"
fi
if [ -d "templates" ]; then
    cp -R templates "$RESOURCES_DIR/"
fi
if [ -d "static" ]; then
    cp -R static "$RESOURCES_DIR/"
fi

# ディレクトリを作成
mkdir -p "$RESOURCES_DIR/logs"
mkdir -p "$RESOURCES_DIR/drivers"
mkdir -p "$RESOURCES_DIR/backups"
mkdir -p "$RESOURCES_DIR/crawled_data"

# ChromeDriverをコピー
if [ -d "drivers" ]; then
    cp -R drivers "$RESOURCES_DIR/"
fi

# app_launcher.pyをコピー
cp app_launcher.py "$RESOURCES_DIR/"

# アイコンの処理
echo "アプリケーションアイコンを作成しています..."
ICON_CREATED=false

# 1. original_icon.png から生成
if [ -f "original_icon.png" ]; then
    echo "original_icon.png からアイコンを作成します..."
    if command -v sips &> /dev/null && command -v iconutil &> /dev/null; then
        # 一時的なiconsetディレクトリを作成
        TEMP_ICONSET_DIR="tmp_icon_gen.iconset"
        mkdir -p "$TEMP_ICONSET_DIR"

        # sips を使用して必要なサイズのアイコンを生成
        sips -z 16 16     original_icon.png --out "$TEMP_ICONSET_DIR/icon_16x16.png" > /dev/null 2>&1
        sips -z 32 32     original_icon.png --out "$TEMP_ICONSET_DIR/icon_16x16@2x.png" > /dev/null 2>&1
        sips -z 32 32     original_icon.png --out "$TEMP_ICONSET_DIR/icon_32x32.png" > /dev/null 2>&1
        sips -z 64 64     original_icon.png --out "$TEMP_ICONSET_DIR/icon_32x32@2x.png" > /dev/null 2>&1
        sips -z 128 128   original_icon.png --out "$TEMP_ICONSET_DIR/icon_128x128.png" > /dev/null 2>&1
        sips -z 256 256   original_icon.png --out "$TEMP_ICONSET_DIR/icon_128x128@2x.png" > /dev/null 2>&1
        sips -z 256 256   original_icon.png --out "$TEMP_ICONSET_DIR/icon_256x256.png" > /dev/null 2>&1
        sips -z 512 512   original_icon.png --out "$TEMP_ICONSET_DIR/icon_256x256@2x.png" > /dev/null 2>&1
        sips -z 512 512   original_icon.png --out "$TEMP_ICONSET_DIR/icon_512x512.png" > /dev/null 2>&1
        # sips -z 1024 1024 original_icon.png --out "$TEMP_ICONSET_DIR/icon_512x512@2x.png" > /dev/null 2>&1 # 1024pxはオプション

        # iconutil を使用して .icns ファイルを作成
        iconutil -c icns "$TEMP_ICONSET_DIR" -o "$RESOURCES_DIR/AppIcon.icns"
        
        # 一時ディレクトリを削除
        rm -rf "$TEMP_ICONSET_DIR"
        
        echo "アイコンファイルを作成しました: $RESOURCES_DIR/AppIcon.icns"
        ICON_CREATED=true
    else
        echo "警告: アイコン生成に必要な sips または iconutil コマンドが見つかりません。アイコン作成をスキップします。"
    fi
# 2. 既存の AppIcon.icns を使用
elif [ -f "AppIcon.icns" ] && [ "$ICON_CREATED" != true ]; then
    # 既存のicnsファイルを使用
    echo "既存のアイコンファイルを使用します: AppIcon.icns"
    cp AppIcon.icns "$RESOURCES_DIR/"
    ICON_CREATED=true
# 3. temp_icons/AppIcon.iconset から生成
elif [ -d "temp_icons/AppIcon.iconset" ] && [ "$(ls -A temp_icons/AppIcon.iconset)" ] && [ "$ICON_CREATED" != true ]; then
    echo "既存のアイコンセットからアイコンファイルを作成します..."
    
    # 一時的なディレクトリを作成
    mkdir -p "tmp_iconset"
    
    # アイコンを正しい名前でコピー (既存のロジックを流用)
    if [ -f "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" ]; then cp "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" "tmp_iconset/icon_16x16@2x.png"; fi
    if [ -f "temp_icons/AppIcon.iconset/Icon-App-20x20@1x.png" ]; then cp "temp_icons/AppIcon.iconset/Icon-App-20x20@1x.png" "tmp_iconset/icon_16x16.png"; fi
    if [ -f "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" ]; then cp "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" "tmp_iconset/icon_32x32.png"; fi
    if [ -f "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" ]; then 
        cp "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" "tmp_iconset/icon_32x32@2x.png"; 
        cp "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" "tmp_iconset/icon_128x128.png"; 
    fi
    if [ -f "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" ]; then 
        cp "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" "tmp_iconset/icon_128x128@2x.png"; 
        cp "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" "tmp_iconset/icon_256x256.png"; 
    fi
    if [ -f "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" ]; then 
        cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_256x256@2x.png"; 
        cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_512x512.png"; 
        cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_512x512@2x.png"; 
    fi
    
    # icnsファイルを作成
    if command -v iconutil &> /dev/null; then
        iconutil -c icns "tmp_iconset" -o "tmp_AppIcon.icns"
        cp "tmp_AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"
        echo "アイコンファイルを作成しました: $RESOURCES_DIR/AppIcon.icns"
        ICON_CREATED=true
        
        # 一時ファイル削除
        rm -rf "tmp_iconset" "tmp_AppIcon.icns"
    else
        echo "警告: iconutilがインストールされていないため、アイコンファイルの作成をスキップします。"
    fi
fi

# アイコンが作成されなかった場合のフォールバックメッセージ
if [ "$ICON_CREATED" != true ]; then
    echo "有効なアイコンソースが見つからなかったため、アイコンの作成をスキップします。"
fi

# 起動スクリプトを作成（シンプル版）
cat > "$MACOS_DIR/run" << 'EOF_RUN'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"
VENV_DIR="$HOME/Library/Application Support/ankenNaviCHO/venv"
SETUP_DONE_FLAG="$HOME/Library/Application Support/ankenNaviCHO/.setup_done"

# セットアップ済みかチェック
if [ ! -f "$SETUP_DONE_FLAG" ]; then
  RESULT=$(/usr/bin/osascript <<EOF
    display dialog "初回セットアップが必要です。実行しますか？" buttons {"キャンセル", "実行"} default button "実行"
EOF
  )
  
  # キャンセルしたら終了
  if [[ "$RESULT" != *"実行"* ]]; then
    exit 1
  fi
  
  # 初回環境構築を実行
  "$SCRIPT_DIR/setup"
  
  # セットアップ後はメッセージを表示して終了
  /usr/bin/osascript -e 'display dialog "環境構築が完了しました。これからもう一度アプリケーションを起動してください。" buttons {"OK"} default button "OK" with title "ankenNaviCHO"'
  exit 0
fi

# セットアップ済みなら直接アプリを起動
source "$VENV_DIR/bin/activate"
cd "$RESOURCES_DIR"
python3 "$RESOURCES_DIR/app_launcher.py"
EOF_RUN

# セットアップスクリプトを作成
cat > "$MACOS_DIR/setup" << 'EOF_SETUP'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"
VENV_DIR="$HOME/Library/Application Support/ankenNaviCHO/venv"
SETUP_DONE_FLAG="$HOME/Library/Application Support/ankenNaviCHO/.setup_done"

# 初回起動ダイアログ表示
/usr/bin/osascript -e 'display dialog "環境構築を開始します。しばらくお待ちください。\n\n完了後に改めて通知します。" buttons {"OK"} default button "OK" with title "ankenNaviCHO"'

# ポート競合チェックと自動選択機能
DEFAULT_PORT=8080
ALTERNATIVE_PORTS=(8000 3000 8888 9000 7000)

check_port() {
  local port=$1
  lsof -i:$port > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    return 1  # ポートは使用中
  else
    return 0  # ポートは利用可能
  fi
}

# デフォルトポートをチェック
if ! check_port $DEFAULT_PORT; then
  echo "デフォルトポート $DEFAULT_PORT は使用中です。代替ポートを探します..."
  
  # 代替ポートをチェック
  SELECTED_PORT=""
  for port in "${ALTERNATIVE_PORTS[@]}"; do
    if check_port $port; then
      SELECTED_PORT=$port
      echo "ポート $SELECTED_PORT が利用可能です。このポートを使用します。"
      break
    fi
  done
  
  if [ -z "$SELECTED_PORT" ]; then
    # 空いているポートをランダムに探す (3000-9000の範囲)
    for port in $(shuf -i 3000-9000 -n 100); do
      if [ $port -eq $DEFAULT_PORT ]; then
        continue  # デフォルトポートはスキップ
      fi
      if check_port $port; then
        SELECTED_PORT=$port
        echo "ランダムに選択したポート $SELECTED_PORT が利用可能です。このポートを使用します。"
        break
      fi
    done
  fi
  
  if [ -z "$SELECTED_PORT" ]; then
    /usr/bin/osascript -e 'display dialog "利用可能なポートが見つかりませんでした。他のアプリケーションを終了してから再試行してください。" buttons {"OK"} default button "OK" with icon stop with title "エラー"'
    exit 1
  fi
  
  # 選択したポートを環境変数に設定
  export PORT=$SELECTED_PORT
else
  echo "デフォルトポート $DEFAULT_PORT は利用可能です。"
  export PORT=$DEFAULT_PORT
fi

# 事前チェック機能
# Pythonバージョン確認
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ $PYTHON_VERSION != *"Python 3"* ]]; then
  /usr/bin/osascript -e 'display dialog "Python 3が必要です。インストールしてから再度お試しください。" buttons {"OK"} default button "OK" with icon stop with title "エラー"'
  exit 1
fi

# Chromeがインストールされているか確認
if [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "$HOME/Applications/Google Chrome.app" ]; then
  /usr/bin/osascript -e 'display dialog "Google Chromeがインストールされていません。インストールしてから再度お試しください。" buttons {"OK"} default button "OK" with icon stop with title "エラー"'
  exit 1
fi

# 仮想環境のセットアップ
mkdir -p "$(dirname "$VENV_DIR")"
if [ ! -d "$VENV_DIR" ]; then
  echo "仮想環境を作成しています..."
  python3 -m venv "$VENV_DIR"
fi

# 仮想環境を有効化
source "$VENV_DIR/bin/activate"

# 必要なパッケージをインストール
cd "$RESOURCES_DIR"
if [ -f "requirements.txt" ]; then
  pip install -q -r requirements.txt
else
  pip install -q python-dotenv flask requests selenium webdriver_manager supabase
fi

# .envファイルの妥当性確認
if [ -f ".env" ]; then
  if ! grep -q "API_KEY" ".env" && ! grep -q "SUPABASE_URL" ".env"; then
    /usr/bin/osascript -e 'display dialog ".envファイルの内容が不完全です。必要な設定を確認してください。" buttons {"続行", "終了"} default button "終了" with icon caution with title "警告"'
    if [ "$?" -ne "0" ]; then
      exit 1
    fi
  fi
fi

# PORT環境変数を.envファイルに設定
if [ -f ".env" ]; then
  if grep -q "^PORT=" ".env"; then
    # PORTが既に存在する場合は更新
    sed -i "" "s/^PORT=.*/PORT=$PORT/" ".env"
  else
    # PORTが存在しない場合は追加
    echo "PORT=$PORT" >> ".env"
  fi

  # FLASK_DEBUGを強制的に0に設定
  if grep -q "^FLASK_DEBUG=" ".env"; then
    # FLASK_DEBUGが既に存在する場合は更新
    sed -i "" "s/^FLASK_DEBUG=.*/FLASK_DEBUG=0/" ".env"
  else
    # FLASK_DEBUGが存在しない場合は追加
    echo "FLASK_DEBUG=0" >> ".env"
  fi
  
  # SKIP_NODE_SERVER設定を追加（npmエラー対策）
  if ! grep -q "^SKIP_NODE_SERVER=" ".env"; then
    echo "SKIP_NODE_SERVER=1" >> ".env"
  fi
  
  # CHROMEDRIVER_PRECACHE設定を追加（起動高速化）
  if ! grep -q "^CHROMEDRIVER_PRECACHE=" ".env"; then
    echo "CHROMEDRIVER_PRECACHE=1" >> ".env"
  fi
  
  # DISABLE_CHROMEDRIVER_BACKGROUND_UPDATE設定を追加（起動高速化）
  if ! grep -q "^DISABLE_CHROMEDRIVER_BACKGROUND_UPDATE=" ".env"; then
    echo "DISABLE_CHROMEDRIVER_BACKGROUND_UPDATE=1" >> ".env"
  fi
fi

# 事前にChromeDriverをキャッシュして起動を高速化
if [ -f "$RESOURCES_DIR/chromedriver_manager.py" ]; then
  echo "ChromeDriverを事前にキャッシュしています..."
  # 仮想環境のPythonでChromeDriverを事前キャッシュするスクリプトを実行
  CACHE_SCRIPT=$(cat <<'END_SCRIPT'
import sys
import os
import time
import subprocess
import re

# Chromeのバージョンを取得
def get_chrome_version():
    # MacOSのChromeバージョン取得
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
        print(f"Chromeバージョン取得エラー: {e}")
    return None

# モジュールのインポートパスを設定
sys.path.insert(0, os.getcwd())

try:
    from chromedriver_manager import setup_driver
    
    # 現在のChromeバージョンを取得
    chrome_version = get_chrome_version()
    print(f"検出されたChromeバージョン: {chrome_version}")
    
    # ChromeDriverを事前にセットアップして結果をキャッシュ
    driver_path = setup_driver()
    
    if not driver_path:
        raise Exception("ChromeDriverのセットアップが失敗しました")
        
    print(f"ChromeDriverを事前キャッシュしました: {driver_path}")
    
    # セットアップ後の情報をファイルに保存（Chromeバージョン含む）
    with open(".chromedriver_cache_info", "w") as f:
        f.write(f"PATH={driver_path}\n")
        f.write(f"TIMESTAMP={int(time.time())}\n")
        if chrome_version:
            f.write(f"CHROME_VERSION={chrome_version}\n")
    
except Exception as e:
    print(f"ChromeDriverのキャッシュ中にエラーが発生しました: {e}")
    sys.exit(1)
END_SCRIPT
)
  
  # スクリプトを一時ファイルに書き出して実行
  TEMP_SCRIPT_FILE="$RESOURCES_DIR/.temp_chromedriver_cache.py"
  echo "$CACHE_SCRIPT" > "$TEMP_SCRIPT_FILE"
  python3 "$TEMP_SCRIPT_FILE"
  rm -f "$TEMP_SCRIPT_FILE"
fi

# セットアップ完了フラグを作成
mkdir -p "$(dirname "$SETUP_DONE_FLAG")"
touch "$SETUP_DONE_FLAG"

# バックグラウンド初期化が完了するのを待つ
echo "バックグラウンド初期化が完了するのを待っています（20秒）..."
sleep 20

# 処理が完了したことを表示
echo "環境構築が完了しました。"
EOF_SETUP

# app_launcher.pyに最適化パッチを適用（事前キャッシュ情報を利用するため）
if [ -f "app_launcher.py" ]; then
    # パッチ内容を一時ファイルに保存
    PATCH_CONTENT=$(cat <<'EOF_PATCH'
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
EOF_PATCH
)

    # 既存のapp_launcher.pyを上書き
    echo "$PATCH_CONTENT" > "$RESOURCES_DIR/app_launcher.py"
    echo "app_launcher.pyを最適化しました。"
fi

# 起動スクリプトに実行権限を付与
chmod +x "$MACOS_DIR/run"
chmod +x "$MACOS_DIR/setup"

# Info.plistを作成
cat > "$CONTENTS_DIR/Info.plist" << EOF_PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>run</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.anken.navicho</string>
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
EOF_PLIST

echo -e "${GREEN}アプリケーションの修正が完了しました！${NC}"
echo -e "アプリケーションは以下の場所に作成されました:"
echo -e "${BLUE}$INSTALL_DIR${NC}"

echo -e "\n${GREEN}アプリケーションの起動方法:${NC}"
echo -e "Finderから ${BLUE}$INSTALL_DIR${NC} をダブルクリックします。"
echo -e "※初回起動時は環境構築が実行され、完了後に再度起動が必要です。"
echo -e "※2回目以降はすぐにアプリケーションが起動します。"

echo -e "\n${GREEN}ログファイルの場所:${NC}"
echo -e "${BLUE}$RESOURCES_DIR/logs/${NC}"

echo ""
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}修正が正常に完了しました！${NC}"
echo -e "${BLUE}====================================================${NC}"

# アプリケーションの配布方法の説明
echo -e "\n${BLUE}配布方法:${NC}"
echo -e "1. ${BLUE}${APP_NAME}_mac.app${NC} をzipファイルに圧縮します:"
echo -e "   ${GREEN}zip -r ${APP_NAME}_mac.zip ${APP_NAME}_mac.app${NC}"
echo -e "2. zipファイルを配布先に提供します。"
echo -e "3. ユーザーはzipファイルを解凍し、アプリケーションをダブルクリックして実行します。"

