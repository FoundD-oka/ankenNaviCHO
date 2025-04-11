#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
from fix_settings_patch import get_app_paths

def test_app_paths():
    """アプリケーションパスのテスト"""
    print("=== アプリケーションパスのテスト ===")
    
    # パスを取得
    paths = get_app_paths()
    bundle_dir = paths['bundle_dir']
    data_dir = paths['data_dir']
    settings_file = paths['settings_file']
    
    # パスを表示
    print(f"バンドルディレクトリ: {bundle_dir}")
    print(f"データディレクトリ: {data_dir}")
    print(f"設定ファイル: {settings_file}")
    
    # データディレクトリが存在するか確認
    if data_dir.exists():
        print(f"データディレクトリが存在します: {data_dir}")
    else:
        print(f"データディレクトリが存在しません: {data_dir}")
        print("データディレクトリを作成します...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"データディレクトリを作成しました: {data_dir}")
    
    # サブディレクトリを作成
    subdirs = ['logs', 'drivers', 'backups', 'crawled_data']
    for subdir in subdirs:
        subdir_path = data_dir / subdir
        if not subdir_path.exists():
            subdir_path.mkdir(parents=True, exist_ok=True)
            print(f"サブディレクトリを作成しました: {subdir_path}")
        else:
            print(f"サブディレクトリが存在します: {subdir_path}")

def test_settings_io():
    """設定の保存と読み込みのテスト"""
    print("\n=== 設定の保存と読み込みのテスト ===")
    
    # パスを取得
    paths = get_app_paths()
    settings_file = paths['settings_file']
    
    # テスト用の設定
    test_settings = {
        'model': 'gpt-4o-test',
        'api_key': 'test-api-key',
        'deepseek_api_key': 'test-deepseek-key',
        'max_items': 42,
        'filter_prompt': 'テスト用のプロンプト',
        'self_introduction': 'テスト用の自己紹介',
        'crowdworks_email': 'test@example.com',
        'crowdworks_password': 'test-password'
    }
    
    # 設定を保存
    print(f"テスト設定を保存します: {settings_file}")
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(test_settings, f, ensure_ascii=False, indent=2)
    print("設定を保存しました")
    
    # 設定を読み込み
    print("設定を読み込みます")
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            loaded_settings = json.load(f)
        print("設定を読み込みました")
        
        # 設定内容を表示
        print("\n設定の内容:")
        for key, value in loaded_settings.items():
            print(f"  {key}: {value}")
        
        # 設定値が一致するか確認
        success = True
        for key, value in test_settings.items():
            if key not in loaded_settings or loaded_settings[key] != value:
                success = False
                print(f"❌ エラー: キー '{key}' の値が一致しません")
                print(f"  期待値: {value}")
                print(f"  実際値: {loaded_settings.get(key, '未設定')}")
        
        if success:
            print("\n✅ テスト成功: 設定値が正しく保存・読み込みされました")
    else:
        print(f"❌ エラー: 設定ファイルが見つかりません: {settings_file}")

def main():
    """メイン関数"""
    print("アプリケーション設定パスのテストを開始します")
    
    # アプリケーションパスのテスト
    test_app_paths()
    
    # 設定の保存と読み込みのテスト
    test_settings_io()
    
    print("\nテストが完了しました")

if __name__ == "__main__":
    main() 