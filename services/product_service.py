"""
CARTIVANTA - Product Management Service
Handles product catalog operations, pricing calculations, margin %,
stock valuation, low-stock detection, and stock movement history.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from database.models import ShopProduct, ShopCategory, Supplier, StockMovement, BillItem

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def get_products(
        self,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve products matching filters with calculated unit profit and margin %."""
        query = self.db.query(ShopProduct)
        if active_only:
            query = query.filter(ShopProduct.is_active == True)
        if category_id:
            query = query.filter(ShopProduct.category_id == category_id)
        if supplier_id:
            query = query.filter(ShopProduct.supplier_id == supplier_id)
        if low_stock_only:
            query = query.filter(ShopProduct.stock_qty <= ShopProduct.min_stock_qty, ShopProduct.stock_qty > 0)
        if out_of_stock_only:
            query = query.filter(ShopProduct.stock_qty <= 0)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(
                ShopProduct.name.ilike(term),
                ShopProduct.barcode.ilike(term),
                ShopProduct.brand.ilike(term)
            ))

        products = query.order_by(ShopProduct.name.asc()).all()
        result = []
        for p in products:
            cost = float(p.purchase_price or 0.0)
            sell = float(p.selling_price or 0.0)
            stock = float(p.stock_qty or 0.0)
            unit_profit = sell - cost
            margin_pct = (unit_profit / sell * 100) if sell > 0 else 0.0
            stock_val = stock * cost
            pot_val = stock * sell

            result.append({
                "id": p.id,
                "barcode": p.barcode or "",
                "name": p.name,
                "brand": p.brand or "",
                "category_id": p.category_id,
                "category_name": p.category.name if p.category else "General",
                "unit": p.unit or "Piece",
                "purchase_price": cost,
                "selling_price": sell,
                "stock_qty": stock,
                "min_stock_qty": float(p.min_stock_qty or 5.0),
                "gst_rate": float(p.gst_rate or 0.0),
                "supplier_id": p.supplier_id,
                "supplier_name": p.supplier.name if p.supplier else "-",
                "unit_profit": round(unit_profit, 2),
                "margin_pct": round(margin_pct, 1),
                "stock_value": round(stock_val, 2),
                "potential_value": round(pot_val, 2),
                "is_low_stock": stock <= float(p.min_stock_qty or 5.0),
                "is_out_of_stock": stock <= 0,
                "is_active": p.is_active
            })
        return result

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single product with full details."""
        p = self.db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
        if not p:
            return None
        cost = float(p.purchase_price or 0.0)
        sell = float(p.selling_price or 0.0)
        stock = float(p.stock_qty or 0.0)
        unit_profit = sell - cost
        margin_pct = (unit_profit / sell * 100) if sell > 0 else 0.0

        return {
            "id": p.id,
            "barcode": p.barcode or "",
            "name": p.name,
            "brand": p.brand or "",
            "category_id": p.category_id,
            "category_name": p.category.name if p.category else "General",
            "unit": p.unit or "Piece",
            "purchase_price": cost,
            "selling_price": sell,
            "stock_qty": stock,
            "min_stock_qty": float(p.min_stock_qty or 5.0),
            "gst_rate": float(p.gst_rate or 0.0),
            "supplier_id": p.supplier_id,
            "supplier_name": p.supplier.name if p.supplier else "-",
            "unit_profit": round(unit_profit, 2),
            "margin_pct": round(margin_pct, 1),
            "stock_value": round(stock * cost, 2),
            "is_active": p.is_active,
            "description": p.description or ""
        }

    def get_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Find product by barcode for POS scanner."""
        p = self.db.query(ShopProduct).filter(
            ShopProduct.barcode == barcode.strip(),
            ShopProduct.is_active == True
        ).first()
        if not p:
            return None
        return self.get_product_by_id(p.id)

    def create_product(self, data: Dict[str, Any], user_id: Optional[int] = None) -> ShopProduct:
        """Create a new product with duplicate barcode check and initial stock movement."""
        barcode = data.get("barcode", "").strip() or None
        if barcode:
            existing = self.db.query(ShopProduct).filter(ShopProduct.barcode == barcode).first()
            if existing:
                raise ValueError(f"Product with barcode '{barcode}' already exists: {existing.name}")

        stock_qty = Decimal(str(data.get("stock_qty", 0.0)))
        product = ShopProduct(
            barcode=barcode,
            name=data["name"].strip(),
            brand=data.get("brand", "").strip() or None,
            category_id=data.get("category_id"),
            unit=data.get("unit", "Piece"),
            purchase_price=Decimal(str(data.get("purchase_price", 0.0))),
            selling_price=Decimal(str(data.get("selling_price", 0.0))),
            stock_qty=stock_qty,
            min_stock_qty=Decimal(str(data.get("min_stock_qty", 5.0))),
            gst_rate=Decimal(str(data.get("gst_rate", 0.0))),
            supplier_id=data.get("supplier_id"),
            description=data.get("description", "").strip() or None,
            is_active=True
        )
        self.db.add(product)
        self.db.flush()

        # Record opening stock movement if stock > 0
        if stock_qty > 0:
            movement = StockMovement(
                product_id=product.id,
                movement_type="adjustment",
                quantity_change=stock_qty,
                balance_after=stock_qty,
                reason="Opening stock balance",
                user_id=user_id
            )
            self.db.add(movement)

        self.db.commit()
        return product

    def update_product(self, product_id: int, data: Dict[str, Any]) -> ShopProduct:
        """Update product details."""
        product = self.db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
        if not product:
            raise ValueError("Product not found.")

        barcode = data.get("barcode", "").strip() or None
        if barcode and barcode != product.barcode:
            existing = self.db.query(ShopProduct).filter(
                ShopProduct.barcode == barcode,
                ShopProduct.id != product_id
            ).first()
            if existing:
                raise ValueError(f"Barcode '{barcode}' is already in use by {existing.name}.")

        product.barcode = barcode
        if "name" in data and data["name"].strip():
            product.name = data["name"].strip()
        if "brand" in data:
            product.brand = data["brand"].strip() or None
        if "category_id" in data:
            product.category_id = data["category_id"]
        if "unit" in data:
            product.unit = data["unit"]
        if "purchase_price" in data:
            product.purchase_price = Decimal(str(data["purchase_price"]))
        if "selling_price" in data:
            product.selling_price = Decimal(str(data["selling_price"]))
        if "min_stock_qty" in data:
            product.min_stock_qty = Decimal(str(data["min_stock_qty"]))
        if "gst_rate" in data:
            product.gst_rate = Decimal(str(data["gst_rate"]))
        if "supplier_id" in data:
            product.supplier_id = data["supplier_id"]
        if "description" in data:
            product.description = data["description"].strip() or None

        self.db.commit()
        return product

    def archive_product(self, product_id: int) -> bool:
        """Soft delete a product."""
        product = self.db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
        if not product:
            return False
        product.is_active = False
        self.db.commit()
        return True

    def get_stock_valuation_summary(self) -> Dict[str, Any]:
        """Calculate total inventory cost and retail valuation."""
        products = self.db.query(ShopProduct).filter(ShopProduct.is_active == True).all()
        total_items = len(products)
        total_units = sum(float(p.stock_qty or 0) for p in products)
        total_cost_val = sum(float(p.stock_qty or 0) * float(p.purchase_price or 0) for p in products)
        total_retail_val = sum(float(p.stock_qty or 0) * float(p.selling_price or 0) for p in products)
        low_stock_count = sum(1 for p in products if float(p.stock_qty or 0) <= float(p.min_stock_qty or 5) and float(p.stock_qty or 0) > 0)
        out_of_stock_count = sum(1 for p in products if float(p.stock_qty or 0) <= 0)

        return {
            "total_products": total_items,
            "total_units": round(total_units, 2),
            "total_inventory_cost": round(total_cost_val, 2),
            "total_retail_value": round(total_retail_val, 2),
            "potential_gross_profit": round(total_retail_val - total_cost_val, 2),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count
        }
