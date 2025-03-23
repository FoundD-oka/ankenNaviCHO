# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('drivers', 'drivers'), ('.env', '.env'), ('chromedriver', 'chromedriver'), ('requirements.txt', 'requirements.txt'), ('chromedriver_manager.py', 'chromedriver_manager.py'), ('bulk_apply.py', 'bulk_apply.py'), ('crawler.py', 'crawler.py'), ('updater.py', 'updater.py'), ('supabase_stripe_handler.py', 'supabase_stripe_handler.py'), ('app.py', 'app.py')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SeleniumAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)
app = BUNDLE(
    exe,
    name='SeleniumAutomation.app',
    icon='icon.icns',
    bundle_identifier=None,
)
