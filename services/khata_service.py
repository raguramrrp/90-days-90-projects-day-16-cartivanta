"""
CARTIVANTA - Khata & Customer Credit Management Service
Manages customer credit ledgers (Udhaar), repayment logging, and statements of account.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import ShopCustomer, CustomerCreditTransaction, Bill

class KhataService:
    def __init__(self, db: Session):
        self.db = db

    def get_customers(self, search: Optional[str] = None, credit_only: bool = False) -> List[Dict[str, Any]]:
        """List customers with balance, visits, and total spent."""
        query = self.db.query(ShopCustomer)
        if credit_only:
            query = query.filter(ShopCustomer.credit_balance > 0)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(ShopCustomer.name.ilike(term) | ShopCustomer.phone.ilike(term))

        customers = query.order_by(desc(ShopCustomer.credit_balance), ShopCustomer.name.asc()).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "address": c.address or "",
                "credit_balance": float(c.credit_balance or 0.0),
                "total_spent": float(c.total_spent or 0.0),
                "visit_count": c.visit_count or 0,
                "created_at": c.created_at.strftime("%d-%m-%Y") if c.created_at else ""
            }
            for c in customers
        ]

    def add_customer(self, name: str, phone: str, address: Optional[str] = None, email: Optional[str] = None) -> ShopCustomer:
        """Register a new customer for billing and khata."""
        phone_clean = phone.strip()
        existing = self.db.query(ShopCustomer).filter(ShopCustomer.phone == phone_clean).first()
        if existing:
            raise ValueError(f"Customer with phone '{phone_clean}' already exists: {existing.name}")

        cust = ShopCustomer(
            name=name.strip(),
            phone=phone_clean,
            address=address.strip() if address else None,
            email=email.strip() if email else None,
            credit_balance=Decimal("0.00"),
            total_spent=Decimal("0.00"),
            visit_count=0
        )
        self.db.add(cust)
        self.db.commit()
        return cust

    def record_payment(
        self,
        customer_id: int,
        amount: float,
        payment_mode: str = "cash",
        notes: Optional[str] = None
    ) -> CustomerCreditTransaction:
        """Record repayment of Udhaar from customer."""
        customer = self.db.query(ShopCustomer).filter(ShopCustomer.id == customer_id).first()
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found.")

        amt = Decimal(str(amount))
        if amt <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        # Update customer credit balance
        new_balance = max(Decimal("0.00"), (customer.credit_balance or Decimal("0.00")) - amt)
        customer.credit_balance = new_balance

        txn = CustomerCreditTransaction(
            customer_id=customer.id,
            txn_type="payment_received",
            amount=amt,
            balance_after=new_balance,
            payment_mode=payment_mode,
            notes=notes or "Customer Udhaar repayment"
        )
        self.db.add(txn)
        self.db.commit()
        return txn

    def get_customer_statement(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve complete ledger history of purchases and repayments for customer statement."""
        customer = self.db.query(ShopCustomer).filter(ShopCustomer.id == customer_id).first()
        if not customer:
            return None

        txns = self.db.query(CustomerCreditTransaction).filter(
            CustomerCreditTransaction.customer_id == customer_id
        ).order_by(desc(CustomerCreditTransaction.created_at)).all()

        txn_list = [
            {
                "id": t.id,
                "date": t.created_at.strftime("%d-%m-%Y %I:%M %p"),
                "type": "Credit Purchase" if t.txn_type == "credit_issued" else "Payment Received",
                "amount": float(t.amount),
                "balance_after": float(t.balance_after),
                "payment_mode": (t.payment_mode or "").upper(),
                "notes": t.notes or ""
            }
            for t in txns
        ]

        recent_bills = self.db.query(Bill).filter(
            Bill.customer_id == customer_id
        ).order_by(desc(Bill.created_at)).limit(10).all()

        bill_list = [
            {
                "id": b.id,
                "bill_number": b.bill_number,
                "date": b.created_at.strftime("%d-%m-%Y %I:%M %p"),
                "total_amount": float(b.total_amount),
                "paid_amount": float(b.paid_amount),
                "balance_due": float(b.balance_due),
                "status": b.status
            }
            for b in recent_bills
        ]

        return {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "address": customer.address or "",
                "credit_balance": float(customer.credit_balance or 0.0),
                "total_spent": float(customer.total_spent or 0.0),
                "visit_count": customer.visit_count or 0
            },
            "transactions": txn_list,
            "bills": bill_list
        }
