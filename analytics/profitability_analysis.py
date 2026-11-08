"""
CARTIVANTA - Profitability Intelligence Module (Module 06)
Analyzes product and category gross margins, cost structures, margin erosion risks,
loss-making catalog items, and flags high-revenue but low-profit products.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class ProfitabilityAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_category_profitability(self) -> List[Dict[str, Any]]:
        """Return profitability and gross margins aggregated by product category."""
        query = text("""
            SELECT
                p.category,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit
            FROM order_items oi
            JOIN products p ON oi.stock_code = p.stock_code
            GROUP BY p.category
            ORDER BY estimated_gross_profit DESC
        """)
        rows = self.session.execute(query).mappings().all()
        results = []
        for r in rows:
            rev = float(r["net_revenue"])
            cogs = float(r["estimated_cogs"])
            profit = float(r["estimated_gross_profit"])
            margin = round((profit / rev * 100), 2) if rev > 0 else 0.0

            results.append({
                "category": r["category"],
                "units_sold": int(r["units_sold"]),
                "net_revenue": round(rev, 2),
                "estimated_cogs": round(cogs, 2),
                "estimated_gross_profit": round(profit, 2),
                "estimated_gross_margin_pct": margin
            })

        return results

    def get_high_revenue_low_margin_products(self, revenue_threshold: float = 3000.0, margin_threshold: float = 20.0) -> List[Dict[str, Any]]:
        """
        Detect items that consume high transaction volume and revenue but generate substandard profit margins.
        Prime candidates for supplier cost renegotiation or selective price increases.
        """
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description, p.category
            HAVING SUM(oi.line_total) >= :revenue_threshold
            ORDER BY net_revenue DESC
        """)
        rows = self.session.execute(query, {"revenue_threshold": revenue_threshold}).mappings().all()
        flagged = []
        for r in rows:
            rev = float(r["net_revenue"])
            profit = float(r["estimated_gross_profit"])
            margin = round((profit / rev * 100), 2) if rev > 0 else 0.0
            if margin < margin_threshold:
                flagged.append({
                    "stock_code": r["stock_code"],
                    "description": r["description"],
                    "category": r["category"],
                    "net_revenue": round(rev, 2),
                    "estimated_gross_profit": round(profit, 2),
                    "estimated_gross_margin_pct": margin,
                    "condition": f"High Revenue (£{rev:,.0f}) with Low Margin ({margin:.1f}%)"
                })

        return flagged

    def get_loss_making_products(self) -> List[Dict[str, Any]]:
        """Identify products with negative net gross profit due to excessive return/refund value."""
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_gross_profit,
                COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_value
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description, p.category
            HAVING (SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END)) < 0
            ORDER BY estimated_gross_profit ASC
            LIMIT 15
        """)
        rows = self.session.execute(query).mappings().all()
        return [
            {
                "stock_code": r["stock_code"],
                "description": r["description"],
                "category": r["category"],
                "net_revenue": round(float(r["net_revenue"]), 2),
                "estimated_gross_profit": round(float(r["estimated_gross_profit"]), 2),
                "returns_value": round(float(r["returns_value"]), 2)
            }
            for r in rows
        ]
