@echo off
setlocal

echo.
echo ========================================
echo   ShanuFx Downloader - Build System
echo ========================================
echo.

:: 1. Build the standalone executable using PyInstaller
echo [1/2] Building standalone executable...
pip install -r requirements.txt
python -m PyInstaller ShanuFxDownloader.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b %ERRORLEVEL%
)

:: 2. Build the installer using Inno Setup
echo [2/2] Building setup.exe (Inno Setup)...

:: Try to find ISCC.exe in default locations
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "%ISCC_PATH%" (
    echo [WARNING] Inno Setup Compiler (ISCC.exe) not found at default locations.
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo Or manually run ISCC on installer_script.iss
    exit /b 1
)

echo Using Inno Setup: "%ISCC_PATH%"
"%ISCC_PATH%" installer_script.iss

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================
echo   BUILD SUCCESSFUL!
echo   Installer: Output\ShanuFxDownloader_Setup.exe
echo ========================================
pause
