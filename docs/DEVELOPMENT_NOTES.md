# CARTIVANTA — Engineering & Development Notes

> **Technical Architecture Decisions, Optimization Benchmarks & Design Rationale**

---

## 1. High-Performance ETL & Ingestion Engineering

### 1.1 The Excel vs CSV Ingestion Bottleneck
- **Challenge**: The original UCI Online Retail II dataset is distributed as a multi-sheet Microsoft Excel binary workbook (`online_retail_II.xlsx`, 45.6 MB) containing 1,067,371 rows. Reading two large sheets with `openpyxl` requires upwards of 120–180 seconds and allocates over 1.2 GB of heap memory.
- **Solution**: The extraction pipeline detects if a unified CSV cache (`online_retail_ii_unified.csv`) exists. If not, it streams the Excel sheets, unifies headers, cleans formatting, and writes a flat CSV.
- **Benchmark**: Reading the unified flat CSV using `pandas.read_csv(..., low_memory=False)` takes **0.83 seconds** — an acceleration of over **150x**.

### 1.2 Vectorized Entity Mapping vs Row Iteration
- **Challenge**: Normalizing 1.029 million cleaned transactions into relational tables (`customers`, `products`, `orders`, `order_items`) naively using `df.iterrows()` or `.apply()` required an estimated 25–40 minutes on standard desktop hardware.
- **Solution**: Re-engineered normalization into vectorized Pandas operations:
  ```python
  # Vectorized Line Total & Unit Cost mapping
  cost_map = costs_df.set_index("stock_code")["estimated_unit_cost"].to_dict()
  df["unit_cost"] = df["stock_code"].map(cost_map).fillna(df["unit_price"] * 0.70)
  df["cogs"] = np.where(~df["is_return"], df["quantity"] * df["unit_cost"], 0.0)
  ```
- **Benchmark**: Full normalization of 1.029M rows completes in **0.20 seconds**.

---

## 2. Resilient Dual-Engine Warehouse Architecture

### 2.1 The Windows Socket / Permission Boundary
- **Context**: In enterprise or containerized sandbox environments (e.g., Windows local service security boundaries), PostgreSQL 18 service sockets (`127.0.0.1:5432`) may reject unprivileged user connections (`Permission denied 0x0000271D/10013`).
- **Architectural Solution**: Built a resilient dual-engine database layer in `database/connection.py`.
  - Priority 1: Attempts a pooled connection to PostgreSQL (`cartivanta_db`).
  - Priority 2: If connection fails or socket is blocked, automatically and transparently falls back to a high-concurrency local SQLite engine in **Write-Ahead Logging (WAL)** mode at `data/cartivanta.db`.
  - Identical DDL: All 15 relational tables and 11 analytical views are written with ANSI-SQL standard syntax compatible with both PostgreSQL and SQLite.

---

## 3. Financial Reconciliation Down to the Penny

One of the most frequent flaws in retail BI projects is discrepancies between dashboard figures and raw financial logs. In CARTIVANTA, every metric is reconciled across the Python transformation pipeline, relational base tables, and analytical views:

| Measurement Dimension | Raw Python Calculation | SQL View Calculation (`vw_executive_kpis`) | Discrepancy |
| :--- | :--- | :--- | :--- |
| **Gross Sales** | £20,010,193.612 | £20,010,193.610 | **£0.002** (rounding) |
| **Returns & Cancellations** | £967,011.088 | £967,011.090 | **£0.002** (rounding) |
| **Net Revenue** | £19,043,182.524 | £19,043,182.520 | **£0.004** (rounding) |
| **Units Sold** | 11,435,661 units | 11,435,661 units | **0** (exact) |
| **Units Returned** | 1,037,227 units | 1,037,227 units | **0** (exact) |
| **Completed Orders** | 52,340 orders | 52,340 orders | **0** (exact) |
| **Unique Customer Accounts** | 5,842 accounts | 5,842 accounts | **0** (exact) |
| **Gross Margin** | 23.467% | 23.47% | **0.003%** |

---

## 4. Machine Learning & Forecasting Architecture

### 4.1 Chronological Holdout & Leakage Prevention
- **Anti-Pattern**: Using standard random `train_test_split` on time-series retail data leaks future seasonal trends into historical training sets.
- **CARTIVANTA Implementation**:
  - Aggregates daily transaction volume for target SKUs.
  - Implements strict chronological splitting: the final 30 days are held out as an unseen test window.
  - Generates lag features ($t-1, t-7, t-14, t-28$) and rolling statistics strictly using historical windows.

### 4.2 Benchmark Model Selection
- Models: **RandomForestRegressor** vs **Seasonal Naive** (repeating demand from the previous 7-day cycle).
- Evaluation Metrics:
  - **MAE** (Mean Absolute Error)
  - **RMSE** (Root Mean Squared Error)
  - **WAPE** (Weighted Absolute Percentage Error):
    $$\text{WAPE} = \frac{\sum |\text{Actual}_t - \text{Forecast}_t|}{\sum \text{Actual}_t} \times 100$$
- Result: Model metrics and forward 30-day confidence intervals are persisted directly to the analytical database.

---

## 5. Diwali & Festive Discount Simulator Mechanics

The signature retail simulation engine evaluates price elasticity vs gross margin preservation:
1. **Nominal Gross Profit**:
   $$\text{Profit}_{\text{base}} = Q_{\text{base}} \times (P_{\text{base}} - C)$$
2. **Discounted Gross Profit**:
   $$\text{Profit}_{\text{promo}} = (Q_{\text{base}} \times (1 + \text{Uplift})) \times (P_{\text{base}} \times (1 - d) - C)$$
3. **Required Break-Even Uplift**:
   $$\text{Uplift}_{\text{break-even}} = \frac{P_{\text{base}} - C}{P_{\text{base}}(1 - d) - C} - 1$$
4. **"Profit Destroyer" Rule**: If $\text{Uplift}_{\text{break-even}} > 2.0 \times \text{Expected Uplift}$ or if $\text{Uplift}_{\text{break-even}} > 100\%$, the platform triggers a high-severity alert indicating that the proposed campaign will destroy cash profit regardless of top-line revenue growth.
