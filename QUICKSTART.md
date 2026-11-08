# CARTIVANTA — Quickstart Guide
### Retail Shop Management, Billing (POS) & Business Intelligence Platform
> **Run Your Shop. Track Your Stock. Understand Your Profit.**

---

## 1. Prerequisites

- **Operating System**: Windows 10 or 11 (64-bit)
- **Python**: Version 3.10, 3.11, or 3.12 installed and on `PATH`
- **Database**: Zero external dependencies! Runs out of the box on high-performance SQLite WAL mode (`data/cartivanta.db`) with optional PostgreSQL support via `.env`.

---

## 2. One-Click Automated Setup

Open Command Prompt or PowerShell in the project directory:

```cmd
cd "D:\90 days\90-days-90-projects-day-16-cartivanta"
setup.bat
```

The script will automatically:
1. Verify Python 3.10–3.12.
2. Create the virtual environment (`.venv`).
3. Install all required dependencies from `requirements.txt`.
4. Create `.env` configuration file.
5. Initialize the 16 operational shop management tables in `data/cartivanta.db`.
6. Seed realistic Indian retail products (Aashirvaad Atta, Fortune Oil, Tata Salt, Basmati Rice, Amul Butter, Maggi Noodles, Dettol Soap, etc.), suppliers, sample Khata customer accounts, and default credentials.

---

## 3. Launching the Application

Start the local server with one click:

```cmd
run.bat
```

Open your browser to:
- **Shopkeeper Dashboard (Home)**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Billing / POS Terminal**: [http://127.0.0.1:8000/billing](http://127.0.0.1:8000/billing)
- **Products Catalog & Margins**: [http://127.0.0.1:8000/products](http://127.0.0.1:8000/products)
- **Stock & Inventory**: [http://127.0.0.1:8000/stock](http://127.0.0.1:8000/stock)
- **Purchases & Suppliers**: [http://127.0.0.1:8000/purchases](http://127.0.0.1:8000/purchases)
- **Customers & Khata (Udhaar)**: [http://127.0.0.1:8000/customers](http://127.0.0.1:8000/customers)
- **Expenses & Net Real Profit**: [http://127.0.0.1:8000/expenses](http://127.0.0.1:8000/expenses)
- **Festive Offers & Campaigns**: [http://127.0.0.1:8000/campaigns](http://127.0.0.1:8000/campaigns)
- **Reports & P&L Statements**: [http://127.0.0.1:8000/reports](http://127.0.0.1:8000/reports)
- **Historical Benchmark Insights**: [http://127.0.0.1:8000/insights](http://127.0.0.1:8000/insights)
- **Interactive API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Default Login Accounts

| Role | Username | Password | Permitted Features |
| :--- | :--- | :--- | :--- |
| **Owner** | `admin` | `admin123` | **Full access**: Purchase costs, profit margins, supplier khata, operating expenses, financial reports, cashier accounts, settings. |
| **Cashier** | `cashier` | `cashier123` | **Counter access**: Fast POS billing, barcode scan, selling price, available stock, customer khata. *Purchase prices, profits, and expense records are confidential and hidden.* |

> **Pro Tip**: Use the quick role toggle button in the top navigation bar or go to `/switch-role` to instantly swap between Owner and Cashier for paired review!

---

## 5. Running the Verification Test Suite

Run the complete automated test suite (20 tests covering both operational retail workflows and historical machine learning models):

```cmd
test.bat
```

Or via python:

```cmd
.\.venv\Scripts\python -m pytest -v
```

Expected result:
```
====================== 20 passed in 24.10s =======================
```
