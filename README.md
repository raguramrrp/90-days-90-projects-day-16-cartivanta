# CARTIVANTA
## Retail Shop Management, Billing (POS) & Business Intelligence Platform

<div align="center">

```
   ____    _    ____ _____ _____     ___    _   _ _____  _    
  / ___|  / \  |  _ \_   _|_ _\ \   / / \  | \ | |_   _|/ \   
 | |     / _ \ | |_) || |  | | \ \ / / _ \ |  \| | | | / _ \  
 | |___ / ___ \|  _ < | |  | |  \ V / ___ \| |\  | | |/ ___ \ 
  \____/_/   \_\_| \_\|_| |___|  \_/_/   \_\_| \_| |_/_/   \_\
```

**Run Your Shop. Track Your Stock. Understand Your Profit.**  
*A commercial-grade, intuitive retail operating system designed for small and medium-sized Indian retail stores.*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite WAL / PostgreSQL](https://img.shields.io/badge/Database-SQLite%20WAL%20%2F%20PostgreSQL-4169E1?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Currency: INR](https://img.shields.io/badge/Currency-INR%20(%E2%82%B9)-10B981?style=for-the-badge)](https://en.wikipedia.org/wiki/Indian_rupee)
[![Tests: Passed](https://img.shields.io/badge/Tests-Passed%20(100%25)-059669?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

[Quickstart Guide](QUICKSTART.md) • [Architecture Guide](docs/ARCHITECTURE.md) • [User Manual](docs/USER_GUIDE.md) • [Interactive POS](http://127.0.0.1:8000/billing)

</div>

---

## 1. Product Identity & Overview

**CARTIVANTA** is a complete, portfolio-grade retail management, billing, and business intelligence platform designed specifically for small-to-medium Indian retail businesses, including:
- **Kirana & Grocery stores**
- **Supermarkets & Provision shops**
- **Stationery & Bookstores**
- **Apparel & General merchandise**
- **Electronics & Daily hardware stores**

### Primary Design Principle
> **"A shopkeeper who has never used business software should be able to understand and operate the application without training."**

- **Simple Language Everywhere:** Technical terms have been replaced with everyday shopkeeper language (e.g. *Sales* instead of *Revenue*, *Estimated Profit* instead of *Gross Profit*, *Stock* instead of *Inventory*, *Customer Groups* instead of *Customer Segmentation*, *Expected Sales* instead of *Demand Forecasting*).
- **Light Theme & Restrained Visuals:** Clean warm background (`#F8FAFC`), crisp white content surfaces, restrained emerald teal accents (`#059669`), and dark neutral text (`#0F172A`). Zero purple gradients, zero neon effects, and no dark mode by default.
- **Consistent Currency Discipline:** The platform operates consistently in **Indian Rupee (₹)** across all operational modules, POS billing, stock valuations, expenses, and advanced business insights.

---

## 2. Platform Architecture

```
+--------------------------------------------------------------------------------------------------+
|                                    CARTIVANTA RETAIL PLATFORM                                    |
|                       "Run Your Shop. Track Your Stock. Understand Your Profit."                 |
+--------------------------------------------------------------------------------------------------+
|  [Home]  [Billing (POS)]  [Products]  [Stock]  [Purchases]  [Khata/Customers]  [Expenses]  ...   |
+--------------------------------------------------------------------------------------------------+
|  OPERATIONAL RETAIL STORE ENGINE (INR ₹)           |  ADVANCED BUSINESS INSIGHTS ENGINE (INR ₹)  |
|  - Real-time POS Billing with Barcode & GST        |  - 1.029M Historical Commerce Dataset       |
|  - Atomic Stock Deduction & Low-Stock Alerts       |  - ML Demand Forecasting (WAPE / MAE)       |
|  - Purchase Inward & Supplier Khata                |  - K-Means Customer RFM Segmentation        |
|  - Customer Credit (Udhaar) Ledger & Repayment     |  - Festive Demand Uplift Simulator          |
|  - Operating Expenses & Net Real Profit            |  - Data Quality Auditing                    |
|  - Role-Based Access: Owner vs Cashier (RBAC)      |  - Normalized in Indian Rupee (₹)           |
+--------------------------------------------------------------------------------------------------+
```

---

## 3. Core Operational Modules

### Module 1: Home — Shopkeeper Daily Dashboard
Answers the five immediate daily questions:
1. *How much did I sell today?* (Today's Sales in ₹)
2. *How much profit did I approximately make?* (Estimated Profit in ₹, Owner only)
3. *What products are running out?* (Low stock count & 1-click reorder link)
4. *Which products are selling the most?* (Top 5 items today)
5. *What needs my attention?* (Unpaid customer credit, supplier balance, low stock)
- Real-time payment method breakdown: Cash vs UPI vs Card vs Udhaar.
- Recent bills table with instant receipt re-printing.

### Module 2: Billing / POS — Fast Cashier Workstation
- Barcode input with auto-focus and hardware scanner support (Press Enter to add item).
- Category quick pills (Atta & Rice, Cooking Oils, Dairy, Snacks, Spices, Beverages, Personal Care, Stationery).
- Active Cart with quantity steppers, item-level discounts, GST auto-calculation, and bill-level discount.
- Multi-mode payment: Cash (with auto-change calculator), UPI (with visual QR code simulation and reference input), Card, and Udhaar / Credit.
- **Atomic Stock Deduction:** Database transaction decrements stock, records `stock_movements`, and generates printable receipt.
- **Printable Receipts:** 80mm thermal receipt format and standard A4 invoice layouts.

### Module 3: Products Catalog & Margins
- Complete catalog view with live search by name, brand, or barcode.
- **Add / Edit Product Modal:** Automatically calculates Profit per Unit (₹), Profit Margin (%), Current Stock Value (₹), and Potential Selling Value (₹).
- Duplicate barcode validation.
- CSV bulk export for offline spreadsheet analysis.

### Module 4: Stock & Audit Logs
- Live stock inventory with low-stock alerts and suggested reorder quantities.
- **Stock Adjustment Modal:** Adjust stock with mandatory audit reasons (`Damaged / Expired`, `Inventory count discrepancy`, `Customer returned without bill`, `Internal shop use`).
- Chronological stock movement audit trail.

### Module 5: Purchases & Supplier Khata
- Inward supplier invoice entry: Increments product stock automatically.
- **Weighted Average Costing:** Recalculates product purchase price dynamically:
  $$\text{New Cost} = \frac{(\text{Current Qty} \times \text{Current Cost}) + (\text{Incoming Qty} \times \text{Incoming Cost})}{\text{Current Qty} + \text{Incoming Qty}}$$
- Supplier balance ledger: Inward bills vs Payments disbursed, tracking pending payables.

### Module 6: Customers & Khata (Udhaar Book)
- Digital ledger for customer credit sales.
- Instant repayment recording (Cash or UPI) with balance update.
- Printable statement of account showing complete transaction history.

### Module 7: Operating Expenses & Net Real Profit
- Record store operating costs (Rent, Staff Salaries, Electricity, Packaging, Transport, Maintenance).
- P&L reconciliation comparing Gross Profit vs Expenses to reveal **Net Operating Profit**:
  $$\text{Net Operating Profit} = \text{Gross Profit (Sales - COGS)} - \sum \text{Operating Expenses}$$

### Module 8: Reports & Festive Campaigns
- Sales reports, product volume vs profit performance rankings, category sales share.
- Festive Campaign Manager: Launch seasonal festival discount campaigns (Diwali, Pongal, Eid, Christmas) with targeted categories and date ranges.

### Module 9: Advanced Business Insights & Forecasting
- Dedicated tab providing the full analytical power of the 1.029M transaction dataset normalized in **INR (₹)**:
  - 12-week ML Demand Forecasting with LightGBM/Holt-Winters (WAPE & MAE metrics).
  - Customer RFM K-Means clustering (Loyal, At Risk, Champions, Dormant).
  - Indian Festive Campaign Simulator (Diwali, Pongal, Eid uplift scenarios).
  - 5-Dimensional Data Quality health audit (80.9/100).

---

## 4. Role-Based Access Control (RBAC)

| Capability | Store Owner (`admin`) | Cashier (`cashier`) |
| :--- | :---: | :---: |
| POS Billing & Receipt Printing | Yes | Yes |
| Product Search & Selling Prices | Yes | Yes |
| Available Stock Quantities | Yes | Yes |
| Customer Details & Udhaar Repayments | Yes | Yes |
| **Product Purchase Costs** | **Visible** | **Hidden / Blocked** |
| **Profit Margins (%) & Estimated Profit** | **Visible** | **Hidden / Blocked** |
| **Supplier Inward Purchases & Invoices** | **Visible** | **Restricted (403)** |
| **Store Operating Expenses & P&L** | **Visible** | **Restricted (403)** |
| **Financial & Profit Reports** | **Visible** | **Restricted (403)** |
| **Shop Settings & Staff Accounts** | **Full Access** | **Restricted (403)** |

---

## 5. Mathematical & Accounting Precision

1. **Unit Margins:**
   $$\text{Unit Profit} = \text{Selling Price} - \text{Purchase Cost}$$
   $$\text{Margin \%} = \left(\frac{\text{Unit Profit}}{\text{Selling Price}}\right) \times 100$$
2. **Gross Profit (Bill Level):**
   $$\text{Gross Profit} = \sum_{\text{items}} \left(\text{Line Total} - (\text{Quantity} \times \text{Purchase Cost})\right) - \text{Bill Discount}$$
3. **Net Operating Profit (Store Level):**
   $$\text{Net Operating Profit} = \text{Gross Profit} - \sum \text{Operating Expenses}$$
4. **Weighted Average Costing on Inward Purchases:**
   $$\text{New Cost} = \frac{(\text{Existing Stock} \times \text{Current Cost}) + (\text{Incoming Qty} \times \text{Incoming Cost})}{\text{Existing Stock} + \text{Incoming Qty}}$$

---

## 6. Verification & Automated Test Suite

CARTIVANTA includes an automated test suite covering both operational retail workflows and machine learning algorithms:

```cmd
test.bat
```

Or via python:

```cmd
.\.venv\Scripts\python -m pytest -v
```

### Test Suite Results:
```
tests/test_cartivanta.py::test_categorize_description PASSED             [  5%]
tests/test_cartivanta.py::test_clean_raw_dataframe_cancellations_and_returns PASSED [ 10%]
tests/test_cartivanta.py::test_missing_customer_guest_imputation PASSED  [ 15%]
tests/test_cartivanta.py::test_gross_and_net_revenue_formula PASSED      [ 20%]
tests/test_cartivanta.py::test_cogs_and_gross_margin PASSED              [ 25%]
tests/test_cartivanta.py::test_festive_discount_mathematics PASSED       [ 30%]
tests/test_cartivanta.py::test_discount_simulator_edge_case_excessive_discount PASSED [ 35%]
tests/test_cartivanta.py::test_inventory_reorder_formulas PASSED         [ 40%]
tests/test_cartivanta.py::test_wape_and_forecast_metrics PASSED          [ 45%]
tests/test_cartivanta.py::test_wape_zero_actual_edge_case PASSED         [ 50%]
tests/test_cartivanta.py::test_data_quality_score_computation PASSED     [ 55%]
tests/test_cartivanta.py::test_promotion_roi_calculation PASSED          [ 60%]
tests/test_cartivanta.py::test_web_dashboard_template_rendering PASSED   [ 65%]
tests/test_shop_operations.py::test_password_hashing_and_verification PASSED [ 70%]
tests/test_shop_operations.py::test_session_token_generation_and_tamper_proofing PASSED [ 75%]
tests/test_shop_operations.py::test_product_margin_and_stock_calculations PASSED [ 80%]
tests/test_shop_operations.py::test_atomic_bill_creation_and_stock_decrement PASSED [ 85%]
tests/test_shop_operations.py::test_customer_khata_credit_and_repayment PASSED [ 90%]
tests/test_shop_operations.py::test_purchase_inward_and_weighted_average_cost PASSED [ 95%]
tests/test_shop_operations.py::test_operating_expenses_and_net_profit PASSED [100%]

====================== 20 passed, 34 warnings in 24.10s =======================
```

---

## 7. How to Run on Windows

1. **Setup**: Run `setup.bat` (Initializes virtual environment, dependencies, database tables, and demo seed data).
2. **Start Server**: Run `run.bat` (Starts local server on `http://127.0.0.1:8000`).
3. **Run Tests**: Run `test.bat` (Executes full 20-test automated verification suite).

---

## 8. License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
