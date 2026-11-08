"""
CARTIVANTA - Retail Shop Management, Billing (POS) & Business Intelligence Platform
FastAPI Application serving daily shopkeeper operations, POS billing, inventory management,
customer Khata credit ledgers, operating expenses, and the segregated 1.02M UCI benchmark analytics engine.
"""
import os
import io
import csv
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Form, Response, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import func, desc

from config.settings import APP_NAME
from database.connection import get_session
from database.models import (
    ShopProfile, User, ShopCategory, Supplier, ShopProduct,
    Bill, BillItem, Purchase, PurchaseItem, StockMovement,
    ShopCustomer, CustomerCreditTransaction, SupplierPayment,
    Expense, FestiveCampaign, DiscountOffer, CustomerSegment, DemandForecast,
    DataQualityResult
)
from services.auth_service import (
    authenticate_user, generate_session_token, verify_session_token, hash_password
)
from services.product_service import ProductService
from services.pos_service import PosService
from services.stock_service import StockService
from services.purchase_service import PurchaseService
from services.khata_service import KhataService
from services.expense_service import ExpenseService
from services.shop_service import ShopService
from services.discount_service import DiscountService

# Historical UCI Analytics Engines
from analytics.sales_analysis import SalesAnalyticsEngine
from analytics.product_analysis import ProductAnalyticsEngine
from analytics.customer_analysis import CustomerAnalyticsEngine
from analytics.inventory_analysis import InventoryAnalyticsEngine
from analytics.profitability_analysis import ProfitabilityAnalyticsEngine
from analytics.promotion_analysis import PromotionAnalyticsEngine
from festive.discount_simulator import FestiveDiscountSimulator
from recommendations.business_rules import BusinessRecommendationEngine

app = FastAPI(title=APP_NAME, description="Retail Shop Management, Billing & Intelligence Platform")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

COOKIE_NAME = "cartivanta_session"

# --- AUTH & SESSION DEPENDENCY ---

def get_current_user(request: Request) -> Dict[str, Any]:
    """Retrieve session from cookie or default to Owner for seamless demo evaluation."""
    token = request.cookies.get(COOKIE_NAME)
    session_data = verify_session_token(token) if token else None
    if session_data:
        return session_data

    # Local default: Auto-authenticate as Owner
    return {
        "user_id": 1,
        "username": "admin",
        "full_name": "RR Store Manager (Owner)",
        "role": "owner",
        "is_owner": True
    }

# --- PYDANTIC SCHEMAS FOR API INPUTS ---

class CartItemInput(BaseModel):
    product_id: int
    quantity: float
    discount_amount: float = 0.0

class CreateBillInput(BaseModel):
    items: List[CartItemInput]
    payment_method: str = "cash"
    customer_id: Optional[int] = None
    bill_discount: float = 0.0
    discount_id: Optional[int] = None
    discount_name: Optional[str] = None
    discount_type: Optional[str] = None
    discount_rate: Optional[float] = None
    paid_amount: Optional[float] = None
    notes: Optional[str] = None

class DiscountInput(BaseModel):
    name: str
    discount_type: str = "percentage"
    discount_value: float
    applies_to: str = "entire_bill"
    target_product_id: Optional[int] = None
    target_category_id: Optional[int] = None
    min_bill_amount: Optional[float] = 0.0
    max_discount_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None

class QuickDiscountInput(BaseModel):
    name: str
    discount_type: str = "percentage"
    discount_value: float
    applies_to: str = "entire_bill"
    target_product_id: Optional[int] = None

class AddCustomerInput(BaseModel):
    name: str
    phone: str
    address: Optional[str] = None
    email: Optional[str] = None

class RepaymentInput(BaseModel):
    amount: float
    payment_mode: str = "cash"
    notes: Optional[str] = None

class StockAdjustInput(BaseModel):
    product_id: int
    quantity_change: float
    reason: str

class ProductInput(BaseModel):
    name: str
    barcode: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[int] = None
    unit: str = "Piece"
    purchase_price: float = 0.0
    selling_price: float = 0.0
    stock_qty: float = 0.0
    min_stock_qty: float = 5.0
    gst_rate: float = 0.0
    supplier_id: Optional[int] = None
    description: Optional[str] = None

class InwardItemInput(BaseModel):
    product_id: int
    quantity: float
    unit_cost: float
    gst_rate: float = 0.0

class RecordPurchaseInput(BaseModel):
    supplier_id: int
    invoice_no: str
    items: List[InwardItemInput]
    paid_amount: float = 0.0
    notes: Optional[str] = None

class SupplierPaymentInput(BaseModel):
    supplier_id: int
    amount: float
    payment_mode: str = "upi"
    reference_no: Optional[str] = None
    notes: Optional[str] = None

class ExpenseInput(BaseModel):
    category: str
    amount: float
    description: str
    payment_method: str = "cash"

class CampaignInput(BaseModel):
    name: str
    festival_type: str
    discount_percentage: float
    target_category: str = "All"
    start_date: str
    end_date: str
    description: Optional[str] = None

class ShopSettingsInput(BaseModel):
    shop_name: str
    tagline: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    receipt_footer: Optional[str] = None

class RegisterStaffInput(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "cashier"

# --- AUTHENTICATION ROUTES ---

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request}
    )

@app.post("/login")
def login_action(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    session = get_session()
    try:
        user = authenticate_user(session, username, password)
        if not user:
            return templates.TemplateResponse(
                request=Request(scope={"type": "http"}),
                name="login.html",
                context={"request": Request(scope={"type": "http"}), "error": "Invalid username or password. Please try again."}
            )
        token = generate_session_token(user)
        resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        resp.set_cookie(key=COOKIE_NAME, value=token, max_age=86400 * 7, httponly=True)
        return resp
    finally:
        session.close()

@app.get("/logout")
def logout_action():
    resp = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(COOKIE_NAME)
    return resp

@app.get("/switch-role")
def switch_role(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Toggle between Owner and Cashier for smooth testing and demonstration."""
    session = get_session()
    try:
        target_username = "cashier" if current_user.get("role") == "owner" else "admin"
        target_user = session.query(User).filter(User.username == target_username).first()
        if not target_user:
            # Fallback
            target_user = session.query(User).first()
        token = generate_session_token(target_user)
        resp = RedirectResponse(url=request.headers.get("referer", "/"), status_code=status.HTTP_302_FOUND)
        resp.set_cookie(key=COOKIE_NAME, value=token, max_age=86400 * 7, httponly=True)
        return resp
    finally:
        session.close()

# --- WEB PAGE ROUTES ---

@app.get("/", response_class=HTMLResponse)
def home_view(request: Request, user: Optional[Dict[str, Any]] = None):
    if user is None or not isinstance(user, dict):
        user = get_current_user(request)
    session = get_session()
    try:
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        dash = shop_svc.get_dashboard_summary(is_owner=user.get("is_owner", True))
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "request": request,
                "page_title": f"Home &bull; {profile['shop_name']}",
                "active_page": "home",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "dashboard": dash,
                "current_date": date.today().strftime("%A, %d %B %Y")
            }
        )
    finally:
        session.close()

# Backwards compatibility alias for tests
index_view = home_view

@app.get("/billing", response_class=HTMLResponse)
def billing_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        prod_svc = ProductService(session)
        khata_svc = KhataService(session)
        shop_svc = ShopService(session)
        disc_svc = DiscountService(session)
        profile = shop_svc.get_shop_profile()
        products = prod_svc.get_products(active_only=True)
        categories = session.query(ShopCategory).filter(ShopCategory.is_active == True).all()
        customers = khata_svc.get_customers()
        active_discounts = disc_svc.get_active_discounts_for_billing()

        return templates.TemplateResponse(
            request=request,
            name="billing.html",
            context={
                "request": request,
                "page_title": "Billing / POS &bull; CARTIVANTA",
                "active_page": "billing",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "products": products,
                "categories": categories,
                "customers": customers,
                "active_discounts": active_discounts
            }
        )
    finally:
        session.close()

@app.get("/bill/{bill_id}/receipt", response_class=HTMLResponse)
def view_receipt_direct(bill_id: int, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        pos_svc = PosService(session)
        receipt = pos_svc.get_bill_receipt_data(bill_id)
        if not receipt:
            raise HTTPException(status_code=404, detail="Bill not found.")
        return templates.TemplateResponse(
            request=request,
            name="billing.html",
            context={
                "request": request,
                "page_title": f"Receipt #{receipt['bill_number']}",
                "active_page": "billing",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "receipt": receipt
            }
        )
    finally:
        session.close()

@app.get("/products", response_class=HTMLResponse)
def products_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        prod_svc = ProductService(session)
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        products = prod_svc.get_products(active_only=True)
        valuation = prod_svc.get_stock_valuation_summary()
        categories = session.query(ShopCategory).filter(ShopCategory.is_active == True).all()
        suppliers = session.query(Supplier).filter(Supplier.is_active == True).all()

        return templates.TemplateResponse(
            request=request,
            name="products.html",
            context={
                "request": request,
                "page_title": "Products Catalog &bull; CARTIVANTA",
                "active_page": "products",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "products": products,
                "valuation": valuation,
                "categories": categories,
                "suppliers": suppliers
            }
        )
    finally:
        session.close()

@app.get("/stock", response_class=HTMLResponse)
def stock_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        stock_svc = StockService(session)
        prod_svc = ProductService(session)
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        low_stock = stock_svc.get_low_stock_products()
        movements = stock_svc.get_stock_movements(limit=50)
        all_prods = prod_svc.get_products(active_only=True)

        return templates.TemplateResponse(
            request=request,
            name="stock.html",
            context={
                "request": request,
                "page_title": "Stock & Inventory &bull; CARTIVANTA",
                "active_page": "stock",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "low_stock_items": low_stock,
                "movements": movements,
                "all_products": all_prods
            }
        )
    finally:
        session.close()

@app.get("/purchases", response_class=HTMLResponse)
def purchases_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers do not have access to purchase costs or suppliers.")
    session = get_session()
    try:
        pur_svc = PurchaseService(session)
        prod_svc = ProductService(session)
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        suppliers = pur_svc.get_suppliers()
        purchases = pur_svc.get_purchases()
        products = prod_svc.get_products(active_only=True)

        return templates.TemplateResponse(
            request=request,
            name="purchases.html",
            context={
                "request": request,
                "page_title": "Purchases & Suppliers &bull; CARTIVANTA",
                "active_page": "purchases",
                "current_user": user,
                "is_owner": True,
                "shop_profile": profile,
                "suppliers": suppliers,
                "purchases": purchases,
                "products": products
            }
        )
    finally:
        session.close()

@app.get("/customers", response_class=HTMLResponse)
def customers_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        khata_svc = KhataService(session)
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        customers = khata_svc.get_customers()
        total_credit = sum(c["credit_balance"] for c in customers)
        credit_accounts_count = sum(1 for c in customers if c["credit_balance"] > 0)

        return templates.TemplateResponse(
            request=request,
            name="customers.html",
            context={
                "request": request,
                "page_title": "Customers & Khata &bull; CARTIVANTA",
                "active_page": "customers",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "customers": customers,
                "total_credit": total_credit,
                "credit_accounts_count": credit_accounts_count
            }
        )
    finally:
        session.close()

@app.get("/expenses", response_class=HTMLResponse)
def expenses_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers do not have access to store expense records.")
    session = get_session()
    try:
        exp_svc = ExpenseService(session)
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        expenses = exp_svc.get_expenses(limit=50)
        profit_summary = exp_svc.get_net_operating_profit_summary()

        return templates.TemplateResponse(
            request=request,
            name="expenses.html",
            context={
                "request": request,
                "page_title": "Expenses & Net Real Profit &bull; CARTIVANTA",
                "active_page": "expenses",
                "current_user": user,
                "is_owner": True,
                "shop_profile": profile,
                "expenses": expenses,
                "profit_summary": profit_summary
            }
        )
    finally:
        session.close()

@app.get("/reports", response_class=HTMLResponse)
def reports_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers do not have access to financial reports.")
    session = get_session()
    try:
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()

        # Compile real operational reports
        bills = session.query(Bill).filter(Bill.status == "completed").all()
        total_sales = sum((float(b.total_amount) for b in bills), 0.0)
        bills_count = len(bills)
        avg_bill = (float(total_sales) / bills_count) if bills_count > 0 else 0.0

        bill_ids = [b.id for b in bills]
        gross_profit = 0.0
        if bill_ids:
            items = session.query(BillItem).filter(BillItem.bill_id.in_(bill_ids)).all()
            for it in items:
                gross_profit += float(it.profit or 0.0)

        gross_margin_pct = (gross_profit / float(total_sales) * 100) if total_sales > 0 else 0.0

        # Product Rankings
        prod_rankings_query = session.query(
            BillItem.product_name,
            BillItem.unit_price,
            BillItem.purchase_cost,
            func.sum(BillItem.quantity).label("units"),
            func.sum(BillItem.line_total).label("sales"),
            func.sum(BillItem.profit).label("profit")
        ).join(Bill, Bill.id == BillItem.bill_id)\
         .filter(Bill.status == "completed")\
         .group_by(BillItem.product_name)\
         .order_by(desc("sales")).limit(15).all()

        rankings = []
        for r in prod_rankings_query:
            s_val = float(r[4] or 0)
            p_val = float(r[5] or 0)
            m_pct = (p_val / s_val * 100) if s_val > 0 else 0.0
            rankings.append({
                "name": r[0],
                "selling_price": float(r[1] or 0),
                "purchase_cost": float(r[2] or 0),
                "units_sold": float(r[3] or 0),
                "sales_total": round(s_val, 2),
                "profit_total": round(p_val, 2),
                "margin_pct": round(m_pct, 1)
            })

        # Category sales
        categories = session.query(ShopCategory).all()
        cat_sales = []
        for c in categories:
            c_prods = [p.id for p in c.products]
            if c_prods and bill_ids:
                c_items = session.query(BillItem).filter(
                    BillItem.bill_id.in_(bill_ids),
                    BillItem.product_id.in_(c_prods)
                ).all()
                c_rev = sum((float(it.line_total) for it in c_items), 0.0)
                if c_rev > 0:
                    pct = round((c_rev / float(total_sales) * 100), 1) if total_sales > 0 else 0.0
                    cat_sales.append({"category": c.name, "sales": round(c_rev, 2), "pct": pct})

        # Payment channels
        pm_breakdown = {}
        pm_counts = {}
        for b in bills:
            pm = b.payment_method.upper()
            pm_breakdown[pm] = pm_breakdown.get(pm, 0.0) + float(b.total_amount)
            pm_counts[pm] = pm_counts.get(pm, 0) + 1

        channels = []
        for pm, amt in pm_breakdown.items():
            share = round((amt / float(total_sales) * 100), 1) if total_sales > 0 else 0.0
            channels.append({
                "method": pm,
                "amount": round(amt, 2),
                "bill_count": pm_counts.get(pm, 0),
                "share_pct": share
            })

        customers = session.query(ShopCustomer).all()
        total_udhaar = sum((float(c.credit_balance or 0) for c in customers), 0.0)

        report_data = {
            "total_sales": round(float(total_sales), 2),
            "bills_count": bills_count,
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_margin_pct, 1),
            "avg_bill_value": round(avg_bill, 2),
            "total_udhaar": round(total_udhaar, 2),
            "product_rankings": rankings,
            "category_sales": cat_sales,
            "payment_channels": channels
        }

        return templates.TemplateResponse(
            request=request,
            name="reports.html",
            context={
                "request": request,
                "page_title": "Reports & Analytics &bull; CARTIVANTA",
                "active_page": "reports",
                "current_user": user,
                "is_owner": True,
                "shop_profile": profile,
                "report_data": report_data
            }
        )
    finally:
        session.close()

@app.get("/discounts", response_class=HTMLResponse)
@app.get("/campaigns", response_class=HTMLResponse)
def discounts_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        shop_svc = ShopService(session)
        disc_svc = DiscountService(session)
        profile = shop_svc.get_shop_profile()
        overview = disc_svc.get_overview_metrics()
        discounts = disc_svc.get_all_discounts()
        products = session.query(ShopProduct).filter(ShopProduct.is_active == True).order_by(ShopProduct.name).all()
        categories = session.query(ShopCategory).filter(ShopCategory.is_active == True).order_by(ShopCategory.name).all()

        return templates.TemplateResponse(
            request=request,
            name="discounts.html",
            context={
                "request": request,
                "page_title": "Discounts & Offers &bull; CARTIVANTA",
                "active_page": "discounts",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "overview": overview,
                "discounts": discounts,
                "products": products,
                "categories": categories
            }
        )
    finally:
        session.close()

@app.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers do not have access to shop settings.")
    session = get_session()
    try:
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()
        users = session.query(User).filter(User.is_active == True).all()

        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "request": request,
                "page_title": "Settings &bull; CARTIVANTA",
                "active_page": "settings",
                "current_user": user,
                "is_owner": True,
                "shop_profile": profile,
                "users": users
            }
        )
    finally:
        session.close()

# --- SEGREGATED HISTORICAL 1.02M UCI BENCHMARK INSIGHTS TAB (GBP £) ---

@app.get("/insights", response_class=HTMLResponse)
def insights_view(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        shop_svc = ShopService(session)
        profile = shop_svc.get_shop_profile()

        # Historical UCI calculations (strictly GBP £)
        engine = SalesAnalyticsEngine(session)
        hist_kpis = engine.calculate_executive_kpis()
        monthly_trend = engine.get_monthly_sales_trend()
        category_sales = engine.get_sales_by_category()

        # Forecasts sample
        forecasts = session.query(DemandForecast).limit(10).all()
        forecasts_sample = [
            {
                "stock_code": f.stock_code,
                "date": str(f.forecast_date),
                "predicted_demand": float(f.predicted_demand),
                "lower_bound": float(f.lower_bound or 0),
                "upper_bound": float(f.upper_bound or 0),
                "wape": float(f.wape or 0.12)
            }
            for f in forecasts
        ]

        # Customer Segments summary
        c_engine = CustomerAnalyticsEngine(session)
        seg_summary = c_engine.get_segment_summary()

        return templates.TemplateResponse(
            request=request,
            name="insights.html",
            context={
                "request": request,
                "page_title": "Business Insights &bull; CARTIVANTA",
                "active_page": "insights",
                "current_user": user,
                "is_owner": user.get("is_owner", True),
                "shop_profile": profile,
                "historical_kpis": hist_kpis,
                "monthly_trend": monthly_trend,
                "category_sales": category_sales,
                "forecasts_sample": forecasts_sample,
                "customer_segments": seg_summary
            }
        )
    finally:
        session.close()

# --- OPERATIONAL REST API ENDPOINTS ---

@app.post("/api/billing/create")
def api_create_bill(data: CreateBillInput, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        pos_svc = PosService(session)
        items_payload = [it.dict() for it in data.items]
        bill = pos_svc.create_bill(
            items=items_payload,
            payment_method=data.payment_method,
            customer_id=data.customer_id,
            cashier_id=user.get("user_id"),
            bill_discount=data.bill_discount,
            paid_amount=data.paid_amount,
            notes=data.notes,
            discount_id=data.discount_id,
            discount_name=data.discount_name,
            discount_type=data.discount_type,
            discount_rate=data.discount_rate
        )
        receipt = pos_svc.get_bill_receipt_data(bill.id)
        return {"status": "success", "bill_id": bill.id, "bill_number": bill.bill_number, "receipt": receipt}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="We couldn't save this bill. Your stock has not been changed. Please try again.")
    finally:
        session.close()

@app.post("/api/billing/{bill_id}/cancel")
def api_cancel_bill(bill_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        pos_svc = PosService(session)
        bill = pos_svc.cancel_bill(bill_id=bill_id, user_id=user.get("user_id"))
        return {"status": "success", "bill_number": bill.bill_number, "bill_status": bill.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.get("/api/products")
def api_get_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    session = get_session()
    try:
        prod_svc = ProductService(session)
        products = prod_svc.get_products(search=search, category_id=category_id, active_only=True)
        # Cashier Privacy Check: Strip purchase price, profit, and margin %
        if not user.get("is_owner", False):
            for p in products:
                p["purchase_price"] = None
                p["unit_profit"] = None
                p["margin_pct"] = None
                p["stock_value"] = None
        return {"products": products}
    finally:
        session.close()

@app.get("/api/products/{product_id}")
def api_get_product_detail(product_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        prod_svc = ProductService(session)
        p = prod_svc.get_product_by_id(product_id)
        if not p:
            raise HTTPException(status_code=404, detail="Product not found.")
        if not user.get("is_owner", False):
            p["purchase_price"] = None
            p["unit_profit"] = None
            p["margin_pct"] = None
            p["stock_value"] = None
        return p
    finally:
        session.close()

@app.post("/api/products/add")
def api_add_product(data: ProductInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot create products.")
    session = get_session()
    try:
        prod_svc = ProductService(session)
        product = prod_svc.create_product(data.dict(), user_id=user.get("user_id"))
        return {"status": "success", "product_id": product.id, "name": product.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.put("/api/products/{product_id}/update")
def api_update_product(product_id: int, data: ProductInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot edit product details.")
    session = get_session()
    try:
        prod_svc = ProductService(session)
        product = prod_svc.update_product(product_id, data.dict())
        return {"status": "success", "product_id": product.id, "name": product.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/products/{product_id}/archive")
def api_archive_product(product_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot delete products.")
    session = get_session()
    try:
        prod_svc = ProductService(session)
        success = prod_svc.archive_product(product_id)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found.")
        return {"status": "success"}
    finally:
        session.close()

@app.get("/api/products/export-csv")
def api_export_products_csv(user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        prod_svc = ProductService(session)
        products = prod_svc.get_products(active_only=True)

        output = io.StringIO()
        writer = csv.writer(output)
        if user.get("is_owner", False):
            writer.writerow(["ID", "Barcode", "Product Name", "Brand", "Category", "Unit", "Cost Price", "Selling Price", "Margin %", "Current Stock", "GST Rate %", "Supplier"])
            for p in products:
                writer.writerow([p["id"], p["barcode"], p["name"], p["brand"], p["category_name"], p["unit"], p["purchase_price"], p["selling_price"], p["margin_pct"], p["stock_qty"], p["gst_rate"], p["supplier_name"]])
        else:
            writer.writerow(["ID", "Barcode", "Product Name", "Brand", "Category", "Unit", "Selling Price", "Current Stock", "GST Rate %"])
            for p in products:
                writer.writerow([p["id"], p["barcode"], p["name"], p["brand"], p["category_name"], p["unit"], p["selling_price"], p["stock_qty"], p["gst_rate"]])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cartivanta_products.csv"}
        )
    finally:
        session.close()

@app.post("/api/stock/adjust")
def api_adjust_stock(data: StockAdjustInput, user: Dict[str, Any] = Depends(get_current_user)):
    session = get_session()
    try:
        stock_svc = StockService(session)
        prod = stock_svc.adjust_stock(
            product_id=data.product_id,
            quantity_change=data.quantity_change,
            reason=data.reason,
            user_id=user.get("user_id")
        )
        return {"status": "success", "product_id": prod.id, "new_stock": float(prod.stock_qty)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/purchases/record")
def api_record_purchase(data: RecordPurchaseInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot record inward supplier purchases.")
    session = get_session()
    try:
        pur_svc = PurchaseService(session)
        items_payload = [it.dict() for it in data.items]
        purchase = pur_svc.record_purchase(
            supplier_id=data.supplier_id,
            invoice_no=data.invoice_no,
            items=items_payload,
            paid_amount=data.paid_amount,
            notes=data.notes,
            user_id=user.get("user_id")
        )
        return {"status": "success", "purchase_id": purchase.id, "invoice_no": purchase.invoice_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/purchases/supplier-payment")
def api_pay_supplier(data: SupplierPaymentInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot disburse supplier payments.")
    session = get_session()
    try:
        pur_svc = PurchaseService(session)
        sp = pur_svc.record_supplier_payment(
            supplier_id=data.supplier_id,
            amount=data.amount,
            payment_mode=data.payment_mode,
            reference_no=data.reference_no,
            notes=data.notes
        )
        return {"status": "success", "payment_id": sp.id, "remaining_balance": float(sp.balance_after)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/customers/add")
def api_add_customer(data: AddCustomerInput):
    session = get_session()
    try:
        khata_svc = KhataService(session)
        cust = khata_svc.add_customer(
            name=data.name,
            phone=data.phone,
            address=data.address,
            email=data.email
        )
        return {"id": cust.id, "name": cust.name, "phone": cust.phone}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/customers/{customer_id}/repayment")
def api_customer_repayment(customer_id: int, data: RepaymentInput):
    session = get_session()
    try:
        khata_svc = KhataService(session)
        txn = khata_svc.record_payment(
            customer_id=customer_id,
            amount=data.amount,
            payment_mode=data.payment_mode,
            notes=data.notes
        )
        return {"status": "success", "remaining_balance": float(txn.balance_after)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.get("/api/customers/{customer_id}/statement")
def api_customer_statement(customer_id: int):
    session = get_session()
    try:
        khata_svc = KhataService(session)
        stmt = khata_svc.get_customer_statement(customer_id)
        if not stmt:
            raise HTTPException(status_code=404, detail="Customer not found.")
        return stmt
    finally:
        session.close()

@app.post("/api/expenses/record")
def api_record_expense(data: ExpenseInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot record store expenses.")
    session = get_session()
    try:
        exp_svc = ExpenseService(session)
        exp = exp_svc.record_expense(
            category=data.category,
            amount=data.amount,
            description=data.description,
            payment_method=data.payment_method,
            user_id=user.get("user_id")
        )
        return {"status": "success", "expense_id": exp.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.get("/api/discounts/active")
def api_get_active_discounts():
    session = get_session()
    try:
        disc_svc = DiscountService(session)
        return disc_svc.get_active_discounts_for_billing()
    finally:
        session.close()

@app.post("/api/discounts/create")
def api_create_discount(data: DiscountInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot configure general discounts.")
    session = get_session()
    try:
        disc_svc = DiscountService(session)
        discount = disc_svc.create_discount(data.dict())
        return {"status": "success", "id": discount.id, "name": discount.name, "value": float(discount.discount_value), "type": discount.discount_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        session.close()

@app.post("/api/discounts/quick-create")
def api_quick_create_discount(data: QuickDiscountInput, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Allow Owner or authorized Cashier to create a custom discount on the fly directly from the billing POS screen.
    """
    session = get_session()
    try:
        disc_svc = DiscountService(session)
        today = date.today()
        payload = {
            "name": data.name,
            "discount_type": data.discount_type,
            "discount_value": data.discount_value,
            "applies_to": data.applies_to,
            "target_product_id": data.target_product_id,
            "start_date": today,
            "end_date": today + timedelta(days=30),
            "is_active": True,
            "description": "Created at billing counter"
        }
        discount = disc_svc.create_discount(payload)
        return {
            "status": "success",
            "id": discount.id,
            "name": discount.name,
            "discount_value": float(discount.discount_value),
            "discount_type": discount.discount_type,
            "applies_to": discount.applies_to
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        session.close()

@app.post("/api/discounts/{discount_id}/toggle")
def api_toggle_discount(discount_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Only owners can activate/deactivate discounts.")
    session = get_session()
    try:
        disc_svc = DiscountService(session)
        is_active = disc_svc.toggle_discount_active(discount_id)
        return {"status": "success", "is_active": is_active}
    finally:
        session.close()

@app.delete("/api/discounts/{discount_id}")
def api_delete_discount(discount_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Only owners can delete discounts.")
    session = get_session()
    try:
        disc_svc = DiscountService(session)
        success = disc_svc.delete_discount(discount_id)
        if not success:
            raise HTTPException(status_code=404, detail="Discount not found.")
        return {"status": "success"}
    finally:
        session.close()

@app.post("/api/campaigns/create")
def api_create_campaign(data: CampaignInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot configure festive campaigns.")
    session = get_session()
    try:
        camp = FestiveCampaign(
            name=data.name,
            festival_type=data.festival_type,
            discount_percentage=data.discount_percentage,
            target_category=data.target_category,
            start_date=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
            end_date=datetime.strptime(data.end_date, "%Y-%m-%d").date(),
            description=data.description,
            is_active=True
        )
        session.add(camp)
        session.commit()
        return {"status": "success", "campaign_id": camp.id, "name": camp.name}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()

@app.post("/api/settings/update")
def api_update_settings(data: ShopSettingsInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Cashiers cannot update store settings.")
    session = get_session()
    try:
        shop_svc = ShopService(session)
        prof = shop_svc.update_shop_profile(data.dict())
        return {"status": "success", "shop_name": prof.shop_name}
    finally:
        session.close()

@app.post("/api/auth/register-staff")
def api_register_staff(data: RegisterStaffInput, user: Dict[str, Any] = Depends(get_current_user)):
    if not user.get("is_owner", False):
        raise HTTPException(status_code=403, detail="Only Owners can create staff accounts.")
    session = get_session()
    try:
        existing = session.query(User).filter(User.username == data.username.strip().lower()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Username '{data.username}' is already taken.")
        new_u = User(
            username=data.username.strip().lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            role=data.role.lower(),
            is_active=True
        )
        session.add(new_u)
        session.commit()
        return {"status": "success", "username": new_u.username, "role": new_u.role}
    finally:
        session.close()

# --- HISTORICAL UCI ANALYTICS APIS (PRESERVED) ---

@app.get("/api/health")
def api_health():
    return {"status": "healthy", "platform": APP_NAME, "version": "2.0.0"}

@app.get("/api/festive/simulate-discount")
def simulate_festive_discount(
    stock_code: str = Query("85123A", description="Product Stock Code"),
    discount_pct: float = Query(0.15, description="Discount fraction, e.g. 0.15 for 15%"),
    uplift_pct: Optional[float] = Query(None, description="Expected volume uplift fraction"),
    campaign_name: str = Query("Diwali Golden Sparkle Sale")
):
    session = get_session()
    try:
        sim = FestiveDiscountSimulator(session)
        result = sim.simulate_discount(
            stock_code=stock_code,
            discount_pct=discount_pct,
            expected_demand_uplift_pct=uplift_pct,
            campaign_name=campaign_name
        )
        return result
    finally:
        session.close()

@app.get("/api/forecasts")
def get_forecast_results():
    session = get_session()
    try:
        forecasts = session.query(DemandForecast).all()
        grouped = {}
        for f in forecasts:
            code = f.stock_code
            if code not in grouped:
                grouped[code] = {
                    "stock_code": code,
                    "model_name": f.model_name,
                    "mae": float(f.mae or 0.0),
                    "rmse": float(f.rmse or 0.0),
                    "wape": float(f.wape or 0.0),
                    "forecast": []
                }
            grouped[code]["forecast"].append({
                "date": str(f.forecast_date),
                "predicted_demand": float(f.predicted_demand),
                "lower_bound": float(f.lower_bound or 0.0),
                "upper_bound": float(f.upper_bound or 0.0)
            })
        return {"products": list(grouped.values())}
    finally:
        session.close()
