"""
CARTIVANTA - SQLAlchemy ORM Models
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database.connection import Base

class EtlExecutionLog(Base):
    __tablename__ = "etl_execution_logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False)
    step_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class DataQualityResult(Base):
    __tablename__ = "data_quality_results"
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False)
    check_name = Column(String(128), nullable=False)
    metric_category = Column(String(64), nullable=False)
    metric_value = Column(Numeric(12, 4), nullable=False)
    threshold_value = Column(Numeric(12, 4), nullable=True)
    status = Column(String(32), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Calendar(Base):
    __tablename__ = "calendar"
    date_id = Column(Date, primary_key=True)
    day_name = Column(String(16), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    day_of_month = Column(Integer, nullable=False)
    day_of_year = Column(Integer, nullable=False)
    week_of_year = Column(Integer, nullable=False)
    month_number = Column(Integer, nullable=False)
    month_name = Column(String(16), nullable=False)
    quarter_number = Column(Integer, nullable=False)
    year_number = Column(Integer, nullable=False)
    is_weekend = Column(Boolean, default=False)

class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(String(32), primary_key=True)
    first_invoice_date = Column(DateTime, nullable=True)
    last_invoice_date = Column(DateTime, nullable=True)
    country = Column(String(64), nullable=False)
    is_registered = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    orders = relationship("Order", back_populates="customer")
    segment = relationship("CustomerSegment", back_populates="customer", uselist=False)

class Product(Base):
    __tablename__ = "products"
    stock_code = Column(String(32), primary_key=True)
    description = Column(String(255), nullable=False)
    category = Column(String(64), default="General Merchandise")
    first_seen_date = Column(DateTime, nullable=True)
    last_seen_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cost = relationship("ProductCost", back_populates="product", uselist=False)
    inventory = relationship("InventorySnapshot", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")

class ProductCost(Base):
    __tablename__ = "product_costs"
    stock_code = Column(String(32), ForeignKey("products.stock_code", ondelete="CASCADE"), primary_key=True)
    estimated_unit_cost = Column(Numeric(10, 4), nullable=False)
    cost_category = Column(String(64), nullable=False)
    is_synthetic = Column(Boolean, default=True)
    effective_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="cost")

class Order(Base):
    __tablename__ = "orders"
    invoice_no = Column(String(32), primary_key=True)
    customer_id = Column(String(32), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    invoice_date = Column(DateTime, nullable=False)
    country = Column(String(64), nullable=False)
    is_cancelled = Column(Boolean, default=False)
    total_line_items = Column(Integer, default=0)
    gross_order_value = Column(Numeric(14, 4), default=0.0)
    net_order_value = Column(Numeric(14, 4), default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(32), ForeignKey("orders.invoice_no", ondelete="CASCADE"), nullable=False)
    stock_code = Column(String(32), ForeignKey("products.stock_code", ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=False)
    line_total = Column(Numeric(14, 4), nullable=False)
    is_return = Column(Boolean, default=False)
    estimated_cost_total = Column(Numeric(14, 4), nullable=True)
    estimated_profit = Column(Numeric(14, 4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshot"
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(32), ForeignKey("products.stock_code", ondelete="CASCADE"), nullable=False)
    available_stock = Column(Integer, nullable=False)
    safety_stock = Column(Integer, nullable=False)
    supplier_lead_time_days = Column(Integer, nullable=False)
    target_stock = Column(Integer, nullable=False)
    last_restock_date = Column(Date, nullable=True)
    inventory_health_status = Column(String(32), nullable=False)
    is_synthetic = Column(Boolean, default=True)
    snapshot_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")

class FestivalCalendar(Base):
    __tablename__ = "festival_calendar"
    festival_id = Column(Integer, primary_key=True, autoincrement=True)
    festival_name = Column(String(64), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    festival_category = Column(String(64), nullable=False)
    demand_uplift_assumption = Column(Numeric(6, 4), nullable=False)
    notes = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromotionCampaign(Base):
    __tablename__ = "promotion_campaigns"
    campaign_id = Column(String(32), primary_key=True)
    campaign_name = Column(String(128), nullable=False)
    promotion_type = Column(String(64), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_category = Column(String(64), nullable=False)
    discount_percentage = Column(Numeric(6, 4), nullable=False)
    campaign_budget = Column(Numeric(12, 2), nullable=False)
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromotionTransaction(Base):
    __tablename__ = "promotion_transactions"
    promo_txn_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(32), nullable=False)
    stock_code = Column(String(32), ForeignKey("products.stock_code", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(String(32), ForeignKey("promotion_campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    original_price = Column(Numeric(10, 4), nullable=False)
    discount_percentage = Column(Numeric(6, 4), nullable=False)
    discount_amount = Column(Numeric(10, 4), nullable=False)
    final_selling_price = Column(Numeric(10, 4), nullable=False)
    quantity = Column(Integer, nullable=False)
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DemandForecast(Base):
    __tablename__ = "demand_forecasts"
    forecast_id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(32), ForeignKey("products.stock_code", ondelete="CASCADE"), nullable=False)
    forecast_date = Column(Date, nullable=False)
    model_name = Column(String(64), nullable=False)
    predicted_demand = Column(Numeric(12, 4), nullable=False)
    lower_bound = Column(Numeric(12, 4), nullable=True)
    upper_bound = Column(Numeric(12, 4), nullable=True)
    mae = Column(Numeric(10, 4), nullable=True)
    rmse = Column(Numeric(10, 4), nullable=True)
    wape = Column(Numeric(10, 4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CustomerSegment(Base):
    __tablename__ = "customer_segments"
    customer_id = Column(String(32), ForeignKey("customers.customer_id", ondelete="CASCADE"), primary_key=True)
    recency_days = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False)
    monetary = Column(Numeric(14, 4), nullable=False)
    r_score = Column(Integer, nullable=False)
    f_score = Column(Integer, nullable=False)
    m_score = Column(Integer, nullable=False)
    cluster_id = Column(Integer, nullable=False)
    segment_name = Column(String(64), nullable=False)
    avg_order_value = Column(Numeric(12, 4), nullable=False)
    lifetime_revenue = Column(Numeric(14, 4), nullable=False)
    last_calculated_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="segment")

class BusinessAlert(Base):
    __tablename__ = "business_alerts"
    alert_id = Column(String(64), primary_key=True)
    alert_category = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)
    affected_entity_type = Column(String(32), nullable=False)
    affected_entity_id = Column(String(64), nullable=False)
    detected_condition = Column(Text, nullable=False)
    supporting_metric = Column(String(128), nullable=False)
    threshold_value = Column(String(64), nullable=True)
    suggested_action = Column(Text, nullable=False)
    expected_impact = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    generated_timestamp = Column(DateTime, default=datetime.utcnow)


# ==============================================================================
# OPERATIONAL RETAIL STORE MODELS (INDIAN SHOP MANAGEMENT & POS)
# Currency: INR (₹)
# ==============================================================================

class ShopProfile(Base):
    __tablename__ = "shop_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_name = Column(String(128), nullable=False, default="Cartivanta Retail Store")
    tagline = Column(String(255), nullable=True, default="Run Your Shop. Track Your Stock. Understand Your Profit.")
    phone = Column(String(32), nullable=True, default="+91 98765 43210")
    address = Column(Text, nullable=True, default="Shop No. 12, Market Road, Bengaluru, Karnataka - 560001")
    gstin = Column(String(32), nullable=True, default="29ABCDE1234F1Z5")
    currency = Column(String(8), nullable=False, default="INR")
    currency_symbol = Column(String(8), nullable=False, default="₹")
    receipt_footer = Column(Text, nullable=True, default="Thank you for shopping with us! Please visit again.")
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="cashier")  # "owner" or "cashier"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ShopCategory(Base):
    __tablename__ = "shop_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    icon = Column(String(64), nullable=True, default="package")
    is_active = Column(Boolean, default=True)

    products = relationship("ShopProduct", back_populates="category")

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=False)
    email = Column(String(128), nullable=True)
    address = Column(Text, nullable=True)
    gstin = Column(String(32), nullable=True)
    balance_due = Column(Numeric(12, 2), default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("ShopProduct", back_populates="supplier")
    purchases = relationship("Purchase", back_populates="supplier")

class ShopProduct(Base):
    __tablename__ = "shop_products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode = Column(String(64), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(128), nullable=True)
    category_id = Column(Integer, ForeignKey("shop_categories.id", ondelete="SET NULL"), nullable=True)
    unit = Column(String(32), default="Piece")  # Piece, Kg, Gram, Litre, ml, Packet, Box, Dozen
    purchase_price = Column(Numeric(10, 2), nullable=False, default=0.0)
    selling_price = Column(Numeric(10, 2), nullable=False, default=0.0)
    stock_qty = Column(Numeric(10, 2), nullable=False, default=0.0)
    min_stock_qty = Column(Numeric(10, 2), nullable=False, default=5.0)
    gst_rate = Column(Numeric(5, 2), nullable=False, default=0.0)  # 0, 5, 12, 18, 28
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    expiry_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("ShopCategory", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    movements = relationship("StockMovement", back_populates="product")
    bill_items = relationship("BillItem", back_populates="product")

class ShopCustomer(Base):
    __tablename__ = "shop_customers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    email = Column(String(128), nullable=True)
    gstin = Column(String(32), nullable=True)
    credit_balance = Column(Numeric(12, 2), default=0.0)  # Positive = customer owes money (Udhaar)
    total_spent = Column(Numeric(14, 2), default=0.0)
    visit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    bills = relationship("Bill", back_populates="customer")
    credit_transactions = relationship("CustomerCreditTransaction", back_populates="customer")

class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_number = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("shop_customers.id", ondelete="SET NULL"), nullable=True)
    cashier_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    payment_method = Column(String(32), nullable=False, default="cash")  # "cash", "upi", "card", "credit"
    subtotal = Column(Numeric(12, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(12, 2), default=0.0)
    discount_id = Column(Integer, ForeignKey("discount_offers.id", ondelete="SET NULL"), nullable=True)
    discount_name = Column(String(128), nullable=True)
    discount_type = Column(String(32), nullable=True)
    discount_rate = Column(Numeric(5, 2), nullable=True)
    tax_amount = Column(Numeric(12, 2), default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    paid_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    balance_due = Column(Numeric(12, 2), default=0.0)
    status = Column(String(32), default="completed")  # "completed", "cancelled", "refunded"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("ShopCustomer", back_populates="bills")
    cashier = relationship("User")
    discount = relationship("DiscountOffer")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")

class BillItem(Base):
    __tablename__ = "bill_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("shop_products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    purchase_cost = Column(Numeric(10, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(10, 2), default=0.0)
    tax_rate = Column(Numeric(5, 2), default=0.0)
    line_total = Column(Numeric(12, 2), nullable=False)
    profit = Column(Numeric(12, 2), default=0.0)

    bill = relationship("Bill", back_populates="items")
    product = relationship("ShopProduct", back_populates="bill_items")

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(64), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    paid_amount = Column(Numeric(12, 2), default=0.0)
    balance_due = Column(Numeric(12, 2), default=0.0)
    payment_status = Column(String(32), default="paid")  # "paid", "partial", "pending"
    purchase_date = Column(Date, default=date.today)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("shop_products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), default=0.0)
    line_total = Column(Numeric(12, 2), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("ShopProduct")

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("shop_products.id", ondelete="CASCADE"), nullable=False)
    movement_type = Column(String(32), nullable=False)  # "sale", "purchase", "return", "damage", "adjustment"
    quantity_change = Column(Numeric(10, 2), nullable=False)  # negative for deduction, positive for addition
    balance_after = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("ShopProduct", back_populates="movements")
    user = relationship("User")

class CustomerCreditTransaction(Base):
    __tablename__ = "customer_credit_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("shop_customers.id", ondelete="CASCADE"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="SET NULL"), nullable=True)
    txn_type = Column(String(32), nullable=False)  # "credit_issued", "payment_received"
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    payment_mode = Column(String(32), default="cash")  # "cash", "upi"
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("ShopCustomer", back_populates="credit_transactions")
    bill = relationship("Bill")

class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    payment_mode = Column(String(32), default="upi")  # "cash", "upi", "bank_transfer", "cheque"
    reference_no = Column(String(64), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(64), nullable=False)  # "rent", "electricity", "salary", "transport", "packaging", "maintenance", "other"
    amount = Column(Numeric(12, 2), nullable=False)
    expense_date = Column(Date, default=date.today)
    payment_method = Column(String(32), default="cash")  # "cash", "upi", "bank_transfer"
    description = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class FestiveCampaign(Base):
    __tablename__ = "festive_campaigns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    festival_type = Column(String(64), nullable=False)  # "Diwali", "Pongal", "Christmas", "New Year", "Eid", "Regional"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=10.0)
    target_category = Column(String(64), default="All")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DiscountOffer(Base):
    __tablename__ = "discount_offers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    discount_type = Column(String(32), nullable=False, default="percentage")  # "percentage", "fixed"
    discount_value = Column(Numeric(10, 2), nullable=False)  # e.g. 10.00 for 10% or 50.00 for ₹50
    applies_to = Column(String(32), nullable=False, default="entire_bill")  # "entire_bill", "product", "category"
    target_product_id = Column(Integer, ForeignKey("shop_products.id", ondelete="SET NULL"), nullable=True)
    target_category_id = Column(Integer, ForeignKey("shop_categories.id", ondelete="SET NULL"), nullable=True)
    min_bill_amount = Column(Numeric(10, 2), nullable=True, default=0.0)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    target_product = relationship("ShopProduct")
    target_category = relationship("ShopCategory")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
