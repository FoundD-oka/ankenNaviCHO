# SeleniumAutomation ワンクリックインストーラー

このドキュメントでは、SeleniumAutomationアプリケーションのインストール方法と使用方法について説明します。

## 前提条件

- macOS 10.14以上
- Python 3.7以上がインストールされていること
- Chromeブラウザがインストールされていること

## インストール方法

1. ターミナルを開きます
2. 以下のコマンドを実行してインストールスクリプトを実行します：

```bash
chmod +x simple_installer.sh
./simple_installer.sh
```

3. インストールプロセスに従って進めます。必要な場合はパスワードを入力してください。
4. インストールが完了すると、`/Applications` フォルダに `SeleniumAutomation.app` が作成されます。

## 起動方法

以下のいずれかの方法でアプリケーションを起動できます：

1. Finder から `/Applications/SeleniumAutomation.app` をダブルクリックします。
2. Launchpad から「SeleniumAutomation」を探して起動します。

## 主な機能

- **ポート自動検出**: デフォルトポート（8000）が使用中の場合、自動的に別のポートを検索します。
- **ChromeDriver自動管理**: ChromeDriverの設定と管理を自動的に行います。
- **エラー表示**: 問題が発生した場合、分かりやすいエラーメッセージを表示します。
- **ブラウザ自動起動**: アプリケーションの起動時に自動的にブラウザが開きます。

## トラブルシューティング

### アプリケーションが起動しない場合

1. ターミナルを開き、以下のコマンドを実行してログを確認します：

```bash
cat ~/Applications/SeleniumAutomation.app/Contents/Resources/logs/launcher.log
```

2. 依存関係の問題が考えられる場合は、以下のコマンドを実行してください：

```bash
cd ~/Applications/SeleniumAutomation.app/Contents/Resources
pip install -r requirements.txt
```

### ポートの競合が発生する場合

アプリケーションは自動的に利用可能なポートを検索しますが、手動で.envファイルを編集して別のポートを指定することもできます：

```bash
vim ~/Applications/SeleniumAutomation.app/Contents/Resources/.env
```

`PORT=` の値を変更して保存します。

### ChromeDriverの問題

ChromeDriverに問題がある場合は、以下の手順で更新できます：

1. アプリケーションを起動し、ログインします。
2. 設定ページで「ChromeDriverを更新」ボタンをクリックします。

## アンインストール方法

アプリケーションを削除するには、以下のコマンドを実行します：

```bash
rm -rf ~/Applications/SeleniumAutomation.app
rm -f /Applications/SeleniumAutomation.app
```

## 注意事項

- このアプリケーションは開発者モードで実行されるため、初回起動時にはmacOSのセキュリティ警告が表示される場合があります。
- アプリケーションのデータは `~/Applications/SeleniumAutomation.app/Contents/Resources` に保存されます。 