"""
CARTIVANTA - ETL Transform Module
Cleans, normalizes, validates, and models UCI Online Retail II raw records into
analytics-ready entities: customers, products, orders, and order_items.
Preserves return transactions and financial impacts without data loss.
"""
import re
import logging
from typing import Dict, Tuple, Optional, List
import numpy as np
import pandas as pd

logger = logging.getLogger("cartivanta.etl.transform")

# Standard Column Mapping
COLUMN_RENAME_MAP = {
    "Invoice": "invoice_no",
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "UnitPrice": "unit_price",
    "Customer ID": "customer_id",
    "CustomerID": "customer_id",
    "Country": "country"
}

def categorize_description(description: str) -> str:
    """Classify product into category using description keywords."""
    if not isinstance(description, str) or not description.strip():
        return "General Merchandise"

    desc = description.upper()
    if any(k in desc for k in ["BRACELET", "NECKLACE", "EARRINGS", "JEWELLERY", "RING", "SCARF", "GLOVES", "SOCKS", "HAT"]):
        return "Fashion & Accessories"
    elif any(k in desc for k in ["HEART", "LANTERN", "LIGHT", "CANDLE", "CLOCK", "MIRROR", "FRAME", "CUSHION", "SIGN"]):
        return "Home Decor"
    elif any(k in desc for k in ["MUG", "CUP", "PLATE", "BOWL", "TEAPOT", "JAR", "BREAD BIN", "BAKING", "CUTLERY", "FORK", "SPOON", "TRAY", "CAKE"]):
        return "Kitchen & Dining"
    elif any(k in desc for k in ["CHRISTMAS", "XMAS", "TREE", "STAR", "WARMER", "HOT WATER", "EASTER", "HALLOWEEN", "FESTIVE", "SNOW"]):
        return "Gifts & Seasonal"
    elif any(k in desc for k in ["BAG", "PURSE", "TOTE", "WALLET", "LUNCH BAG", "JUMBO BAG", "SUITCASE", "LUGGAGE"]):
        return "Bags & Travel"
    elif any(k in desc for k in ["NOTEBOOK", "PEN", "PENCIL", "ERASER", "CARD", "WRAP", "PAPER", "RIBBON", "TAPE", "BOX", "TIN"]):
        return "Stationery & Craft"
    elif any(k in desc for k in ["TOY", "GAME", "DOLL", "BABUSHKA", "PUZZLE", "PLAYING CARDS", "BUBBLE", "STICKER"]):
        return "Toys & Novelties"
    elif any(k in desc for k in ["SCARF", "GLOVES", "SOCKS", "HAT", "JEWELLERY", "BRACELET", "NECKLACE", "EARRINGS"]):
        return "Fashion & Accessories"
    else:
        return "General Merchandise"

def clean_raw_dataframe(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Standardize, validate, and clean raw dataset.
    Returns cleaned dataframe and transformation metrics for data quality auditing.
    """
    df = raw_df.copy()
    
    # 1. Rename columns
    df = df.rename(columns=lambda c: COLUMN_RENAME_MAP.get(c.strip(), c.strip()))
    
    total_source_records = len(df)
    
    # 2. Check and log duplicates
    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates()
    
    # 3. Clean invoice numbers & identify cancellations
    df["invoice_no"] = df["invoice_no"].astype(str).str.strip()
    df["is_cancelled"] = df["invoice_no"].str.startswith("C", na=False)
    
    # 4. Clean customer_id (preserve unregistered guest transactions as GUEST-<Country>)
    df["raw_customer_id"] = df["customer_id"]
    missing_customer_count = int(df["customer_id"].isna().sum())
    
    def format_customer_id(val, country):
        if pd.isna(val) or str(val).strip() in ("", "nan", "None", "NaN"):
            # Mark unregistered guest with country identifier for grouping
            country_code = str(country).strip()[:3].upper() if pd.notna(country) else "UNK"
            return f"GUEST-{country_code}"
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            return str(val).strip()

    df["customer_id"] = [format_customer_id(cid, ctry) for cid, ctry in zip(df["customer_id"], df["country"])]
    df["is_registered_customer"] = ~df["customer_id"].str.startswith("GUEST-")
    
    # 5. Clean stock codes & descriptions
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description"] = df["description"].fillna("UNSPECIFIED PRODUCT").astype(str).str.strip()
    
    # 6. Parse dates
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    invalid_dates_count = int(df["invoice_date"].isna().sum())
    df = df.dropna(subset=["invoice_date"])
    
    # 7. Clean quantities and prices
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0).astype(float)
    
    # Eliminate non-commercial manual adjustments (negative unit prices or stock codes like 'B', 'AMAZONFEE')
    invalid_price_count = int((df["unit_price"] < 0).sum())
    df = df[df["unit_price"] >= 0]
    
    # Remove system administrative codes that are not products
    administrative_codes = {"POST", "D", "M", "CRUK", "BANK CHARGES", "TEST001", "TEST002"}
    df = df[~df["stock_code"].isin(administrative_codes)]
    
    # 8. Classify returns
    # A transaction is a return if quantity < 0 or invoice starts with 'C'
    df["is_return"] = (df["quantity"] < 0) | df["is_cancelled"]
    
    # Financial line total: quantity * unit_price (negative for returns)
    df["line_total"] = np.round(df["quantity"] * df["unit_price"], 4)
    
    # Clean country
    df["country"] = df["country"].fillna("Unspecified").astype(str).str.strip()
    
    # Assign category
    df["category"] = df["description"].apply(categorize_description)
    
    metrics = {
        "total_source_records": total_source_records,
        "duplicate_records": duplicate_count,
        "missing_customer_ids": missing_customer_count,
        "invalid_dates": invalid_dates_count,
        "invalid_prices": invalid_price_count,
        "cancellation_invoices": int(df["is_cancelled"].sum()),
        "return_transactions": int(df["is_return"].sum()),
        "valid_processed_records": len(df)
    }
    
    return df, metrics

def build_normalized_entities(cleaned_df: pd.DataFrame, costs_df: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
    """
    Split cleaned transaction log into normalized relational tables:
    - customers
    - products
    - orders
    - order_items
    """
    logger.info("Building normalized relational entities...")
    
    # 1. Customers Table
    customers_grouped = cleaned_df.groupby("customer_id").agg(
        first_invoice_date=("invoice_date", "min"),
        last_invoice_date=("invoice_date", "max"),
        country=("country", "last"),
        is_registered=("is_registered_customer", "first")
    ).reset_index()
    
    # 2. Products Table
    products_grouped = cleaned_df.groupby("stock_code").agg(
        description=("description", "last"),
        category=("category", "last"),
        first_seen_date=("invoice_date", "min"),
        last_seen_date=("invoice_date", "max"),
        unit_price=("unit_price", "median")
    ).reset_index()
    products_grouped["is_active"] = True

    # 3. Orders Table
    orders_grouped = cleaned_df.groupby("invoice_no").agg(
        customer_id=("customer_id", "first"),
        invoice_date=("invoice_date", "first"),
        country=("country", "first"),
        is_cancelled=("is_cancelled", "any"),
        total_line_items=("stock_code", "count"),
        gross_order_value=("line_total", lambda s: np.round(s[s > 0].sum(), 4)),
        net_order_value=("line_total", lambda s: np.round(s.sum(), 4))
    ).reset_index()

    # 4. Order Items Table
    order_items = cleaned_df[[
        "invoice_no", "stock_code", "description", "quantity", 
        "unit_price", "line_total", "is_return"
    ]].copy()
    
    # Merge estimated unit cost if provided
    if costs_df is not None and not costs_df.empty:
        costs_map = dict(zip(costs_df["stock_code"].astype(str), costs_df["estimated_unit_cost"].astype(float)))
        default_cost_factor = 0.55
        
        # Vectorized cost assignment
        unit_costs = order_items["stock_code"].map(costs_map).fillna(order_items["unit_price"] * default_cost_factor)
        order_items["estimated_cost_total"] = np.round(unit_costs * order_items["quantity"].abs(), 4)
        order_items["estimated_profit"] = np.where(
            order_items["quantity"] > 0,
            np.round(order_items["line_total"] - order_items["estimated_cost_total"], 4),
            np.round(order_items["line_total"], 4)
        )
    else:
        # Default 50% cost estimate
        order_items["estimated_cost_total"] = np.round(order_items["line_total"].abs() * 0.50, 4)
        order_items["estimated_profit"] = np.round(order_items["line_total"] - order_items["estimated_cost_total"], 4)

    return {
        "customers": customers_grouped,
        "products": products_grouped,
        "orders": orders_grouped,
        "order_items": order_items
    }
