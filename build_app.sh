#!/bin/bash

# エラーが発生したら終了
set -e

# 古いビルドを削除
echo "古いビルドを削除しています..."
rm -rf build dist
rm -rf *.app

# ユニバーサルバイナリとしてビルドするための環境変数を設定
echo "ユニバーサルバイナリ（Intel + Apple Silicon）としてビルドするための環境を準備します..."
export ARCHFLAGS="-arch x86_64 -arch arm64"

# 必要なパッケージをバイナリとしてインストール
echo "必要なパッケージをインストールしています..."
pip install --upgrade pip
pip install -r requirements.txt

# Pydanticとpydantic-coreを明示的に再インストール
echo "PyInstallerを使用してユニバーサルバイナリをビルドします..."
pip install pyinstaller

# アイコンが存在しない場合は作成
if [ ! -f icon.icns ]; then
    echo "アイコンを作成しています..."
    python create_icon.py
fi

# アプリケーションをビルド
echo "PyInstallerでアプリケーションをユニバーサルバイナリとしてビルドしています..."
pyinstaller --clean --noconfirm \
    --name="SeleniumAutomation" \
    --windowed \
    --icon=icon.icns \
    --add-data="templates:templates" \
    --add-data="static:static" \
    --add-data="drivers:drivers" \
    --add-data=".env:.env" \
    --add-data="requirements.txt:requirements.txt" \
    --hidden-import="flask" \
    --hidden-import="flask_bootstrap" \
    --hidden-import="flask_login" \
    --hidden-import="flask_wtf" \
    --hidden-import="selenium" \
    --hidden-import="python_dotenv" \
    --hidden-import="dotenv" \
    --hidden-import="supabase" \
    --hidden-import="pandas" \
    --hidden-import="bs4" \
    --hidden-import="requests" \
    --hidden-import="apscheduler" \
    --hidden-import="loguru" \
    --hidden-import="semver" \
    --hidden-import="openai" \
    --hidden-import="pydantic" \
    --hidden-import="pydantic_core" \
    app_launcher.py

# ビルド成功を確認
if [ ! -d "dist/SeleniumAutomation.app" ]; then
    echo "PyInstallerビルドに失敗しました。"
    exit 1
fi

# 必要なファイルをコピー
echo "追加ファイルをコピーしています..."
mkdir -p dist/SeleniumAutomation.app/Contents/Resources/logs
mkdir -p dist/SeleniumAutomation.app/Contents/Resources/crawled_data
mkdir -p dist/SeleniumAutomation.app/Contents/Resources/backups
touch dist/SeleniumAutomation.app/Contents/Resources/logs/app.log

# 他の必要なPythonスクリプトをコピー
cp chromedriver_manager.py dist/SeleniumAutomation.app/Contents/Resources/
cp bulk_apply.py dist/SeleniumAutomation.app/Contents/Resources/
cp crawler.py dist/SeleniumAutomation.app/Contents/Resources/
cp updater.py dist/SeleniumAutomation.app/Contents/Resources/
cp supabase_stripe_handler.py dist/SeleniumAutomation.app/Contents/Resources/
cp app.py dist/SeleniumAutomation.app/Contents/Resources/

# chromedriverをコピー
if [ -f "chromedriver" ]; then
    cp chromedriver dist/SeleniumAutomation.app/Contents/Resources/
    chmod +x dist/SeleniumAutomation.app/Contents/Resources/chromedriver
fi

# ビルドしたアプリケーションをカレントディレクトリにコピー
cp -r dist/SeleniumAutomation.app .

echo "ユニバーサルバイナリとしてビルドが完了しました: $(pwd)/SeleniumAutomation.app"
echo "Intel(x86_64)とApple Silicon(arm64)の両方に対応しています"

# 確認
echo "ビルドしたアプリケーションを実行しますか？(y/n)"
read -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "SeleniumAutomation.app"
fi 