# CARTIVANTA — Quality Assurance & Testing Guide

> **Verification Suite, Mathematical Assertions & Test Execution**

---

## 1. Testing Philosophy

In retail decision-support systems, software bugs directly cause flawed inventory purchases, margin erosion, or misallocated marketing budgets. Testing in CARTIVANTA emphasizes three distinct tiers:
1. **Unit Verification**: Ensuring pure functions (categorization, ROP formulas, discount math) behave deterministically.
2. **Integration Verification**: Testing end-to-end data flow from raw data structures to relational database persistence.
3. **Mathematical Reconciliation**: Enforcing strict mathematical equality between raw transactional rows, summary database views, and analytical dashboards.

---

## 2. Test Suite Overview (`tests/test_cartivanta.py`)

| Test Function | Target Module | Verification Focus |
| :--- | :--- | :--- |
| `test_categorize_description` | `etl/transform.py` | Accurate product classification into retail categories based on description text |
| `test_clean_raw_dataframe_cancellations_and_returns` | `etl/transform.py` | Proper detection of 'C' prefix invoices, return line items, and duplicate deduplication |
| `test_data_quality_scoring_bounds` | `quality/data_quality.py` | Enforces DQ score remains strictly bounded between 0.0 and 100.0 |
| `test_festive_discount_simulator_math` | `festive/discount_simulator.py` | Mathematical verification of unit profit, margin degradation, and break-even uplift percentage |
| `test_profit_destroyer_detection` | `festive/discount_simulator.py` | Validates that severe discounts exceeding break-even limits trigger the `is_profit_destroyer` flag |
| `test_inventory_classification_logic` | `analytics/inventory_analysis.py` | Verifies stock status assignments (*Critical*, *Low*, *Healthy*, *Overstocked*, *Dead Stock*) |
| `test_sales_analytics_gross_and_net_revenue` | `analytics/sales_analysis.py` | Confirms Net Revenue equals Gross Sales minus Returns |
| `test_customer_rfm_kpi_calculations` | `analytics/customer_analysis.py` | Verifies Recency, Frequency, and Monetary aggregation logic |
| `test_database_tables_exist` | `database/schema.py` | Verifies all 15 relational tables are created and indexed |
| `test_financial_reconciliation_penny_accuracy` | `etl/pipeline.py` | Ensures database view `vw_executive_kpis` matches raw data down to fractional pence |
| `test_synthetic_data_integrity` | `etl/generate_synthetic.py` | Validates deterministic seed generation and presence of `is_synthetic = True` flag |
| `test_business_alert_rule_triggers` | `recommendations/business_rules.py` | Verifies alerts generate when stock or customer conditions are met |

---

## 3. Running the Test Suite

### Via Windows Batch Runner
```cmd
test.bat
```

### Via Python / Pytest CLI
```cmd
call .venv\Scripts\activate.bat
pytest -v tests/ --cov=. --cov-report=term-missing
```

---

## 4. Benchmark Test Execution Output

```
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-9.2.0, pluggy-1.6.0
rootdir: D:\90 days\90-days-90-projects-day-16-cartivanta
configfile: pyproject.toml
plugins: cov-7.1.0
collected 12 items

tests/test_cartivanta.py::test_categorize_description PASSED            [  8%]
tests/test_cartivanta.py::test_clean_raw_dataframe_cancellations_and_returns PASSED [ 16%]
tests/test_cartivanta.py::test_data_quality_scoring_bounds PASSED       [ 25%]
tests/test_cartivanta.py::test_festive_discount_simulator_math PASSED    [ 33%]
tests/test_cartivanta.py::test_profit_destroyer_detection PASSED         [ 41%]
tests/test_cartivanta.py::test_inventory_classification_logic PASSED   [ 50%]
tests/test_cartivanta.py::test_sales_analytics_gross_and_net_revenue PASSED [ 58%]
tests/test_cartivanta.py::test_customer_rfm_kpi_calculations PASSED   [ 66%]
tests/test_cartivanta.py::test_database_tables_exist PASSED             [ 75%]
tests/test_cartivanta.py::test_financial_reconciliation_penny_accuracy PASSED [ 83%]
tests/test_cartivanta.py::test_synthetic_data_integrity PASSED          [ 91%]
tests/test_cartivanta.py::test_business_alert_rule_triggers PASSED       [100%]

============================== 12 passed in 1.48s ==============================
```
