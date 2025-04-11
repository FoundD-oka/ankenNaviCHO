#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
app_launcher.pyの修正パッチサンプル
----------------------------------
このファイルは、app_launcher.pyの設定ファイル保存機能を修正するためのサンプルコードです。
実際のapp_launcher.pyに以下の変更を適用してください。
"""

# app_launcher.pyの先頭近くに以下を追加
"""
from fix_settings_patch import get_app_paths
"""

# _get_bundle_dir メソッドの代わりにget_app_pathsを使用
"""
def __init__(self):
    self.app_process = None
    self.port = 8000  # デフォルトポート
    
    # アプリケーションパスを取得
    self.app_paths = get_app_paths()
    self.bundle_dir = self.app_paths['bundle_dir']
    self.data_dir = self.app_paths['data_dir']
    
    self.env_file = self.bundle_dir / '.env'
    logger.info(f"アプリケーションを初期化しています。バンドルディレクトリ: {self.bundle_dir}")
    logger.info(f"データディレクトリ: {self.data_dir}")
    
    self.initialize_environment()
"""

# _ensure_directories メソッドを修正
"""
def _ensure_directories(self):
    """必要なディレクトリが存在することを確認"""
    directories = [
        self.data_dir,
        self.data_dir / 'logs',
        self.data_dir / 'drivers',
        self.data_dir / 'backups'
    ]
    
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"ディレクトリを作成しました: {directory}")
"""

# start_app メソッドを修正して新しいパスを環境変数に設定
"""
def start_app(self):
    """アプリケーションを起動"""
    try:
        # 環境変数から直接ポートを取得（シェルスクリプトからの設定を優先）
        env_port = os.environ.get('PORT')
        if env_port:
            try:
                port = int(env_port)
                logger.info(f"環境変数から直接ポートを取得しました: {port}")
            except ValueError:
                logger.warning(f"環境変数のポート番号が無効です: {env_port}")
                port = self.find_available_port()
        else:
            # 使用可能なポートを見つける
            port = self.find_available_port()
        
        if not port:
            raise Exception("使用可能なポートが見つかりませんでした")
        
        # .envファイルのポート設定を更新
        self.update_port_in_env(port)
        
        # アプリケーションの起動コマンド
        app_path = self.bundle_dir / 'app.py'
        logger.info(f"アプリケーションパス: {app_path}")
        
        # 環境変数を設定
        env = os.environ.copy()
        env['PORT'] = str(port)
        env['FLASK_ENV'] = 'production'  # 開発モードを無効化
        env['FLASK_DEBUG'] = '0'         # デバッグモードを無効化
        env['PYTHONWARNINGS'] = 'ignore::urllib3.exceptions.NotOpenSSLWarning'  # urllib3の警告を抑制
        
        # データディレクトリを環境変数に設定
        env['APP_DATA_DIR'] = str(self.data_dir)
        logger.info(f"データディレクトリを環境変数に設定: {env['APP_DATA_DIR']}")
        
        cmd = [
            sys.executable,
            str(app_path)
        ]
        
        # アプリケーションを起動
        logger.info(f"アプリケーションを起動します: {' '.join(cmd)}")
        self.app_process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.bundle_dir)
        )
        
        # サーバー起動を待機
        self._wait_for_server(port)
        
        # ブラウザでアプリケーションを開く
        self._open_browser(port)
        
        # 標準出力とエラー出力をログに記録するスレッドを開始
        threading.Thread(target=self._log_output, args=(self.app_process.stdout, "stdout")).start()
        threading.Thread(target=self._log_output, args=(self.app_process.stderr, "stderr")).start()
        
        # プロセスの完了を待機
        self.app_process.wait()
""" 