#!/usr/bin/env python3
"""
ankenNaviCHO スタンドアロンランチャー
conda環境に依存しない実行モジュール
"""
import os
import sys
import subprocess
import platform
import shutil

def main():
    """
    アプリケーションのメインエントリーポイント
    """
    print("ankenNaviCHO スタンドアロンランチャーを起動しています...")
    
    # 必要なパッケージをインストール
    required_packages = [
        "python-dotenv",
        "flask",
        "flask_bootstrap",
        "flask_login",
        "flask_wtf",
        "selenium",
        "supabase",
    ]
    
    # 現在のスクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 必要なディレクトリを作成
    os.makedirs(os.path.join(script_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "crawled_data"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "backups"), exist_ok=True)
    
    # アプリケーションを起動
    try:
        app_path = os.path.join(script_dir, "app.py")
        if os.path.exists(app_path):
            # 環境変数を設定（必要に応じて）
            env = os.environ.copy()
            env["FLASK_APP"] = app_path
            
            # Flaskアプリケーションを起動
            subprocess.run([sys.executable, app_path], env=env)
        else:
            print(f"エラー: {app_path} が見つかりません")
            sys.exit(1)
    except Exception as e:
        print(f"アプリケーション起動中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 