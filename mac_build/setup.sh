#!/bin/bash
set -e

# This script is bundled into the .app and executed on first launch.
# It creates a venv inside the app bundle, installs dependencies,
# and writes a flag file to skip future setup runs.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$SCRIPT_DIR/.."  # Contents/MacOS → Contents
RES_DIR="$APP_ROOT/Resources"
VENV_DIR="$RES_DIR/venv"
SETUP_DONE_FLAG="$APP_ROOT/.setup_done"
REQ_FILE="$RES_DIR/requirements.txt"

if [ -f "$SETUP_DONE_FLAG" ]; then
  echo "[setup] already done"
  exit 0
fi

echo "[setup] creating venv at $VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

if [ -f "$REQ_FILE" ]; then
  echo "[setup] installing requirements"
  pip install --upgrade pip
  pip install -r "$REQ_FILE"
fi

deactivate

touch "$SETUP_DONE_FLAG"
echo "[setup] complete" 