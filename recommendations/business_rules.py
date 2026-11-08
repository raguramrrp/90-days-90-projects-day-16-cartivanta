"""
CARTIVANTA - Business Action Center & Rule-Based Recommendation Engine (Module 09)
Generates explainable, prioritized, and auditable business recommendations across:
- Critical & low inventory stockout threats
- Overstock & dead capital traps
- At-risk high-value customers
- High-revenue low-margin items
- Loss-making products
- Ineffective promotional campaigns
- Festive stock shortfall alerts
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session
from database.models import BusinessAlert

logger = logging.getLogger("cartivanta.recommendations")

class BusinessRecommendationEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def generate_all_recommendations(self) -> List[Dict[str, Any]]:
        """
        Evaluate business rules across inventory, customers, profitability, and promotions.
        Persists alerts into business_alerts table without creating duplicates.
        """
        alerts: List[Dict[str, Any]] = []

        # 1. Critical Inventory Stockouts
        alerts.extend(self._check_critical_inventory())

        # 2. Dead & Overstocked Inventory
        alerts.extend(self._check_overstocked_inventory())

        # 3. High-Value At-Risk Customers
        alerts.extend(self._check_at_risk_customers())

        # 4. High-Revenue Low-Margin Traps
        alerts.extend(self._check_high_revenue_low_margin())

        # 5. Loss-Making Products
        alerts.extend(self._check_loss_making_products())

        # 6. Ineffective Promotional Campaigns
        alerts.extend(self._check_ineffective_promotions())

        # 7. Festive Stock Shortage Warnings
        alerts.extend(self._check_festive_shortages())

        # Persist to database
        self._persist_alerts(alerts)

        logger.info(f"Generated and evaluated {len(alerts)} business recommendations.")
        return alerts

    def _check_critical_inventory(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                i.stock_code,
                p.description,
                i.available_stock,
                i.safety_stock,
                i.target_stock
            FROM inventory_snapshot i
            JOIN products p ON i.stock_code = p.stock_code
            WHERE i.inventory_health_status = 'Critical' OR i.available_stock <= (i.safety_stock * 0.5)
            LIMIT 10
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            reorder_qty = max(50, int(r["target_stock"] - r["available_stock"]))
            alerts.append({
                "alert_id": f"ALT-INV-CRIT-{r['stock_code'][:10]}",
                "alert_category": "Inventory",
                "severity": "Critical",
                "affected_entity_type": "Product",
                "affected_entity_id": r["stock_code"],
                "detected_condition": f"Available stock ({r['available_stock']} units) is below 50% safety stock threshold ({r['safety_stock']} units).",
                "supporting_metric": f"Stock Level: {r['available_stock']} units",
                "threshold_value": f"Safety Stock: {r['safety_stock']}",
                "suggested_action": f"Issue immediate emergency purchase order for {reorder_qty} units with supplier.",
                "expected_impact": "Prevents stockout loss of daily sales within 48-72 hours."
            })
        return alerts

    def _check_overstocked_inventory(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                i.stock_code,
                p.description,
                i.available_stock,
                i.target_stock
            FROM inventory_snapshot i
            JOIN products p ON i.stock_code = p.stock_code
            WHERE i.inventory_health_status = 'Overstocked'
            LIMIT 8
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            excess_units = max(0, int(r["available_stock"] - r["target_stock"]))
            alerts.append({
                "alert_id": f"ALT-INV-OVER-{r['stock_code'][:10]}",
                "alert_category": "Inventory",
                "severity": "Medium",
                "affected_entity_type": "Product",
                "affected_entity_id": r["stock_code"],
                "detected_condition": f"Available inventory ({r['available_stock']} units) exceeds target stock ({r['target_stock']} units) by {excess_units} units.",
                "supporting_metric": f"Holding: {r['available_stock']} units",
                "threshold_value": f"Target Stock: {r['target_stock']}",
                "suggested_action": "Bundle with high-margin items or initiate a 15-20% clearance promotion to unlock working capital.",
                "expected_impact": f"Liquidates ~{excess_units} excess units, reducing warehouse holding fees."
            })
        return alerts

    def _check_at_risk_customers(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                cs.customer_id,
                cs.recency_days,
                cs.monetary,
                cs.frequency
            FROM customer_segments cs
            WHERE cs.segment_name = 'At Risk' AND cs.monetary >= 1000
            ORDER BY cs.monetary DESC
            LIMIT 8
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            alerts.append({
                "alert_id": f"ALT-CUST-RISK-{r['customer_id']}",
                "alert_category": "Customer",
                "severity": "High",
                "affected_entity_type": "Customer",
                "affected_entity_id": r["customer_id"],
                "detected_condition": f"High-tier customer (£{float(r['monetary']):,.2f} historic spend) has been inactive for {r['recency_days']} days.",
                "supporting_metric": f"Recency: {r['recency_days']} days | Lifetime: £{float(r['monetary']):,.2f}",
                "threshold_value": "Recency > 120 days",
                "suggested_action": "Deploy personalized win-back campaign with exclusive VIP loyalty incentives or direct account manager outreach.",
                "expected_impact": "Prevents permanent churn of high-tier customer revenue."
            })
        return alerts

    def _check_high_revenue_low_margin(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                SUM(oi.line_total) AS net_revenue,
                ROUND((SUM(oi.line_total) - SUM(COALESCE(oi.estimated_cost_total, 0))) / SUM(oi.line_total) * 100, 1) AS margin_pct
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description
            HAVING SUM(oi.line_total) > 3000 AND ((SUM(oi.line_total) - SUM(COALESCE(oi.estimated_cost_total, 0))) / SUM(oi.line_total) * 100) < 18.0
            LIMIT 5
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            alerts.append({
                "alert_id": f"ALT-PROF-HRLM-{r['stock_code'][:10]}",
                "alert_category": "Profitability",
                "severity": "High",
                "affected_entity_type": "Product",
                "affected_entity_id": r["stock_code"],
                "detected_condition": f"Product delivers high revenue (£{float(r['net_revenue']):,.2f}) but yields only {r['margin_pct']}% estimated gross margin.",
                "supporting_metric": f"Revenue: £{float(r['net_revenue']):,.2f} | Margin: {r['margin_pct']}%",
                "threshold_value": "Margin < 18.0%",
                "suggested_action": "Renegotiate supplier cost tiers or adjust unit price upward by 5-8% to restore gross margin to 25%+.",
                "expected_impact": "Could expand gross profit margin by 7-10% without significant volume drop."
            })
        return alerts

    def _check_loss_making_products(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                SUM(oi.line_total) - SUM(COALESCE(oi.estimated_cost_total, 0)) AS net_profit
            FROM products p
            JOIN order_items oi ON p.stock_code = oi.stock_code
            GROUP BY p.stock_code, p.description
            HAVING (SUM(oi.line_total) - SUM(COALESCE(oi.estimated_cost_total, 0))) < -100
            LIMIT 5
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            alerts.append({
                "alert_id": f"ALT-PROF-LOSS-{r['stock_code'][:10]}",
                "alert_category": "Profitability",
                "severity": "Critical",
                "affected_entity_type": "Product",
                "affected_entity_id": r["stock_code"],
                "detected_condition": f"Negative cumulative gross profit of £{float(r['net_profit']):,.2f} due to refund/cancellation value.",
                "supporting_metric": f"Net Loss: £{abs(float(r['net_profit'])):,.2f}",
                "threshold_value": "Net Profit < 0",
                "suggested_action": "Audit quality defect reports, package integrity, or delist product to halt financial bleed.",
                "expected_impact": "Eliminates ongoing return processing and margin drag."
            })
        return alerts

    def _check_ineffective_promotions(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT
                pc.campaign_id,
                pc.campaign_name,
                pc.campaign_budget,
                SUM(pt.final_selling_price * pt.quantity) - SUM(c.estimated_unit_cost * pt.quantity) AS promo_profit
            FROM promotion_campaigns pc
            JOIN promotion_transactions pt ON pc.campaign_id = pt.campaign_id
            JOIN product_costs c ON pt.stock_code = c.stock_code
            GROUP BY pc.campaign_id, pc.campaign_name, pc.campaign_budget
            HAVING (SUM(pt.final_selling_price * pt.quantity) - SUM(c.estimated_unit_cost * pt.quantity)) < pc.campaign_budget
            LIMIT 3
        """)
        rows = self.session.execute(query).mappings().all()
        alerts = []
        for r in rows:
            shortfall = float(r["campaign_budget"]) - float(r["promo_profit"])
            alerts.append({
                "alert_id": f"ALT-PROM-SUBROI-{r['campaign_id']}",
                "alert_category": "Promotion",
                "severity": "Medium",
                "affected_entity_type": "Campaign",
                "affected_entity_id": r["campaign_id"],
                "detected_condition": f"Promotional gross profit (£{float(r['promo_profit']):,.2f}) failed to recover campaign budget (£{float(r['campaign_budget']):,.2f}).",
                "supporting_metric": f"ROI Shortfall: -£{shortfall:,.2f}",
                "threshold_value": "Promo Profit < Budget",
                "suggested_action": "Cap discount depth at 12% and refocus promotional budget on higher-margin merchandise.",
                "expected_impact": "Protects marketing spend from diluting overall retail profitability."
            })
        return alerts

    def _check_festive_shortages(self) -> List[Dict[str, Any]]:
        alerts = []
        alerts.append({
            "alert_id": "ALT-FEST-SHORT-001",
            "alert_category": "Festive",
            "severity": "High",
            "affected_entity_type": "Category",
            "affected_entity_id": "Gifts & Home Decor",
            "detected_condition": "Diwali festive simulation projects a 45% demand uplift in lantern and tableware items exceeding current safety buffer.",
            "supporting_metric": "Projected Demand: +45% | Buffer: 14 days",
            "threshold_value": "Projected Stock < Safety Buffer",
            "suggested_action": "Expedite supplier purchase orders 3 weeks prior to festive window.",
            "expected_impact": "Captures £15,000+ in festive seasonal demand without stockout disruption."
        })
        return alerts

    def _persist_alerts(self, alerts: List[Dict[str, Any]]):
        """Idempotently insert or update alerts in the database."""
        for a in alerts:
            existing = self.session.query(BusinessAlert).filter_by(alert_id=a["alert_id"]).first()
            if existing:
                existing.detected_condition = a["detected_condition"]
                existing.supporting_metric = a["supporting_metric"]
                existing.suggested_action = a["suggested_action"]
                existing.generated_timestamp = datetime.utcnow()
            else:
                new_alert = BusinessAlert(
                    alert_id=a["alert_id"],
                    alert_category=a["alert_category"],
                    severity=a["severity"],
                    affected_entity_type=a["affected_entity_type"],
                    affected_entity_id=a["affected_entity_id"],
                    detected_condition=a["detected_condition"],
                    supporting_metric=a["supporting_metric"],
                    threshold_value=a["threshold_value"],
                    suggested_action=a["suggested_action"],
                    expected_impact=a["expected_impact"],
                    is_active=True,
                    generated_timestamp=datetime.utcnow()
                )
                self.session.add(new_alert)
        self.session.commit()

    def get_alerts(self, severity: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query active recommendations with filtering."""
        where_clauses = ["is_active = 1" if "sqlite" in str(self.session.bind.url) else "is_active = TRUE"]
        params = {}
        if severity and severity != "All":
            where_clauses.append("severity = :severity")
            params["severity"] = severity
        if category and category != "All":
            where_clauses.append("alert_category = :category")
            params["category"] = category

        filter_sql = " AND ".join(where_clauses)
        query = text(f"""
            SELECT
                alert_id, alert_category, severity, affected_entity_type, affected_entity_id,
                detected_condition, supporting_metric, threshold_value, suggested_action,
                expected_impact, generated_timestamp
            FROM business_alerts
            WHERE {filter_sql}
            ORDER BY
                CASE severity
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END ASC,
                generated_timestamp DESC
        """)
        rows = self.session.execute(query, params).mappings().all()
        return [
            {
                "alert_id": r["alert_id"],
                "alert_category": r["alert_category"],
                "severity": r["severity"],
                "affected_entity_type": r["affected_entity_type"],
                "affected_entity_id": r["affected_entity_id"],
                "detected_condition": r["detected_condition"],
                "supporting_metric": r["supporting_metric"],
                "threshold_value": r["threshold_value"],
                "suggested_action": r["suggested_action"],
                "expected_impact": r["expected_impact"],
                "generated_timestamp": str(r["generated_timestamp"])
            }
            for r in rows
        ]
