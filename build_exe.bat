@echo off
setlocal
title AntiPiracyReporter Builder

echo ========================================
echo AntiPiracyReporter Windows EXE Builder
echo ========================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 goto :python_error

echo.
echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :install_error

echo.
echo [3/4] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist AntiPiracyReporter.spec del /q AntiPiracyReporter.spec

echo.
echo [4/4] Building EXE...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name AntiPiracyReporter --hidden-import=openpyxl --hidden-import=pyperclip app.py
if errorlevel 1 goto :build_error

echo.
echo ========================================
echo BUILD SUCCESS
echo EXE location:
echo dist\AntiPiracyReporter.exe
echo ========================================
echo.
pause
exit /b 0

:python_error
echo.
echo ERROR: Python was not found.
pause
exit /b 1

:install_error
echo.
echo ERROR: Dependency installation failed.
pause
exit /b 1

:build_error
echo.
echo ERROR: PyInstaller build failed.
pause
exit /b 1
