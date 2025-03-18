#!/bin/bash

# エラーが発生したら終了
set -e

# 古いビルドを削除
echo "古いビルドを削除しています..."
rm -rf build dist
rm -rf "YourAppName.app"

# 必要なパッケージをインストール
echo "必要なパッケージをインストールしています..."
pip install -r requirements.txt
pip install py2app pillow

# アイコンファイルが存在しない場合は作成
if [ ! -f "icon.icns" ]; then
    echo "アイコンを作成しています..."
    python create_icon.py
fi

# アプリケーションをビルド
echo "アプリケーションをビルドしています..."
python setup.py py2app

# 出来上がったアプリを適切な場所にコピー
echo "アプリケーションをコピーしています..."
cp -R "dist/YourAppName.app" .

echo "ビルドが完了しました！"
echo "アプリケーション: $(pwd)/YourAppName.app" 