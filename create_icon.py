#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont
import tempfile
import shutil

def create_icon():
    """
    シンプルなアイコンを作成し、.icnsファイルに変換
    """
    # アイコンサイズのリスト (macOS用)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # テンポラリディレクトリを作成
    iconset_dir = os.path.join('temp_icons', 'AppIcon.iconset')
    os.makedirs(iconset_dir, exist_ok=True)
    
    # 各サイズのアイコンを生成
    for size in sizes:
        # キャンバスを作成
        img = Image.new('RGBA', (size, size), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 背景の円を描画
        circle_size = size * 0.9
        circle_pos = (size - circle_size) / 2
        draw.ellipse(
            [(circle_pos, circle_pos), 
             (circle_pos + circle_size, circle_pos + circle_size)], 
            fill=(65, 105, 225, 255)  # ロイヤルブルー
        )
        
        # テキストを描画（サイズに応じてフォントサイズを調整）
        font_size = int(size * 0.5)
        try:
            # 標準のシステムフォントを使用
            font = ImageFont.truetype("Arial.ttf", font_size)
        except IOError:
            # フォントが見つからない場合はデフォルトフォントを使用
            font = ImageFont.load_default()
        
        # テキストを中央に配置
        text = "S"
        try:
            if hasattr(draw, 'textsize'):
                text_width, text_height = draw.textsize(text, font=font)
            elif hasattr(font, 'getsize'):
                text_width, text_height = font.getsize(text)
            else:
                # Pillow 9.2.0以降
                left, top, right, bottom = font.getbbox(text)
                text_width, text_height = right - left, bottom - top
        except Exception as e:
            print(f"テキストサイズの取得に失敗しました: {e}")
            # デフォルト値を使用
            text_width, text_height = size // 4, size // 4
        
        position = ((size - text_width) / 2, (size - text_height) / 2)
        
        # テキストを描画
        draw.text(position, text, fill=(255, 255, 255, 255), font=font)
        
        # 画像を保存
        normal_filename = os.path.join(iconset_dir, f'icon_{size}x{size}.png')
        retina_filename = os.path.join(iconset_dir, f'icon_{size//2}x{size//2}@2x.png')
        
        img.save(normal_filename)
        
        # Retinaディスプレイ用のアイコンも保存（サイズが適切な場合）
        if size > 16:
            img.save(retina_filename)
    
    # macOS特有のファイル命名規則に変更
    for size in [16, 32, 64, 128, 256, 512]:
        src = os.path.join(iconset_dir, f'icon_{size}x{size}.png')
        dst = os.path.join(iconset_dir, f'icon_{size}x{size}.png')
        if os.path.exists(src):
            os.rename(src, dst)
        
        src_retina = os.path.join(iconset_dir, f'icon_{size//2}x{size//2}@2x.png')
        dst_retina = os.path.join(iconset_dir, f'icon_{size//2}x{size//2}@2x.png')
        if os.path.exists(src_retina):
            os.rename(src_retina, dst_retina)
    
    # iconutilコマンドを使用してicnsファイルに変換
    try:
        subprocess.run([
            'iconutil', 
            '-c', 'icns', 
            iconset_dir,
            '-o', 'icon.icns'
        ], check=True)
        print(f"アイコンが正常に作成されました: {os.path.abspath('icon.icns')}")
    except subprocess.CalledProcessError as e:
        print(f"icnsファイルの作成中にエラーが発生しました: {e}")
        return False
    except FileNotFoundError:
        print("iconutilコマンドが見つかりません。macOS環境でのみ実行できます。")
        return False
    
    return True

if __name__ == "__main__":
    create_icon() 