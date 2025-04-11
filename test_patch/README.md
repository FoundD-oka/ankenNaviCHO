# 設定ファイル保存問題の解決パッチ

このパッチは、.appビルド時に設定ファイル（特に`model`, `api_key`などの設定）が正しく保存されない問題を解決します。

## 問題点

.appとして実行すると以下の設定が保存されません:
- model
- api_key
- deepseek_api_key
- max_items
- filter_prompt

一方、"crowdworks_password"などの他の設定は保存されていました。

## 原因

.appとして実行された場合、アプリケーションの実行パスが通常の実行時と異なります。.appビルド時は以下のような問題が発生していました:

1. カレントディレクトリが適切に設定されていない
2. 設定ファイルの保存先が書き込み権限のない場所になっている
3. app.pyから直接実行する場合とapp_launcher.pyを経由して実行する場合でパスの解決方法が異なる

## 解決策

このパッチでは以下の修正を行います:

1. アプリケーションの実行環境を検出する関数 `get_app_paths()` を追加
2. .appとして実行されている場合は、ユーザーのホームディレクトリに設定ファイルを保存するよう変更
   - `~/Library/Application Support/ankenNaviCHO/data/settings.json` に保存
3. 通常実行時は従来通り `crawled_data/settings.json` に保存

## 適用方法

1. app.pyの設定ファイル関連のコードを以下のように修正:

```python
# 設定ファイルのパス機能をインポート
from fix_settings_patch import get_app_paths

# 以下のコードを置き換え
# SETTINGS_FILE = 'crawled_data/settings.json'
app_paths = get_app_paths()
SETTINGS_FILE = str(app_paths['settings_file'])
```

2. app_launcher.pyも同様に修正:

```python
from fix_settings_patch import get_app_paths
app_paths = get_app_paths()
```

3. ディレクトリ作成ロジックも更新:
```python
def _ensure_directories(self):
    """必要なディレクトリが存在することを確認"""
    app_paths = get_app_paths()
    data_dir = app_paths['data_dir']
    
    directories = [
        data_dir,
        data_dir / 'logs',
        data_dir / 'drivers',
        data_dir / 'backups'
    ]
    
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"ディレクトリを作成しました: {directory}")
```

## 主な変更内容

- 環境に応じた設定ファイルのパスを返す `get_app_paths()` 関数の追加
- app.pyの SETTINGS_FILE 定義の更新
- クロスプラットフォーム対応のパス処理

これにより、.appビルド版でも設定ファイルが正しく保存されるようになります。 