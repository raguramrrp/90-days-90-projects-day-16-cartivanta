"""
CARTIVANTA - Stock & Inventory Movement Service
Handles stock adjustments, movement audit trails, and low-stock queries.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import ShopProduct, StockMovement, User

class StockService:
    def __init__(self, db: Session):
        self.db = db

    def adjust_stock(
        self,
        product_id: int,
        quantity_change: float,
        reason: str,
        user_id: Optional[int] = None
    ) -> ShopProduct:
        """
        Manually adjust product stock with a mandatory reason.
        positive quantity_change = addition (e.g. stock found, returned)
        negative quantity_change = deduction (e.g. damaged, expired, theft, count correction)
        """
        if not reason or not reason.strip():
            raise ValueError("A clear reason for stock adjustment is required.")

        prod = self.db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
        if not prod:
            raise ValueError(f"Product ID {product_id} not found.")

        qty_delta = Decimal(str(quantity_change))
        if qty_delta == 0:
            raise ValueError("Quantity change cannot be zero.")

        new_stock = prod.stock_qty + qty_delta
        if new_stock < 0:
            raise ValueError(f"Cannot adjust stock below zero. Current: {prod.stock_qty}, Delta: {qty_delta}.")

        prod.stock_qty = new_stock

        movement_type = "adjustment"
        r_lower = reason.lower()
        if "damage" in r_lower or "expire" in r_lower:
            movement_type = "damage"
        elif "return" in r_lower:
            movement_type = "return"

        sm = StockMovement(
            product_id=prod.id,
            movement_type=movement_type,
            quantity_change=qty_delta,
            balance_after=new_stock,
            reason=reason.strip(),
            user_id=user_id
        )
        self.db.add(sm)
        self.db.commit()
        return prod

    def get_stock_movements(
        self,
        product_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve historical stock audit logs."""
        query = self.db.query(StockMovement)
        if product_id:
            query = query.filter(StockMovement.product_id == product_id)
        if movement_type:
            query = query.filter(StockMovement.movement_type == movement_type)

        movements = query.order_by(desc(StockMovement.created_at)).limit(limit).all()
        result = []
        for m in movements:
            result.append({
                "id": m.id,
                "product_id": m.product_id,
                "product_name": m.product.name if m.product else "Deleted Product",
                "movement_type": m.movement_type,
                "quantity_change": float(m.quantity_change),
                "balance_after": float(m.balance_after),
                "reason": m.reason,
                "user_name": m.user.full_name if m.user else "System",
                "created_at": m.created_at.strftime("%d-%m-%Y %I:%M %p")
            })
        return result

    def get_low_stock_products(self) -> List[Dict[str, Any]]:
        """Fetch all products that are below or at minimum stock threshold."""
        products = self.db.query(ShopProduct).filter(
            ShopProduct.is_active == True,
            ShopProduct.stock_qty <= ShopProduct.min_stock_qty
        ).order_by(ShopProduct.stock_qty.asc()).all()

        result = []
        for p in products:
            curr = float(p.stock_qty or 0)
            min_q = float(p.min_stock_qty or 5)
            suggested_reorder = max(10, int((min_q * 2) - curr))
            result.append({
                "id": p.id,
                "name": p.name,
                "barcode": p.barcode or "",
                "category": p.category.name if p.category else "General",
                "unit": p.unit,
                "current_stock": curr,
                "min_stock": min_q,
                "suggested_reorder": suggested_reorder,
                "supplier_name": p.supplier.name if p.supplier else "No Supplier",
                "supplier_phone": p.supplier.phone if p.supplier else "",
                "is_out_of_stock": curr <= 0
            })
        return result
