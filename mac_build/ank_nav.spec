# -*- mode: python ; coding: utf-8 -*-

# PyInstaller spec file for ankenNaviCHO_mac
# ビルドコマンド例:
#   pyinstaller mac_build/ank_nav.spec

# NOTE: 必要に応じて pathex や datas のパスを調整してください

block_cipher = None

import os

# PyInstaller が spec を実行する際は __file__ が未定義のため、
# カレントディレクトリを基準にプロジェクトルートを取得する。
project_root = os.getcwd()  # build_app.sh ではプロジェクトルートで実行している

# エントリポイント: app.py（必要に応じて変更）
entry_script = os.path.join(project_root, 'app.py')

# バンドルに含める追加データ (相対パス, アプリ内配置先)
extra_datas = [
    (os.path.join(project_root, 'static'), 'static'),
    (os.path.join(project_root, 'templates'), 'templates'),
    (os.path.join(project_root, 'requirements.txt'), '.'),
]

# アイコンファイル (.icns) がある場合は指定
icon_file = os.path.join(project_root, 'original_icon.png')  # 画像から .icns を作っているなら変更

# ------------------------------ Spec Definition ------------------------------

a = Analysis(
    [entry_script],
    pathex=[project_root],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ankenNaviCHO_mac',
    bundle_identifier='com.anken.navicho',
    icon=icon_file,
    console=False,
    windowed=True,
)

app = BUNDLE(
    exe,
    name='ankenNaviCHO_mac.app',
    icon=icon_file,
    bundle_identifier='com.anken.navicho',
) 