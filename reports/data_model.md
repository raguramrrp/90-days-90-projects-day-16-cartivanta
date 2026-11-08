# CARTIVANTA — Analytical Data Model & Relationship Specification

This document details the relational star schema, entity dictionaries, cardinality, and filter directions for the **CARTIVANTA** Power BI model and PostgreSQL/SQLite analytical warehouse.

---

## 1. Star Schema Architecture

CARTIVANTA follows an enterprise dimensional star-schema centered around the primary financial transaction facts:

```
                           +------------------------+
                           |        calendar        |
                           +------------------------+
                                       | 1
                                       |
                                       | *
+----------------------+   *       1 +------------------------+ 1       *   +------------------------+
|      customers       | <---------- |         orders         | ----------> |      order_items       |
+----------------------+             +------------------------+             +------------------------+
          | 1                                                                            | *
          |                                                                              |
          | 1                                                                            | 1
+----------------------+                                                    +------------------------+
|  customer_segments   |                                                    |        products        |
+----------------------+                                                    +------------------------+
                                                                                 | 1            | 1
                                                                                 |              |
                                                                                 | 1            | 1
                                                                    +--------------------+ +--------------------+
                                                                    |   product_costs    | | inventory_snapshot |
                                                                    +--------------------+ +--------------------+

Auxiliary Promotional Star:
+------------------------+ 1       * +------------------------+
|  promotion_campaigns   | --------> | promotion_transactions |
+------------------------+           +------------------------+
                                                 | *
                                                 | 1
                                     +------------------------+
                                     |        products        |
                                     +------------------------+
```

---

## 2. Table Cardinality & Relationships

| From Table (Fact / Child) | To Table (Dimension / Parent) | From Column | To Column | Cardinality | Cross Filter Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `order_items` | `orders` | `invoice_no` | `invoice_no` | Many-to-One (*:1) | Single |
| `order_items` | `products` | `stock_code` | `stock_code` | Many-to-One (*:1) | Single |
| `orders` | `customers` | `customer_id` | `customer_id` | Many-to-One (*:1) | Single |
| `orders` | `calendar` | `invoice_date` (Date) | `date_id` | Many-to-One (*:1) | Single |
| `customer_segments` | `customers` | `customer_id` | `customer_id` | One-to-One (1:1) | Both |
| `product_costs` | `products` | `stock_code` | `stock_code` | One-to-One (1:1) | Both |
| `inventory_snapshot` | `products` | `stock_code` | `stock_code` | One-to-One (1:1) | Both |
| `demand_forecasts` | `products` | `stock_code` | `stock_code` | Many-to-One (*:1) | Single |
| `promotion_transactions` | `promotion_campaigns` | `campaign_id` | `campaign_id` | Many-to-One (*:1) | Single |
| `promotion_transactions` | `products` | `stock_code` | `stock_code` | Many-to-One (*:1) | Single |

---

## 3. Dimension & Fact Dictionaries

### 3.1. `order_items` (Core Fact Table)
- `item_id`: Primary Key (Integer).
- `invoice_no`: Foreign key to `orders`.
- `stock_code`: Foreign key to `products`.
- `description`: Cleaned merchandise description.
- `quantity`: Signed integer. Positive for sales, negative for refunds/returns.
- `unit_price`: Selling price in GBP per unit.
- `line_total`: Computed financial amount ($\text{Quantity} \times \text{Unit Price}$).
- `is_return`: Boolean flag identifying returned lines.
- `estimated_cost_total`: Synthetic COGS for the line item.
- `estimated_profit`: Estimated gross profit ($\text{Line Total} - \text{Estimated COGS}$).

### 3.2. `orders` (Order Header Fact Table)
- `invoice_no`: Primary Key (String).
- `customer_id`: Foreign key to `customers`.
- `invoice_date`: Timestamp of purchase.
- `country`: Shipping country.
- `is_cancelled`: Boolean indicator if invoice prefix was 'C'.
- `total_line_items`: Count of items in invoice.
- `gross_order_value`: Gross sales value.
- `net_order_value`: Net order value after returns.

### 3.3. `products` (Product Dimension)
- `stock_code`: Primary Key (String).
- `description`: Primary title.
- `category`: Retail taxonomy category (Home Decor, Kitchen & Dining, Gifts & Seasonal, etc.).
- `first_seen_date`: Earliest transaction.
- `last_seen_date`: Most recent transaction.
- `is_active`: Operational flag.

### 3.4. `customers` (Customer Dimension)
- `customer_id`: Primary Key (String).
- `first_invoice_date`: Customer acquisition timestamp.
- `last_invoice_date`: Latest purchase timestamp.
- `country`: Primary location.
- `is_registered`: `True` for known account IDs, `False` for guest checkouts.

### 3.5. `customer_segments` (Analytical Dimension)
- `customer_id`: Primary Key.
- `recency_days`: Days between latest purchase and dataset end.
- `frequency`: Total lifetime orders.
- `monetary`: Total lifetime net spend.
- `r_score`, `f_score`, `m_score`: RFM Quintiles (1-5).
- `cluster_id`: Machine learning K-Means cluster index.
- `segment_name`: Champions, Loyal Customers, Potential Loyalists, New Customers, At Risk, Hibernating, Lost Customers.
- `avg_order_value`: Monetary / Frequency.
- `lifetime_revenue`: Cumulative historical revenue.

### 3.6. `inventory_snapshot` (Synthetic Dimension)
- `stock_code`: Primary Key.
- `available_stock`: Current warehouse units.
- `safety_stock`: Minimum buffer threshold.
- `supplier_lead_time_days`: Lead time.
- `target_stock`: Reorder target level.
- `inventory_health_status`: Critical, Low, Healthy, Overstocked, Dead Stock.

### 3.7. `demand_forecasts` (Predictive Fact Table)
- `forecast_id`: Primary Key.
- `stock_code`: Foreign key to `products`.
- `forecast_date`: Target prediction date.
- `model_name`: RandomForestRegressor / SeasonalNaive.
- `predicted_demand`: Point forecast in units.
- `lower_bound`: 90% confidence lower bound.
- `upper_bound`: 90% confidence upper bound.
- `mae`, `rmse`, `wape`: Actual holdout evaluation accuracy metrics.

---

## 4. Power BI Desktop Connection Instructions

1. **Open Power BI Desktop.**
2. Click **Get Data** -> Select **PostgreSQL database** (or **SQLite ODBC / Text/CSV** for local file access).
3. **Database Server:** `localhost:5432` (or path `data/cartivanta.db`).
4. **Database Name:** `cartivanta_db`.
5. **Data Connectivity Mode:** Select **Import**.
6. Select the analytical tables: `orders`, `order_items`, `products`, `customers`, `customer_segments`, `inventory_snapshot`, `product_costs`, `demand_forecasts`, `festival_calendar`, `promotion_campaigns`, `promotion_transactions`, `business_alerts`, and `calendar`.
7. Verify that relationships match Section 2 above.
8. Create a blank table `_Measures` and paste DAX definitions from `reports/dax_measures.md`.
