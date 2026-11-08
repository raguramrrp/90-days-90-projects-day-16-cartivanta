-- ============================================================================
-- CARTIVANTA: Analytical Views
-- ============================================================================

-- 1. Executive KPIs View
CREATE OR REPLACE VIEW vw_executive_kpis AS
SELECT
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS total_gross_sales,
    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS total_returns_value,
    COALESCE(SUM(oi.line_total), 0) AS net_revenue,
    COUNT(DISTINCT o.invoice_no) AS total_orders,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS total_units_sold,
    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END)), 0) AS total_units_returned,
    CASE 
        WHEN COUNT(DISTINCT o.invoice_no) > 0 
        THEN ROUND(COALESCE(SUM(oi.line_total), 0) / COUNT(DISTINCT o.invoice_no), 2)
        ELSE 0 
    END AS average_order_value,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs,
    COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit,
    CASE 
        WHEN COALESCE(SUM(oi.line_total), 0) > 0 
        THEN ROUND(((COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0)) / SUM(oi.line_total)) * 100, 2)
        ELSE 0 
    END AS estimated_gross_margin_pct,
    CASE 
        WHEN SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END) > 0 
        THEN ROUND((ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)) / SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END)) * 100, 2)
        ELSE 0 
    END AS return_rate_pct
FROM order_items oi
JOIN orders o ON oi.invoice_no = o.invoice_no;

-- 2. Monthly Sales Trend View
CREATE OR REPLACE VIEW vw_monthly_sales AS
SELECT
    TO_CHAR(o.invoice_date, 'YYYY-MM') AS year_month,
    EXTRACT(YEAR FROM o.invoice_date) AS sales_year,
    EXTRACT(MONTH FROM o.invoice_date) AS sales_month,
    COUNT(DISTINCT o.invoice_no) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS gross_sales,
    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_value,
    COALESCE(SUM(oi.line_total), 0) AS net_revenue,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs,
    COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit,
    CASE 
        WHEN COALESCE(SUM(oi.line_total), 0) > 0 
        THEN ROUND(((COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0)) / SUM(oi.line_total)) * 100, 2)
        ELSE 0 
    END AS estimated_gross_margin_pct
FROM orders o
JOIN order_items oi ON o.invoice_no = oi.invoice_no
GROUP BY TO_CHAR(o.invoice_date, 'YYYY-MM'), EXTRACT(YEAR FROM o.invoice_date), EXTRACT(MONTH FROM o.invoice_date)
ORDER BY year_month ASC;

-- 3. Product Performance View
CREATE OR REPLACE VIEW vw_product_performance AS
SELECT
    p.stock_code,
    p.description,
    p.category,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END)), 0) AS units_returned,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS gross_revenue,
    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_revenue,
    COALESCE(SUM(oi.line_total), 0) AS net_revenue,
    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs,
    COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit,
    CASE 
        WHEN COALESCE(SUM(oi.line_total), 0) > 0 
        THEN ROUND(((COALESCE(SUM(oi.line_total), 0) - COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0)) / SUM(oi.line_total)) * 100, 2)
        ELSE 0 
    END AS estimated_margin_pct,
    CASE 
        WHEN SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) > 0 
        THEN ROUND((ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END))::NUMERIC / SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END)) * 100, 2)
        ELSE 0 
    END AS return_quantity_rate_pct
FROM products p
JOIN order_items oi ON p.stock_code = oi.stock_code
GROUP BY p.stock_code, p.description, p.category;

-- 4. Customer RFM View
CREATE OR REPLACE VIEW vw_customer_rfm AS
SELECT
    cs.customer_id,
    c.country,
    cs.recency_days,
    cs.frequency,
    cs.monetary,
    cs.r_score,
    cs.f_score,
    cs.m_score,
    cs.cluster_id,
    cs.segment_name,
    cs.avg_order_value,
    cs.lifetime_revenue,
    c.first_invoice_date,
    c.last_invoice_date
FROM customer_segments cs
JOIN customers c ON cs.customer_id = c.customer_id;

-- 5. Inventory Health View
CREATE OR REPLACE VIEW vw_inventory_health AS
SELECT
    i.stock_code,
    p.description,
    p.category,
    i.available_stock,
    i.safety_stock,
    i.supplier_lead_time_days,
    i.target_stock,
    i.inventory_health_status,
    i.last_restock_date,
    COALESCE(perf.units_sold, 0) AS historical_units_sold,
    ROUND(COALESCE(perf.units_sold, 0)::NUMERIC / 730, 2) AS estimated_daily_demand,
    ROUND(
        (COALESCE(perf.units_sold, 0)::NUMERIC / 730) * i.supplier_lead_time_days + i.safety_stock, 
        0
    ) AS calculated_reorder_point,
    GREATEST(0, i.target_stock - i.available_stock) AS suggested_reorder_quantity,
    CASE 
        WHEN (COALESCE(perf.units_sold, 0)::NUMERIC / 730) > 0 
        THEN ROUND(i.available_stock / (COALESCE(perf.units_sold, 0)::NUMERIC / 730), 1)
        ELSE 999 
    END AS days_of_inventory_remaining
FROM inventory_snapshot i
JOIN products p ON i.stock_code = p.stock_code
LEFT JOIN (
    SELECT stock_code, SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS units_sold
    FROM order_items
    GROUP BY stock_code
) perf ON i.stock_code = perf.stock_code;

-- 6. Profitability View
CREATE OR REPLACE VIEW vw_profitability AS
SELECT
    p.stock_code,
    p.description,
    p.category,
    pc.estimated_unit_cost,
    pc.cost_category,
    COALESCE(perf.net_revenue, 0) AS net_revenue,
    COALESCE(perf.estimated_cogs, 0) AS estimated_cogs,
    COALESCE(perf.estimated_gross_profit, 0) AS estimated_gross_profit,
    COALESCE(perf.estimated_margin_pct, 0) AS estimated_margin_pct,
    CASE 
        WHEN perf.net_revenue > 5000 AND perf.estimated_margin_pct < 15.0 THEN TRUE 
        ELSE FALSE 
    END AS is_high_revenue_low_margin,
    CASE 
        WHEN perf.estimated_gross_profit < 0 THEN TRUE 
        ELSE FALSE 
    END AS is_loss_making
FROM products p
LEFT JOIN product_costs pc ON p.stock_code = pc.stock_code
LEFT JOIN vw_product_performance perf ON p.stock_code = perf.stock_code;

-- 7. Demand Forecast Results View
CREATE OR REPLACE VIEW vw_forecast_results AS
SELECT
    df.forecast_id,
    df.stock_code,
    p.description,
    p.category,
    df.forecast_date,
    df.model_name,
    df.predicted_demand,
    df.lower_bound,
    df.upper_bound,
    df.mae,
    df.rmse,
    df.wape
FROM demand_forecasts df
JOIN products p ON df.stock_code = p.stock_code;

-- 8. Festival Performance View
CREATE OR REPLACE VIEW vw_festival_performance AS
SELECT
    fc.festival_id,
    fc.festival_name,
    fc.start_date,
    fc.end_date,
    fc.festival_category,
    fc.demand_uplift_assumption,
    fc.notes
FROM festival_calendar fc;

-- 9. Promotion Performance View
CREATE OR REPLACE VIEW vw_promotion_performance AS
SELECT
    pc.campaign_id,
    pc.campaign_name,
    pc.promotion_type,
    pc.start_date,
    pc.end_date,
    pc.target_category,
    pc.discount_percentage,
    pc.campaign_budget,
    COUNT(pt.promo_txn_id) AS total_promo_transactions,
    COALESCE(SUM(pt.quantity), 0) AS units_sold_under_promo,
    COALESCE(SUM(pt.final_selling_price * pt.quantity), 0) AS promo_revenue,
    COALESCE(SUM(pt.discount_amount * pt.quantity), 0) AS total_discount_given,
    COALESCE(SUM((pt.final_selling_price - cost.estimated_unit_cost) * pt.quantity), 0) AS estimated_promo_profit,
    CASE 
        WHEN pc.campaign_budget > 0 
        THEN ROUND(
            ((COALESCE(SUM((pt.final_selling_price - cost.estimated_unit_cost) * pt.quantity), 0) - pc.campaign_budget) / pc.campaign_budget) * 100, 
            2
        )
        ELSE 0 
    END AS estimated_promotion_roi_pct
FROM promotion_campaigns pc
LEFT JOIN promotion_transactions pt ON pc.campaign_id = pt.campaign_id
LEFT JOIN product_costs cost ON pt.stock_code = cost.stock_code
GROUP BY pc.campaign_id, pc.campaign_name, pc.promotion_type, pc.start_date, pc.end_date, pc.target_category, pc.discount_percentage, pc.campaign_budget;

-- 10. Business Recommendations View
CREATE OR REPLACE VIEW vw_business_recommendations AS
SELECT
    ba.alert_id,
    ba.alert_category,
    ba.severity,
    ba.affected_entity_type,
    ba.affected_entity_id,
    ba.detected_condition,
    ba.supporting_metric,
    ba.threshold_value,
    ba.suggested_action,
    ba.expected_impact,
    ba.is_active,
    ba.generated_timestamp
FROM business_alerts ba
ORDER BY 
    CASE ba.severity
        WHEN 'Critical' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Low' THEN 4
        ELSE 5
    END ASC,
    ba.generated_timestamp DESC;

-- 11. Data Quality View
CREATE OR REPLACE VIEW vw_data_quality AS
SELECT
    dqr.result_id,
    dqr.batch_id,
    dqr.check_name,
    dqr.metric_category,
    dqr.metric_value,
    dqr.threshold_value,
    dqr.status,
    dqr.details,
    dqr.created_at
FROM data_quality_results dqr
ORDER BY dqr.created_at DESC;
