#!/bin/bash
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ----------- venv 自動作成 & 有効化 -----------
VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "[build] venv が見つかりません。作成して PyInstaller をインストールします"
  python3 -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip
  pip install pyinstaller==6.13.0
  pip install pillow
else
  source "$VENV_DIR/bin/activate"
  pip install --quiet --exists-action i pillow || true
fi
PYI="$VENV_DIR/bin/pyinstaller"
# --------------------------------------------

echo "=== PyInstaller ==="
$PYI --noconfirm mac_build/ank_nav.spec  # spec を使用して .app を生成

# BUNDLE 出力先確認
APP_BUNDLE="dist/ankenNaviCHO_mac.app"
if [ ! -d "$APP_BUNDLE" ]; then
  echo "[ERROR] $APP_BUNDLE が見つかりません。PyInstaller の出力先を確認してください" >&2
  exit 1
fi

echo "=== 同梱ファイル追加 ==="
cp mac_build/setup.sh "$APP_BUNDLE/Contents/MacOS/setup"
chmod +x "$APP_BUNDLE/Contents/MacOS/setup"

echo "=== 事前セットアップ (venv 構築) ==="
bash mac_build/setup.sh

echo "=== Notarize & Zip ==="
cd dist

ditto -c -k --sequesterRsrc --keepParent \
      ankenNaviCHO_mac.app ankenNaviCHO_mac.zip

# notarize ステップは配布要件により省略可能です。
# オンライン初回起動前提であれば以下をコメントアウトしたままで問題ありません。

cd "$PROJECT_ROOT"

echo "=== 完了: dist/ankenNaviCHO_mac.zip を Google Drive へアップロードしてください ==="