"""
CARTIVANTA - Promotion Intelligence Module (Module 08)
Evaluates promotional campaign performance, discount effectiveness, margin erosion,
and true return on promotional investment (ROI):
Promotion ROI = (Promotion Profit - Campaign Budget) / Campaign Budget * 100
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session

class PromotionAnalyticsEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_campaign_overview(self) -> List[Dict[str, Any]]:
        """
        Aggregate promotional campaigns performance, discount margins, and calculated ROI.
        """
        query = text("""
            SELECT
                pc.campaign_id,
                pc.campaign_name,
                pc.promotion_type,
                pc.start_date,
                pc.end_date,
                pc.target_category,
                pc.discount_percentage,
                pc.campaign_budget,
                COUNT(pt.promo_txn_id) AS total_transactions,
                COALESCE(SUM(pt.quantity), 0) AS total_units_sold,
                COALESCE(SUM(pt.original_price * pt.quantity), 0) AS full_price_value,
                COALESCE(SUM(pt.final_selling_price * pt.quantity), 0) AS promo_revenue,
                COALESCE(SUM(pt.discount_amount * pt.quantity), 0) AS total_discount_given,
                COALESCE(SUM(c.estimated_unit_cost * pt.quantity), 0) AS promo_cogs
            FROM promotion_campaigns pc
            LEFT JOIN promotion_transactions pt ON pc.campaign_id = pt.campaign_id
            LEFT JOIN product_costs c ON pt.stock_code = c.stock_code
            GROUP BY pc.campaign_id, pc.campaign_name, pc.promotion_type, pc.start_date, pc.end_date, pc.target_category, pc.discount_percentage, pc.campaign_budget
            ORDER BY promo_revenue DESC
        """)
        rows = self.session.execute(query).mappings().all()
        results = []

        for r in rows:
            rev = float(r["promo_revenue"] or 0.0)
            cogs = float(r["promo_cogs"] or (rev * 0.55))
            discount_given = float(r["total_discount_given"] or 0.0)
            budget = float(r["campaign_budget"] or 0.0)
            
            promo_profit = round(rev - cogs, 2)
            margin_pct = round((promo_profit / rev * 100), 2) if rev > 0 else 0.0
            
            # Promotion ROI = (Promotion Profit - Campaign Budget) / Campaign Budget * 100
            # Defined rigorously with budget as the marketing capital denominator
            if budget > 0:
                roi_pct = round(((promo_profit - budget) / budget * 100), 2)
            else:
                roi_pct = 0.0

            # Margin erosion: Difference between full price margin and promotional margin
            full_val = float(r["full_price_value"] or rev)
            full_margin_pct = round(((full_val - cogs) / full_val * 100), 2) if full_val > 0 else 0.0
            margin_erosion_pct = round(full_margin_pct - margin_pct, 2)

            results.append({
                "campaign_id": r["campaign_id"],
                "campaign_name": r["campaign_name"],
                "promotion_type": r["promotion_type"],
                "target_category": r["target_category"],
                "start_date": str(r["start_date"]),
                "end_date": str(r["end_date"]),
                "discount_percentage": round(float(r["discount_percentage"]) * 100, 1),
                "campaign_budget": budget,
                "total_transactions": int(r["total_transactions"]),
                "total_units_sold": int(r["total_units_sold"]),
                "promo_revenue": round(rev, 2),
                "total_discount_given": round(discount_given, 2),
                "estimated_promo_profit": promo_profit,
                "promo_gross_margin_pct": margin_pct,
                "margin_erosion_pct": margin_erosion_pct,
                "promotion_roi_pct": roi_pct
            })

        return results

    def get_category_promotion_breakdown(self) -> List[Dict[str, Any]]:
        """Return promotional volume and discount share by merchandise category."""
        query = text("""
            SELECT
                pc.target_category,
                COUNT(DISTINCT pc.campaign_id) AS active_campaigns,
                COALESCE(SUM(pt.quantity), 0) AS promo_units,
                COALESCE(SUM(pt.final_selling_price * pt.quantity), 0) AS promo_revenue,
                COALESCE(SUM(pt.discount_amount * pt.quantity), 0) AS total_discount
            FROM promotion_campaigns pc
            JOIN promotion_transactions pt ON pc.campaign_id = pt.campaign_id
            GROUP BY pc.target_category
            ORDER BY promo_revenue DESC
        """)
        rows = self.session.execute(query).mappings().all()
        return [
            {
                "category": r["target_category"],
                "active_campaigns": int(r["active_campaigns"]),
                "promo_units": int(r["promo_units"]),
                "promo_revenue": round(float(r["promo_revenue"]), 2),
                "total_discount": round(float(r["total_discount"]), 2)
            }
            for r in rows
        ]
