"""
CARTIVANTA - Initialize Operational Retail Schema
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from database.connection import get_engine, Base
import database.models as models

def main():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Base.metadata.create_all completed successfully.")

    conn = sqlite3.connect('data/cartivanta.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Total tables in database: {len(tables)}")
    operational_tables = [
        'shop_profiles', 'users', 'shop_categories', 'suppliers', 'shop_products',
        'bills', 'bill_items', 'purchases', 'purchase_items', 'stock_movements',
        'shop_customers', 'customer_credit_transactions', 'supplier_payments',
        'expenses', 'festive_campaigns', 'audit_logs'
    ]
    present = [t for t in operational_tables if t in tables]
    print(f"Operational tables present ({len(present)}/{len(operational_tables)}):", present)
    conn.close()

if __name__ == "__main__":
    main()
