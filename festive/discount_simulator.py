"""
CARTIVANTA - Festive Discount Simulator Module (Module 07C - Mandatory Signature Module)
Simulates promotional pricing, demand elasticity, gross margin erosion,
break-even sales uplift, and flags discounts that increase revenue while reducing profit.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

@dataclass
class SingleDiscountScenario:
    discount_pct: float
    discount_amount: float
    discounted_price: float
    expected_quantity: int
    discounted_revenue: float
    estimated_profit: float
    gross_margin_pct: float
    revenue_diff: float
    profit_diff: float
    margin_diff_pct: float
    breakeven_units: int
    breakeven_uplift_pct: float
    is_profit_destroyer: bool
    is_loss_making: bool

class FestiveDiscountSimulator:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def simulate_discount(
        self,
        stock_code: str,
        discount_pct: float = 0.15,
        expected_demand_uplift_pct: Optional[float] = None,
        campaign_name: str = "Diwali Festive Promotion",
        custom_base_price: Optional[float] = None,
        custom_unit_cost: Optional[float] = None,
        custom_base_quantity: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute comprehensive discount simulation for a product.
        """
        # Fetch product metadata, price, cost, and historical sales
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(c.estimated_unit_cost, 0) AS unit_cost,
                COALESCE(i.available_stock, 100) AS available_stock,
                COALESCE(perf.median_price, 3.50) AS median_price,
                COALESCE(perf.total_units, 100) AS total_units
            FROM products p
            LEFT JOIN product_costs c ON p.stock_code = c.stock_code
            LEFT JOIN inventory_snapshot i ON p.stock_code = i.stock_code
            LEFT JOIN (
                SELECT 
                    stock_code, 
                    AVG(unit_price) AS median_price,
                    SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS total_units
                FROM order_items
                WHERE unit_price > 0
                GROUP BY stock_code
            ) perf ON p.stock_code = perf.stock_code
            WHERE p.stock_code = :stock_code
        """)
        row = self.session.execute(query, {"stock_code": stock_code}).mappings().first()
        if not row:
            return {"error": f"Product {stock_code} not found."}

        orig_price = float(custom_base_price or row["median_price"])
        unit_cost = float(custom_unit_cost or row["unit_cost"])
        if unit_cost <= 0:
            unit_cost = round(orig_price * 0.55, 2)

        # Baseline volume over a 14-day promotional window
        observed_days = 730.0
        daily_units = max(1.0, float(row["total_units"] or 50) / observed_days)
        base_qty = int(custom_base_quantity or np.ceil(daily_units * 14))

        # Default demand elasticity assumption if not provided
        # Retail price elasticity typically between -1.2 and -2.0 for non-essential giftware
        if expected_demand_uplift_pct is None:
            # e.g. 15% discount yields ~27% uplift (elasticity ~ -1.8)
            uplift_pct = discount_pct * 1.8
        else:
            uplift_pct = expected_demand_uplift_pct

        # 1. Normal Price Scenario
        normal_revenue = round(orig_price * base_qty, 2)
        normal_profit = round((orig_price - unit_cost) * base_qty, 2)
        normal_margin_pct = round(((orig_price - unit_cost) / orig_price * 100), 2) if orig_price > 0 else 0.0

        # 2. Discounted Scenario
        discount_amount = round(orig_price * discount_pct, 2)
        discounted_price = round(orig_price - discount_amount, 2)
        expected_qty = int(np.ceil(base_qty * (1.0 + uplift_pct)))
        discounted_revenue = round(discounted_price * expected_qty, 2)
        
        discounted_unit_margin = discounted_price - unit_cost
        discounted_profit = round(discounted_unit_margin * expected_qty, 2)
        discounted_margin_pct = round((discounted_unit_margin / discounted_price * 100), 2) if discounted_price > 0 else 0.0

        # 3. Differences
        revenue_diff = round(discounted_revenue - normal_revenue, 2)
        profit_diff = round(discounted_profit - normal_profit, 2)
        margin_diff_pct = round(discounted_margin_pct - normal_margin_pct, 2)

        # 4. Break-even Uplift Analysis
        # Q_breakeven = Normal Profit / Discounted Unit Margin
        if discounted_unit_margin > 0:
            breakeven_units = int(np.ceil(normal_profit / discounted_unit_margin))
            breakeven_uplift_pct = round(((breakeven_units - base_qty) / base_qty * 100), 2)
        else:
            breakeven_units = 999999
            breakeven_uplift_pct = 999.9

        # 5. Strategic Flags
        is_profit_destroyer = (revenue_diff > 0) and (profit_diff < 0)
        is_loss_making = discounted_unit_margin <= 0

        # Stock adequacy check
        available_stock = int(row["available_stock"])
        stock_shortage = max(0, expected_qty - available_stock)

        # Build comparison grid across preset discount rates (5%, 10%, 15%, 20%, 25%, 30%)
        comparison_grid = []
        for d in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
            p_disc = round(orig_price * (1 - d), 2)
            u_disc = d * 1.8
            q_disc = int(np.ceil(base_qty * (1 + u_disc)))
            r_disc = round(p_disc * q_disc, 2)
            prof_disc = round((p_disc - unit_cost) * q_disc, 2)
            m_disc = round(((p_disc - unit_cost) / p_disc * 100), 2) if p_disc > 0 else 0.0
            p_diff = round(prof_disc - normal_profit, 2)
            r_diff = round(r_disc - normal_revenue, 2)
            p_destroyer = (r_diff > 0) and (p_diff < 0)

            comparison_grid.append({
                "discount_pct": int(d * 100),
                "discounted_price": p_disc,
                "expected_quantity": q_disc,
                "revenue": r_disc,
                "profit": prof_disc,
                "margin_pct": m_disc,
                "profit_difference": p_diff,
                "is_profit_destroyer": p_destroyer
            })

        return {
            "stock_code": row["stock_code"],
            "description": row["description"],
            "category": row["category"],
            "campaign_name": campaign_name,
            "original_selling_price": orig_price,
            "estimated_unit_cost": unit_cost,
            "applied_discount_pct": round(discount_pct * 100, 1),
            "discount_amount": discount_amount,
            "discounted_selling_price": discounted_price,
            "normal_scenario": {
                "base_quantity": base_qty,
                "revenue": normal_revenue,
                "profit": normal_profit,
                "margin_pct": normal_margin_pct
            },
            "discounted_scenario": {
                "expected_quantity": expected_qty,
                "revenue": discounted_revenue,
                "profit": discounted_profit,
                "margin_pct": discounted_margin_pct,
                "demand_uplift_pct": round(uplift_pct * 100, 1)
            },
            "variance": {
                "revenue_difference": revenue_diff,
                "profit_difference": profit_diff,
                "margin_difference_pct": margin_diff_pct
            },
            "breakeven_analysis": {
                "required_sales_volume_units": breakeven_units,
                "breakeven_volume_uplift_pct": breakeven_uplift_pct,
                "additional_units_needed": max(0, breakeven_units - base_qty)
            },
            "inventory_feasibility": {
                "available_stock": available_stock,
                "expected_promotional_demand": expected_qty,
                "projected_shortage_units": stock_shortage,
                "is_stock_sufficient": stock_shortage == 0
            },
            "strategic_evaluation": {
                "is_profit_destroyer": is_profit_destroyer,
                "is_loss_making": is_loss_making,
                "recommendation": (
                    "REJECT: Discount destroys profit despite higher revenue." if is_profit_destroyer
                    else ("REJECT: Selling below unit cost!" if is_loss_making
                          else "RECOMMENDED: Generates net profit uplift.")
                )
            },
            "comparison_grid": comparison_grid,
            "is_simulation": True
        }
