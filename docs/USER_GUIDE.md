# CARTIVANTA — User Guide

> **Operational Manual & Analytical Navigation Guide**

---

## 1. Quick Navigation

CARTIVANTA provides dual interfaces for analytics consumption:
1. **Interactive Web Workstation**: Modern, zero-configuration local web application served by FastAPI at `http://127.0.0.1:8000`.
2. **Power BI Semantic Reporting**: Production-ready star schema with enterprise DAX measures for executive reporting.

---

## 2. Navigating the Web Analytics Workstation

Start the workstation by running:
```cmd
run.bat
```
Open your browser to `http://127.0.0.1:8000`.

### Tab 1: Executive Overview (`/` or `?tab=executive`)
- **Key Scorecards**: View real-time Gross Sales (£20.01M), Returns (£967.0K), Net Revenue (£19.04M), Estimated Gross Profit (£4.47M), Gross Margin (23.47%), Total Orders (52,340), and AOV (£363.84).
- **Monthly Revenue & Profit Trend**: Multi-axis time-series visualization tracking seasonal peak periods (notably Q4 holiday spikes).
- **Category Sales Breakdown**: Distribution across Home Decor, Gifts & Novelties, Kitchen & Dining, Craft & Stationery, and Fashion.
- **Top 5 Revenue Products**: Quick glance at the highest revenue drivers.

### Tab 2: Product & Inventory (`?tab=products`)
- **Product Search & Matrix**: Inspect individual SKU velocity, total units sold, net revenue, unit costs, and estimated gross margin.
- **Inventory Health Status**:
  - **Critical**: Items where `available_stock < safety_stock`. Immediate stockout danger.
  - **Low**: Items below the calculated `Reorder Point (ROP)`. Purchase order required.
  - **Healthy**: Operating comfortably between ROP and Target Stock.
  - **Overstocked / Dead Stock**: Working capital locked in slow-moving inventory.
- **Inventory Metrics**: Average Daily Demand, Supplier Lead Time, Reorder Point, and Suggested Reorder Quantity.

### Tab 3: Demand Forecasts (`?tab=forecasts`)
- **Machine Learning Holdout Comparisons**: Inspect genuine test metrics (MAE, RMSE, WAPE) comparing **Random Forest** against **Seasonal Naive**.
- **30-Day Forward Projections**: Daily unit demand forecast for high-velocity SKUs with 90% confidence prediction intervals (lower bound, point forecast, upper bound).
- **Model Transparency**: Notice that all metrics are evaluated on unseen historical holdout periods without artificial accuracy claims.

### Tab 4: Customer Intelligence & Profitability (`?tab=customers`)
- **RFM Customer Segmentation**:
  - **Champions** (9.2%): High spenders who order frequently. Strategy: VIP loyalty rewards, early product previews.
  - **Loyal Customers** (39.4%): Regular repeat purchasers. Strategy: Upsell and cross-sell bundles.
  - **At Risk** (23.9%): High past spend but dormant for 90+ days. Strategy: Personalized win-back incentives.
  - **Lost Customers** (27.5%): Dormant >250 days with low frequency. Strategy: Automated re-engagement or pruning.
- **Profitability Breakdown**: Margin distribution across categories, identifying loss-leader items with high revenue but razor-thin margins.

### Tab 5: Diwali & Festive Intelligence (`?tab=festive`)
- **Festival Calendar**: Pre-configured festive periods (Diwali, Christmas, Black Friday, Cyber Week, New Year) with expected baseline demand uplift.
- **Interactive Discount & Margin Simulator**:
  1. Select a target SKU (e.g., `85123A — WHITE HANGING HEART T-LIGHT HOLDER`).
  2. Adjust the **Discount Percentage** (e.g., 20%).
  3. Adjust the **Expected Demand Uplift** (e.g., 30%).
  4. Click **"Run Festive Simulation"**.
- **Simulator Output & Warnings**:
  - **Projected Revenue vs Gross Profit**: Shows whether gross profit increases or decreases.
  - **Required Break-Even Volume Uplift**: The exact percentage increase in unit sales required just to maintain previous cash gross profit.
  - **"Profit Destroyer" Alert**: If the required volume uplift exceeds what the market is likely to deliver (e.g., needing +53% volume on a 20% discount), the system warns merchandisers before they approve the promotion.

### Tab 6: Business Action Center & Data Quality (`?tab=actions`)
- **Categorized Actionable Recommendations**: Real-time alerts generated from inventory stockouts, customer churn risks, and margin erosion.
  - Each alert includes: Severity (Critical / High / Medium), Potential GBP Impact, Category, and Specific Recommended Action.
- **Data Quality Audit Scorecard**:
  - Overall Score: **80.9 / 100**.
  - Dimension breakdown: Completeness (80.0%), Validity (85.0%), Uniqueness (88.0%), Consistency (80.0%), Timeliness (68.0%).
  - Audit counts: Total raw rows (1,067,371), valid rows (1,029,247), duplicates removed (34,335), cancellations preserved (18,088), returns processed (21,481).

---

## 3. Power BI Integration Guide

For enterprise BI reporting teams:
1. Open **Power BI Desktop**.
2. Connect to the analytical database:
   - For PostgreSQL: `Home -> Get Data -> PostgreSQL database` (Server: `localhost:5432`, Database: `cartivanta_db`).
   - For SQLite: `Home -> Get Data -> ODBC` or import exported tables from `data/processed/`.
3. Select the analytical views (`vw_executive_kpis`, `vw_monthly_sales`, `vw_product_performance`, etc.).
4. Review the data model against [reports/data_model.md](file:///D:/90%20days/90-days-90-projects-day-16-cartivanta/reports/data_model.md).
5. Copy the DAX measures from [reports/dax_measures.md](file:///D:/90%20days/90-days-90-projects-day-16-cartivanta/reports/dax_measures.md).
6. Reference the visual layouts in `reports/screenshots/` to build identical interactive report pages.
