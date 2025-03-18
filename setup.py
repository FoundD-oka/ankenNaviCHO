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
        'dotenv',
        'supabase',
        'openai',
        'pandas',
        'bs4',
        'requests',
        'apscheduler',
        'loguru',
        'semver',
        'zipfile36'
    ],
    'site_packages': True,
    'resources': DATA_FILES,
    'plist': {
        'CFBundleName': 'YourAppName',
        'CFBundleDisplayName': 'YourAppName',
        'CFBundleGetInfoString': 'ワンクリックで起動するSelenium自動化アプリ',
        'CFBundleIdentifier': 'com.yourcompany.youappname',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 YourCompany. All rights reserved.',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False
    },
    'iconfile': 'icon.icns'
}

setup(
    app=APP,
    name='YourAppName',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 