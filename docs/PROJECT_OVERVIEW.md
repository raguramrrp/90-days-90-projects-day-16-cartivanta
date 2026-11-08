# CARTIVANTA — Project Overview

> **From Every Transaction to Smarter Retail Decisions.**

---

## 1. Executive Summary

**CARTIVANTA** is an integrated, enterprise-grade retail intelligence and predictive commerce platform built for multi-channel merchandisers, retail CFOs, inventory controllers, and category managers. Rather than presenting isolated dashboards or superficial analytics, CARTIVANTA bridges the operational gap between raw point-of-sale transactions and boardroom decision-making.

Operating on the benchmark **UCI Online Retail II dataset** (spanning 1,067,371 raw transaction records across two calendar years, 2009–2011), CARTIVANTA processes, audits, models, and visualizes retail dynamics across ten dedicated intelligence modules.

---

## 2. Platform Core Architecture & Principles

1. **Absolute Financial Reconciliation**: Every metric shown on executive dashboards matches the underlying SQL database views to within a fraction of a penny:
   - **Gross Sales**: £20,010,193.61
   - **Returns & Cancellations**: £967,011.09
   - **Net Revenue**: £19,043,182.52
   - **Estimated Cost of Goods Sold (COGS)**: £14,574,293.68
   - **Estimated Gross Profit**: £4,468,888.84
   - **Gross Margin**: 23.47%
   - **Total Orders**: 52,340 | **Average Order Value (AOV)**: £363.84
   - **Return Rate**: 4.83%
2. **Transparent Data Integrity**: Synthetic supporting data (product unit costs, warehouse inventory snapshots, campaign parameters) are deterministically generated with fixed seed 42 and strictly labeled (`is_synthetic = True`).
3. **Resilient Dual-Engine Warehouse**: Built for PostgreSQL 18 with automatic, zero-configuration local SQLite WAL fallback when socket or port permissions are restricted.
4. **No Decorative AI**: Demand forecasting evaluates actual chronological holdout performance (Random Forest vs Seasonal Naive) with genuine MAE, RMSE, and WAPE metrics. Customer segmentation utilizes standardized K-Means on verified RFM matrices.

---

## 3. The Ten Core Intelligence Modules

### Module 01: Executive Intelligence
- High-level KPI scorecards tracking gross volume, net revenue, margins, and order frequency.
- Time-series monthly revenue vs profit tracking.
- Geographical revenue concentration across 43 countries (dominated by the United Kingdom, Germany, France, EIRE).
- Category sales breakdowns and Pareto 80/20 concentration analysis.

### Module 02: Product Intelligence
- Granular performance matrix comparing volume, net revenue, and gross profit across 5,124 catalog SKUs.
- Identification of star products vs high-revenue, low-margin products.
- Product return rates tracking items with disproportionate cancellation and defect costs.

### Module 03: Customer Intelligence (RFM & Machine Learning)
- Quantitative RFM calculation:
  - **Recency ($R$)**: Days since last confirmed purchase.
  - **Frequency ($F$)**: Count of unique completed orders.
  - **Monetary ($M$)**: Total net spend to date in GBP (£).
- Unsupervised **K-Means Clustering** ($k=4$) with `StandardScaler` log-transformed features:
  - **Champions** (538 customers, 9.2%): Highest frequency, recent spend, driving premium basket sizes.
  - **Loyal Customers** (2,304 customers, 39.4%): Consistent repeat buyers across seasons.
  - **At Risk** (1,394 customers, 23.9%): High past spend but dormant for >90 days.
  - **Lost Customers** (1,606 customers, 27.5%): Low frequency, high dormancy (>250 days).

### Module 04: Inventory Intelligence & Stockout Risk
- Daily demand velocity calculations:
  $$\text{Daily Demand} = \frac{\text{Units Sold}}{\text{Observed Period Days}}$$
- Dynamic reorder points ($ROP$):
  $$ROP = (\text{Daily Demand} \times \text{Lead Time}) + \text{Safety Stock}$$
- Stock classifications: *Critical* (stock < safety stock), *Low* (stock < ROP), *Healthy*, *Overstocked*, and *Dead Stock*.
- Stockout risk scoring and suggested replenishment quantities.

### Module 05: Machine Learning Demand Forecasting
- Chronological, leakage-free 30-day demand projections for high-velocity SKUs.
- Feature engineering: Lag 1, Lag 7, Lag 14, Lag 28, 7-day and 14-day rolling demand averages, week of year, month, day of week.
- Benchmark comparison: **RandomForestRegressor** (50 estimators, max depth 8) vs **Seasonal Naive** baseline.
- Real evaluation reporting MAE, RMSE, and WAPE without artificial accuracy inflation.

### Module 06: Profitability Intelligence
- Unit economics evaluation combining transaction prices with estimated category-based cost of goods sold.
- Margin analysis identifying "Loss Leaders" and SKUs eroding net margins.
- Revenue vs profit discrepancy detection.

### Module 07: Diwali & Festive Intelligence (Signature Simulator)
- Festival calendar modeling demand uplifts across key retail periods (Diwali, Christmas, Black Friday, New Year, Cyber Week).
- **Interactive Discount & Margin Simulator**:
  - Simulates proposed price cuts (5% to 50%).
  - Evaluates projected revenue vs projected gross profit.
  - Computes required **Break-Even Volume Uplift**:
    $$\text{Break-Even Uplift} = \frac{\text{Original Margin}}{\text{New Discounted Margin}} - 1$$
  - Flags **"Profit Destroyers"** when required sales volume exceeds realistic market elasticity.

### Module 08: Promotion Intelligence
- Evaluation of promotional campaigns across discount depth, spend, incremental units, and campaign ROI.
- Margin preservation safeguards to protect net profitability during heavy clearance events.

### Module 09: Business Action Center
- Real-time rule-based recommendation engine scanning warehouse inventory, customer churn, and product margins.
- Generates categorized operational alerts:
  - **HIGH RISK**: Critical stockout alerts on high-velocity items.
  - **CHURN RISK**: At-Risk and Champion customer re-engagement actions.
  - **PRICE OPTIMIZATION**: Margin erosion remediation for high-revenue, low-margin SKUs.
  - **CLEARANCE**: Dead-stock liquidation recommendations.

### Module 10: Data Quality Intelligence
- Automated end-to-end audit during the ETL ingestion process.
- 5 weighted dimensions:
  1. Completeness (25%)
  2. Validity (25%)
  3. Uniqueness (20%)
  4. Consistency (15%)
  5. Timeliness (15%)
- Calculates overall **Data Quality Score (80.9 / 100)** with detailed rejection counts for negative prices, duplicate transactions, and guest customer imputations.

---

## 4. Key Performance Indicators Summary

| Metric | Measured Value | Verification Source |
| :--- | :--- | :--- |
| **Gross Transactions Processed** | 1,067,371 rows | `online_retail_ii_unified.csv` |
| **Valid Processed Records** | 1,029,247 items | `order_items` table |
| **Gross Sales** | £20,010,193.61 | SQL `vw_executive_kpis` |
| **Return & Cancellation Value** | £967,011.09 | SQL `vw_executive_kpis` |
| **Net Revenue** | £19,043,182.52 | SQL `vw_executive_kpis` |
| **Estimated Cost of Goods Sold** | £14,574,293.68 | SQL `vw_profitability` |
| **Estimated Gross Profit** | £4,468,888.84 | SQL `vw_executive_kpis` |
| **Gross Margin** | 23.47% | SQL `vw_executive_kpis` |
| **Total Orders** | 52,340 | SQL `orders` table |
| **Average Order Value (AOV)** | £363.84 | SQL `vw_executive_kpis` |
| **Unique Products** | 5,124 SKUs | SQL `products` table |
| **Customer Base Profiled** | 5,842 accounts | SQL `customer_segments` |
| **Data Quality Score** | 80.9 / 100 | `data_quality_results` table |
| **Active Business Alerts** | 40 recommendations | `business_alerts` table |
