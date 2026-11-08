"""
CARTIVANTA - Indian Retail Demo Seed Data Generator
Populates realistic FMCG products, suppliers, customers, categories,
initial stock movements, sample bills, and expenses in INR (₹).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, date, timedelta
from decimal import Decimal
from database.connection import get_session, get_engine, Base
from database.models import (
    ShopProfile, User, ShopCategory, Supplier, ShopProduct,
    ShopCustomer, Bill, BillItem, StockMovement, CustomerCreditTransaction,
    Expense, FestiveCampaign
)
from services.auth_service import hash_password

def seed_database():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session = get_session()

    try:
        # 1. Shop Profile
        profile = session.query(ShopProfile).first()
        if not profile:
            profile = ShopProfile(
                shop_name="RR Supermarket",
                tagline="Quality Daily Needs, Groceries & Provisions (Demo Store)",
                phone="+91 99999 00000",
                address="Shop 101, Fictional Commercial Ring Road, Sector 0, Unreal Nagar, Fantasy City - 000000",
                gstin="00XXXXX0000X1Z5",
                currency="INR",
                currency_symbol="₹",
                receipt_footer="Thank you for shopping at RR Supermarket! Visit again. Save Paper, Save Trees."
            )
            session.add(profile)
            session.commit()
            print("Seeded ShopProfile.")

        # 2. Users (Owner & Cashier)
        owner = session.query(User).filter(User.username == "admin").first()
        if not owner:
            owner = User(
                username="admin",
                password_hash=hash_password("admin123"),
                full_name="RR Store Manager (Admin)",
                role="owner",
                is_active=True
            )
            session.add(owner)
            print("Seeded Owner user (admin / admin123).")

        cashier = session.query(User).filter(User.username == "cashier").first()
        if not cashier:
            cashier = User(
                username="cashier",
                password_hash=hash_password("cashier123"),
                full_name="RR Cashier (Counter 1)",
                role="cashier",
                is_active=True
            )
            session.add(cashier)
            print("Seeded Cashier user (cashier / cashier123).")
        session.commit()

        # 3. Categories
        categories_data = [
            ("Atta, Rice & Grains", "Daily staple grains, pulses, flours and basmati rice", "wheat"),
            ("Cooking Oils & Ghee", "Refined sunflower oil, mustard oil, desi cow ghee and vanaspati", "droplet"),
            ("Spices, Salt & Masalas", "Iodised salt, turmeric, chilli, garam masala and spices", "flame"),
            ("Dairy & Bakery", "Milk, butter, curd, paneer, bread and bakery essentials", "coffee"),
            ("Snacks & Biscuits", "Instant noodles, glucose biscuits, cookies and namkeens", "cookie"),
            ("Tea, Coffee & Beverages", "Premium CTC tea, instant coffee, juices and health drinks", "cup"),
            ("Personal Care & Soaps", "Bathing soaps, shampoos, toothpastes and detergents", "smile"),
            ("Stationery & Household", "School notebooks, ball pens, cleaners and insect repellents", "book")
        ]
        cat_map = {}
        for name, desc, icon in categories_data:
            cat = session.query(ShopCategory).filter(ShopCategory.name == name).first()
            if not cat:
                cat = ShopCategory(name=name, description=desc, icon=icon, is_active=True)
                session.add(cat)
                session.flush()
            cat_map[name] = cat.id
        session.commit()
        print(f"Seeded {len(cat_map)} Categories.")

        # 4. Suppliers
        suppliers_data = [
            ("Apex Wholesale Staples (Demo)", "+91 99000 00011", "orders@demo-apex.local", "Plot 1, Unreal Logistics Park, Fantasy City", "00SUPP000001Z1", 12450.0),
            ("Metro Provisions Depot (Demo)", "+91 99000 00012", "depot@demo-metro.local", "Plot 2, Unreal Logistics Park, Fantasy City", "00SUPP000002Z2", 8200.0),
            ("National Dairy & Provisions Hub (Demo)", "+91 99000 00013", "agency@demo-dairy.local", "Plot 3, Unreal Logistics Park, Fantasy City", "00SUPP000003Z3", 3150.0),
            ("Quality Edible Oils Depot (Demo)", "+91 99000 00014", "supply@demo-oils.local", "Plot 4, Unreal Logistics Park, Fantasy City", "00SUPP000004Z4", 0.0),
            ("Central General & Stationery Hub (Demo)", "+91 99000 00015", "wholesale@demo-stationery.local", "Plot 5, Unreal Logistics Park, Fantasy City", "00SUPP000005Z5", 1800.0)
        ]
        sup_map = {}
        for name, phone, email, addr, gstin, bal in suppliers_data:
            sup = session.query(Supplier).filter(Supplier.name == name).first()
            if not sup:
                sup = Supplier(name=name, phone=phone, email=email, address=addr, gstin=gstin, balance_due=Decimal(str(bal)), is_active=True)
                session.add(sup)
                session.flush()
            sup_map[name] = sup.id
        session.commit()
        print(f"Seeded {len(sup_map)} Suppliers.")

        # 5. Products
        products_data = [
            # barcode, name, brand, category, unit, cost, sell, stock, min_stock, gst, supplier
            ("8901030383182", "Aashirvaad Superior MP Sharbati Atta 5 kg", "ITC", "Atta, Rice & Grains", "Packet", 245.0, 295.0, 24, 8, 5, "Metro Provisions Depot (Demo)"),
            ("8901030383199", "Aashirvaad Whole Wheat Atta 10 kg", "ITC", "Atta, Rice & Grains", "Packet", 410.0, 485.0, 15, 5, 5, "Metro Provisions Depot (Demo)"),
            ("8906007281014", "Fortune Sunlite Refined Sunflower Oil 1L Pouch", "Fortune", "Cooking Oils & Ghee", "Packet", 122.0, 145.0, 42, 12, 5, "Quality Edible Oils Depot (Demo)"),
            ("8906007281021", "Fortune Kachi Ghani Mustard Oil 1L Bottle", "Fortune", "Cooking Oils & Ghee", "Bottle", 140.0, 168.0, 18, 6, 5, "Quality Edible Oils Depot (Demo)"),
            ("8901725181222", "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "Tata", "Spices, Salt & Masalas", "Packet", 22.0, 28.0, 55, 15, 0, "Metro Provisions Depot (Demo)"),
            ("8901725181339", "Tata Sampann Unpolished Toor Dal 1 kg", "Tata", "Atta, Rice & Grains", "Packet", 145.0, 175.0, 28, 10, 5, "Metro Provisions Depot (Demo)"),
            ("8901112001018", "India Gate Basmati Rice Classic 5 kg", "India Gate", "Atta, Rice & Grains", "Bag", 540.0, 650.0, 14, 4, 5, "Metro Provisions Depot (Demo)"),
            ("8901112001025", "Sona Masoori Raw Rice Premium 25 kg Bag", "RR Select", "Atta, Rice & Grains", "Bag", 1350.0, 1550.0, 9, 3, 5, "Metro Provisions Depot (Demo)"),
            ("8901262010014", "Amul Pasteurised Butter 500g", "Amul", "Dairy & Bakery", "Packet", 240.0, 275.0, 16, 5, 12, "National Dairy & Provisions Hub (Demo)"),
            ("8901262010021", "Amul Taaza Homogenised Toned Milk 1L Tetra", "Amul", "Dairy & Bakery", "Piece", 62.0, 72.0, 25, 8, 0, "National Dairy & Provisions Hub (Demo)"),
            ("8901262010038", "Amul Pure Ghee 1 Litre Tin", "Amul", "Cooking Oils & Ghee", "Tin", 560.0, 640.0, 12, 4, 12, "National Dairy & Provisions Hub (Demo)"),
            ("8901058852332", "Maggi 2-Minute Instant Noodles Masala 4-Pack (280g)", "Nestle", "Snacks & Biscuits", "Packet", 48.0, 58.0, 38, 10, 12, "Apex Wholesale Staples (Demo)"),
            ("8901719101014", "Parle-G Original Glucose Biscuits 800g Family Pack", "Parle", "Snacks & Biscuits", "Packet", 68.0, 85.0, 30, 10, 18, "Apex Wholesale Staples (Demo)"),
            ("8901233010012", "Britannia Good Day Butter Cookies 600g Value Pack", "Britannia", "Snacks & Biscuits", "Packet", 95.0, 120.0, 22, 8, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030740015", "Brooke Bond Red Label Tea 500g", "HUL", "Tea, Coffee & Beverages", "Packet", 230.0, 280.0, 19, 6, 5, "Apex Wholesale Staples (Demo)"),
            ("8901058001013", "Nescafe Classic Instant Coffee Jar 100g", "Nestle", "Tea, Coffee & Beverages", "Jar", 260.0, 320.0, 14, 5, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010019", "Lifebuoy Total Germ Protection Soap 125g (Buy 4 Get 1)", "HUL", "Personal Care & Soaps", "Packet", 138.0, 175.0, 20, 6, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010026", "Dettol Original Germ Protection Bathing Soap (Pack of 4)", "Reckitt", "Personal Care & Soaps", "Packet", 185.0, 225.0, 15, 5, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010033", "Clinic Plus Strong & Long Shampoo Bottle 340ml", "HUL", "Personal Care & Soaps", "Bottle", 170.0, 215.0, 16, 5, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010040", "Surf Excel Easy Wash Detergent Powder 1 kg Pouch", "HUL", "Personal Care & Soaps", "Packet", 115.0, 145.0, 24, 8, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010057", "Vim Dishwash Liquid Gel Lemon Bottle 500ml", "HUL", "Stationery & Household", "Bottle", 92.0, 120.0, 22, 6, 18, "Apex Wholesale Staples (Demo)"),
            ("8901030010064", "Good Knight Gold Flash Liquid Vaporizer Twin Refill", "Godrej", "Stationery & Household", "Pack", 135.0, 165.0, 11, 4, 18, "Central General & Stationery Hub (Demo)"),
            ("8901030010071", "Classmate Long Notebook 160 Pages Single Line (Pack of 3)", "ITC", "Stationery & Household", "Pack", 125.0, 165.0, 25, 8, 12, "Central General & Stationery Hub (Demo)"),
            ("8901030010088", "Reynolds 045 Fine Carabine Ball Pen Blue (Jar of 20)", "Reynolds", "Stationery & Household", "Jar", 140.0, 190.0, 10, 3, 12, "Central General & Stationery Hub (Demo)"),
            # Low stock trigger items
            ("8901030010095", "Madhur Pure & Hygienic Granulated Sugar 5 kg Pouch", "Madhur", "Atta, Rice & Grains", "Packet", 210.0, 245.0, 3, 10, 0, "Metro Provisions Depot (Demo)"),
            ("8901030010101", "Catch Black Pepper Powder 100g Sprinkler Can", "Catch", "Spices, Salt & Masalas", "Can", 75.0, 95.0, 2, 6, 5, "Metro Provisions Depot (Demo)")
        ]

        prod_count = 0
        for barcode, name, brand, cat_name, unit, cost, sell, stock, min_s, gst, sup_name in products_data:
            existing = session.query(ShopProduct).filter(ShopProduct.barcode == barcode).first()
            if not existing:
                p = ShopProduct(
                    barcode=barcode,
                    name=name,
                    brand=brand,
                    category_id=cat_map.get(cat_name),
                    unit=unit,
                    purchase_price=Decimal(str(cost)),
                    selling_price=Decimal(str(sell)),
                    stock_qty=Decimal(str(stock)),
                    min_stock_qty=Decimal(str(min_s)),
                    gst_rate=Decimal(str(gst)),
                    supplier_id=sup_map.get(sup_name),
                    is_active=True
                )
                session.add(p)
                prod_count += 1
        session.commit()
        print(f"Seeded {prod_count} new Indian FMCG Products.")

        # 6. Customers (Khata / Credit)
        customers_data = [
            ("Customer Alpha (Regular)", "9900000001", "House 1, Demo Avenue, Unreal City", 1250.0, 14580.0, 18),
            ("Customer Beta (Neighborhood)", "9900000002", "House 2, Demo Avenue, Unreal City", 450.0, 8920.0, 12),
            ("Customer Gamma (Khata Member)", "9900000003", "House 3, Demo Avenue, Unreal City", 0.0, 22340.0, 31),
            ("Customer Delta (Monthly Credit)", "9900000004", "House 4, Demo Avenue, Unreal City", 2800.0, 19450.0, 24),
            ("Customer Epsilon (Walk-in Regular)", "9900000005", "House 5, Demo Avenue, Unreal City", 0.0, 6750.0, 9)
        ]
        cust_map = {}
        for name, phone, addr, credit, spent, visits in customers_data:
            c = session.query(ShopCustomer).filter(ShopCustomer.phone == phone).first()
            if not c:
                c = ShopCustomer(
                    name=name,
                    phone=phone,
                    address=addr,
                    credit_balance=Decimal(str(credit)),
                    total_spent=Decimal(str(spent)),
                    visit_count=visits
                )
                session.add(c)
                session.flush()
            cust_map[phone] = c.id
        session.commit()
        print(f"Seeded {len(cust_map)} Customers with Khata accounts.")

        # 7. Sample Initial Bills & Stock Movements
        bills_exist = session.query(Bill).first()
        if not bills_exist:
            all_prods = session.query(ShopProduct).all()
            prod_lookup = {p.barcode: p for p in all_prods}

            # Bill 1 - Cash completed today
            bill1 = Bill(
                bill_number="BILL-2026-0001",
                customer_id=cust_map.get("9900000003"),  # Customer Gamma
                cashier_id=cashier.id if cashier else None,
                payment_method="cash",
                subtotal=Decimal("440.00"),
                discount_amount=Decimal("15.00"),
                tax_amount=Decimal("21.25"),
                total_amount=Decimal("446.25"),
                paid_amount=Decimal("500.00"),
                balance_due=Decimal("0.00"),
                status="completed",
                created_at=datetime.utcnow() - timedelta(hours=2)
            )
            session.add(bill1)
            session.flush()

            # Bill 1 items
            p_atta = prod_lookup.get("8901030383182")
            p_salt = prod_lookup.get("8901725181222")
            p_maggi = prod_lookup.get("8901058852332")
            if p_atta and p_salt and p_maggi:
                bi1 = BillItem(bill_id=bill1.id, product_id=p_atta.id, product_name=p_atta.name, quantity=1, unit_price=p_atta.selling_price, purchase_cost=p_atta.purchase_price, discount_amount=Decimal("10.00"), tax_rate=p_atta.gst_rate, line_total=Decimal("285.00"), profit=Decimal("40.00"))
                bi2 = BillItem(bill_id=bill1.id, product_id=p_salt.id, product_name=p_salt.name, quantity=2, unit_price=p_salt.selling_price, purchase_cost=p_salt.purchase_price, discount_amount=Decimal("0.00"), tax_rate=p_salt.gst_rate, line_total=Decimal("56.00"), profit=Decimal("12.00"))
                bi3 = BillItem(bill_id=bill1.id, product_id=p_maggi.id, product_name=p_maggi.name, quantity=2, unit_price=p_maggi.selling_price, purchase_cost=p_maggi.purchase_price, discount_amount=Decimal("5.00"), tax_rate=p_maggi.gst_rate, line_total=Decimal("111.00"), profit=Decimal("15.00"))
                session.add_all([bi1, bi2, bi3])

            # Bill 2 - UPI completed today
            bill2 = Bill(
                bill_number="BILL-2026-0002",
                customer_id=cust_map.get("9900000001"),  # Customer Alpha
                cashier_id=cashier.id if cashier else None,
                payment_method="upi",
                subtotal=Decimal("795.00"),
                discount_amount=Decimal("25.00"),
                tax_amount=Decimal("38.50"),
                total_amount=Decimal("808.50"),
                paid_amount=Decimal("808.50"),
                balance_due=Decimal("0.00"),
                status="completed",
                created_at=datetime.utcnow() - timedelta(minutes=45)
            )
            session.add(bill2)
            session.flush()

            p_oil = prod_lookup.get("8906007281014")
            p_ghee = prod_lookup.get("8901262010038")
            if p_oil and p_ghee:
                bi4 = BillItem(bill_id=bill2.id, product_id=p_oil.id, product_name=p_oil.name, quantity=1, unit_price=p_oil.selling_price, purchase_cost=p_oil.purchase_price, discount_amount=Decimal("5.00"), tax_rate=p_oil.gst_rate, line_total=Decimal("140.00"), profit=Decimal("18.00"))
                bi5 = BillItem(bill_id=bill2.id, product_id=p_ghee.id, product_name=p_ghee.name, quantity=1, unit_price=p_ghee.selling_price, purchase_cost=p_ghee.purchase_price, discount_amount=Decimal("20.00"), tax_rate=p_ghee.gst_rate, line_total=Decimal("620.00"), profit=Decimal("60.00"))
                session.add_all([bi4, bi5])

            # Bill 3 - Credit (Udhaar)
            bill3 = Bill(
                bill_number="BILL-2026-0003",
                customer_id=cust_map.get("9900000004"),  # Customer Delta
                cashier_id=cashier.id if cashier else None,
                payment_method="credit",
                subtotal=Decimal("1250.00"),
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("62.50"),
                total_amount=Decimal("1312.50"),
                paid_amount=Decimal("0.00"),
                balance_due=Decimal("1312.50"),
                status="completed",
                notes="Udhaar - Promised to settle on weekend",
                created_at=datetime.utcnow() - timedelta(minutes=15)
            )
            session.add(bill3)
            session.flush()

            # Record customer credit transaction
            cred_txn = CustomerCreditTransaction(
                customer_id=cust_map.get("9900000004"),
                bill_id=bill3.id,
                txn_type="credit_issued",
                amount=Decimal("1312.50"),
                balance_after=Decimal("2800.00"),
                notes="Credit sale bill #BILL-2026-0003"
            )
            session.add(cred_txn)
            session.commit()
            print("Seeded Sample Bills & Credit Transactions.")

        # 8. Operating Store Expenses
        expenses_exist = session.query(Expense).first()
        if not expenses_exist:
            expenses_data = [
                ("rent", 25000.0, "Store Monthly Rent - Unreal Commercial Hub", date.today() - timedelta(days=7), "bank_transfer"),
                ("electricity", 4200.0, "Commercial Electricity Bill for Deep Freezers & Lights", date.today() - timedelta(days=5), "upi"),
                ("salary", 15000.0, "Staff Salary - Helper & Loading Staff", date.today() - timedelta(days=6), "bank_transfer"),
                ("packaging", 1450.0, "Eco-friendly Grocery Cloth & Paper Bags", date.today() - timedelta(days=2), "cash"),
                ("maintenance", 850.0, "Electronic Weighing Scale Calibration & Service", date.today() - timedelta(days=1), "cash")
            ]
            for cat, amt, desc, exp_date, p_meth in expenses_data:
                e = Expense(
                    category=cat,
                    amount=Decimal(str(amt)),
                    expense_date=exp_date,
                    payment_method=p_meth,
                    description=desc,
                    user_id=owner.id if owner else None
                )
                session.add(e)
            session.commit()
            print("Seeded Initial Operating Expenses.")

        # 9. Festive Campaigns
        camp_exist = session.query(FestiveCampaign).first()
        if not camp_exist:
            camp1 = FestiveCampaign(
                name="Diwali Mahotsav Deepavali Dhamaka Sale",
                festival_type="Diwali",
                start_date=date.today() - timedelta(days=3),
                end_date=date.today() + timedelta(days=7),
                discount_percentage=Decimal("15.00"),
                target_category="Cooking Oils & Ghee",
                description="Special festive discount on Amul Ghee, Fortune Sunlite, dry fruits & festive confectionery."
            )
            camp2 = FestiveCampaign(
                name="Pongal & Sankranti Harvest Mega Offer",
                festival_type="Pongal",
                start_date=date.today() + timedelta(days=60),
                end_date=date.today() + timedelta(days=65),
                discount_percentage=Decimal("10.00"),
                target_category="Atta, Rice & Grains",
                description="Special offers on Sona Masoori Rice, Jaggery, Moong Dal & traditional sweets."
            )
            session.add_all([camp1, camp2])
            session.commit()
            print("Seeded Festive Campaigns.")

        print("=== INDIAN RETAIL SEED DATA INSERTION COMPLETE ===")

    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
