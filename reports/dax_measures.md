# CARTIVANTA — Power BI DAX Measures & Analytical Definitions

This document provides the complete, production-grade DAX (Data Analysis Expressions) library for **CARTIVANTA**. All measures are organized into functional measure tables for clean report architecture.

---

## 1. Core Revenue & Order Measures

### 1.1. Gross Sales
Calculates total gross transaction value before subtracting returns or cancellations.
```dax
[Gross Sales] = 
SUMX(
    FILTER('order_items', 'order_items'[quantity] > 0),
    'order_items'[line_total]
)
```

### 1.2. Returns Value
Calculates total refunded or returned merchandise value.
```dax
[Returns Value] = 
ABS(
    SUMX(
        FILTER('order_items', 'order_items'[quantity] < 0 || 'order_items'[is_return] = TRUE()),
        'order_items'[line_total]
    )
)
```

### 1.3. Net Revenue
The true top-line financial metric reconciling gross sales and returns.
```dax
[Net Revenue] = 
SUM('order_items'[line_total])
```

### 1.4. Total Orders
Distinct count of completed commercial purchase transactions.
```dax
[Total Orders] = 
DISTINCTCOUNT('orders'[invoice_no])
```

### 1.5. Units Sold
Net volume of merchandise units sold.
```dax
[Units Sold] = 
SUMX(
    FILTER('order_items', 'order_items'[quantity] > 0),
    'order_items'[quantity]
)
```

### 1.6. Units Returned
Total count of physical returned units.
```dax
[Units Returned] = 
ABS(
    SUMX(
        FILTER('order_items', 'order_items'[quantity] < 0),
        'order_items'[quantity]
    )
)
```

### 1.7. Return Rate (%)
Proportion of gross sales eroded by product returns.
```dax
[Return Rate %] = 
DIVIDE([Returns Value], [Gross Sales], 0) * 100
```

### 1.8. Average Order Value (AOV)
Average net basket value per invoice.
```dax
[Average Order Value] = 
DIVIDE([Net Revenue], [Total Orders], 0)
```

---

## 2. Customer Intelligence Measures

### 2.1. Active Customers
Count of unique purchasing customer entities.
```dax
[Active Customers] = 
DISTINCTCOUNT('orders'[customer_id])
```

### 2.2. Returning Customers
Count of customers who have completed more than one distinct invoice.
```dax
[Returning Customers] = 
CALCULATE(
    DISTINCTCOUNT('orders'[customer_id]),
    FILTER(
        VALUES('orders'[customer_id]),
        CALCULATE(DISTINCTCOUNT('orders'[invoice_no])) > 1 &&
        NOT(ISBLANK('orders'[customer_id])) &&
        NOT(LEFT('orders'[customer_id], 6) = "GUEST-")
    )
)
```

### 2.3. Customer Repeat Rate (%)
Proportion of customer base exhibiting repeat purchasing behavior.
```dax
[Customer Repeat Rate %] = 
DIVIDE([Returning Customers], [Active Customers], 0) * 100
```

---

## 3. Profitability & COGS Measures

### 3.1. Estimated Cost of Goods Sold (COGS)
Aggregated synthetic acquisition costs for sold units.
```dax
[Estimated COGS] = 
SUMX(
    FILTER('order_items', 'order_items'[quantity] > 0),
    'order_items'[estimated_cost_total]
)
```

### 3.2. Estimated Gross Profit
Net revenue minus estimated cost of goods sold.
```dax
[Estimated Gross Profit] = 
[Net Revenue] - [Estimated COGS]
```

### 3.3. Estimated Gross Margin (%)
Gross margin percentage of net revenue.
```dax
[Estimated Gross Margin %] = 
DIVIDE([Estimated Gross Profit], [Net Revenue], 0) * 100
```

---

## 4. Time Intelligence & Growth

### 4.1. Previous Period Revenue
Revenue for the same duration in the preceding calendar period.
```dax
[Previous Period Revenue] = 
CALCULATE(
    [Net Revenue],
    DATEADD('calendar'[date_id], -1, MONTH)
)
```

### 4.2. Revenue Growth (MoM %)
Month-over-month revenue growth trajectory.
```dax
[Revenue Growth %] = 
VAR PrevRev = [Previous Period Revenue]
RETURN
DIVIDE([Net Revenue] - PrevRev, PrevRev, 0) * 100
```

### 4.3. Previous Period Profit
Profit for the previous period.
```dax
[Previous Period Profit] = 
CALCULATE(
    [Estimated Gross Profit],
    DATEADD('calendar'[date_id], -1, MONTH)
)
```

### 4.4. Profit Growth (MoM %)
Month-over-month gross profit growth rate.
```dax
[Profit Growth %] = 
VAR PrevProf = [Previous Period Profit]
RETURN
DIVIDE([Estimated Gross Profit] - PrevProf, ABS(PrevProf), 0) * 100
```

---

## 5. Demand & Forecasting Measures

### 5.1. Forecast Demand
Aggregated machine learning forward demand prediction.
```dax
[Forecast Demand] = 
SUM('demand_forecasts'[predicted_demand])
```

### 5.2. Forecast Lower Bound
90% confidence interval lower prediction bound.
```dax
[Forecast Lower Bound] = 
SUM('demand_forecasts'[lower_bound])
```

### 5.3. Forecast Upper Bound
90% confidence interval upper prediction bound.
```dax
[Forecast Upper Bound] = 
SUM('demand_forecasts'[upper_bound])
```

---

## 6. Promotional & Festive Intelligence Measures

### 6.1. Promotional Revenue
Revenue generated during active campaign transactions.
```dax
[Promotional Revenue] = 
SUMX(
    'promotion_transactions',
    'promotion_transactions'[final_selling_price] * 'promotion_transactions'[quantity]
)
```

### 6.2. Total Discount Amount Given
Cumulative discount markdown granted across promotional transactions.
```dax
[Total Discount Amount] = 
SUMX(
    'promotion_transactions',
    'promotion_transactions'[discount_amount] * 'promotion_transactions'[quantity]
)
```

### 6.3. Promotional Profit
Estimated gross profit earned from discounted campaign sales.
```dax
[Promotional Profit] = 
SUMX(
    'promotion_transactions',
    ('promotion_transactions'[final_selling_price] - RELATED('product_costs'[estimated_unit_cost])) * 'promotion_transactions'[quantity]
)
```

### 6.4. Promotion ROI (%)
True return on promotional spend using campaign budget as investment denominator.
```dax
[Promotion ROI %] = 
VAR PromoProfit = [Promotional Profit]
VAR Budget = SUM('promotion_campaigns'[campaign_budget])
RETURN
DIVIDE(PromoProfit - Budget, Budget, 0) * 100
```

---

## 7. Inventory Measures

### 7.1. Available Stock Units
```dax
[Available Stock] = 
SUM('inventory_snapshot'[available_stock])
```

### 7.2. Safety Stock Threshold
```dax
[Safety Stock] = 
SUM('inventory_snapshot'[safety_stock])
```

### 7.3. Suggested Reorder Quantity
```dax
[Suggested Reorder Quantity] = 
SUMX(
    'inventory_snapshot',
    MAX(0, 'inventory_snapshot'[target_stock] - 'inventory_snapshot'[available_stock])
)
```
