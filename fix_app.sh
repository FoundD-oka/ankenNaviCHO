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
if [ -f "AppIcon.icns" ]; then
    # 既存のicnsファイルを使用
    echo "既存のアイコンファイルを使用します: AppIcon.icns"
    cp AppIcon.icns "$RESOURCES_DIR/"
else
    # temp_iconsディレクトリから新しいアイコンを作成
    if [ -d "temp_icons/AppIcon.iconset" ] && [ "$(ls -A temp_icons/AppIcon.iconset)" ]; then
        echo "既存のアイコンセットからアイコンファイルを作成します..."
        
        # 一時的なディレクトリを作成
        mkdir -p "tmp_iconset"
        
        # アイコンを正しい名前でコピー
        if [ -f "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" ]; then
            cp "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" "tmp_iconset/icon_16x16@2x.png"
        fi
        if [ -f "temp_icons/AppIcon.iconset/Icon-App-20x20@1x.png" ]; then
            cp "temp_icons/AppIcon.iconset/Icon-App-20x20@1x.png" "tmp_iconset/icon_16x16.png"
        fi
        if [ -f "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" ]; then
            cp "temp_icons/AppIcon.iconset/Icon-App-40x40@1x.png" "tmp_iconset/icon_32x32.png"
        fi
        if [ -f "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" ]; then
            cp "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" "tmp_iconset/icon_32x32@2x.png"
            cp "temp_icons/AppIcon.iconset/Icon-App-76x76@1x.png" "tmp_iconset/icon_128x128.png"
        fi
        if [ -f "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" ]; then
            cp "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" "tmp_iconset/icon_128x128@2x.png"
            cp "temp_icons/AppIcon.iconset/Icon-App-83.5x83.5@2x.png" "tmp_iconset/icon_256x256.png"
        fi
        if [ -f "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" ]; then
            cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_256x256@2x.png"
            cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_512x512.png"
            cp "temp_icons/AppIcon.iconset/ItunesArtwork@2x.png" "tmp_iconset/icon_512x512@2x.png"
        fi
        
        # icnsファイルを作成
        if command -v iconutil &> /dev/null; then
            iconutil -c icns "tmp_iconset" -o "tmp_AppIcon.icns"
            cp "tmp_AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"
            echo "アイコンファイルを作成しました: $RESOURCES_DIR/AppIcon.icns"
            
            # 一時ファイル削除
            rm -rf "tmp_iconset" "tmp_AppIcon.icns"
        else
            echo "iconutilがインストールされていないため、アイコンファイルの作成をスキップします。"
        fi
    else
        echo "アイコンセットが見つからないため、アイコンの作成をスキップします。"
    fi
fi

# 起動スクリプトを作成（conda依存を除去）
cat > "$MACOS_DIR/run" << 'EOF_RUN'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

# 必要なPythonパッケージをインストール
cd "$RESOURCES_DIR"
python3 -m pip install -q python-dotenv flask requests selenium webdriver_manager supabase

# アプリケーションを起動
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

# アプリケーションを今すぐ起動するか確認
read -p "アプリケーションを今すぐ起動しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "アプリケーションを起動しています..."
    open "$INSTALL_DIR"
fi 