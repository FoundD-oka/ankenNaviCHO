@echo off
setlocal
set PROJECT_ROOT=%~dp0..
set VENV_DIR=%PROJECT_ROOT%\.venv

if not exist "%VENV_DIR%" (
  echo [build] venv not found. Creating and installing PyInstaller
  python -m venv "%VENV_DIR%"
  call "%VENV_DIR%\Scripts\activate"
  pip install --upgrade pip
  pip install pyinstaller==6.13.0
  pip install pillow
  pip install -r "%PROJECT_ROOT%\requirements.txt"
) else (
  call "%VENV_DIR%\Scripts\activate"
  pip install --quiet --exists-action i pillow
  pip install --quiet --exists-action i -r "%PROJECT_ROOT%\requirements.txt"
)
set PYI=%VENV_DIR%\Scripts\pyinstaller.exe

REM --- icon conversion (.png -> .ico) ---
python convert_icon.py

%PYI% --noconfirm ank_nav.spec

if exist dist\ankenNaviCHO_win.exe (
  echo [DONE] dist\ankenNaviCHO_win.exe created.
) else (
  echo [ERROR] build failed.
  exit /b 1
)
endlocal
