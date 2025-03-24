#!/bin/bash
set -e

echo "スタンドアロン版 ankenNaviCHO インストーラー"
echo "------------------------------------------------"

# インストール先ディレクトリ
INSTALL_DIR="$HOME/Applications/ankenNaviCHO.app"
RESOURCES_DIR="$INSTALL_DIR/Contents/Resources"
MACOS_DIR="$INSTALL_DIR/Contents/MacOS"

# 必要なディレクトリを作成
echo "ディレクトリを作成しています..."
mkdir -p "$RESOURCES_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR/logs"
mkdir -p "$RESOURCES_DIR/crawled_data"
mkdir -p "$RESOURCES_DIR/backups"

# 実行スクリプトを作成
echo "実行スクリプトを作成しています..."
cat > "$MACOS_DIR/run" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

cd "$RESOURCES_DIR"
python3 standalone_app.py
EOF

chmod +x "$MACOS_DIR/run"

# Info.plistを作成
echo "Info.plistを作成しています..."
cat > "$INSTALL_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleDisplayName</key>
    <string>ankenNaviCHO</string>
    <key>CFBundleExecutable</key>
    <string>run</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.anken.navicho</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>ankenNaviCHO</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 All rights reserved.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

# 必要なファイルをコピー
echo "ファイルをコピーしています..."
cp standalone_app.py "$RESOURCES_DIR/"
cp app.py "$RESOURCES_DIR/"
cp -r templates "$RESOURCES_DIR/"
cp -r static "$RESOURCES_DIR/"
cp -r drivers "$RESOURCES_DIR/" 2>/dev/null || mkdir -p "$RESOURCES_DIR/drivers"
cp .env "$RESOURCES_DIR/" 2>/dev/null || touch "$RESOURCES_DIR/.env"
cp requirements.txt "$RESOURCES_DIR/" 2>/dev/null || touch "$RESOURCES_DIR/requirements.txt"
cp bulk_apply.py "$RESOURCES_DIR/"
cp crawler.py "$RESOURCES_DIR/"
cp updater.py "$RESOURCES_DIR/"
cp chromedriver_manager.py "$RESOURCES_DIR/"
cp supabase_stripe_handler.py "$RESOURCES_DIR/" 2>/dev/null || echo "// Dummy file" > "$RESOURCES_DIR/supabase_stripe_handler.py"

# アイコンファイルをコピー
if [ -f "icon.icns" ]; then
  cp icon.icns "$RESOURCES_DIR/"
fi

# パッケージのインストール
echo "必要なパッケージをインストールしています..."
pip3 install -t "$RESOURCES_DIR/lib" python-dotenv flask flask_bootstrap flask_login flask_wtf selenium supabase

# PYTHONPATHを設定するためのスクリプトを作成
cat > "$RESOURCES_DIR/setup_env.py" << 'EOF'
import os
import sys

# スクリプトのディレクトリを取得
script_dir = os.path.dirname(os.path.abspath(__file__))

# パスを追加
lib_path = os.path.join(script_dir, 'lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)
EOF

# スタンドアロンアプリを実行するための修正をstandalone_app.pyに追加
cat > "$RESOURCES_DIR/standalone_app.py" << 'EOF'
#!/usr/bin/env python3
"""
ankenNaviCHO スタンドアロンランチャー
conda環境に依存しない実行モジュール
"""
import os
import sys
import subprocess

# ライブラリパスを設定
script_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(script_dir, 'lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

def main():
    """
    アプリケーションのメインエントリーポイント
    """
    print("ankenNaviCHO スタンドアロンランチャーを起動しています...")
    
    # 必要なディレクトリを作成
    os.makedirs(os.path.join(script_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "crawled_data"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "backups"), exist_ok=True)
    
    # アプリケーションを起動
    try:
        app_path = os.path.join(script_dir, "app.py")
        if os.path.exists(app_path):
            # 環境変数を設定
            env = os.environ.copy()
            env["FLASK_APP"] = app_path
            
            # PYTHONPATHを設定
            env["PYTHONPATH"] = lib_path + ":" + env.get("PYTHONPATH", "")
            
            # Flaskアプリケーションを起動
            os.chdir(script_dir)  # 作業ディレクトリを変更
            subprocess.run([sys.executable, app_path], env=env)
        else:
            print(f"エラー: {app_path} が見つかりません")
            sys.exit(1)
    except Exception as e:
        print(f"アプリケーション起動中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "インストールが完了しました！"
echo "アプリケーションは以下の場所にインストールされました: $INSTALL_DIR"
echo "アプリケーションを起動するには:"
echo "  open $INSTALL_DIR"
echo "または Finderでアプリケーションを開いてください。"

# ユーザーに確認して今すぐアプリケーションを起動
read -p "今すぐアプリケーションを起動しますか？ (y/n): " -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    open "$INSTALL_DIR"
fi 