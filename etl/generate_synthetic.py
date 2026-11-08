"""
CARTIVANTA - Synthetic Supporting Data Generator
Generates reproducible synthetic supporting datasets for retail intelligence:
- product_costs.csv
- inventory_snapshot.csv
- promotion_campaigns.csv
- promotion_transactions.csv
- festival_calendar.csv

All generated records are explicitly marked is_synthetic=True.
Uses fixed random seed 42 for 100% reproducibility.
"""
import random
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np
import pandas as pd
from config.settings import SYNTHETIC_DATA_DIR, RANDOM_SEED
from festive.festival_calendar import DEFAULT_FESTIVALS

logger = logging.getLogger("cartivanta.synthetic")

# Baseline sample products in case generation is run before UCI extraction
SEED_PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55, "Home Decor"),
    ("71053", "WHITE METAL LANTERN", 3.39, "Home Decor"),
    ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75, "Home Accessories"),
    ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.39, "Seasonal & Gifts"),
    ("84029E", "RED WOOLLY HOTTIE WHITE HEART.", 3.39, "Seasonal & Gifts"),
    ("22752", "SET 7 BABUSHKA NESTING BOXES", 8.50, "Gifts & Novelties"),
    ("21733", "RED HANGING HEART T-LIGHT HOLDER", 2.55, "Home Decor"),
    ("22848", "BREAD BIN DINER STYLE RED", 16.95, "Kitchenware"),
    ("22834", "HAND WARMER BABUSHKA DESIGN", 2.10, "Seasonal & Gifts"),
    ("22837", "HOT WATER BOTTLE BABUSHKA", 4.65, "Seasonal & Gifts"),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75, "Kitchen & Dining"),
    ("47566", "PARTY BUNTING", 4.95, "Party & Events"),
    ("85099B", "JUMBO BAG RED RETROSPOT", 1.95, "Bags & Luggage"),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65, "Bags & Luggage"),
    ("20727", "LUNCH BAG BLACK SKULL.", 1.65, "Bags & Luggage"),
    ("20728", "LUNCH BAG CARS BLUE", 1.65, "Bags & Luggage"),
    ("22383", "LUNCH BAG SUKI DESIGN", 1.65, "Bags & Luggage"),
    ("22384", "LUNCH BAG PINK POLKADOT", 1.65, "Bags & Luggage"),
    ("20726", "LUNCH BAG WOODLAND", 1.65, "Bags & Luggage"),
    ("22382", "LUNCH BAG SPACEBOY DESIGN", 1.65, "Bags & Luggage"),
]

def generate_product_costs(products_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Generate product_costs with realistic COGS margins."""
    rng = np.random.default_rng(RANDOM_SEED)
    records = []

    if products_df is not None and not products_df.empty:
        items = products_df[["stock_code", "unit_price"]].drop_duplicates("stock_code")
        for _, row in items.iterrows():
            code = str(row["stock_code"])
            price = float(row["unit_price"]) if row["unit_price"] > 0 else 2.50
            # Cost multiplier between 0.40 and 0.72 (28% to 60% gross margin)
            cost_factor = rng.uniform(0.40, 0.72)
            unit_cost = round(price * cost_factor, 4)
            if cost_factor < 0.50:
                cost_cat = "High Margin"
            elif cost_factor < 0.65:
                cost_cat = "Balanced"
            else:
                cost_cat = "Low Margin"

            records.append({
                "stock_code": code,
                "estimated_unit_cost": unit_cost,
                "cost_category": cost_cat,
                "is_synthetic": True,
                "effective_date": "2010-01-01"
            })
    else:
        for code, _, price, _ in SEED_PRODUCTS:
            cost_factor = rng.uniform(0.40, 0.70)
            records.append({
                "stock_code": code,
                "estimated_unit_cost": round(price * cost_factor, 4),
                "cost_category": "Balanced" if cost_factor < 0.60 else "Low Margin",
                "is_synthetic": True,
                "effective_date": "2010-01-01"
            })

    df = pd.DataFrame(records).drop_duplicates("stock_code")
    return df

def generate_inventory_snapshot(products_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Generate inventory_snapshot with realistic stock, safety stock, and reorder metrics."""
    rng = np.random.default_rng(RANDOM_SEED + 1)
    records = []

    codes = []
    if products_df is not None and not products_df.empty:
        codes = products_df["stock_code"].astype(str).unique().tolist()
    else:
        codes = [item[0] for item in SEED_PRODUCTS]

    statuses = ["Healthy", "Low", "Critical", "Overstocked", "Dead Stock"]
    status_weights = [0.60, 0.18, 0.08, 0.10, 0.04]

    for code in codes:
        lead_time = int(rng.choice([5, 7, 10, 14, 21]))
        daily_demand = rng.uniform(2.0, 35.0)
        safety_stock = int(np.ceil(daily_demand * 7))
        target_stock = int(np.ceil(safety_stock + (daily_demand * lead_time * 2)))
        
        status = rng.choice(statuses, p=status_weights)
        if status == "Critical":
            available_stock = int(rng.uniform(0, safety_stock * 0.4))
        elif status == "Low":
            available_stock = int(rng.uniform(safety_stock * 0.5, safety_stock + (daily_demand * lead_time)))
        elif status == "Healthy":
            available_stock = int(rng.uniform(safety_stock + (daily_demand * lead_time), target_stock * 1.1))
        elif status == "Overstocked":
            available_stock = int(rng.uniform(target_stock * 1.4, target_stock * 2.5))
        else: # Dead Stock
            available_stock = int(rng.uniform(50, 300))

        records.append({
            "stock_code": str(code),
            "available_stock": max(0, available_stock),
            "safety_stock": safety_stock,
            "supplier_lead_time_days": lead_time,
            "target_stock": target_stock,
            "last_restock_date": str(date(2011, 10, int(rng.integers(1, 28)))),
            "inventory_health_status": status,
            "is_synthetic": True,
            "snapshot_date": "2011-12-09"
        })

    return pd.DataFrame(records).drop_duplicates("stock_code")

def generate_promotion_campaigns() -> pd.DataFrame:
    """Generate promotion campaigns."""
    campaigns = [
        {
            "campaign_id": "CMP-2010-01",
            "campaign_name": "Autumn Festive Lighting & Lantern Blitz",
            "promotion_type": "Festive",
            "start_date": "2010-10-15",
            "end_date": "2010-11-15",
            "target_category": "Home Decor",
            "discount_percentage": 0.15,
            "campaign_budget": 5000.0,
            "is_synthetic": True
        },
        {
            "campaign_id": "CMP-2010-02",
            "campaign_name": "Christmas Grand Joy Mega Sale",
            "promotion_type": "Seasonal",
            "start_date": "2010-12-01",
            "end_date": "2010-12-24",
            "target_category": "Gifts & Novelties",
            "discount_percentage": 0.20,
            "campaign_budget": 12000.0,
            "is_synthetic": True
        },
        {
            "campaign_id": "CMP-2011-01",
            "campaign_name": "New Year Home Renewal Special",
            "promotion_type": "Clearance",
            "start_date": "2011-01-02",
            "end_date": "2011-01-20",
            "target_category": "Kitchenware",
            "discount_percentage": 0.25,
            "campaign_budget": 3500.0,
            "is_synthetic": True
        },
        {
            "campaign_id": "CMP-2011-02",
            "campaign_name": "Diwali Golden Radiance Gifting Fest",
            "promotion_type": "Festive",
            "start_date": "2011-10-10",
            "end_date": "2011-11-05",
            "target_category": "Seasonal & Gifts",
            "discount_percentage": 0.18,
            "campaign_budget": 8500.0,
            "is_synthetic": True
        },
        {
            "campaign_id": "CMP-2011-03",
            "campaign_name": "Black Friday & Cyber Week Countdown",
            "promotion_type": "Flash",
            "start_date": "2011-11-20",
            "end_date": "2011-11-30",
            "target_category": "General Merchandise",
            "discount_percentage": 0.30,
            "campaign_budget": 15000.0,
            "is_synthetic": True
        }
    ]
    return pd.DataFrame(campaigns)

def generate_promotion_transactions(campaigns_df: pd.DataFrame, products_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Generate promotion_transactions tied to campaigns."""
    rng = np.random.default_rng(RANDOM_SEED + 2)
    records = []

    catalog = []
    if products_df is not None and not products_df.empty:
        for _, r in products_df[["stock_code", "unit_price"]].drop_duplicates("stock_code").head(100).iterrows():
            catalog.append((str(r["stock_code"]), float(r["unit_price"]) if r["unit_price"] > 0 else 3.50))
    else:
        catalog = [(code, price) for code, _, price, _ in SEED_PRODUCTS]

    for _, camp in campaigns_df.iterrows():
        c_id = camp["campaign_id"]
        disc_pct = float(camp["discount_percentage"])
        num_txns = int(rng.integers(120, 300))
        
        for i in range(num_txns):
            item_code, orig_price = catalog[rng.integers(0, len(catalog))]
            disc_amt = round(orig_price * disc_pct, 4)
            final_price = round(orig_price - disc_amt, 4)
            qty = int(rng.integers(2, 25))

            records.append({
                "invoice_no": f"PRM-{c_id.split('-')[-1]}-{10000+i}",
                "stock_code": item_code,
                "campaign_id": c_id,
                "original_price": orig_price,
                "discount_percentage": disc_pct,
                "discount_amount": disc_amt,
                "final_selling_price": final_price,
                "quantity": qty,
                "is_synthetic": True
            })

    return pd.DataFrame(records)

def generate_all_synthetic(products_df: Optional[pd.DataFrame] = None, output_dir: Path = SYNTHETIC_DATA_DIR):
    """Generate and persist all synthetic datasets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating synthetic datasets with seed=%d...", RANDOM_SEED)

    # 1. Product Costs
    costs_df = generate_product_costs(products_df)
    costs_path = output_dir / "product_costs.csv"
    costs_df.to_csv(costs_path, index=False)
    logger.info("Saved %d records to %s", len(costs_df), costs_path.name)

    # 2. Inventory Snapshot
    inv_df = generate_inventory_snapshot(products_df)
    inv_path = output_dir / "inventory_snapshot.csv"
    inv_df.to_csv(inv_path, index=False)
    logger.info("Saved %d records to %s", len(inv_df), inv_path.name)

    # 3. Festival Calendar
    fest_df = pd.DataFrame([
        {
            "festival_name": f.festival_name,
            "start_date": f.start_date,
            "end_date": f.end_date,
            "festival_category": f.festival_category,
            "demand_uplift_assumption": f.demand_uplift_assumption,
            "notes": f.notes,
            "is_synthetic": True
        }
        for f in DEFAULT_FESTIVALS
    ])
    fest_path = output_dir / "festival_calendar.csv"
    fest_df.to_csv(fest_path, index=False)
    logger.info("Saved %d records to %s", len(fest_df), fest_path.name)

    # 4. Promotion Campaigns
    camp_df = generate_promotion_campaigns()
    camp_path = output_dir / "promotion_campaigns.csv"
    camp_df.to_csv(camp_path, index=False)
    logger.info("Saved %d records to %s", len(camp_df), camp_path.name)

    # 5. Promotion Transactions
    promo_txn_df = generate_promotion_transactions(camp_df, products_df)
    promo_path = output_dir / "promotion_transactions.csv"
    promo_txn_df.to_csv(promo_path, index=False)
    logger.info("Saved %d records to %s", len(promo_txn_df), promo_path.name)

    return {
        "product_costs": costs_path,
        "inventory_snapshot": inv_path,
        "festival_calendar": fest_path,
        "promotion_campaigns": camp_path,
        "promotion_transactions": promo_path
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_all_synthetic()
