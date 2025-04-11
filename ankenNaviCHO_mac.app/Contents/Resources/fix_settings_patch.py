#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from pathlib import Path

# アプリケーションパスの初期化
def get_app_paths():
    """アプリケーションの各種パスを取得"""
    # 実行環境がfrozenか（.appとして実行されているか）確認
    if getattr(sys, 'frozen', False):
        # .appとして実行されている場合
        if hasattr(sys, '_MEIPASS'):
            # PyInstallerの場合
            bundle_dir = Path(sys._MEIPASS)
        else:
            # py2appの場合
            bundle_dir = Path(os.path.dirname(os.path.dirname(sys.executable))) / 'Resources'
        
        # データディレクトリを設定（ユーザーのホームディレクトリ内）
        app_data_dir = Path(os.path.expanduser('~/Library/Application Support/ankenNaviCHO/data'))
        
        # 必要なディレクトリを作成
        ensure_app_directories(app_data_dir)
        
        # 設定ファイルのパス
        settings_file = app_data_dir / 'settings.json'
        
        return {
            'bundle_dir': bundle_dir,
            'data_dir': app_data_dir,
            'settings_file': settings_file
        }
    else:
        # 開発環境で実行されている場合
        bundle_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        data_dir = bundle_dir / 'crawled_data'
        
        # 必要なディレクトリを作成
        ensure_app_directories(data_dir)
        
        # 設定ファイルのパス
        settings_file = data_dir / 'settings.json'
        
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

# アプリケーションに必要なディレクトリを作成する関数
def ensure_app_directories(base_dir):
    """アプリケーションに必要なディレクトリを作成"""
    # ベースディレクトリを作成
    os.makedirs(base_dir, exist_ok=True)
    
    # 必要なサブディレクトリを作成
    subdirs = ['logs', 'drivers', 'backups', 'crawled_data']
    for subdir in subdirs:
        os.makedirs(base_dir / subdir, exist_ok=True)

# main関数（テスト用）
def main():
    """テスト用のメイン関数"""
    paths = get_app_paths()
    print(f"バンドルディレクトリ: {paths['bundle_dir']}")
    print(f"データディレクトリ: {paths['data_dir']}")
    print(f"設定ファイル: {paths['settings_file']}")
    
    # サブディレクトリの確認
    subdirs = ['logs', 'drivers', 'backups', 'crawled_data']
    for subdir in subdirs:
        subdir_path = paths['data_dir'] / subdir
        print(f"サブディレクトリ {subdir}: {'存在します' if subdir_path.exists() else '存在しません'}")

if __name__ == "__main__":
    main() 