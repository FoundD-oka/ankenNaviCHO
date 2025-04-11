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
        os.makedirs(app_data_dir, exist_ok=True)
        
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
        os.makedirs(data_dir, exist_ok=True)
        
        # 設定ファイルのパス
        settings_file = data_dir / 'settings.json'
        
        return {
            'bundle_dir': bundle_dir,
            'data_dir': data_dir,
            'settings_file': settings_file
        }

# main関数（テスト用）
def main():
    paths = get_app_paths()
    print(f"バンドルディレクトリ: {paths['bundle_dir']}")
    print(f"データディレクトリ: {paths['data_dir']}")
    print(f"設定ファイル: {paths['settings_file']}")

if __name__ == "__main__":
    main() 