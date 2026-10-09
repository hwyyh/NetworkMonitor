
@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo       NetworkMonitor EXE Builder
echo ======================================

python --version
if errorlevel 1 (
    echo Python not found.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 goto error

python -m pip install pyinstaller
if errorlevel 1 goto error

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name NetworkMonitor ^
    src\main.py

if errorlevel 1 goto error

echo.
echo Build successful!
echo EXE: dist\NetworkMonitor.exe
pause
exit /b 0

:error
echo Build failed.
pause
exit /b 1
