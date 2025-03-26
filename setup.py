#!/usr/bin/env python3
from setuptools import setup

APP = ['app_launcher.py']
DATA_FILES = [
    'templates',
    'static',
    'drivers',
    '.env',
    'chromedriver',
    'requirements.txt',
    'chromedriver_manager.py',
    'bulk_apply.py',
    'crawler.py',
    'updater.py',
    'supabase_stripe_handler.py',
    'app.py'
]

OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'flask',
        'flask_bootstrap',
        'flask_login',
        'flask_wtf',
        'selenium',
        'python_dotenv',
        'dotenv',
        'supabase',
        'pandas',
        'bs4',
        'requests',
        'apscheduler',
        'loguru',
        'semver',
        'zipfile36',
        'jinja2',
        'werkzeug',
        'wtforms',
        'itsdangerous',
        'openai',
        'numpy'
    ],
    'includes': [
        'queue',
        'threading',
        'socket',
        'json',
        'time',
        'logging',
        'traceback',
        'shutil'
    ],
    'excludes': ['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'PIL', 'PyInstaller'],
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'ankenNaviCHO',
        'CFBundleDisplayName': 'ankenNaviCHO',
        'CFBundleGetInfoString': '案件ナビCHOアプリケーション',
        'CFBundleIdentifier': 'com.anken.navicho',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 All rights reserved.',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False
    },
    'recipe_append': ['py2app.recipes.no_PIL']
}

setup(
    app=APP,
    name='ankenNaviCHO',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 