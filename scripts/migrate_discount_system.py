"""
Database migration: Create discount_offers table and extend bills table.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from decimal import Decimal
from database.connection import get_engine, Base, get_session
from database.models import DiscountOffer, ShopProduct, ShopCategory
from sqlalchemy import text

def run_migration():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session = get_session()

    try:
        # Check bills columns
        res = session.execute(text("PRAGMA table_info(bills)")).fetchall()
        col_names = [r[1] for r in res]
        print(f"Existing columns in 'bills': {col_names}")

        if "discount_id" not in col_names:
            session.execute(text("ALTER TABLE bills ADD COLUMN discount_id INTEGER REFERENCES discount_offers(id)"))
            print("Added discount_id to bills.")
        if "discount_name" not in col_names:
            session.execute(text("ALTER TABLE bills ADD COLUMN discount_name VARCHAR(128)"))
            print("Added discount_name to bills.")
        if "discount_type" not in col_names:
            session.execute(text("ALTER TABLE bills ADD COLUMN discount_type VARCHAR(32)"))
            print("Added discount_type to bills.")
        if "discount_rate" not in col_names:
            session.execute(text("ALTER TABLE bills ADD COLUMN discount_rate NUMERIC(5, 2)"))
            print("Added discount_rate to bills.")

        # Seed initial realistic discounts if table is empty
        count = session.query(DiscountOffer).count()
        if count == 0:
            today = date.today()
            # 1. Active: Weekend Grocery Offer (10% on entire bill above ₹500)
            d1 = DiscountOffer(
                name="Weekend Special (10% Off)",
                discount_type="percentage",
                discount_value=Decimal("10.00"),
                applies_to="entire_bill",
                min_bill_amount=Decimal("500.00"),
                max_discount_amount=Decimal("200.00"),
                start_date=today - timedelta(days=2),
                end_date=today + timedelta(days=5),
                is_active=True,
                description="10% discount on entire bill for purchases above ₹500 (Max discount ₹200)"
            )
            # 2. Active: Flat ₹50 Off on Atta & Staples
            cat_atta = session.query(ShopCategory).filter(ShopCategory.name.like("%Atta%")).first()
            d2 = DiscountOffer(
                name="Flat ₹50 Off on Atta & Grains",
                discount_type="fixed",
                discount_value=Decimal("50.00"),
                applies_to="category",
                target_category_id=cat_atta.id if cat_atta else None,
                min_bill_amount=Decimal("300.00"),
                max_discount_amount=Decimal("50.00"),
                start_date=today - timedelta(days=3),
                end_date=today + timedelta(days=10),
                is_active=True,
                description="Instant ₹50 price deduction on any staple grain or flour purchase above ₹300"
            )
            # 3. Active: 5% General Walk-in Customer Offer
            d3 = DiscountOffer(
                name="Regular Customer 5% Savings",
                discount_type="percentage",
                discount_value=Decimal("5.00"),
                applies_to="entire_bill",
                min_bill_amount=Decimal("100.00"),
                max_discount_amount=Decimal("150.00"),
                start_date=today - timedelta(days=7),
                end_date=today + timedelta(days=21),
                is_active=True,
                description="Everyday 5% discount on bills above ₹100 for regular loyal shoppers"
            )
            # 4. Scheduled: Upcoming Diwali Mega Dhamaka
            d4 = DiscountOffer(
                name="Upcoming Festival Mega Offer (15% Off)",
                discount_type="percentage",
                discount_value=Decimal("15.00"),
                applies_to="entire_bill",
                min_bill_amount=Decimal("1000.00"),
                max_discount_amount=Decimal("500.00"),
                start_date=today + timedelta(days=7),
                end_date=today + timedelta(days=14),
                is_active=True,
                description="Festive celebration 15% discount for bills exceeding ₹1,000"
            )
            # 5. Expired: Previous Month Clearance Offer
            d5 = DiscountOffer(
                name="Last Month Clearance (₹30 Off)",
                discount_type="fixed",
                discount_value=Decimal("30.00"),
                applies_to="entire_bill",
                min_bill_amount=Decimal("200.00"),
                start_date=today - timedelta(days=30),
                end_date=today - timedelta(days=5),
                is_active=False,
                description="Expired seasonal inventory clearance offer"
            )
            session.add_all([d1, d2, d3, d4, d5])
            print("Seeded 5 sample discount offers.")

        session.commit()
        print("[SUCCESS] Discount system database migration completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
