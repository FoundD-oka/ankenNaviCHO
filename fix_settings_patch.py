#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from pathlib import Path

def is_frozen() -> bool:
    """PyInstaller・py2appの両方を安全に検出"""
    return (
        hasattr(sys, "_MEIPASS") or                  # PyInstaller
        getattr(sys, "frozen", None) not in (None, False)  # py2app ほか
    )

# アプリケーションパスの初期化
def get_app_paths():
    """アプリケーションの各種パスを取得"""
    # 実行環境がfrozenか（.appとして実行されているか）確認
    if is_frozen():
        # .appとして実行されている場合
        if hasattr(sys, '_MEIPASS'):
            # PyInstallerの場合
            bundle_dir = Path(sys._MEIPASS)
        else:
            # py2appの場合
            bundle_dir = Path(os.path.dirname(os.path.dirname(sys.executable))) / 'Resources'
        
        # データディレクトリを設定
        if os.name == 'nt':
            base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            app_data_dir = base / 'ankenNaviCHO'
        else:
            app_data_dir = Path(os.path.expanduser('~/Library/Application Support/ankenNaviCHO'))
        
        # 必要なディレクトリを作成
        ensure_app_directories(app_data_dir)
        
        # 設定ファイルのパス
        settings_file = app_data_dir / 'crawled_data' / 'settings.json'
        
        return {
            'bundle_dir': bundle_dir,
            'data_dir': app_data_dir,
            'settings_file': settings_file
        }
    else:
        # 開発環境で実行されている場合
        bundle_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        # 開発環境ではルートディレクトリを基準としてパスを設定
        project_root = bundle_dir
        data_dir = project_root  # ルートディレクトリをデータディレクトリとして使用
        
        # 必要なディレクトリを作成（開発環境では特別な処理）
        ensure_dev_directories(project_root)
        
        # 設定ファイルのパス（crawled_dataディレクトリ内）
        settings_file = project_root / 'crawled_data' / 'settings.json'
        
        return {
            'bundle_dir': bundle_dir,
            'data_dir': data_dir,
            'settings_file': settings_file
        }

# 環境変数からデータディレクトリを取得する関数
def get_data_dir_from_env():
    """環境変数からデータディレクトリを取得"""
    env_data_dir = os.environ.get('APP_DATA_DIR')
    if env_data_dir:
        data_dir = Path(env_data_dir)
        ensure_app_directories(data_dir)
        return data_dir
    
    # 環境変数にない場合はアプリケーションパスから取得
    return get_app_paths()['data_dir']

# アプリケーションに必要なディレクトリを作成する関数（本番用）
def ensure_app_directories(base_dir):
    """アプリケーションに必要なディレクトリを作成（本番環境用）"""
    # ベースディレクトリを作成
    os.makedirs(base_dir, exist_ok=True)
    
    # 必要なサブディレクトリを作成
    subdirs = ['logs', 'drivers', 'backups', 'crawled_data']
    for subdir in subdirs:
        subdir_path = base_dir / subdir
        os.makedirs(subdir_path, exist_ok=True)
        logging.info(f"ディレクトリを作成しました: {subdir_path}")

# 開発環境用のディレクトリ作成関数（クローリング関連とログなどを分離）
def ensure_dev_directories(project_root):
    """開発環境に必要なディレクトリを作成（各ディレクトリをルートに配置）"""
    # 基本ディレクトリ（ルート直下）
    root_dirs = ['logs', 'drivers', 'backups']
    for dir_name in root_dirs:
        dir_path = project_root / dir_name
        os.makedirs(dir_path, exist_ok=True)
        logging.info(f"開発用ディレクトリを作成しました: {dir_path}")
    
    # データ用ディレクトリ（crawled_data）
    data_path = project_root / 'crawled_data'
    os.makedirs(data_path, exist_ok=True)
    logging.info(f"開発用データディレクトリを作成しました: {data_path}")

# main関数（テスト用）
def main():
    """テスト用のメイン関数"""
    # ロガー設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    paths = get_app_paths()
    print(f"バンドルディレクトリ: {paths['bundle_dir']}")
    print(f"データディレクトリ: {paths['data_dir']}")
    print(f"設定ファイル: {paths['settings_file']}")
    
    # サブディレクトリの確認
    if getattr(sys, 'frozen', False):
        # 本番環境の場合
        subdirs = ['logs', 'drivers', 'backups', 'crawled_data']
        for subdir in subdirs:
            subdir_path = paths['data_dir'] / subdir
            print(f"サブディレクトリ {subdir}: {'存在します' if subdir_path.exists() else '存在しません'}")
    else:
        # 開発環境の場合
        root_dirs = ['logs', 'drivers', 'backups']
        data_dir = paths['data_dir']
        for dir_name in root_dirs:
            dir_path = data_dir / dir_name
            print(f"ルートディレクトリ {dir_name}: {'存在します' if dir_path.exists() else '存在しません'}")
        
        # crawled_dataディレクトリ
        crawled_data_path = data_dir / 'crawled_data'
        print(f"データディレクトリ crawled_data: {'存在します' if crawled_data_path.exists() else '存在しません'}")

if __name__ == "__main__":
    main() 