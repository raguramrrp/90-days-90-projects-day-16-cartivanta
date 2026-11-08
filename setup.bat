@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo    CARTIVANTA - Retail Intelligence & Predictive Commerce Platform
echo    Setup and Environment Initialization
echo ======================================================================

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.10 - 3.12 and add it to your system PATH.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [*] Detected %PYTHON_VER%

:: 2. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment (.venv) already exists.
)

:: 3. Activate virtual environment & install requirements
echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [*] Installing dependencies from requirements.txt...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.

:: 4. Setup environment variables configuration
if not exist ".env" (
    echo [*] Generating .env from .env.example...
    copy .env.example .env >nul
    echo [OK] .env configuration file created.
) else (
    echo [OK] .env configuration file exists.
)

:: 5. Verify analytical database & Seed Operational Indian Retail Data
if not exist "data\cartivanta.db" (
    echo [*] Analytical database not detected. Initializing database pipeline...
    python -m etl.pipeline --sample --sample-size 25000 --sqlite
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] Quick ETL initialization encountered an issue. You can run ETL manually.
    ) else (
        echo [OK] Analytical database populated.
    )
) else (
    echo [OK] Analytical database (data\cartivanta.db) verified and ready.
)

echo [*] Initializing operational shop tables and Indian retail seed data...
python scripts/init_operational_db.py
python etl/seed_indian_shop.py
echo [OK] Operational shop and Indian retail demo data ready!

echo ======================================================================
echo  CARTIVANTA Setup Complete!
echo  Next steps:
echo    - Launch Web Analytics:  run.bat
echo    - Run Test Suite:        test.bat
echo ======================================================================

endlocal
