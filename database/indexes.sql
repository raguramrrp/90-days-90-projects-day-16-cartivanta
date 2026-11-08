-- ============================================================================
-- CARTIVANTA: Performance Indexes
-- ============================================================================

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_invoice_date ON orders(invoice_date);
CREATE INDEX idx_orders_country ON orders(country);
CREATE INDEX idx_orders_is_cancelled ON orders(is_cancelled);

CREATE INDEX idx_order_items_invoice_no ON order_items(invoice_no);
CREATE INDEX idx_order_items_stock_code ON order_items(stock_code);
CREATE INDEX idx_order_items_is_return ON order_items(is_return);

CREATE INDEX idx_customers_country ON customers(country);

CREATE INDEX idx_products_category ON products(category);

CREATE INDEX idx_inventory_stock_code ON inventory_snapshot(stock_code);
CREATE INDEX idx_inventory_status ON inventory_snapshot(inventory_health_status);

CREATE INDEX idx_forecasts_stock_code_date ON demand_forecasts(stock_code, forecast_date);

CREATE INDEX idx_customer_segments_segment ON customer_segments(segment_name);

CREATE INDEX idx_business_alerts_severity ON business_alerts(severity);
CREATE INDEX idx_business_alerts_category ON business_alerts(alert_category);

CREATE INDEX idx_promotion_txns_campaign ON promotion_transactions(campaign_id);
CREATE INDEX idx_promotion_txns_stock ON promotion_transactions(stock_code);
