# CARTIVANTA — Synthetic Supporting Data Methodology

## 1. Purpose and Scope
The primary analytical dataset used in CARTIVANTA is the **UCI Online Retail II** repository (2009–2011 UK e-commerce transactions). While the primary dataset provides actual customer transaction events (invoices, stock codes, descriptions, quantities, prices, dates, customer IDs, and countries), real-world retail decision-making requires additional dimensions:
- Acquisition unit costs and COGS (Cost of Goods Sold)
- Inventory holdings, replenishment targets, and lead times
- Promotional campaigns, promotional pricing, and campaign budgets
- Festive event calendar and promotional simulation benchmarks

To enable end-to-end retail intelligence without fabricating actual historical sales, CARTIVANTA generates **reproducible synthetic supporting datasets** with a fixed pseudo-random seed (`RANDOM_SEED = 42`).

---

## 2. Integrity and Labeling Standards
- **Explicit Synthetic Flags:** Every synthetic record in database tables contains a boolean column `is_synthetic = TRUE` or metadata explicitly indicating it is synthetic.
- **Traceability:** No synthetic data is mixed into historical sales orders (`orders` and `order_items` remain 100% historical UCI transactions).
- **Transparency:** The system never claims synthetic inventory or campaign records represent physical warehouse audits or actual marketing spend.

---

## 3. Synthetic Datasets Specification

### 3.1. `product_costs.csv`
- **Fields:**
  - `stock_code`: Primary key linking to products.
  - `estimated_unit_cost`: Modeled as a cost-to-price ratio based on retail margin standards:
    $$\text{Estimated Unit Cost} = \text{Benchmark Price} \times \text{Uniform}(0.40, 0.75)$$
    This ensures gross profit margins range realistically between 25% and 60%.
  - `cost_category`: Categorized as *High Margin*, *Balanced*, or *Low Margin*.
  - `effective_date`: Anchor date for cost modeling.
  - `is_synthetic`: Always `True`.

### 3.2. `inventory_snapshot.csv`
- **Fields:**
  - `stock_code`: Foreign key to products.
  - `available_stock`: Modeled around product velocity and historical average daily demand:
    $$\text{Available Stock} = \text{Daily Demand} \times \text{Normal}(\mu=30, \sigma=10)$$
  - `safety_stock`: Minimum buffer calculated as:
    $$\text{Safety Stock} = \text{Daily Demand} \times 7$$
  - `supplier_lead_time`: Modeled between 5 and 21 days based on supplier tiers.
  - `target_stock`: Target inventory level:
    $$\text{Target Stock} = \text{Safety Stock} + (\text{Daily Demand} \times \text{Supplier Lead Time} \times 2)$$
  - `inventory_health_status`:
    - **Critical:** $\text{Available Stock} \le \text{Safety Stock} \times 0.5$
    - **Low:** $\text{Safety Stock} \times 0.5 < \text{Available Stock} \le \text{Reorder Point}$
    - **Healthy:** $\text{Reorder Point} < \text{Available Stock} \le \text{Target Stock} \times 1.2$
    - **Overstocked:** $\text{Available Stock} > \text{Target Stock} \times 1.5$
    - **Dead Stock:** Zero sales velocity in last 90 days.
  - `is_synthetic`: Always `True`.

### 3.3. `festival_calendar.csv`
- **Fields:**
  - `festival_name`: Diwali, Pongal, Christmas, New Year, Eid, Black Friday.
  - `start_date` and `end_date`: Calendar windows.
  - `festival_category`: Category mapping (e.g., Gifts, Home Decor, Seasonal).
  - `demand_uplift_assumption`: Multiplier assumption (e.g., +25% for Diwali, +40% for Christmas).
  - `notes`: Domain rationale.
  - `is_synthetic`: Always `True`.

### 3.4. `promotion_campaigns.csv` & `promotion_transactions.csv`
- **Fields:**
  - `campaign_id`: Structured identifier (`CMP-2010-01`, etc.).
  - `campaign_name`: E.g., "Diwali Golden Glow Mega Sale", "Christmas Joy Clearance".
  - `promotion_type`: Festive, Clearance, Flash Sale, Category Spotlight.
  - `discount_percentage`: Configurable percentage discount (5% to 30%).
  - `campaign_budget`: Assigned marketing allocation in GBP.
  - `is_synthetic`: Always `True`.

---

## 4. Reproducibility
All generation code is encapsulated in `festive/festival_calendar.py` and `etl/generate_synthetic.py`. Running the generator with `seed=42` produces bit-for-bit identical datasets every execution.
