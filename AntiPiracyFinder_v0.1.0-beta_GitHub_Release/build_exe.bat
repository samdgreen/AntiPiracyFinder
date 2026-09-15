@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo AntiPiracy Finder v0.1.0-beta EXE Builder
echo ==========================================
echo.

python -m pip install --upgrade pip
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist AntiPiracyFinder.spec del /q AntiPiracyFinder.spec

echo.
echo Building Windows EXE...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "AntiPiracyFinder" ^
  --collect-all selenium ^
  --hidden-import selenium.webdriver.edge.webdriver ^
  --hidden-import selenium.webdriver.edge.service ^
  --hidden-import selenium.webdriver.edge.options ^
  app.py

if errorlevel 1 goto :error

echo.
echo ==========================================
echo Build complete:
echo dist\AntiPiracyFinder.exe
echo ==========================================
pause
exit /b 0

:error
echo.
echo Build failed. Please review the error above.
pause
exit /b 1
