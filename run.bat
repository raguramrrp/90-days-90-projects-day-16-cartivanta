@echo off
setlocal

echo ======================================================================
echo    CARTIVANTA - Retail Shop Management, Billing ^& Intelligence Platform
echo    Run Your Shop. Track Your Stock. Understand Your Profit.
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Running setup.bat first...
    call setup.bat
    if %ERRORLEVEL% neq 0 exit /b 1
)

call .venv\Scripts\activate.bat

set PYTHONPATH=.

echo [*] Starting Cartivanta Retail Platform Server...
echo [*] Retail Workstation:    http://127.0.0.1:8000
echo [*] Billing / POS:          http://127.0.0.1:8000/billing
echo [*] Products Catalog:       http://127.0.0.1:8000/products
echo [*] Stock ^& Inventory:     http://127.0.0.1:8000/stock
echo [*] Customers ^& Khata:     http://127.0.0.1:8000/customers
echo [*] Expenses ^& Profit:     http://127.0.0.1:8000/expenses
echo [*] Discounts & Offers:     http://127.0.0.1:8000/discounts
echo [*] Business Insights:      http://127.0.0.1:8000/insights
echo [*] Interactive API Docs:   http://127.0.0.1:8000/docs
echo [*] Default Login:          Owner: admin / admin123  ^|  Cashier: cashier / cashier123
echo [*] Press CTRL+C to terminate the application.
echo ======================================================================

uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload

endlocal
