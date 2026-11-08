"""
CARTIVANTA - Customer Intelligence Reporting & Analytics (Module 03)
Provides segment breakdown, customer lifetime rankings, retention and churn metrics.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class CustomerAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_segment_summary(self) -> List[Dict[str, Any]]:
        """Return segment size, revenue contribution, and average RFM metrics."""
        query = text("""
            SELECT
                cs.segment_name,
                COUNT(cs.customer_id) AS customer_count,
                ROUND(AVG(cs.recency_days), 1) AS avg_recency,
                ROUND(AVG(cs.frequency), 1) AS avg_frequency,
                ROUND(AVG(cs.monetary), 2) AS avg_monetary,
                ROUND(SUM(cs.monetary), 2) AS total_segment_revenue
            FROM customer_segments cs
            GROUP BY cs.segment_name
            ORDER BY total_segment_revenue DESC
        """)
        rows = self.session.execute(query).mappings().all()
        total_rev = sum(float(r["total_segment_revenue"]) for r in rows) or 1.0

        return [
            {
                "segment_name": r["segment_name"],
                "customer_count": int(r["customer_count"]),
                "avg_recency_days": float(r["avg_recency"]),
                "avg_frequency": float(r["avg_frequency"]),
                "avg_monetary": float(r["avg_monetary"]),
                "total_segment_revenue": float(r["total_segment_revenue"]),
                "revenue_share_pct": round((float(r["total_segment_revenue"]) / total_rev * 100), 2)
            }
            for r in rows
        ]

    def get_top_customers(self, top_n: int = 15) -> List[Dict[str, Any]]:
        """Return high-value customers by historical spend."""
        query = text("""
            SELECT
                cs.customer_id,
                c.country,
                cs.segment_name,
                cs.frequency AS total_orders,
                cs.monetary AS lifetime_revenue,
                cs.avg_order_value,
                cs.recency_days
            FROM customer_segments cs
            JOIN customers c ON cs.customer_id = c.customer_id
            ORDER BY cs.monetary DESC
            LIMIT :top_n
        """)
        rows = self.session.execute(query, {"top_n": top_n}).mappings().all()
        return [
            {
                "customer_id": r["customer_id"],
                "country": r["country"],
                "segment_name": r["segment_name"],
                "total_orders": int(r["total_orders"]),
                "lifetime_revenue": round(float(r["lifetime_revenue"]), 2),
                "avg_order_value": round(float(r["avg_order_value"]), 2),
                "recency_days": int(r["recency_days"])
            }
            for r in rows
        ]

    def get_at_risk_customers(self, top_n: int = 15) -> List[Dict[str, Any]]:
        """Identify high-monetary customers whose recency indicates risk of churning."""
        query = text("""
            SELECT
                cs.customer_id,
                c.country,
                cs.segment_name,
                cs.recency_days,
                cs.monetary AS lifetime_revenue,
                cs.frequency
            FROM customer_segments cs
            JOIN customers c ON cs.customer_id = c.customer_id
            WHERE cs.segment_name IN ('At Risk', 'Hibernating') AND cs.monetary > 500
            ORDER BY cs.monetary DESC
            LIMIT :top_n
        """)
        rows = self.session.execute(query, {"top_n": top_n}).mappings().all()
        return [
            {
                "customer_id": r["customer_id"],
                "country": r["country"],
                "segment_name": r["segment_name"],
                "recency_days": int(r["recency_days"]),
                "lifetime_revenue": round(float(r["lifetime_revenue"]), 2),
                "frequency": int(r["frequency"])
            }
            for r in rows
        ]
