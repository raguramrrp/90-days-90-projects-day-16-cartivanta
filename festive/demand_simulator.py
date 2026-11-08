"""
CARTIVANTA - Festive Demand Simulation Engine (Module 07B)
Calculates festive surge demand scenarios, inventory adequacy, and stockout shortfalls:
Scenario Demand = Baseline Demand * (1 + Demand Uplift Percentage)
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session
from festive.festival_calendar import FestivalCalendarManager

@dataclass
class DemandSimulationResult:
    stock_code: str
    description: str
    category: str
    festival_name: str
    uplift_pct: float
    baseline_daily_demand: float
    duration_days: int
    baseline_period_demand: float
    scenario_period_demand: float
    demand_increase_units: float
    available_stock: int
    projected_ending_stock: float
    stockout_risk: str
    shortage_units: int
    required_reorder_units: int
    is_simulation: bool = True

class FestiveDemandSimulator:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
        self.calendar_mgr = FestivalCalendarManager()

    def simulate_product_demand(
        self,
        stock_code: str,
        festival_name: str,
        custom_uplift_pct: Optional[float] = None,
        duration_days: int = 14
    ) -> Dict[str, Any]:
        """
        Simulate demand for an individual product under festive conditions.
        """
        # 1. Fetch product baseline sales velocity and current inventory
        query = text("""
            SELECT
                p.stock_code,
                p.description,
                p.category,
                COALESCE(i.available_stock, 100) AS available_stock,
                COALESCE(i.safety_stock, 30) AS safety_stock,
                COALESCE(i.target_stock, 250) AS target_stock,
                COALESCE(perf.units_sold, 0) AS units_sold
            FROM products p
            LEFT JOIN inventory_snapshot i ON p.stock_code = i.stock_code
            LEFT JOIN (
                SELECT stock_code, SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS units_sold
                FROM order_items
                GROUP BY stock_code
            ) perf ON p.stock_code = perf.stock_code
            WHERE p.stock_code = :stock_code
        """)
        row = self.session.execute(query, {"stock_code": stock_code}).mappings().first()
        if not row:
            return {"error": f"Product {stock_code} not found."}

        # Determine uplift percentage
        fest = self.calendar_mgr.get_festival(festival_name)
        default_uplift = fest.demand_uplift_assumption if fest else 0.35
        uplift_pct = custom_uplift_pct if custom_uplift_pct is not None else default_uplift

        # Historical baseline daily demand
        observed_days = 730.0
        baseline_daily = max(1.0, float(row["units_sold"] or 0) / observed_days)
        baseline_demand_period = round(baseline_daily * duration_days, 1)

        # Scenario Demand = Baseline Demand * (1 + Uplift %)
        scenario_demand_period = round(baseline_demand_period * (1.0 + uplift_pct), 1)
        increase_units = round(scenario_demand_period - baseline_demand_period, 1)

        available_stock = int(row["available_stock"])
        projected_ending = available_stock - scenario_demand_period
        
        shortage = int(abs(projected_ending)) if projected_ending < 0 else 0
        stockout_risk = "High / Shortage" if projected_ending < 0 else ("Moderate" if projected_ending < row["safety_stock"] else "Low / Adequate")
        required_reorder = max(0, int(np.ceil(scenario_demand_period + row["safety_stock"] - available_stock)))

        return {
            "stock_code": row["stock_code"],
            "description": row["description"],
            "category": row["category"],
            "festival_name": festival_name,
            "duration_days": duration_days,
            "demand_uplift_pct": round(uplift_pct * 100, 1),
            "baseline_daily_demand": round(baseline_daily, 2),
            "baseline_period_demand": baseline_demand_period,
            "scenario_period_demand": scenario_demand_period,
            "additional_demand_units": increase_units,
            "available_stock": available_stock,
            "projected_ending_stock": round(projected_ending, 1),
            "stockout_risk": stockout_risk,
            "stock_shortage_units": shortage,
            "recommended_stock_replenishment": required_reorder,
            "is_simulation": True
        }

    def simulate_category_demand(
        self,
        category: str,
        festival_name: str,
        custom_uplift_pct: Optional[float] = None,
        duration_days: int = 14
    ) -> Dict[str, Any]:
        """Simulate demand aggregated across all products in a category."""
        query = text("""
            SELECT p.stock_code
            FROM products p
            WHERE p.category = :category
            LIMIT 50
        """)
        rows = self.session.execute(query, {"category": category}).mappings().all()
        sim_results = [
            self.simulate_product_demand(r["stock_code"], festival_name, custom_uplift_pct, duration_days)
            for r in rows
        ]
        sim_results = [r for r in sim_results if "error" not in r]

        total_baseline = sum(r["baseline_period_demand"] for r in sim_results)
        total_scenario = sum(r["scenario_period_demand"] for r in sim_results)
        total_shortage = sum(r["stock_shortage_units"] for r in sim_results)
        shortage_items_count = sum(1 for r in sim_results if r["stock_shortage_units"] > 0)

        return {
            "category": category,
            "festival_name": festival_name,
            "duration_days": duration_days,
            "products_evaluated": len(sim_results),
            "total_baseline_demand": round(total_baseline, 1),
            "total_scenario_demand": round(total_scenario, 1),
            "total_demand_increase": round(total_scenario - total_baseline, 1),
            "total_shortage_units": total_shortage,
            "products_at_stockout_risk": shortage_items_count,
            "product_details": sim_results[:10],
            "is_simulation": True
        }
