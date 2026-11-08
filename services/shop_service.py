"""
CARTIVANTA - Shop Overview & Daily Dashboard Service
Aggregates daily sales, profit, payment modes, best sellers, and alerts for shopkeepers.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database.models import (
    Bill, BillItem, ShopProduct, ShopCustomer, Supplier,
    Expense, ShopProfile, StockMovement
)

class ShopService:
    def __init__(self, db: Session):
        self.db = db

    def get_shop_profile(self) -> Dict[str, Any]:
        """Fetch shop profile configuration."""
        profile = self.db.query(ShopProfile).first()
        if not profile:
            return {
                "shop_name": "RR Supermarket",
                "tagline": "Quality Daily Needs, Groceries & Provisions (Demo Store)",
                "phone": "+91 99999 00000",
                "address": "Shop 101, Fictional Commercial Ring Road, Sector 0, Unreal Nagar, Fantasy City - 000000",
                "gstin": "00XXXXX0000X1Z5",
                "currency": "INR",
                "currency_symbol": "₹",
                "receipt_footer": "Thank you for shopping at RR Supermarket! Visit again. Save Paper, Save Trees."
            }
        return {
            "id": profile.id,
            "shop_name": profile.shop_name,
            "tagline": profile.tagline or "",
            "phone": profile.phone or "",
            "address": profile.address or "",
            "gstin": profile.gstin or "",
            "currency": profile.currency or "INR",
            "currency_symbol": profile.currency_symbol or "₹",
            "receipt_footer": profile.receipt_footer or ""
        }

    def update_shop_profile(self, data: Dict[str, Any]) -> ShopProfile:
        """Update shop details."""
        profile = self.db.query(ShopProfile).first()
        if not profile:
            profile = ShopProfile()
            self.db.add(profile)

        if "shop_name" in data and data["shop_name"].strip():
            profile.shop_name = data["shop_name"].strip()
        if "tagline" in data:
            profile.tagline = data["tagline"].strip()
        if "phone" in data:
            profile.phone = data["phone"].strip()
        if "address" in data:
            profile.address = data["address"].strip()
        if "gstin" in data:
            profile.gstin = data["gstin"].strip()
        if "receipt_footer" in data:
            profile.receipt_footer = data["receipt_footer"].strip()

        self.db.commit()
        return profile

    def get_dashboard_summary(self, is_owner: bool = True) -> Dict[str, Any]:
        """
        Answers the 5 core shopkeeper questions:
        1. How much did I sell today?
        2. How much profit did I approximately make? (Owner only)
        3. What products are running out?
        4. Which products are selling the most?
        5. What needs my attention? (Pending Udhaar, low stock)
        """
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_end - timedelta(days=1)

        # Today's completed bills
        today_bills = self.db.query(Bill).filter(
            Bill.status == "completed",
            Bill.created_at >= today_start,
            Bill.created_at <= today_end
        ).all()

        today_sales = sum((b.total_amount for b in today_bills), Decimal("0.00"))
        today_bills_count = len(today_bills)

        # Yesterday's sales for comparison
        yest_bills = self.db.query(Bill).filter(
            Bill.status == "completed",
            Bill.created_at >= yesterday_start,
            Bill.created_at <= yesterday_end
        ).all()
        yest_sales = sum((b.total_amount for b in yest_bills), Decimal("0.00"))

        sales_growth_pct = 0.0
        if yest_sales > 0:
            sales_growth_pct = round(((float(today_sales) - float(yest_sales)) / float(yest_sales)) * 100, 1)

        # Profit & Units calculation
        today_profit = Decimal("0.00")
        today_units_sold = 0.0
        today_bill_ids = [b.id for b in today_bills]

        if today_bill_ids:
            items = self.db.query(BillItem).filter(BillItem.bill_id.in_(today_bill_ids)).all()
            for it in items:
                today_units_sold += float(it.quantity or 0)
                today_profit += Decimal(str(it.profit or 0.0))

        # Payment methods breakdown today
        payment_breakdown = {"CASH": 0.0, "UPI": 0.0, "CARD": 0.0, "CREDIT": 0.0}
        for b in today_bills:
            pm = b.payment_method.upper()
            payment_breakdown[pm] = payment_breakdown.get(pm, 0.0) + float(b.total_amount)

        # Low stock count
        low_stock_prods = self.db.query(ShopProduct).filter(
            ShopProduct.is_active == True,
            ShopProduct.stock_qty <= ShopProduct.min_stock_qty
        ).all()
        low_stock_count = len(low_stock_prods)

        # Total outstanding Udhaar across all customers
        total_udhaar = self.db.query(func.sum(ShopCustomer.credit_balance)).scalar() or Decimal("0.00")
        total_supplier_payable = self.db.query(func.sum(Supplier.balance_due)).scalar() or Decimal("0.00")

        # Top 5 selling products today (by quantity)
        top_items_query = self.db.query(
            BillItem.product_name,
            func.sum(BillItem.quantity).label("units_sold"),
            func.sum(BillItem.line_total).label("sales_val"),
            func.sum(BillItem.profit).label("profit_val")
        ).join(Bill, Bill.id == BillItem.bill_id)\
         .filter(Bill.status == "completed", Bill.created_at >= today_start)\
         .group_by(BillItem.product_name)\
         .order_by(desc("units_sold"))\
         .limit(5).all()

        top_products = []
        for row in top_items_query:
            top_products.append({
                "product_name": row[0],
                "units_sold": float(row[1] or 0),
                "sales_amount": float(row[2] or 0),
                "profit_amount": float(row[3] or 0) if is_owner else None
            })

        # Recent bills
        recent_bills_query = self.db.query(Bill).order_by(desc(Bill.created_at)).limit(6).all()
        recent_bills = []
        for b in recent_bills_query:
            recent_bills.append({
                "id": b.id,
                "bill_number": b.bill_number,
                "time": b.created_at.strftime("%I:%M %p"),
                "customer": b.customer.name if b.customer else "Walk-in",
                "payment_method": b.payment_method.upper(),
                "total_amount": float(b.total_amount),
                "status": b.status
            })

        # Actionable alerts list
        alerts = []
        for p in low_stock_prods[:4]:
            alerts.append({
                "type": "warning",
                "title": f"Low Stock: {p.name}",
                "message": f"Only {float(p.stock_qty):.0f} {p.unit} remaining (minimum threshold: {float(p.min_stock_qty):.0f}).",
                "link": f"/stock"
            })

        if float(total_udhaar) > 0:
            alerts.append({
                "type": "info",
                "title": "Pending Customer Udhaar",
                "message": f"Total outstanding customer credit balance is ₹{float(total_udhaar):,.2f}.",
                "link": "/customers"
            })

        if float(total_supplier_payable) > 0 and is_owner:
            alerts.append({
                "type": "info",
                "title": "Supplier Invoices Due",
                "message": f"Total pending payables to suppliers is ₹{float(total_supplier_payable):,.2f}.",
                "link": "/purchases"
            })

        return {
            "today_sales": round(float(today_sales), 2),
            "today_profit": round(float(today_profit), 2) if is_owner else None,
            "today_bills_count": today_bills_count,
            "today_units_sold": round(today_units_sold, 1),
            "sales_growth_pct": sales_growth_pct,
            "low_stock_count": low_stock_count,
            "total_udhaar": round(float(total_udhaar), 2),
            "total_supplier_payable": round(float(total_supplier_payable), 2) if is_owner else None,
            "payment_breakdown": payment_breakdown,
            "top_products": top_products,
            "recent_bills": recent_bills,
            "alerts": alerts
        }
