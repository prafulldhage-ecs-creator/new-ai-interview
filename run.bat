@echo off
setlocal enabledelayedexpansion

:: Always set working directory to this script's directory
cd /d "%~dp0"

echo ===================================================
echo   InterviewIQ - AI Placement Interview Simulator
echo ===================================================
echo.

:: 1. Check Python availability
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [INFO] Detected: %PYTHON_VER%

:: 2. Check / Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    set NEED_INSTALL=1
) else (
    set NEED_INSTALL=0
)

:: 3. Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Could not find venv\Scripts\activate.bat.
    pause
    exit /b 1
)

:: 4. Install requirements when needed
if not exist "venv\.installed" (
    set NEED_INSTALL=1
)

if "%NEED_INSTALL%"=="1" (
    echo [INFO] Installing required dependencies from requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements. Please check error logs.
        pause
        exit /b 1
    )
    echo installed > venv\.installed
    echo [OK] Dependencies installed.
) else (
    echo [INFO] Dependencies already installed.
)

:: 5. Create default .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating default .env from .env.example...
        copy .env.example .env >nul
    )
)

:: 6. Apply database migrations
echo [INFO] Applying database migrations...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Database migrations failed.
    pause
    exit /b 1
)

:: 7. Start the Django development server
echo.
echo ===================================================
echo [SUCCESS] Starting InterviewIQ server at http://127.0.0.1:8000/
echo Opening default web browser...
echo Press CTRL+C to stop the server.
echo ===================================================
echo.
start http://127.0.0.1:8000/
python manage.py runserver 127.0.0.1:8000

pause
