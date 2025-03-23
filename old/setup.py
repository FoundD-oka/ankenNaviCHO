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
        'itsdangerous'
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
    'excludes': ['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'SeleniumAutomation',
        'CFBundleDisplayName': 'SeleniumAutomation',
        'CFBundleGetInfoString': 'Selenium自動化アプリケーション',
        'CFBundleIdentifier': 'com.selenium.automation',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 All rights reserved.',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False
    }
}

setup(
    app=APP,
    name='SeleniumAutomation',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 