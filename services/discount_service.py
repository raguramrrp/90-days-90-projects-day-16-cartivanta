"""
CARTIVANTA - Discount & Offers Service
Complete discount calculation, lifecycle management, and billing integration.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.models import DiscountOffer, Bill, ShopProduct, ShopCategory

class DiscountService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview_metrics(self) -> Dict[str, Any]:
        """Compute summary metrics for Discounts & Offers screen."""
        today = date.today()
        all_discounts = self.db.query(DiscountOffer).all()

        active_count = 0
        scheduled_count = 0
        expired_count = 0
        products_on_offer_ids = set()

        for d in all_discounts:
            if not d.is_active:
                continue
            if d.end_date < today:
                expired_count += 1
            elif d.start_date > today:
                scheduled_count += 1
            else:
                active_count += 1
                if d.applies_to == "product" and d.target_product_id:
                    products_on_offer_ids.add(d.target_product_id)
                elif d.applies_to == "category" and d.target_category_id:
                    prods = self.db.query(ShopProduct.id).filter(ShopProduct.category_id == d.target_category_id).all()
                    for p in prods:
                        products_on_offer_ids.add(p[0])
                elif d.applies_to == "entire_bill":
                    # All active products participate
                    total_prods = self.db.query(func.count(ShopProduct.id)).scalar() or 0
                    products_on_offer_ids.update(range(1, total_prods + 1))

        # Total historical discount savings given to customers
        total_given = self.db.query(func.coalesce(func.sum(Bill.discount_amount), 0.0)).filter(
            Bill.status == "completed"
        ).scalar() or 0.0

        return {
            "active_discounts": active_count,
            "scheduled_discounts": scheduled_count,
            "expired_discounts": expired_count,
            "total_discount_given": float(total_given),
            "products_on_offer_count": len(products_on_offer_ids)
        }

    def get_all_discounts(self) -> List[Dict[str, Any]]:
        """Retrieve all discounts with calculated display status."""
        today = date.today()
        discounts = self.db.query(DiscountOffer).order_by(desc(DiscountOffer.created_at)).all()

        results = []
        for d in discounts:
            if not d.is_active:
                status = "Inactive"
                badge_class = "bg-slate-100 text-slate-600"
            elif d.end_date < today:
                status = "Expired"
                badge_class = "bg-rose-50 text-rose-700 border border-rose-200"
            elif d.start_date > today:
                status = "Scheduled"
                badge_class = "bg-amber-50 text-amber-700 border border-amber-200"
            else:
                status = "Active"
                badge_class = "bg-emerald-50 text-emerald-700 border border-emerald-200"

            applies_to_display = "Entire Bill"
            if d.applies_to == "product" and d.target_product:
                applies_to_display = f"Product: {d.target_product.name}"
            elif d.applies_to == "category" and d.target_category:
                applies_to_display = f"Category: {d.target_category.name}"

            results.append({
                "id": d.id,
                "name": d.name,
                "discount_type": d.discount_type,
                "discount_value": float(d.discount_value),
                "value_display": f"{d.discount_value}%" if d.discount_type == "percentage" else f"₹{d.discount_value:.2f}",
                "applies_to": d.applies_to,
                "applies_to_display": applies_to_display,
                "target_product_id": d.target_product_id,
                "target_category_id": d.target_category_id,
                "min_bill_amount": float(d.min_bill_amount or 0.0),
                "max_discount_amount": float(d.max_discount_amount) if d.max_discount_amount else None,
                "start_date": str(d.start_date),
                "end_date": str(d.end_date),
                "is_active": d.is_active,
                "status": status,
                "badge_class": badge_class,
                "description": d.description or ""
            })
        return results

    def get_active_discounts_for_billing(self) -> List[Dict[str, Any]]:
        """Fetch only currently valid active discounts for POS cashier dropdown."""
        today = date.today()
        discounts = self.db.query(DiscountOffer).filter(
            DiscountOffer.is_active == True,
            DiscountOffer.start_date <= today,
            DiscountOffer.end_date >= today
        ).order_by(DiscountOffer.name).all()

        results = []
        for d in discounts:
            label = f"{d.name} ({d.discount_value}% Off)" if d.discount_type == "percentage" else f"{d.name} (Flat ₹{d.discount_value:.0f} Off)"
            results.append({
                "id": d.id,
                "name": d.name,
                "label": label,
                "discount_type": d.discount_type,
                "discount_value": float(d.discount_value),
                "applies_to": d.applies_to,
                "target_product_id": d.target_product_id,
                "target_category_id": d.target_category_id,
                "min_bill_amount": float(d.min_bill_amount or 0.0),
                "max_discount_amount": float(d.max_discount_amount) if d.max_discount_amount else None
            })
        return results

    def create_discount(self, data: Dict[str, Any]) -> DiscountOffer:
        """Validate and create a new discount offer."""
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Discount Name is required.")

        discount_type = str(data.get("discount_type", "percentage")).lower()
        if discount_type not in ["percentage", "fixed"]:
            raise ValueError("Discount Type must be 'percentage' or 'fixed'.")

        try:
            val = Decimal(str(data.get("discount_value", 0.0)))
        except Exception:
            raise ValueError("Invalid discount value.")

        if val <= Decimal("0.00"):
            raise ValueError("Discount value must be greater than zero.")
        if discount_type == "percentage" and val > Decimal("100.00"):
            raise ValueError("Percentage discount cannot exceed 100%.")

        applies_to = str(data.get("applies_to", "entire_bill")).lower()
        if applies_to not in ["entire_bill", "product", "category"]:
            applies_to = "entire_bill"

        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif not start_date:
            start_date = date.today()

        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif not end_date:
            end_date = start_date

        if end_date < start_date:
            raise ValueError("End date cannot be earlier than start date.")

        min_bill = Decimal(str(data.get("min_bill_amount") or "0.00"))
        max_disc = Decimal(str(data["max_discount_amount"])) if data.get("max_discount_amount") else None

        discount = DiscountOffer(
            name=name,
            discount_type=discount_type,
            discount_value=val,
            applies_to=applies_to,
            target_product_id=data.get("target_product_id"),
            target_category_id=data.get("target_category_id"),
            min_bill_amount=min_bill,
            max_discount_amount=max_disc,
            start_date=start_date,
            end_date=end_date,
            is_active=bool(data.get("is_active", True)),
            description=data.get("description", "")
        )
        self.db.add(discount)
        self.db.commit()
        self.db.refresh(discount)
        return discount

    def quick_create_discount(self, name: str, discount_type: str, discount_value: float, min_bill_amount: float = 0.0) -> DiscountOffer:
        """Create and activate a quick discount directly from the billing screen."""
        today = date.today()
        end = today + timedelta(days=30)
        return self.create_discount({
            "name": name,
            "description": "Quick custom discount created at checkout",
            "discount_type": discount_type,
            "discount_value": discount_value,
            "applies_to": "entire_bill",
            "min_bill_amount": min_bill_amount,
            "max_discount_amount": 0.0,
            "start_date": today,
            "end_date": end
        })

    def toggle_discount_active(self, discount_id: int) -> bool:
        """Activate or deactivate a discount offer."""
        d = self.db.query(DiscountOffer).filter(DiscountOffer.id == discount_id).first()
        if not d:
            return False
        d.is_active = not d.is_active
        self.db.commit()
        return d.is_active

    def delete_discount(self, discount_id: int) -> bool:
        """Safely delete a discount offer."""
        d = self.db.query(DiscountOffer).filter(DiscountOffer.id == discount_id).first()
        if not d:
            return False
        self.db.delete(d)
        self.db.commit()
        return True

    def calculate_bill_discount(self, discount_id: int, items_data: List[Dict[str, Any]], subtotal: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Evaluate eligible items, calculate exact discount amount, and enforce bounds.
        """
        if subtotal is None:
            subtotal = Decimal("0.00")
            for it in items_data:
                lt = it.get("line_total")
                if lt is not None:
                    subtotal += Decimal(str(lt))
                else:
                    up = Decimal(str(it.get("unit_price", 0)))
                    q = Decimal(str(it.get("quantity", 1)))
                    subtotal += up * q
        else:
            subtotal = Decimal(str(subtotal))

        discount = self.db.query(DiscountOffer).filter(DiscountOffer.id == discount_id).first()
        if not discount or not discount.is_active:
            return {"discount_amount": Decimal("0.00"), "name": "", "rate": Decimal("0.00"), "type": "none"}

        today = date.today()
        if discount.start_date > today or discount.end_date < today:
            return {"discount_amount": Decimal("0.00"), "name": "", "rate": Decimal("0.00"), "type": "none"}

        # Check minimum bill threshold
        if discount.min_bill_amount and subtotal < discount.min_bill_amount:
            return {"discount_amount": Decimal("0.00"), "name": "", "rate": Decimal("0.00"), "type": "none", "reason": f"Requires min bill ₹{discount.min_bill_amount:.2f}"}

        # Calculate eligible amount
        eligible_amount = Decimal("0.00")
        if discount.applies_to == "entire_bill":
            eligible_amount = subtotal
        elif discount.applies_to == "product" and discount.target_product_id:
            for it in items_data:
                if it.get("product_id") == discount.target_product_id:
                    eligible_amount += Decimal(str(it.get("line_total", 0.0)))
        elif discount.applies_to == "category" and discount.target_category_id:
            # Look up products belonging to this category
            cat_prod_ids = set([p[0] for p in self.db.query(ShopProduct.id).filter(ShopProduct.category_id == discount.target_category_id).all()])
            for it in items_data:
                if it.get("product_id") in cat_prod_ids:
                    eligible_amount += Decimal(str(it.get("line_total", 0.0)))
        else:
            eligible_amount = subtotal

        if eligible_amount <= Decimal("0.00"):
            return {"discount_amount": Decimal("0.00"), "name": "", "rate": Decimal("0.00"), "type": "none"}

        # Compute calculated discount
        if discount.discount_type == "percentage":
            calc_discount = (eligible_amount * discount.discount_value) / Decimal("100.00")
        else:
            calc_discount = min(discount.discount_value, eligible_amount)

        # Apply maximum discount cap if configured
        if discount.max_discount_amount and discount.max_discount_amount > Decimal("0.00"):
            calc_discount = min(calc_discount, discount.max_discount_amount)

        # Cannot exceed eligible amount or total bill
        calc_discount = min(calc_discount, subtotal)
        calc_discount = max(Decimal("0.00"), calc_discount)

        return {
            "discount_id": discount.id,
            "discount_name": discount.name,
            "discount_type": discount.discount_type,
            "discount_rate": discount.discount_value,
            "discount_amount": calc_discount.quantize(Decimal("0.01")),
            "eligible_amount": eligible_amount.quantize(Decimal("0.01"))
        }
