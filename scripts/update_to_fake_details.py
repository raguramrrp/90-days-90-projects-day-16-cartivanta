"""
Update all store details, customer names, staff names, supplier information,
and addresses in data/cartivanta.db to strictly unreal / demo values.
Store Name: RR Supermarket
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import get_session
from database.models import ShopProfile, User, ShopCustomer, Supplier, Expense, ShopProduct

def update_database_records():
    session = get_session()
    try:
        # 1. Shop Profile
        profile = session.query(ShopProfile).first()
        if profile:
            profile.shop_name = "RR Supermarket"
            profile.tagline = "Quality Daily Needs, Groceries & Provisions (Demo Store)"
            profile.phone = "+91 99999 00000"
            profile.address = "Shop 101, Fictional Commercial Ring Road, Sector 0, Unreal Nagar, Fantasy City - 000000"
            profile.gstin = "00XXXXX0000X1Z5"
            profile.receipt_footer = "Thank you for shopping at RR Supermarket! Visit again. Save Paper, Save Trees."
            profile.currency = "INR"
            profile.currency_symbol = "₹"
            print("Updated ShopProfile to RR Supermarket with unreal details.")

        # 2. Staff Accounts
        owner = session.query(User).filter(User.username == "admin").first()
        if owner:
            owner.full_name = "RR Store Manager (Admin)"
        
        cashier = session.query(User).filter(User.username == "cashier").first()
        if cashier:
            cashier.full_name = "RR Cashier (Counter 1)"

        other_users = session.query(User).filter(~User.username.in_(["admin", "cashier"])).all()
        for u in other_users:
            u.full_name = f"RR Staff Member ({u.username})"
        print("Updated Staff Accounts.")

        # 3. Customer Accounts - Rename all to generic dummy names
        all_custs = session.query(ShopCustomer).order_by(ShopCustomer.id).all()
        labels = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota"]
        
        for idx, c in enumerate(all_custs):
            label = labels[idx % len(labels)]
            num_suffix = f"{idx + 1:04d}"
            c.name = f"Customer {label} ({num_suffix})"
            c.phone = f"990000{num_suffix}"
            c.address = f"House {idx + 1}, Demo Avenue, Unreal City"
        print(f"Updated {len(all_custs)} Customer accounts with unreal details.")

        # 4. Suppliers
        sup_updates = [
            ("Apex Wholesale Staples (Demo)", "+91 99000 00011", "orders@demo-apex.local", "Plot 1, Unreal Logistics Park, Fantasy City", "00SUPP000001Z1"),
            ("Metro Provisions Depot (Demo)", "+91 99000 00012", "depot@demo-metro.local", "Plot 2, Unreal Logistics Park, Fantasy City", "00SUPP000002Z2"),
            ("National Dairy & Provisions Hub (Demo)", "+91 99000 00013", "agency@demo-dairy.local", "Plot 3, Unreal Logistics Park, Fantasy City", "00SUPP000003Z3"),
            ("Quality Edible Oils Depot (Demo)", "+91 99000 00014", "supply@demo-oils.local", "Plot 4, Unreal Logistics Park, Fantasy City", "00SUPP000004Z4"),
            ("Central General & Stationery Hub (Demo)", "+91 99000 00015", "wholesale@demo-stationery.local", "Plot 5, Unreal Logistics Park, Fantasy City", "00SUPP000005Z5")
        ]
        all_sups = session.query(Supplier).order_by(Supplier.id).all()
        for s_idx, s in enumerate(all_sups):
            if s_idx < len(sup_updates):
                name, phone, email, addr, gstin = sup_updates[s_idx]
                s.name = name
                s.phone = phone
                s.email = email
                s.address = addr
                s.gstin = gstin
            else:
                s.name = f"Wholesale Supplier #{s_idx + 1} (Demo)"
                s.phone = f"+91 99000 000{s_idx + 10}"
                s.email = f"supplier{s_idx + 1}@demo.local"
                s.address = f"Plot {s_idx + 1}, Unreal Logistics Park, Fantasy City"
                s.gstin = f"00SUPP{s_idx + 10:06d}Z1"
        print("Updated Suppliers with unreal details.")

        # 5. Expenses
        expenses = session.query(Expense).all()
        for e in expenses:
            if "Jayanagar" in (e.description or ""):
                e.description = e.description.replace("Jayanagar", "Unreal Commercial Hub")

        # 6. Products
        products = session.query(ShopProduct).all()
        for p in products:
            if p.brand == "Sri Lakshmi":
                p.brand = "RR Select"

        session.commit()
        print("[SUCCESS] All database records sanitized with fake / unreal details and store name RR Supermarket!")
    except Exception as ex:
        session.rollback()
        print(f"[ERROR] Failed to update records: {ex}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    update_database_records()
