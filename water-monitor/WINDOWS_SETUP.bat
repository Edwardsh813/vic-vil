@echo off
echo ============================================
echo Victorian Village Water Meter Registration
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Installing required packages...
pip install playwright

echo.
echo Installing browser...
playwright install chromium

echo.
echo ============================================
echo Setup complete! Now running registration...
echo ============================================
echo.

python register_accounts.py

pause
