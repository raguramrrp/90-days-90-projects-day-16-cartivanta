-- ============================================================================
-- CARTIVANTA: Retail Intelligence & Predictive Commerce Platform
-- PostgreSQL Relational & Analytical Schema
-- ============================================================================

-- Clean up existing tables if dropping
DROP TABLE IF EXISTS business_alerts CASCADE;
DROP TABLE IF EXISTS customer_segments CASCADE;
DROP TABLE IF EXISTS demand_forecasts CASCADE;
DROP TABLE IF EXISTS promotion_transactions CASCADE;
DROP TABLE IF EXISTS promotion_campaigns CASCADE;
DROP TABLE IF EXISTS festival_calendar CASCADE;
DROP TABLE IF EXISTS inventory_snapshot CASCADE;
DROP TABLE IF EXISTS product_costs CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS calendar CASCADE;
DROP TABLE IF EXISTS data_quality_results CASCADE;
DROP TABLE IF EXISTS etl_execution_logs CASCADE;

-- 1. ETL Execution Logs
CREATE TABLE etl_execution_logs (
    log_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    step_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL, -- STARTED, SUCCESS, FAILED, WARNING
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    details TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 2. Data Quality Results
CREATE TABLE data_quality_results (
    result_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    check_name VARCHAR(128) NOT NULL,
    metric_category VARCHAR(64) NOT NULL,
    metric_value NUMERIC(12, 4) NOT NULL,
    threshold_value NUMERIC(12, 4),
    status VARCHAR(32) NOT NULL, -- PASS, WARNING, FAIL
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Calendar Dimension Table
CREATE TABLE calendar (
    date_id DATE PRIMARY KEY,
    day_name VARCHAR(16) NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_year INTEGER NOT NULL,
    week_of_year INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name VARCHAR(16) NOT NULL,
    quarter_number INTEGER NOT NULL,
    year_number INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE
);

-- 4. Customers Dimension Table
CREATE TABLE customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    first_invoice_date TIMESTAMP WITH TIME ZONE,
    last_invoice_date TIMESTAMP WITH TIME ZONE,
    country VARCHAR(64) NOT NULL,
    is_registered BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Products Dimension Table
CREATE TABLE products (
    stock_code VARCHAR(32) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'General Merchandise',
    first_seen_date TIMESTAMP WITH TIME ZONE,
    last_seen_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Product Costs (Supporting Synthetic Dimension)
CREATE TABLE product_costs (
    stock_code VARCHAR(32) PRIMARY KEY REFERENCES products(stock_code) ON DELETE CASCADE,
    estimated_unit_cost NUMERIC(10, 4) NOT NULL,
    cost_category VARCHAR(64) NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    effective_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Orders Fact Table
CREATE TABLE orders (
    invoice_no VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) REFERENCES customers(customer_id) ON DELETE SET NULL,
    invoice_date TIMESTAMP WITH TIME ZONE NOT NULL,
    country VARCHAR(64) NOT NULL,
    is_cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    total_line_items INTEGER NOT NULL DEFAULT 0,
    gross_order_value NUMERIC(14, 4) NOT NULL DEFAULT 0.0,
    net_order_value NUMERIC(14, 4) NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Order Items Fact Table
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(32) NOT NULL REFERENCES orders(invoice_no) ON DELETE CASCADE,
    stock_code VARCHAR(32) NOT NULL REFERENCES products(stock_code) ON DELETE CASCADE,
    description VARCHAR(255),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 4) NOT NULL,
    line_total NUMERIC(14, 4) NOT NULL,
    is_return BOOLEAN NOT NULL DEFAULT FALSE,
    estimated_cost_total NUMERIC(14, 4),
    estimated_profit NUMERIC(14, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Inventory Snapshot Table (Supporting Synthetic)
CREATE TABLE inventory_snapshot (
    snapshot_id SERIAL PRIMARY KEY,
    stock_code VARCHAR(32) NOT NULL REFERENCES products(stock_code) ON DELETE CASCADE,
    available_stock INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL,
    supplier_lead_time_days INTEGER NOT NULL,
    target_stock INTEGER NOT NULL,
    last_restock_date DATE,
    inventory_health_status VARCHAR(32) NOT NULL, -- Critical, Low, Healthy, Overstocked, Dead Stock
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Festival Calendar Table
CREATE TABLE festival_calendar (
    festival_id SERIAL PRIMARY KEY,
    festival_name VARCHAR(64) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    festival_category VARCHAR(64) NOT NULL,
    demand_uplift_assumption NUMERIC(6, 4) NOT NULL,
    notes TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. Promotion Campaigns Table (Supporting Synthetic)
CREATE TABLE promotion_campaigns (
    campaign_id VARCHAR(32) PRIMARY KEY,
    campaign_name VARCHAR(128) NOT NULL,
    promotion_type VARCHAR(64) NOT NULL, -- Festive, Seasonal, Clearance, Flash
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    target_category VARCHAR(64) NOT NULL,
    discount_percentage NUMERIC(6, 4) NOT NULL,
    campaign_budget NUMERIC(12, 2) NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. Promotion Transactions Table (Supporting Synthetic)
CREATE TABLE promotion_transactions (
    promo_txn_id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(32) NOT NULL,
    stock_code VARCHAR(32) NOT NULL REFERENCES products(stock_code) ON DELETE CASCADE,
    campaign_id VARCHAR(32) NOT NULL REFERENCES promotion_campaigns(campaign_id) ON DELETE CASCADE,
    original_price NUMERIC(10, 4) NOT NULL,
    discount_percentage NUMERIC(6, 4) NOT NULL,
    discount_amount NUMERIC(10, 4) NOT NULL,
    final_selling_price NUMERIC(10, 4) NOT NULL,
    quantity INTEGER NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Demand Forecasts Table
CREATE TABLE demand_forecasts (
    forecast_id SERIAL PRIMARY KEY,
    stock_code VARCHAR(32) NOT NULL REFERENCES products(stock_code) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    model_name VARCHAR(64) NOT NULL, -- SeasonalNaive, RandomForestRegressor
    predicted_demand NUMERIC(12, 4) NOT NULL,
    lower_bound NUMERIC(12, 4),
    upper_bound NUMERIC(12, 4),
    mae NUMERIC(10, 4),
    rmse NUMERIC(10, 4),
    wape NUMERIC(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. Customer Segments Table (RFM + K-Means)
CREATE TABLE customer_segments (
    customer_id VARCHAR(32) PRIMARY KEY REFERENCES customers(customer_id) ON DELETE CASCADE,
    recency_days INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    monetary NUMERIC(14, 4) NOT NULL,
    r_score INTEGER NOT NULL,
    f_score INTEGER NOT NULL,
    m_score INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    segment_name VARCHAR(64) NOT NULL, -- Champions, Loyal Customers, Potential Loyalists, New Customers, At Risk, Hibernating, Lost Customers
    avg_order_value NUMERIC(12, 4) NOT NULL,
    lifetime_revenue NUMERIC(14, 4) NOT NULL,
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 15. Business Alerts / Action Center Table
CREATE TABLE business_alerts (
    alert_id VARCHAR(64) PRIMARY KEY,
    alert_category VARCHAR(64) NOT NULL, -- Inventory, Demand, Customer, Profitability, Festive, Promotion
    severity VARCHAR(16) NOT NULL, -- Critical, High, Medium, Low
    affected_entity_type VARCHAR(32) NOT NULL, -- Product, Customer, Category, Campaign
    affected_entity_id VARCHAR(64) NOT NULL,
    detected_condition TEXT NOT NULL,
    supporting_metric VARCHAR(128) NOT NULL,
    threshold_value VARCHAR(64),
    suggested_action TEXT NOT NULL,
    expected_impact TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    generated_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
