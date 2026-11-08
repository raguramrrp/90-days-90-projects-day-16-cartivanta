"""
CARTIVANTA - Inventory Intelligence & Risk Monitoring Module (Module 04)
Calculates daily demand velocities, dynamic reorder points, suggested reorder quantities,
stockout risks, days of supply remaining, and inventory health distribution.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class InventoryAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_inventory_health_overview(self) -> Dict[str, Any]:
        """
        Aggregate stock positions across health statuses: Critical, Low, Healthy, Overstocked, Dead Stock.
        Computes composite Inventory Health Score (0-100).
        """
        query = text("""
            SELECT
                i.stock_code,
                p.description,
                p.category,
                i.available_stock,
                i.safety_stock,
                i.supplier_lead_time_days,
                i.target_stock,
                i.inventory_health_status,
                COALESCE(perf.units_sold, 0) AS total_units_sold
            FROM inventory_snapshot i
            JOIN products p ON i.stock_code = p.stock_code
            LEFT JOIN (
                SELECT stock_code, SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS units_sold
                FROM order_items
                GROUP BY stock_code
            ) perf ON i.stock_code = perf.stock_code
        """)
        rows = self.session.execute(query).mappings().all()
        if not rows:
            return {"total_items": 0, "status_breakdown": {}, "health_score": 0.0, "critical_items": []}

        df = pd.DataFrame(rows)
        # 730 days of historical observation (2 years)
        observed_days = 730.0
        df["daily_demand"] = np.round(df["total_units_sold"] / observed_days, 2)
        # Avoid division by zero
        df["days_of_supply"] = np.where(df["daily_demand"] > 0, np.round(df["available_stock"] / df["daily_demand"], 1), 999.0)
        df["calculated_reorder_point"] = np.ceil(df["daily_demand"] * df["supplier_lead_time_days"] + df["safety_stock"]).astype(int)
        df["suggested_reorder_qty"] = np.maximum(0, df["target_stock"] - df["available_stock"]).astype(int)

        status_counts = df["inventory_health_status"].value_counts().to_dict()
        total_items = len(df)

        # Inventory Health Score (0-100):
        # Healthy items give 100%, Overstocked gives 70%, Low gives 50%, Critical gives 0%, Dead Stock gives 20%
        weights = {"Healthy": 100.0, "Overstocked": 70.0, "Low": 50.0, "Dead Stock": 20.0, "Critical": 0.0}
        weighted_score = sum(status_counts.get(k, 0) * weights.get(k, 50.0) for k in weights)
        final_health_score = round(weighted_score / total_items, 1) if total_items > 0 else 0.0

        # Items requiring immediate attention (Critical or Low)
        urgent_df = df[df["inventory_health_status"].isin(["Critical", "Low"])].sort_values(by="days_of_supply", ascending=True)
        urgent_items = urgent_df.head(15).to_dict(orient="records")

        # Overstocked items
        overstocked_items = df[df["inventory_health_status"] == "Overstocked"].head(10).to_dict(orient="records")

        return {
            "total_items_monitored": total_items,
            "status_breakdown": status_counts,
            "inventory_health_score": final_health_score,
            "critical_stock_count": status_counts.get("Critical", 0),
            "low_stock_count": status_counts.get("Low", 0),
            "healthy_count": status_counts.get("Healthy", 0),
            "overstocked_count": status_counts.get("Overstocked", 0),
            "dead_stock_count": status_counts.get("Dead Stock", 0),
            "immediate_attention_items": urgent_items,
            "overstocked_sample": overstocked_items
        }
