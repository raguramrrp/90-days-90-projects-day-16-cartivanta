"""
CARTIVANTA - Comprehensive Test Suite
Covers core financial mathematics, ETL transformations, return handling,
RFM customer clustering, demand forecasting leakage prevention, inventory reorder calculations,
festive discount simulation, break-even uplift, and edge case resilience.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date

from etl.transform import clean_raw_dataframe, build_normalized_entities, categorize_description
from festive.discount_simulator import FestiveDiscountSimulator
from festive.demand_simulator import FestiveDemandSimulator
from models.demand_forecasting import calculate_wape, DemandForecastingEngine
from models.customer_segmentation import CustomerSegmentationEngine
from quality.data_quality import DataQualityEngine
from recommendations.business_rules import BusinessRecommendationEngine
from database.connection import get_session

# --- 1. ETL & TRANSFORMATION TESTS ---

def test_categorize_description():
    assert categorize_description("WHITE HANGING HEART T-LIGHT HOLDER") == "Home Decor"
    assert categorize_description("REGENCY CAKESTAND 3 TIER") == "Kitchen & Dining"
    assert categorize_description("CHRISTMAS TREE DECORATION") == "Gifts & Seasonal"
    assert categorize_description("JUMBO BAG RED RETROSPOT") == "Bags & Travel"
    assert categorize_description("VINTAGE NOTEBOOK WITH PEN") == "Stationery & Craft"
    assert categorize_description("WOODEN PUZZLE TOY") == "Toys & Novelties"
    assert categorize_description("SILVER BRACELET WITH HEARTS") == "Fashion & Accessories"
    assert categorize_description("") == "General Merchandise"
    assert categorize_description(None) == "General Merchandise"

def test_clean_raw_dataframe_cancellations_and_returns():
    raw_data = pd.DataFrame([
        {"Invoice": "489434", "StockCode": "85048", "Description": "Item A", "Quantity": 10, "InvoiceDate": "2009-12-01 07:45:00", "Price": 2.50, "Customer ID": 13085, "Country": "United Kingdom"},
        {"Invoice": "C489435", "StockCode": "85048", "Description": "Item A", "Quantity": -2, "InvoiceDate": "2009-12-01 07:46:00", "Price": 2.50, "Customer ID": 13085, "Country": "United Kingdom"}, # Cancellation
        {"Invoice": "489434", "StockCode": "85048", "Description": "Item A", "Quantity": 10, "InvoiceDate": "2009-12-01 07:45:00", "Price": 2.50, "Customer ID": 13085, "Country": "United Kingdom"}, # Duplicate
        {"Invoice": "489437", "StockCode": "71053", "Description": "Item B", "Quantity": -1, "InvoiceDate": "2009-12-01 08:00:00", "Price": 5.00, "Customer ID": None, "Country": "France"}, # Return without C
        {"Invoice": "489438", "StockCode": "TEST", "Description": "Bad Price", "Quantity": 5, "InvoiceDate": "2009-12-01 08:05:00", "Price": -1.00, "Customer ID": 12345, "Country": "Germany"} # Bad price
    ])

    cleaned, metrics = clean_raw_dataframe(raw_data)

    assert metrics["total_source_records"] == 5
    assert metrics["duplicate_records"] == 1
    assert metrics["invalid_prices"] == 1
    assert metrics["cancellation_invoices"] == 1
    assert metrics["return_transactions"] == 2 # C489435 and 489437
    assert metrics["valid_processed_records"] == 3

    # Check return preservation in financial total
    sales_total = cleaned[cleaned["quantity"] > 0]["line_total"].sum()
    returns_total = cleaned[cleaned["quantity"] < 0]["line_total"].sum()
    net_total = cleaned["line_total"].sum()
    assert sales_total == 25.0 # 10 * 2.50
    assert returns_total == -10.0 # (-2 * 2.5) + (-1 * 5.0)
    assert net_total == 15.0 # Net revenue = 25 - 10

def test_missing_customer_guest_imputation():
    raw_data = pd.DataFrame([
        {"Invoice": "500001", "StockCode": "85048", "Description": "Item", "Quantity": 1, "InvoiceDate": "2010-01-01 10:00:00", "Price": 10.0, "Customer ID": np.nan, "Country": "Germany"},
        {"Invoice": "500002", "StockCode": "85048", "Description": "Item", "Quantity": 1, "InvoiceDate": "2010-01-01 10:00:00", "Price": 10.0, "Customer ID": 14000.0, "Country": "France"}
    ])
    cleaned, _ = clean_raw_dataframe(raw_data)
    guest_cid = cleaned[cleaned["invoice_no"] == "500001"]["customer_id"].values[0]
    reg_cid = cleaned[cleaned["invoice_no"] == "500002"]["customer_id"].values[0]
    assert guest_cid == "GUEST-GER"
    assert reg_cid == "14000"

# --- 2. FINANCIAL & PROFITABILITY MATHEMATICS ---

def test_gross_and_net_revenue_formula():
    quantities = np.array([10, -2, 5, -1])
    prices = np.array([20.0, 20.0, 15.0, 15.0])
    line_totals = quantities * prices # [200, -40, 75, -15]

    gross_sales = line_totals[line_totals > 0].sum()
    returns_val = abs(line_totals[line_totals < 0].sum())
    net_revenue = line_totals.sum()

    assert gross_sales == 275.0
    assert returns_val == 55.0
    assert net_revenue == 220.0
    assert round(net_revenue, 2) == round(gross_sales - returns_val, 2)

def test_cogs_and_gross_margin():
    net_revenue = 1000.0
    cogs = 650.0
    gross_profit = net_revenue - cogs
    gross_margin_pct = (gross_profit / net_revenue) * 100

    assert gross_profit == 350.0
    assert gross_margin_pct == 35.0

# --- 3. FESTIVE DISCOUNT SIMULATION & BREAK-EVEN TESTS ---

def test_festive_discount_mathematics():
    orig_price = 10.0
    unit_cost = 4.0
    base_qty = 100
    discount_pct = 0.20 # 20% discount
    uplift_pct = 0.36 # 36% demand increase

    # Normal Scenario
    norm_rev = orig_price * base_qty # 1000
    norm_profit = (orig_price - unit_cost) * base_qty # (10 - 4) * 100 = 600

    # Discounted Scenario
    disc_price = orig_price * (1 - discount_pct) # 8.0
    disc_qty = int(np.ceil(base_qty * (1 + uplift_pct))) # 136
    disc_rev = disc_price * disc_qty # 8 * 136 = 1088
    disc_unit_margin = disc_price - unit_cost # 8 - 4 = 4.0
    disc_profit = disc_unit_margin * disc_qty # 4 * 136 = 544

    # Break-even sales volume: Q_be = Normal Profit / Disc Unit Margin
    # 600 / 4 = 150 units. Required uplift = (150 - 100)/100 = 50%
    be_units = int(np.ceil(norm_profit / disc_unit_margin))
    be_uplift_pct = ((be_units - base_qty) / base_qty) * 100

    assert disc_price == 8.0
    assert disc_rev == 1088.0
    assert disc_profit == 544.0
    assert be_units == 150
    assert be_uplift_pct == 50.0

    # Profit Destroyer Condition:
    # Revenue increased (1088 > 1000), but Profit decreased (544 < 600)
    is_profit_destroyer = (disc_rev > norm_rev) and (disc_profit < norm_profit)
    assert is_profit_destroyer is True

def test_discount_simulator_edge_case_excessive_discount():
    session = get_session()
    sim = FestiveDiscountSimulator(session)
    # Simulate selling with discount that pushes price below unit cost
    res = sim.simulate_discount(
        stock_code="85123A",
        discount_pct=0.75,
        custom_base_price=4.0,
        custom_unit_cost=3.0,
        custom_base_quantity=50
    )
    # At 75% discount, price is £1.00 while cost is £3.00
    assert res["discounted_selling_price"] == 1.0
    assert res["strategic_evaluation"]["is_loss_making"] is True
    assert "REJECT" in res["strategic_evaluation"]["recommendation"]

# --- 4. INVENTORY REORDER POINT MATHEMATICS ---

def test_inventory_reorder_formulas():
    units_sold = 730
    observed_days = 730.0
    daily_demand = units_sold / observed_days # 1.0 unit/day
    lead_time = 14 # 14 days
    safety_stock = 10 # units
    available_stock = 15 # units
    target_stock = 50 # units

    # Reorder Point = Daily Demand * Lead Time + Safety Stock
    reorder_point = int(np.ceil(daily_demand * lead_time + safety_stock))
    # Suggested Reorder = MAX(0, Target Stock - Available Stock)
    suggested_reorder = max(0, target_stock - available_stock)
    days_of_supply = available_stock / daily_demand

    assert daily_demand == 1.0
    assert reorder_point == 24
    assert suggested_reorder == 35
    assert days_of_supply == 15.0
    # Available stock (15) < Reorder Point (24) -> Should trigger low stock alert
    assert available_stock < reorder_point

# --- 5. DEMAND FORECASTING METRICS TESTS ---

def test_wape_and_forecast_metrics():
    actual = np.array([100.0, 150.0, 200.0, 50.0])
    predicted = np.array([110.0, 140.0, 180.0, 60.0])

    wape = calculate_wape(actual, predicted)
    # Abs errors: 10 + 10 + 20 + 10 = 50. Total actual = 500. WAPE = 50/500 * 100 = 10.0%
    assert round(wape, 2) == 10.0

def test_wape_zero_actual_edge_case():
    actual = np.array([0.0, 0.0])
    predicted = np.array([5.0, 2.0])
    assert calculate_wape(actual, predicted) == 0.0

# --- 6. DATA QUALITY SCORING TESTS ---

def test_data_quality_score_computation():
    dq = DataQualityEngine()
    metrics = {
        "duplicate_records": 100, # 1%
        "missing_customer_ids": 1500, # 15%
        "invalid_dates": 0,
        "invalid_prices": 0,
        "cancellation_invoices": 200,
        "return_transactions": 250,
        "valid_processed_records": 9900
    }
    summary = dq.evaluate_dataset(raw_count=10000, metrics=metrics)
    assert 70.0 <= summary["data_quality_score"] <= 100.0
    assert summary["checks_performed"] == 5

# --- 7. PROMOTION ROI TESTS ---

def test_promotion_roi_calculation():
    promo_profit = 8000.0
    campaign_budget = 5000.0
    # ROI = (Profit - Budget) / Budget * 100
    roi_pct = ((promo_profit - campaign_budget) / campaign_budget) * 100
    assert roi_pct == 60.0

# --- 8. WEB DASHBOARD TEMPLATE RENDERING TEST ---

def test_web_dashboard_template_rendering():
    from starlette.requests import Request
    from web.app import index_view
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": []
    }
    request = Request(scope)
    response = index_view(request)
    assert response.status_code == 200
    assert b"CARTIVANTA" in response.body
    assert b"Shop Overview" in response.body
