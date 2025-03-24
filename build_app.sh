#!/bin/bash

# エラーが発生したら終了
set -e

# 古いビルドを削除
echo "古いビルドを削除しています..."
rm -rf build dist
rm -rf *.app

# 必要なパッケージをインストール
echo "必要なパッケージをインストールしています..."
pip install py2app pillow python-dotenv flask flask_bootstrap flask_login flask_wtf selenium supabase openai loguru semver

# アイコンが存在しない場合は作成
if [ ! -f icon.icns ]; then
    echo "アイコンを作成しています..."
    python create_icon.py
fi

# アプリケーションの実行スクリプトを作成
cat > run_standalone.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

cd "$RESOURCES_DIR"
./python app_launcher.py
EOF

# アプリケーションをビルド
echo "Py2Appでアプリケーションをビルドしています..."
python setup.py py2app --packages=python_dotenv,flask,flask_bootstrap,flask_login,flask_wtf,selenium,supabase,openai,loguru,semver --includes=dotenv

# 実行ファイルに実行権限を付与
chmod +x dist/ankenNaviCHO.app/Contents/MacOS/run_standalone.sh

# 独自の実行スクリプトを上書き
cp run_standalone.sh dist/ankenNaviCHO.app/Contents/MacOS/run
chmod +x dist/ankenNaviCHO.app/Contents/MacOS/run

# 必要なディレクトリを作成
mkdir -p dist/ankenNaviCHO.app/Contents/Resources/logs
mkdir -p dist/ankenNaviCHO.app/Contents/Resources/crawled_data
mkdir -p dist/ankenNaviCHO.app/Contents/Resources/backups
touch dist/ankenNaviCHO.app/Contents/Resources/logs/app.log

# ビルドしたアプリケーションをカレントディレクトリにコピー
cp -r dist/ankenNaviCHO.app .

echo "ビルドが完了しました: $(pwd)/ankenNaviCHO.app"

# 確認
echo "ビルドしたアプリケーションを実行しますか？(y/n)"
read -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "ankenNaviCHO.app"
fi 