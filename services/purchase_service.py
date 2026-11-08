"""
CARTIVANTA - Purchases and Supplier Management Service
Handles inward inventory, weighted average costing, supplier bills, and payables.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import (
    Purchase, PurchaseItem, Supplier, ShopProduct, StockMovement, SupplierPayment
)

class PurchaseService:
    def __init__(self, db: Session):
        self.db = db

    def record_purchase(
        self,
        supplier_id: int,
        invoice_no: str,
        items: List[Dict[str, Any]],
        paid_amount: float = 0.0,
        purchase_date: Optional[date] = None,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Purchase:
        """
        Record inward stock from supplier invoice.
        Increments stock, recalculates weighted average cost, records movement,
        and manages supplier payable balance.
        """
        if not items:
            raise ValueError("Purchase invoice must contain at least one product.")

        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        p_date = purchase_date or date.today()
        total_amount = Decimal("0.00")
        prepared_items = []

        for it in items:
            pid = it["product_id"]
            prod = self.db.query(ShopProduct).filter(ShopProduct.id == pid).first()
            if not prod:
                raise ValueError(f"Product ID {pid} not found.")

            qty = Decimal(str(it.get("quantity", 1)))
            unit_cost = Decimal(str(it.get("unit_cost", prod.purchase_price)))
            gst_rate = Decimal(str(it.get("gst_rate", prod.gst_rate)))

            if qty <= 0:
                raise ValueError(f"Quantity for {prod.name} must be greater than zero.")

            line_subtotal = qty * unit_cost
            line_tax = line_subtotal * (gst_rate / Decimal("100.0"))
            line_total = line_subtotal + line_tax
            total_amount += line_total

            prepared_items.append({
                "product": prod,
                "quantity": qty,
                "unit_cost": unit_cost,
                "gst_rate": gst_rate,
                "line_total": line_total
            })

        paid = Decimal(str(paid_amount))
        balance_due = max(Decimal("0.00"), total_amount - paid)
        payment_status = "paid" if balance_due <= Decimal("0.00") else ("partial" if paid > 0 else "pending")

        purchase = Purchase(
            invoice_no=invoice_no.strip(),
            supplier_id=supplier_id,
            total_amount=total_amount,
            paid_amount=paid,
            balance_due=balance_due,
            payment_status=payment_status,
            purchase_date=p_date,
            notes=notes
        )
        self.db.add(purchase)
        self.db.flush()

        for p_it in prepared_items:
            prod = p_it["product"]
            qty = p_it["quantity"]
            cost = p_it["unit_cost"]

            item_record = PurchaseItem(
                purchase_id=purchase.id,
                product_id=prod.id,
                product_name=prod.name,
                quantity=qty,
                unit_cost=cost,
                gst_rate=p_it["gst_rate"],
                line_total=p_it["line_total"]
            )
            self.db.add(item_record)

            # Weighted Average Cost Calculation
            current_qty = prod.stock_qty if prod.stock_qty > 0 else Decimal("0.00")
            current_cost = prod.purchase_price
            if (current_qty + qty) > 0:
                new_cost = ((current_qty * current_cost) + (qty * cost)) / (current_qty + qty)
                prod.purchase_price = round(new_cost, 2)

            # Increment stock
            prod.stock_qty = prod.stock_qty + qty

            # Record stock movement
            sm = StockMovement(
                product_id=prod.id,
                movement_type="purchase",
                quantity_change=qty,
                balance_after=prod.stock_qty,
                reason=f"Inward Supplier Invoice #{invoice_no}",
                user_id=user_id
            )
            self.db.add(sm)

        # Update supplier payable balance
        if balance_due > 0:
            supplier.balance_due = (supplier.balance_due or Decimal("0.00")) + balance_due

        self.db.commit()
        return purchase

    def record_supplier_payment(
        self,
        supplier_id: int,
        amount: float,
        payment_mode: str = "upi",
        reference_no: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SupplierPayment:
        """Record payment made to supplier to clear pending balance."""
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        amt = Decimal(str(amount))
        if amt <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        supplier.balance_due = max(Decimal("0.00"), (supplier.balance_due or Decimal("0.00")) - amt)

        sp = SupplierPayment(
            supplier_id=supplier_id,
            amount=amt,
            balance_after=supplier.balance_due,
            payment_mode=payment_mode,
            reference_no=reference_no,
            notes=notes
        )
        self.db.add(sp)
        self.db.commit()
        return sp

    def get_purchases(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent inward purchase records."""
        purchases = self.db.query(Purchase).order_by(desc(Purchase.created_at)).limit(limit).all()
        result = []
        for p in purchases:
            result.append({
                "id": p.id,
                "invoice_no": p.invoice_no,
                "supplier_name": p.supplier.name if p.supplier else "Direct Purchase",
                "purchase_date": p.purchase_date.strftime("%d-%m-%Y") if p.purchase_date else "",
                "total_amount": float(p.total_amount),
                "paid_amount": float(p.paid_amount),
                "balance_due": float(p.balance_due),
                "payment_status": p.payment_status.upper(),
                "item_count": len(p.items)
            })
        return result

    def get_suppliers(self) -> List[Dict[str, Any]]:
        """Fetch all suppliers with outstanding payables."""
        suppliers = self.db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name.asc()).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "phone": s.phone,
                "email": s.email or "",
                "address": s.address or "",
                "gstin": s.gstin or "",
                "balance_due": float(s.balance_due or 0.0),
                "product_count": len(s.products)
            }
            for s in suppliers
        ]
