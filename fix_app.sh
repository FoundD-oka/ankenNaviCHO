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

# 起動スクリプトを作成（conda依存を除去）
cat > "$MACOS_DIR/run" << 'EOF_RUN'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"
VENV_DIR="$HOME/Library/Application Support/ankenNaviCHO/venv"

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

# 初回起動ダイアログ表示
/usr/bin/osascript -e 'display dialog "環境構築を開始します。完了までしばらくお待ちください。" buttons {"OK"} default button "OK" with title "ankenNaviCHO"'

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
fi

# 完了ダイアログ
/usr/bin/osascript -e 'display dialog "環境構築が完了しました。アプリケーションを起動します。" buttons {"OK"} default button "OK" with title "ankenNaviCHO"'

# ChromeでURLを開く代わりに、pythonスクリプトに直接起動させる
python3 "$RESOURCES_DIR/app_launcher.py"
EOF_RUN

# 起動スクリプトに実行権限を付与
chmod +x "$MACOS_DIR/run"

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

