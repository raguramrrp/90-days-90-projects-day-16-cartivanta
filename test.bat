@echo off
setlocal

echo ======================================================================
echo    CARTIVANTA - Test Suite Runner
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Running setup.bat first...
    call setup.bat
    if %ERRORLEVEL% neq 0 exit /b 1
)

call .venv\Scripts\activate.bat

set PYTHONPATH=.

echo [*] Executing Pytest test suite with coverage...
pytest -v tests/ --cov=. --cov-report=term-missing

if %ERRORLEVEL% neq 0 (
    echo [FAIL] Test suite failed!
    exit /b %ERRORLEVEL%
) else (
    echo [PASS] All test assertions completed successfully!
)

endlocal
