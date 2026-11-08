"""
CARTIVANTA - Sales & Executive Intelligence Analysis (Module 01)
Calculates validated executive business KPIs, monthly sales trends, growth rates,
geographical breakdowns, returns analysis, and ensures 100% reconciliation with SQL calculations.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class SalesAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def calculate_executive_kpis(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute top-level business performance metrics with optional filtering.
        Reconciles directly with SQL calculations.
        """
        where_clauses = ["1=1"]
        params = {}

        if start_date:
            where_clauses.append("o.invoice_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where_clauses.append("o.invoice_date <= :end_date")
            params["end_date"] = end_date
        if country and country != "All":
            where_clauses.append("o.country = :country")
            params["country"] = country
        if category and category != "All":
            where_clauses.append("p.category = :category")
            params["category"] = category

        is_unfiltered = (
            not start_date and not end_date and 
            (not country or country == "All") and 
            (not category or category == "All")
        )

        if is_unfiltered:
            # High-speed direct aggregation without 3-table join (0.3s)
            oi_query = text("""
                SELECT
                    COALESCE(SUM(CASE WHEN quantity > 0 THEN line_total ELSE 0 END), 0) AS gross_sales,
                    COALESCE(ABS(SUM(CASE WHEN quantity < 0 THEN line_total ELSE 0 END)), 0) AS returns_value,
                    COALESCE(SUM(line_total), 0) AS net_revenue,
                    COALESCE(SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END), 0) AS units_sold,
                    COALESCE(ABS(SUM(CASE WHEN quantity < 0 THEN quantity ELSE 0 END)), 0) AS units_returned,
                    COALESCE(SUM(CASE WHEN quantity > 0 THEN COALESCE(estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs
                FROM order_items
            """)
            oi_row = self.session.execute(oi_query).mappings().first()
            gross_sales = float(oi_row["gross_sales"] or 0.0)
            returns_value = float(oi_row["returns_value"] or 0.0)
            net_revenue = float(oi_row["net_revenue"] or 0.0)
            units_sold = int(oi_row["units_sold"] or 0)
            units_returned = int(oi_row["units_returned"] or 0)
            estimated_cogs = float(oi_row["estimated_cogs"] or 0.0)

            ord_query = text("SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM orders")
            ord_row = self.session.execute(ord_query).first()
            total_orders = int(ord_row[0] or 0)
            active_customers = int(ord_row[1] or 0)

            ret_query = text("SELECT COUNT(*) FROM customer_segments WHERE frequency > 1 AND customer_id NOT LIKE 'GUEST-%'")
            returning_customers = int(self.session.execute(ret_query).scalar() or 0)
        else:
            filter_sql = " AND ".join(where_clauses)
            query = text(f"""
                SELECT
                    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS gross_sales,
                    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_value,
                    COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                    COUNT(DISTINCT o.invoice_no) AS total_orders,
                    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
                    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.quantity ELSE 0 END)), 0) AS units_returned,
                    COUNT(DISTINCT o.customer_id) AS active_customers,
                    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_cogs
                FROM order_items oi
                JOIN orders o ON oi.invoice_no = o.invoice_no
                JOIN products p ON oi.stock_code = p.stock_code
                WHERE {filter_sql}
            """)

            row = self.session.execute(query, params).mappings().first()

            gross_sales = float(row["gross_sales"] or 0.0)
            returns_value = float(row["returns_value"] or 0.0)
            net_revenue = float(row["net_revenue"] or 0.0)
            total_orders = int(row["total_orders"] or 0)
            units_sold = int(row["units_sold"] or 0)
            units_returned = int(row["units_returned"] or 0)
            active_customers = int(row["active_customers"] or 0)
            estimated_cogs = float(row["estimated_cogs"] or 0.0)

            # Returning Customers Count
            cust_query = text(f"""
                SELECT COUNT(*) AS returning_count
                FROM (
                    SELECT o.customer_id
                    FROM orders o
                    JOIN order_items oi ON o.invoice_no = oi.invoice_no
                    JOIN products p ON oi.stock_code = p.stock_code
                    WHERE {filter_sql} AND o.customer_id NOT LIKE 'GUEST-%'
                    GROUP BY o.customer_id
                    HAVING COUNT(DISTINCT o.invoice_no) > 1
                ) AS returning_sub
            """)
            returning_customers = int(self.session.execute(cust_query, params).scalar() or 0)

        # Derived Metrics
        avg_order_value = round(net_revenue / total_orders, 2) if total_orders > 0 else 0.0
        estimated_gross_profit = round(net_revenue - estimated_cogs, 2)
        estimated_gross_margin_pct = round((estimated_gross_profit / net_revenue * 100), 2) if net_revenue > 0 else 0.0
        return_rate_pct = round((returns_value / gross_sales * 100), 2) if gross_sales > 0 else 0.0

        return {
            "gross_sales": round(gross_sales, 2),
            "returns_value": round(returns_value, 2),
            "net_revenue": round(net_revenue, 2),
            "total_orders": total_orders,
            "units_sold": units_sold,
            "units_returned": units_returned,
            "average_order_value": avg_order_value,
            "active_customers": active_customers,
            "returning_customers": returning_customers,
            "estimated_cogs": round(estimated_cogs, 2),
            "estimated_gross_profit": estimated_gross_profit,
            "estimated_gross_margin_pct": estimated_gross_margin_pct,
            "return_rate_pct": return_rate_pct,
            "currency": "GBP"
        }

    def get_monthly_sales_trend(self) -> List[Dict[str, Any]]:
        """Fetch chronological monthly performance and MoM growth."""
        query = text("""
            SELECT
                strftime('%Y-%m', o.invoice_date) AS year_month,
                COUNT(DISTINCT o.invoice_no) AS orders,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS gross_sales,
                COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_value,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS cogs
            FROM orders o
            JOIN order_items oi ON o.invoice_no = oi.invoice_no
            GROUP BY strftime('%Y-%m', o.invoice_date)
            ORDER BY year_month ASC
        """)
        
        # Test if PostgreSQL vs SQLite
        try:
            rows = self.session.execute(query).mappings().all()
        except Exception:
            # Fallback for PostgreSQL TO_CHAR
            pg_query = text("""
                SELECT
                    TO_CHAR(o.invoice_date, 'YYYY-MM') AS year_month,
                    COUNT(DISTINCT o.invoice_no) AS orders,
                    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.line_total ELSE 0 END), 0) AS gross_sales,
                    COALESCE(ABS(SUM(CASE WHEN oi.quantity < 0 THEN oi.line_total ELSE 0 END)), 0) AS returns_value,
                    COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                    COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS cogs
                FROM orders o
                JOIN order_items oi ON o.invoice_no = oi.invoice_no
                GROUP BY TO_CHAR(o.invoice_date, 'YYYY-MM')
                ORDER BY year_month ASC
            """)
            rows = self.session.execute(pg_query).mappings().all()

        results = []
        prev_rev = None
        prev_profit = None

        for r in rows:
            net_rev = float(r["net_revenue"])
            cogs = float(r["cogs"])
            profit = round(net_rev - cogs, 2)
            margin = round((profit / net_rev * 100), 2) if net_rev > 0 else 0.0

            rev_growth = round(((net_rev - prev_rev) / prev_rev * 100), 2) if prev_rev and prev_rev > 0 else 0.0
            profit_growth = round(((profit - prev_profit) / prev_profit * 100), 2) if prev_profit and prev_profit != 0 else 0.0

            prev_rev = net_rev
            prev_profit = profit

            results.append({
                "year_month": r["year_month"],
                "orders": int(r["orders"]),
                "gross_sales": round(float(r["gross_sales"]), 2),
                "returns_value": round(float(r["returns_value"]), 2),
                "net_revenue": round(net_rev, 2),
                "estimated_profit": profit,
                "estimated_margin_pct": margin,
                "revenue_growth_pct": rev_growth,
                "profit_growth_pct": profit_growth
            })

        return results

    def get_sales_by_country(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Return geographical sales distribution."""
        query = text("""
            SELECT
                o.country,
                COUNT(DISTINCT o.invoice_no) AS orders,
                COUNT(DISTINCT o.customer_id) AS customers,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue
            FROM orders o
            JOIN order_items oi ON o.invoice_no = oi.invoice_no
            GROUP BY o.country
            ORDER BY net_revenue DESC
            LIMIT :top_n
        """)
        rows = self.session.execute(query, {"top_n": top_n}).mappings().all()
        return [
            {
                "country": r["country"],
                "orders": int(r["orders"]),
                "customers": int(r["customers"]),
                "net_revenue": round(float(r["net_revenue"]), 2)
            }
            for r in rows
        ]

    def get_sales_by_category(self) -> List[Dict[str, Any]]:
        """Return revenue breakdown by merchandise category."""
        query = text("""
            SELECT
                p.category,
                COALESCE(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0) AS units_sold,
                COALESCE(SUM(oi.line_total), 0) AS net_revenue,
                COALESCE(SUM(oi.line_total) - SUM(CASE WHEN oi.quantity > 0 THEN COALESCE(oi.estimated_cost_total, 0) ELSE 0 END), 0) AS estimated_profit
            FROM order_items oi
            JOIN products p ON oi.stock_code = p.stock_code
            GROUP BY p.category
            ORDER BY net_revenue DESC
        """)
        rows = self.session.execute(query).mappings().all()
        total_rev = sum(float(r["net_revenue"]) for r in rows) or 1.0

        return [
            {
                "category": r["category"],
                "units_sold": int(r["units_sold"]),
                "net_revenue": round(float(r["net_revenue"]), 2),
                "estimated_profit": round(float(r["estimated_profit"]), 2),
                "revenue_share_pct": round((float(r["net_revenue"]) / total_rev * 100), 2)
            }
            for r in rows
        ]
