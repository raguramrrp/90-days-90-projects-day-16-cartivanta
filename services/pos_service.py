"""
CARTIVANTA - POS & Billing Service
Handles transactional bill creation, atomic stock deduction, unique bill numbering,
multi-mode payments (Cash, UPI, Card, Udhaar/Credit), receipt generation, and returns.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from database.models import (
    Bill, BillItem, ShopProduct, StockMovement, ShopCustomer,
    CustomerCreditTransaction, ShopProfile, User
)

class PosService:
    def __init__(self, db: Session):
        self.db = db

    def generate_bill_number(self) -> str:
        """Generate a sequential unique bill number, e.g. BILL-2026-0004."""
        current_year = datetime.utcnow().year
        prefix = f"BILL-{current_year}-"
        last_bill = self.db.query(Bill).filter(Bill.bill_number.like(f"{prefix}%")).order_by(Bill.id.desc()).first()
        if not last_bill:
            seq = 1
        else:
            try:
                seq_str = last_bill.bill_number.split("-")[-1]
                seq = int(seq_str) + 1
            except Exception:
                seq = self.db.query(Bill).count() + 1
        return f"{prefix}{seq:04d}"

    def create_bill(
        self,
        items: List[Dict[str, Any]],
        payment_method: str = "cash",
        customer_id: Optional[int] = None,
        cashier_id: Optional[int] = None,
        bill_discount: float = 0.0,
        paid_amount: Optional[float] = None,
        notes: Optional[str] = None,
        discount_id: Optional[int] = None,
        discount_name: Optional[str] = None,
        discount_type: Optional[str] = None,
        discount_rate: Optional[float] = None
    ) -> Bill:
        """
        Atomically process and finalize a POS sale bill.
        Enforces stock validation, stock decrement, stock movement audit trail,
        GST calculation, customer metrics, and credit ledger (Udhaar).
        """
        if not items:
            raise ValueError("Cart is empty. Add at least one product to create a bill.")

        payment_method = payment_method.lower().strip()
        if payment_method not in ("cash", "upi", "card", "credit"):
            raise ValueError(f"Invalid payment method: {payment_method}")

        bill_number = self.generate_bill_number()

        # Step 1: Pre-validate stock and load products
        product_ids = [item["product_id"] for item in items]
        products = self.db.query(ShopProduct).filter(ShopProduct.id.in_(product_ids)).all()
        prod_map = {p.id: p for p in products}

        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_item_discount = Decimal("0.00")
        prepared_items = []

        for item in items:
            pid = item["product_id"]
            p = prod_map.get(pid)
            if not p:
                raise ValueError(f"Product ID {pid} not found.")

            qty = Decimal(str(item.get("quantity", 1)))
            if qty <= 0:
                raise ValueError(f"Quantity for '{p.name}' must be greater than zero.")

            # Strict stock availability check
            if p.stock_qty < qty:
                raise ValueError(
                    f"Insufficient stock for '{p.name}'. Available: {p.stock_qty} {p.unit}, Requested: {qty} {p.unit}."
                )

            item_disc = Decimal(str(item.get("discount_amount", 0.0)))
            unit_price = p.selling_price
            unit_cost = p.purchase_price
            gst_rate = p.gst_rate

            line_gross = qty * unit_price
            line_net = max(Decimal("0.00"), line_gross - item_disc)
            
            # Tax calculation (price inclusive of GST or GST applied)
            # Line tax amount = line_net * (gst_rate / 100)
            line_tax = round(line_net * (gst_rate / Decimal("100.0")), 2)
            item_profit = (line_net - (qty * unit_cost))

            subtotal += line_gross
            total_item_discount += item_disc
            total_tax += line_tax

            prepared_items.append({
                "product": p,
                "quantity": qty,
                "unit_price": unit_price,
                "purchase_cost": unit_cost,
                "discount_amount": item_disc,
                "tax_rate": gst_rate,
                "line_total": line_net,
                "profit": item_profit
            })

        overall_discount = total_item_discount + Decimal(str(bill_discount))
        final_total = max(Decimal("0.00"), subtotal - overall_discount + total_tax)

        if paid_amount is None:
            if payment_method == "credit":
                paid = Decimal("0.00")
            else:
                paid = final_total
        else:
            paid = Decimal(str(paid_amount))

        balance_due = max(Decimal("0.00"), final_total - paid)

        # Step 2: Create Bill record
        bill = Bill(
            bill_number=bill_number,
            customer_id=customer_id,
            cashier_id=cashier_id,
            payment_method=payment_method,
            subtotal=subtotal,
            discount_amount=overall_discount,
            discount_id=discount_id,
            discount_name=discount_name,
            discount_type=discount_type,
            discount_rate=Decimal(str(discount_rate)) if discount_rate is not None else None,
            tax_amount=total_tax,
            total_amount=final_total,
            paid_amount=paid,
            balance_due=balance_due,
            status="completed",
            notes=notes
        )
        self.db.add(bill)
        self.db.flush()

        # Step 3: Insert BillItems and Decrement Product Stock atomically
        for p_item in prepared_items:
            prod = p_item["product"]
            qty = p_item["quantity"]

            bi = BillItem(
                bill_id=bill.id,
                product_id=prod.id,
                product_name=prod.name,
                quantity=qty,
                unit_price=p_item["unit_price"],
                purchase_cost=p_item["purchase_cost"],
                discount_amount=p_item["discount_amount"],
                tax_rate=p_item["tax_rate"],
                line_total=p_item["line_total"],
                profit=p_item["profit"]
            )
            self.db.add(bi)

            # Atomic decrement
            prod.stock_qty = prod.stock_qty - qty
            new_balance = prod.stock_qty

            # Audit stock movement
            sm = StockMovement(
                product_id=prod.id,
                movement_type="sale",
                quantity_change=-qty,
                balance_after=new_balance,
                reason=f"Sale Bill #{bill_number}",
                user_id=cashier_id
            )
            self.db.add(sm)

        # Step 4: Handle Customer Metrics and Credit / Udhaar
        if customer_id:
            customer = self.db.query(ShopCustomer).filter(ShopCustomer.id == customer_id).first()
            if customer:
                customer.total_spent = (customer.total_spent or Decimal("0.00")) + final_total
                customer.visit_count = (customer.visit_count or 0) + 1

                # If customer owes money (Credit / Udhaar or partial payment)
                if balance_due > 0:
                    customer.credit_balance = (customer.credit_balance or Decimal("0.00")) + balance_due
                    cred_txn = CustomerCreditTransaction(
                        customer_id=customer.id,
                        bill_id=bill.id,
                        txn_type="credit_issued",
                        amount=balance_due,
                        balance_after=customer.credit_balance,
                        payment_mode=payment_method,
                        notes=f"Credit issued on bill #{bill_number}"
                    )
                    self.db.add(cred_txn)

        self.db.commit()
        return bill

    def cancel_bill(self, bill_id: int, reason: str = "Customer requested cancellation", user_id: Optional[int] = None) -> Bill:
        """
        Cancel a bill, atomically restore inventory stock, and reverse any Udhaar.
        """
        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found.")
        if bill.status == "cancelled":
            raise ValueError(f"Bill #{bill.bill_number} is already cancelled.")

        # Restore stock for each item
        for item in bill.items:
            if item.product_id:
                prod = self.db.query(ShopProduct).filter(ShopProduct.id == item.product_id).first()
                if prod:
                    prod.stock_qty = prod.stock_qty + item.quantity
                    sm = StockMovement(
                        product_id=prod.id,
                        movement_type="return",
                        quantity_change=item.quantity,
                        balance_after=prod.stock_qty,
                        reason=f"Cancelled Bill #{bill.bill_number}: {reason}",
                        user_id=user_id
                    )
                    self.db.add(sm)

        # Reverse credit if Udhaar was issued
        if bill.customer_id and bill.balance_due > 0:
            customer = self.db.query(ShopCustomer).filter(ShopCustomer.id == bill.customer_id).first()
            if customer:
                customer.credit_balance = max(Decimal("0.00"), customer.credit_balance - bill.balance_due)
                cred_txn = CustomerCreditTransaction(
                    customer_id=customer.id,
                    bill_id=bill.id,
                    txn_type="payment_received",
                    amount=bill.balance_due,
                    balance_after=customer.credit_balance,
                    payment_mode="reversal",
                    notes=f"Credit reversed due to cancellation of #{bill.bill_number}"
                )
                self.db.add(cred_txn)

        bill.status = "cancelled"
        bill.notes = f"{bill.notes or ''} [Cancelled: {reason}]".strip()
        self.db.commit()
        return bill

    def get_bill_receipt_data(self, bill_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve complete formatted receipt details for thermal & A4 printouts."""
        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            return None

        profile = self.db.query(ShopProfile).first()
        shop_info = {
            "name": profile.shop_name if profile else "Cartivanta Retail Store",
            "tagline": profile.tagline if profile else "",
            "phone": profile.phone if profile else "",
            "address": profile.address if profile else "",
            "gstin": profile.gstin if profile else "",
            "footer": profile.receipt_footer if profile else "Thank you! Visit again."
        }

        cashier_name = bill.cashier.full_name if bill.cashier else "Cashier"
        customer_info = None
        if bill.customer:
            customer_info = {
                "name": bill.customer.name,
                "phone": bill.customer.phone,
                "address": bill.customer.address or "",
                "credit_balance": float(bill.customer.credit_balance or 0.0)
            }

        items = []
        for it in bill.items:
            items.append({
                "product_name": it.product_name,
                "quantity": float(it.quantity),
                "unit_price": float(it.unit_price),
                "discount": float(it.discount_amount or 0.0),
                "tax_rate": float(it.tax_rate or 0.0),
                "line_total": float(it.line_total)
            })

        return {
            "id": bill.id,
            "bill_number": bill.bill_number,
            "created_at": bill.created_at.strftime("%d-%m-%Y %I:%M %p"),
            "status": bill.status,
            "payment_method": bill.payment_method.upper(),
            "subtotal": float(bill.subtotal),
            "discount_amount": float(bill.discount_amount),
            "discount_name": bill.discount_name or "",
            "discount_rate": float(bill.discount_rate or 0.0),
            "discount_type": bill.discount_type or "",
            "tax_amount": float(bill.tax_amount),
            "total_amount": float(bill.total_amount),
            "paid_amount": float(bill.paid_amount),
            "balance_due": float(bill.balance_due),
            "notes": bill.notes or "",
            "cashier": cashier_name,
            "customer": customer_info,
            "shop": shop_info,
            "items": items
        }

    def get_recent_bills(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch recently generated sales bills."""
        bills = self.db.query(Bill).order_by(desc(Bill.created_at)).limit(limit).all()
        result = []
        for b in bills:
            result.append({
                "id": b.id,
                "bill_number": b.bill_number,
                "created_at": b.created_at.strftime("%d-%m-%Y %I:%M %p"),
                "customer_name": b.customer.name if b.customer else "Walk-in Customer",
                "customer_phone": b.customer.phone if b.customer else "",
                "payment_method": b.payment_method.upper(),
                "total_amount": float(b.total_amount),
                "paid_amount": float(b.paid_amount),
                "balance_due": float(b.balance_due),
                "status": b.status,
                "item_count": len(b.items)
            })
        return result
