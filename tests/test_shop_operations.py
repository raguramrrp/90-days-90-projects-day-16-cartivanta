"""
CARTIVANTA - Operational Retail Shop & POS Automated Test Suite
Validates atomic bill creation, stock decrements, negative stock prevention,
weighted average costing, customer Khata credit math, expense accounting,
and cashier privacy permissions.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from database.connection import get_session
from database.models import ShopProduct, ShopCategory, Supplier, ShopCustomer, User, Bill, Expense
from services.auth_service import hash_password, verify_password, generate_session_token, verify_session_token
from services.product_service import ProductService
from services.pos_service import PosService
from services.stock_service import StockService
from services.purchase_service import PurchaseService
from services.khata_service import KhataService
from services.expense_service import ExpenseService
from services.discount_service import DiscountService

@pytest.fixture
def db_session():
    session = get_session()
    yield session
    session.close()

# --- 1. AUTHENTICATION & RBAC TESTS ---

def test_password_hashing_and_verification():
    raw_pass = "admin123"
    hashed = hash_password(raw_pass)
    assert ":" in hashed
    assert verify_password(hashed, raw_pass) is True
    assert verify_password(hashed, "wrongpass") is False

def test_session_token_generation_and_tamper_proofing():
    dummy_user = User(id=42, username="demo_cashier", role="cashier")
    token = generate_session_token(dummy_user)
    session_data = verify_session_token(token)
    assert session_data is not None
    assert session_data["user_id"] == 42
    assert session_data["username"] == "demo_cashier"
    assert session_data["role"] == "cashier"
    assert session_data["is_owner"] is False

    # Tampered token
    tampered = token[:-4] + "abcd"
    assert verify_session_token(tampered) is None

# --- 2. PRODUCT MANAGEMENT & MARGIN CALCULATIONS ---

def test_product_margin_and_stock_calculations(db_session):
    prod_svc = ProductService(db_session)
    barcode = f"TEST{datetime.utcnow().timestamp()}"
    p = prod_svc.create_product({
        "barcode": barcode,
        "name": "Test Basmati Rice 1 kg",
        "unit": "Packet",
        "purchase_price": 80.0,
        "selling_price": 100.0,
        "stock_qty": 20.0,
        "min_stock_qty": 5.0,
        "gst_rate": 5.0
    })

    fetched = prod_svc.get_product_by_id(p.id)
    assert fetched is not None
    assert fetched["unit_profit"] == 20.0 # 100 - 80
    assert fetched["margin_pct"] == 20.0 # (20 / 100) * 100
    assert fetched["stock_value"] == 1600.0 # 20 * 80

    # Duplicate barcode prevention
    with pytest.raises(ValueError, match="already exists"):
        prod_svc.create_product({
            "barcode": barcode,
            "name": "Duplicate Barcode Item",
            "purchase_price": 50.0,
            "selling_price": 60.0
        })

# --- 3. ATOMIC BILLING & STOCK DEDUCTION TESTS ---

def test_atomic_bill_creation_and_stock_decrement(db_session):
    prod_svc = ProductService(db_session)
    pos_svc = PosService(db_session)

    # 1. Create a product with 10 units
    barcode = f"POS{datetime.utcnow().timestamp()}"
    p = prod_svc.create_product({
        "barcode": barcode,
        "name": "Sunflower Oil Test 1L",
        "unit": "Pouch",
        "purchase_price": 100.0,
        "selling_price": 125.0,
        "stock_qty": 10.0,
        "min_stock_qty": 3.0,
        "gst_rate": 5.0
    })

    # 2. Bill 3 units
    bill = pos_svc.create_bill(
        items=[{"product_id": p.id, "quantity": 3.0, "discount_amount": 5.0}],
        payment_method="cash"
    )

    assert bill.status == "completed"
    assert "BILL-" in bill.bill_number

    # 3. Check remaining stock is 7
    updated_p = prod_svc.get_product_by_id(p.id)
    assert updated_p["stock_qty"] == 7.0

    # 4. Negative stock prevention: Requesting 10 units when only 7 remain
    with pytest.raises(ValueError, match="Insufficient stock"):
        pos_svc.create_bill(
            items=[{"product_id": p.id, "quantity": 10.0, "discount_amount": 0.0}],
            payment_method="cash"
        )

    # Stock must remain unchanged after failure
    assert prod_svc.get_product_by_id(p.id)["stock_qty"] == 7.0

    # 5. Cancel bill restores stock to 10
    pos_svc.cancel_bill(bill.id, reason="Customer cancelled test")
    assert prod_svc.get_product_by_id(p.id)["stock_qty"] == 10.0

# --- 4. CUSTOMER KHATA (UDHAAR) LEDGER TESTS ---

def test_customer_khata_credit_and_repayment(db_session):
    khata_svc = KhataService(db_session)
    pos_svc = PosService(db_session)
    prod_svc = ProductService(db_session)

    import random
    phone = f"99{random.randint(10000000, 99999999)}"
    cust = khata_svc.add_customer(name="Khata Tester", phone=phone, address="Test Road")
    assert cust.credit_balance == Decimal("0.00")

    p = prod_svc.create_product({
        "name": "Khata Test Item",
        "purchase_price": 50.0,
        "selling_price": 60.0,
        "stock_qty": 10.0
    })

    # Create credit sale bill for 2 units (2 * 60 = 120)
    bill = pos_svc.create_bill(
        items=[{"product_id": p.id, "quantity": 2.0}],
        payment_method="credit",
        customer_id=cust.id
    )

    # Customer balance must now be 120
    stmt = khata_svc.get_customer_statement(cust.id)
    assert stmt["customer"]["credit_balance"] == 120.0
    assert len(stmt["transactions"]) == 1

    # Record partial repayment of 50
    khata_svc.record_payment(customer_id=cust.id, amount=50.0, payment_mode="upi", notes="Partial GPay payment")
    stmt2 = khata_svc.get_customer_statement(cust.id)
    assert stmt2["customer"]["credit_balance"] == 70.0 # 120 - 50 = 70
    assert len(stmt2["transactions"]) == 2

# --- 5. INWARD PURCHASES & WEIGHTED AVERAGE COSTING ---

def test_purchase_inward_and_weighted_average_cost(db_session):
    pur_svc = PurchaseService(db_session)
    prod_svc = ProductService(db_session)

    # Existing supplier
    sup = db_session.query(Supplier).first()
    assert sup is not None

    # Product with 10 units @ 100.0
    p = prod_svc.create_product({
        "name": "Cost Average Item",
        "purchase_price": 100.0,
        "selling_price": 130.0,
        "stock_qty": 10.0,
        "supplier_id": sup.id
    })

    # Incoming 10 units @ 120.0
    # Expected weighted average: ((10 * 100) + (10 * 120)) / 20 = 110.0
    invoice_no = f"INV-{int(datetime.utcnow().timestamp())}"
    pur_svc.record_purchase(
        supplier_id=sup.id,
        invoice_no=invoice_no,
        items=[{"product_id": p.id, "quantity": 10.0, "unit_cost": 120.0, "gst_rate": 0.0}],
        paid_amount=0.0
    )

    updated_p = prod_svc.get_product_by_id(p.id)
    assert updated_p["stock_qty"] == 20.0 # 10 + 10
    assert updated_p["purchase_price"] == 110.0 # Weighted average cost!

# --- 6. OPERATING EXPENSES & NET OPERATING PROFIT MATH ---

def test_operating_expenses_and_net_profit(db_session):
    exp_svc = ExpenseService(db_session)
    exp = exp_svc.record_expense(
        category="electricity",
        amount=500.0,
        description="Test Electricity Payment",
        payment_method="upi"
    )
    assert exp.id is not None
    assert float(exp.amount) == 500.0

    summary = exp_svc.get_net_operating_profit_summary(start_date=date.today(), end_date=date.today())
    assert "gross_profit" in summary
    assert "total_operating_expenses" in summary
    assert "net_operating_profit" in summary
    # Net Operating Profit = Gross Profit - Operating Expenses
    expected_net = summary["gross_profit"] - summary["total_operating_expenses"]
    assert round(summary["net_operating_profit"], 2) == round(expected_net, 2)

# --- 7. DISCOUNT & OFFERS SYSTEM TESTS ---

def test_discount_service_lifecycle_and_calculations(db_session):
    disc_svc = DiscountService(db_session)

    # 1. Create a percentage discount with min bill and max cap
    offer = disc_svc.create_discount({
        "name": "Test Weekend Dhamaka 10%",
        "description": "10% off on bills above 500 up to 100 max",
        "discount_type": "percentage",
        "discount_value": 10.0,
        "applies_to": "entire_bill",
        "min_bill_amount": 500.0,
        "max_discount_amount": 100.0,
        "start_date": date.today(),
        "end_date": date.today()
    })
    assert offer.id is not None
    assert offer.is_active is True

    # 2. Calculation below min bill
    sample_cart = [{"product_id": 1, "category_id": 1, "unit_price": 200.0, "quantity": 2}] # Subtotal 400
    calc_below = disc_svc.calculate_bill_discount(offer.id, sample_cart)
    assert calc_below["discount_amount"] == 0.0 # Below min bill of 500

    # 3. Calculation above min bill within cap
    sample_cart_2 = [{"product_id": 1, "category_id": 1, "unit_price": 300.0, "quantity": 2}] # Subtotal 600
    calc_above = disc_svc.calculate_bill_discount(offer.id, sample_cart_2)
    assert calc_above["discount_amount"] == 60.0 # 10% of 600 = 60 <= 100 cap

    # 4. Calculation above min bill exceeding cap
    sample_cart_3 = [{"product_id": 1, "category_id": 1, "unit_price": 800.0, "quantity": 2}] # Subtotal 1600
    calc_cap = disc_svc.calculate_bill_discount(offer.id, sample_cart_3)
    assert calc_cap["discount_amount"] == 100.0 # 10% of 1600 is 160, capped at 100

    # 5. Quick Custom Discount Creation
    quick_offer = disc_svc.quick_create_discount(
        name="Counter Spot Offer",
        discount_type="fixed",
        discount_value=50.0
    )
    assert quick_offer.id is not None
    assert quick_offer.discount_type == "fixed"
    assert quick_offer.discount_value == Decimal("50.00")

    # 6. Toggle Active/Inactive
    toggled = disc_svc.toggle_discount_active(offer.id)
    assert toggled is False
    toggled_back = disc_svc.toggle_discount_active(offer.id)
    assert toggled_back is True

