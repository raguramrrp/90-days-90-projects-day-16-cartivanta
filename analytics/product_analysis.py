"""
CARTIVANTA - Product Intelligence Analysis (Module 02)
Performs Pareto 80/20 analysis, revenue concentration, product classification matrix,
return rate auditing, and identifies high-revenue low-margin items.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class ProductAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_pareto_analysis(self) -> Dict[str, Any]:
        """
        Compute Pareto 80/20 breakdown of catalog products by net revenue.
        Identifies the exact top tier of products generating 80% of revenue.
        """
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description, p.category
            HAVING SUM(oi.line_total) > 0
            ORDER BY net_revenue DESC
        """)
        rows = self.session.execute(query).mappings().all()
        if not rows:
            return {"total_products": 0, "pareto_80_count": 0, "pareto_share_pct": 0.0, "items": []}

        df = pd.DataFrame(rows)
        df["net_revenue"] = df["net_revenue"].astype(float)
        total_revenue = df["net_revenue"].sum()
        df["cumulative_revenue"] = df["net_revenue"].cumsum()
        df["cumulative_pct"] = (df["cumulative_revenue"] / total_revenue) * 100

        # Flag 80% threshold
        df["is_top_80"] = df["cumulative_pct"] <= 80.0
        # Include first product that crossed 80%
        first_cross_idx = (df["cumulative_pct"] >= 80.0).idxmax() if (df["cumulative_pct"] >= 80.0).any() else 0
        df.loc[:first_cross_idx, "is_top_80"] = True

        pareto_count = int(df["is_top_80"].sum())
        total_count = len(df)
        pareto_share_pct = round((pareto_count / total_count * 100), 2) if total_count > 0 else 0.0

        top_items = df.head(20).to_dict(orient="records")
        for item in top_items:
            item["net_revenue"] = round(item["net_revenue"], 2)
            item["cumulative_pct"] = round(item["cumulative_pct"], 2)

        return {
            "total_products_with_sales": total_count,
            "pareto_80_count": pareto_count,
            "pareto_catalog_share_pct": pareto_share_pct,
            "total_revenue": round(total_revenue, 2),
            "top_pareto_items": top_items
        }

    def get_product_performance_matrix(self, min_revenue: float = 100.0) -> List[Dict[str, Any]]:
        """
        Classify products into a 4-quadrant strategic matrix:
        - Stars: High Demand, High Profit Margin
        - Cash Cows: High Demand, Low/Moderate Profit Margin
        - Opportunities: Low Demand, High Profit Margin
        - Underperformers: Low Demand, Low Profit Margin
        Also identifies 'High Revenue, Low Margin' alerts.
        """
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS cogs,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_profit,
                COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END)), 0) AS units_returned
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description, p.category
            HAVING SUM(oi.line_total) >= :min_revenue
            ORDER BY net_revenue DESC
        """)
        rows = self.session.execute(query, {"min_revenue": min_revenue}).mappings().all()
        if not rows:
            return []

        df = pd.DataFrame(rows)
        df["net_revenue"] = df["net_revenue"].astype(float)
        df["estimated_profit"] = df["estimated_profit"].astype(float)
        df["units_sold"] = df["units_sold"].astype(int)
        df["units_returned"] = df["units_returned"].astype(int)

        df["margin_pct"] = np.where(df["net_revenue"] > 0, (df["estimated_profit"] / df["net_revenue"] * 100), 0.0)
        df["return_rate_pct"] = np.where(df["units_sold"] > 0, (df["units_returned"] / df["units_sold"] * 100), 0.0)

        median_units = df["units_sold"].median()
        median_margin = df["margin_pct"].median()

        def classify(row):
            high_vol = row["units_sold"] >= median_units
            high_margin = row["margin_pct"] >= median_margin
            if high_vol and high_margin:
                return "Star"
            elif high_vol and not high_margin:
                return "Cash Cow"
            elif not high_vol and high_margin:
                return "Niche / Opportunity"
            else:
                return "Underperformer"

        df["matrix_quadrant"] = df.apply(classify, axis=1)
        df["is_high_rev_low_margin"] = (df["net_revenue"] > 3000) & (df["margin_pct"] < 20.0)

        return df.to_dict(orient="records")

    def get_top_performing_products(self, metric: str = "revenue", top_n: int = 10) -> List[Dict[str, Any]]:
        """Return top products ranked by revenue, profit, or units sold."""
        order_col = "net_revenue"
        if metric == "units":
            order_col = "units_sold"
        elif metric == "profit":
            order_col = "estimated_profit"

        query = text(f"""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_profit,
                COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END)), 0) AS units_returned
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description, p.category
            ORDER BY {order_col} DESC
            LIMIT :top_n
        """)
        rows = self.session.execute(query, {"top_n": top_n}).mappings().all()
        return [
            {
                "stock_code": r["stock_code"],
                "description": r["description"],
                "category": r["category"],
                "units_sold": int(r["units_sold"]),
                "net_revenue": round(float(r["net_revenue"]), 2),
                "estimated_profit": round(float(r["estimated_profit"]), 2),
                "units_returned": int(r["units_returned"])
            }
            for r in rows
        ]
