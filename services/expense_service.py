"""
CARTIVANTA - Expense and Profitability Service
Tracks store operating costs (rent, salary, power, packaging) and computes
Net Operating Profit: Net Sales - COGS - Operating Expenses = Net Profit.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from database.models import Expense, Bill, BillItem, User

class ExpenseService:
    def __init__(self, db: Session):
        self.db = db

    def record_expense(
        self,
        category: str,
        amount: float,
        description: str,
        payment_method: str = "cash",
        expense_date: Optional[date] = None,
        user_id: Optional[int] = None
    ) -> Expense:
        """Record an operational expenditure."""
        amt = Decimal(str(amount))
        if amt <= 0:
            raise ValueError("Expense amount must be greater than zero.")
        if not description or not description.strip():
            raise ValueError("A clear description for the expense is required.")

        exp = Expense(
            category=category.lower().strip(),
            amount=amt,
            description=description.strip(),
            payment_method=payment_method.lower().strip(),
            expense_date=expense_date or date.today(),
            user_id=user_id
        )
        self.db.add(exp)
        self.db.commit()
        return exp

    def get_expenses(
        self,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List expenses with category and date filtering."""
        query = self.db.query(Expense)
        if category and category.lower() != "all":
            query = query.filter(Expense.category == category.lower())
        if start_date:
            query = query.filter(Expense.expense_date >= start_date)
        if end_date:
            query = query.filter(Expense.expense_date <= end_date)

        expenses = query.order_by(desc(Expense.expense_date), desc(Expense.id)).limit(limit).all()
        return [
            {
                "id": e.id,
                "category": e.category.capitalize(),
                "amount": float(e.amount),
                "description": e.description,
                "expense_date": e.expense_date.strftime("%d-%m-%Y") if e.expense_date else "",
                "payment_method": e.payment_method.upper(),
                "recorded_by": e.user.full_name if e.user else "Admin"
            }
            for e in expenses
        ]

    def get_net_operating_profit_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Compute true store financial statement:
        Sales Revenue - COGS = Gross Profit
        Gross Profit - Operating Expenses = Net Operating Profit
        """
        # Default to current month if no dates supplied
        if not start_date:
            today = date.today()
            start_date = today.replace(day=1)
        if not end_date:
            end_date = date.today()

        # Query completed bills within date range
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        bills = self.db.query(Bill).filter(
            Bill.status == "completed",
            Bill.created_at >= start_dt,
            Bill.created_at <= end_dt
        ).all()

        total_sales = Decimal("0.00")
        total_cogs = Decimal("0.00")
        bill_ids = [b.id for b in bills]

        if bill_ids:
            total_sales = sum((b.total_amount for b in bills), Decimal("0.00"))
            items = self.db.query(BillItem).filter(BillItem.bill_id.in_(bill_ids)).all()
            total_cogs = sum(((it.quantity * it.purchase_cost) for it in items), Decimal("0.00"))

        gross_profit = total_sales - total_cogs
        gross_margin_pct = (float(gross_profit) / float(total_sales) * 100) if total_sales > 0 else 0.0

        # Query expenses within date range
        expenses = self.db.query(Expense).filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).all()

        total_expenses = sum((e.amount for e in expenses), Decimal("0.00"))
        net_operating_profit = gross_profit - total_expenses
        net_profit_margin_pct = (float(net_operating_profit) / float(total_sales) * 100) if total_sales > 0 else 0.0

        # Expense breakdown by category
        cat_breakdown = {}
        for e in expenses:
            cat = e.category.capitalize()
            cat_breakdown[cat] = cat_breakdown.get(cat, 0.0) + float(e.amount)

        return {
            "period": f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}",
            "bills_count": len(bills),
            "net_sales": round(float(total_sales), 2),
            "cogs": round(float(total_cogs), 2),
            "gross_profit": round(float(gross_profit), 2),
            "gross_margin_pct": round(gross_margin_pct, 1),
            "total_operating_expenses": round(float(total_expenses), 2),
            "net_operating_profit": round(float(net_operating_profit), 2),
            "net_profit_margin_pct": round(net_profit_margin_pct, 1),
            "expense_categories": cat_breakdown
        }
