# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))
entry_script = os.path.join(project_root, 'app_launcher.py')
extra_datas = [
    (os.path.join(project_root, 'static'), 'static'),
    (os.path.join(project_root, 'templates'), 'templates'),
    (os.path.join(project_root, 'requirements.txt'), '.'),
    (os.path.join(project_root, '.env'), '.')
]
icon_file = os.path.join(project_root, 'original_icon.ico')

a = Analysis([
    entry_script,
], pathex=[project_root], binaries=[], datas=extra_datas,
    hiddenimports=[
        'supabase',
        'flask_login',
        'semver',
        'flask_bootstrap',
        'flask_wtf',
        'psutil',
        'openai',
        'atexit',
        'msvcrt',
        'chromedriver_manager'
    ],
    hookspath=[], runtime_hooks=[], excludes=[], win_no_prefer_redirects=False,
    win_private_assemblies=False, cipher=block_cipher, noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
          name='ankenNaviCHO_win',
          debug=False, bootloader_ignore_signals=False,
          strip=False, upx=True, console=True,
          icon=icon_file)
