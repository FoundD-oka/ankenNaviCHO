#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
app.pyの修正パッチサンプル
----------------------------
このファイルは、app.pyの設定ファイル保存機能を修正するためのサンプルコードです。
実際のapp.pyに以下の変更を適用してください。
"""

# app.pyの先頭付近に以下を追加
import os
import sys
from pathlib import Path
from fix_settings_patch import get_app_paths

# 以下のコードを検索して置き換え
"""
# 設定ファイルのパス
SETTINGS_FILE = 'crawled_data/settings.json'
"""

# 置き換え後のコード
"""
# アプリケーションパスを取得
app_paths = get_app_paths()

# 設定ファイルのパス
SETTINGS_FILE = str(app_paths['settings_file'])

# ログに出力
logger.info(f"設定ファイルパス: {SETTINGS_FILE}")
"""

# save_settings関数の修正例
"""
# 設定を保存
def save_settings(settings):
    # 親ディレクトリが存在することを確認
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    # プロンプトが更新された場合、prompt.txtも更新
    if 'filter_prompt' in settings:
        prompt_config = {
            'model': settings.get('model', '4o-mini'),
            'prompt': settings['filter_prompt'],
            'temperature': 0,
            'max_tokens': 100
        }
        
        # アプリケーションパスを取得
        prompt_file = os.path.join(os.path.dirname(SETTINGS_FILE), 'prompt.txt')
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompt_config, f, ensure_ascii=False, indent=2)
    
    # デバッグ情報を追加
    logger.info(f"設定を保存します: {SETTINGS_FILE}")
    logger.debug(f"保存する設定: {settings}")
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    
    logger.info("設定を保存しました")
"""

# load_settings関数の修正例
"""
# 設定を読み込む
def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    
    # 設定ファイルから読み込み
    if os.path.exists(SETTINGS_FILE):
        logger.info(f"設定ファイルを読み込みます: {SETTINGS_FILE}")
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                settings.update(loaded_settings)
                logger.debug(f"読み込んだ設定: {settings}")
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {str(e)}")
    else:
        logger.warning(f"設定ファイルが見つかりません: {SETTINGS_FILE}")
    
    # prompt.txtからフィルター設定を読み込み
    prompt_file = os.path.join(os.path.dirname(SETTINGS_FILE), 'prompt.txt')
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_config = json.load(f)
                settings['filter_prompt'] = prompt_config.get('prompt', '')
        except Exception as e:
            logger.error(f"prompt.txtの読み込みに失敗: {str(e)}")
    
    # SelfIntroduction.txtから自己紹介文を読み込み
    self_intro_file = os.path.join(os.path.dirname(SETTINGS_FILE), 'SelfIntroduction.txt')
    if os.path.exists(self_intro_file):
        try:
            with open(self_intro_file, 'r', encoding='utf-8') as f:
                settings['self_introduction'] = f.read()
        except Exception as e:
            logger.error(f"自己紹介文の読み込みに失敗: {str(e)}")
            settings['self_introduction'] = ''
    else:
        # SelfIntroduction.txtがない場合はデフォルトの自己紹介文を設定
        settings['self_introduction'] = ''
    
    return settings
""" 