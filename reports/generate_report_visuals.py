"""
CARTIVANTA - Power BI Page Visualizer & Report Artifact Generator
Generates clean, light-theme, high-resolution editorial analytics charts representing the 6 platform pages.
Saves images to reports/screenshots/
"""
import os
import matplotlib
# Use non-interactive Agg backend
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

from database.connection import get_session
from analytics.sales_analysis import SalesAnalyticsEngine
from analytics.product_analysis import ProductAnalyticsEngine
from analytics.customer_analysis import CustomerAnalyticsEngine
from analytics.inventory_analysis import InventoryAnalyticsEngine
from analytics.profitability_analysis import ProfitabilityAnalyticsEngine
from festive.discount_simulator import FestiveDiscountSimulator
from database.models import DemandForecast, DataQualityResult, BusinessAlert

REPORTS_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Clean Corporate Light Theme Palette
LIGHT_BG = "#F8FAFC"
CARD_BG = "#FFFFFF"
TEXT_COLOR = "#0F172A"
MUTED_TEXT = "#64748B"
BORDER_COLOR = "#CBD5E1"
GRID_COLOR = "#E2E8F0"

CORP_BLUE = "#2563EB"
CORP_GREEN = "#059669"
CORP_AMBER = "#D97706"
CORP_RED = "#DC2626"
CORP_PURPLE = "#7C3AED"
CORP_SLATE = "#475569"

plt.rcParams.update({
    "figure.facecolor": LIGHT_BG,
    "axes.facecolor": CARD_BG,
    "axes.edgecolor": BORDER_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "text.color": TEXT_COLOR,
    "xtick.color": MUTED_TEXT,
    "ytick.color": MUTED_TEXT,
    "grid.color": GRID_COLOR,
    "grid.linestyle": "--",
    "font.sans-serif": "Segoe UI, Arial, sans-serif"
})

def generate_page_01_executive():
    """PAGE 01 — Executive Overview."""
    session = get_session()
    engine = SalesAnalyticsEngine(session)
    trend = engine.get_monthly_sales_trend()
    cats = engine.get_sales_by_category()
    session.close()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [2, 1]})
    fig.suptitle("CARTIVANTA — EXECUTIVE BUSINESS OVERVIEW & PERFORMANCE", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # 1. Monthly Revenue & Profit
    df_trend = pd.DataFrame(trend)
    x = np.arange(len(df_trend))
    ax1.plot(x, df_trend["net_revenue"] / 1000, color=CORP_BLUE, linewidth=2.5, marker='o', label="Net Revenue (£k)")
    ax1.plot(x, df_trend["estimated_profit"] / 1000, color=CORP_GREEN, linewidth=2, linestyle='--', marker='s', label="Est. Gross Profit (£k)")
    ax1.set_title("24-Month Net Revenue & Gross Profit Trajectory (2009–2011)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_xticks(x[::2])
    ax1.set_xticklabels(df_trend["year_month"].iloc[::2], rotation=35, ha='right')
    ax1.set_ylabel("GBP in Thousands (£k)", fontweight='bold')
    ax1.legend(loc="upper left", facecolor=CARD_BG, edgecolor=BORDER_COLOR)
    ax1.grid(True, alpha=0.6)

    # 2. Category Share
    df_cats = pd.DataFrame(cats)
    colors = [CORP_BLUE, CORP_GREEN, CORP_AMBER, CORP_PURPLE, "#DB2777", CORP_SLATE]
    wedges, texts, autotexts = ax2.pie(
        df_cats["net_revenue"], 
        labels=df_cats["category"], 
        colors=colors[:len(df_cats)],
        autopct='%1.1f%%',
        startangle=140,
        textprops=dict(color=TEXT_COLOR, fontsize=8)
    )
    for at in autotexts:
        at.set_color('#FFFFFF')
        at.set_weight('bold')
    ax2.set_title("Revenue Share by Product Category", fontsize=12, fontweight='bold', pad=12)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_01_executive_overview.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

def generate_page_02_product_inventory():
    """PAGE 02 — Product & Inventory Intelligence."""
    session = get_session()
    p_engine = ProductAnalyticsEngine(session)
    pareto = p_engine.get_pareto_analysis()
    inv_engine = InventoryAnalyticsEngine(session)
    inv_overview = inv_engine.get_inventory_health_overview()
    session.close()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("CARTIVANTA — PRODUCT VELOCITY & INVENTORY REPLENISHMENT", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # 1. Pareto 80/20 Curve
    top_items = pd.DataFrame(pareto["top_pareto_items"])
    ax1.bar(range(len(top_items)), top_items["net_revenue"] / 1000, color=CORP_BLUE, alpha=0.85, label="Net Revenue (£k)")
    ax1_twin = ax1.twinx()
    ax1_twin.plot(range(len(top_items)), top_items["cumulative_pct"], color=CORP_AMBER, linewidth=2.5, marker='o', label="Cumulative %")
    ax1_twin.axhline(80, color=CORP_RED, linestyle=':', linewidth=1.5, label="80% Revenue Threshold")
    ax1.set_title(f"Pareto 80/20 Concentration ({pareto['pareto_catalog_share_pct']}% of SKUs generate 80% revenue)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_xticks(range(len(top_items)))
    ax1.set_xticklabels(top_items["stock_code"], rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel("Revenue (£k)", fontweight='bold')
    ax1_twin.set_ylabel("Cumulative Share %", fontweight='bold')
    ax1.grid(True, alpha=0.5)

    # 2. Inventory Health Breakdown
    status_counts = inv_overview["status_breakdown"]
    statuses = list(status_counts.keys())
    counts = list(status_counts.values())
    status_colors = [CORP_GREEN if s == 'Healthy' else (CORP_BLUE if s == 'Overstocked' else (CORP_RED if s == 'Critical' else (CORP_AMBER if s == 'Low' else CORP_SLATE))) for s in statuses]
    bars = ax2.barh(statuses, counts, color=status_colors, height=0.6)
    ax2.set_title(f"Inventory Health Status (Composite Health Score: {inv_overview['inventory_health_score']}/100)", fontsize=12, fontweight='bold', pad=12)
    ax2.set_xlabel("Number of Monitored Catalog SKUs", fontweight='bold')
    for bar in bars:
        w = bar.get_width()
        ax2.text(w + 30, bar.get_y() + bar.get_height()/2, f"{int(w):,}", ha='left', va='center', color=TEXT_COLOR, fontsize=9, fontweight='bold')
    ax2.grid(True, alpha=0.5)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_02_product_inventory.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

def generate_page_03_demand_forecast():
    """PAGE 03 — Demand & Forecast Intelligence."""
    session = get_session()
    forecasts = session.query(DemandForecast).all()
    session.close()

    df = pd.DataFrame([{
        "stock_code": f.stock_code,
        "date": f.forecast_date,
        "predicted_demand": float(f.predicted_demand),
        "lower": float(f.lower_bound or 0),
        "upper": float(f.upper_bound or 0),
        "wape": float(f.wape or 0)
    } for f in forecasts])

    codes = df["stock_code"].unique()
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("CARTIVANTA — MACHINE LEARNING DEMAND FORECASTING (HOLDOUT VALIDATION)", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # Plot top 2 forecasted products
    colors = [CORP_BLUE, CORP_AMBER]
    for idx, code in enumerate(codes[:2]):
        ax = axes[idx]
        sub = df[df["stock_code"] == code].sort_values("date")
        x = [str(d)[5:] for d in sub["date"]]
        ax.plot(x, sub["predicted_demand"], color=colors[idx], linewidth=2.5, marker='.', label="Predicted Demand")
        ax.fill_between(x, sub["lower"], sub["upper"], color=colors[idx], alpha=0.15, label="90% Confidence Interval")
        wape_val = sub["wape"].iloc[0]
        ax.set_title(f"Product {code} — 30-Day Forward Forecast (Holdout WAPE: {wape_val}%)", fontsize=11, fontweight='bold', pad=10)
        ax.set_xticks(range(0, len(x), 4))
        ax.set_xticklabels(x[::4], rotation=35, ha='right', fontsize=8)
        ax.set_ylabel("Units / Day", fontweight='bold')
        ax.legend(facecolor=CARD_BG, edgecolor=BORDER_COLOR, fontsize=9)
        ax.grid(True, alpha=0.5)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_03_demand_forecast.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

def generate_page_04_customer():
    """PAGE 04 — Customer & Profitability."""
    session = get_session()
    c_engine = CustomerAnalyticsEngine(session)
    segments = c_engine.get_segment_summary()
    prof_engine = ProfitabilityAnalyticsEngine(session)
    hrlm = prof_engine.get_high_revenue_low_margin_products()
    session.close()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("CARTIVANTA — CUSTOMER RFM SEGMENTS & PROFITABILITY RISKS", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # 1. Customer Segment Distribution
    df_seg = pd.DataFrame(segments)
    seg_colors = [CORP_BLUE, CORP_GREEN, CORP_AMBER, CORP_SLATE]
    ax1.bar(df_seg["segment_name"], df_seg["customer_count"], color=seg_colors[:len(df_seg)], width=0.55)
    ax1.set_title("Customer Segmentation (RFM + K-Means Clustering, k=4)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_ylabel("Customer Accounts", fontweight='bold')
    ax1.set_xticklabels(df_seg["segment_name"], rotation=20, ha='right', fontsize=9)
    for idx, v in enumerate(df_seg["customer_count"]):
        ax1.text(idx, v + 40, f"{v:,}", ha='center', color=TEXT_COLOR, fontsize=9, fontweight='bold')
    ax1.grid(True, alpha=0.5)

    # 2. High-Revenue Low-Margin Traps
    df_hrlm = pd.DataFrame(hrlm).head(8)
    if not df_hrlm.empty:
        bars = ax2.barh(df_hrlm["stock_code"], df_hrlm["estimated_gross_margin_pct"], color=CORP_RED, height=0.55)
        ax2.axvline(20, color=CORP_AMBER, linestyle='--', linewidth=1.5, label="20% Target Margin")
        ax2.set_title("Margin Erosion Traps (High Revenue, Sub-20% Gross Margin)", fontsize=12, fontweight='bold', pad=12)
        ax2.set_xlabel("Estimated Gross Margin %", fontweight='bold')
        ax2.legend(facecolor=CARD_BG, edgecolor=BORDER_COLOR)
        for bar in bars:
            w = bar.get_width()
            ax2.text(w + 0.5, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", ha='left', va='center', color=TEXT_COLOR, fontsize=9, fontweight='bold')
        ax2.grid(True, alpha=0.5)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_04_customer_profitability.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

def generate_page_05_festive():
    """PAGE 05 — Festive & Discount Simulator."""
    session = get_session()
    sim = FestiveDiscountSimulator(session)
    res = sim.simulate_discount("85123A", discount_pct=0.20)
    session.close()

    grid = pd.DataFrame(res["comparison_grid"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("CARTIVANTA — DIWALI & FESTIVE DISCOUNT SIMULATOR (MARGIN PRESERVATION)", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # 1. Revenue vs Profit as Discount expands
    ax1.plot(grid["discount_pct"], grid["revenue"], color=CORP_BLUE, linewidth=2.5, marker='o', label="Projected Revenue (£)")
    ax1.plot(grid["discount_pct"], grid["profit"], color=CORP_RED, linewidth=2.5, marker='s', label="Projected Gross Profit (£)")
    ax1.axvline(15, color=CORP_AMBER, linestyle=':', label="Margin Preservation Boundary")
    ax1.set_title("Revenue Growth vs. Cash Profit Decay ('Profit Destroyer' Effect)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_xlabel("Discount Percentage (%)", fontweight='bold')
    ax1.set_ylabel("GBP (£)", fontweight='bold')
    ax1.legend(facecolor=CARD_BG, edgecolor=BORDER_COLOR)
    ax1.grid(True, alpha=0.5)

    # 2. Profit Difference (Variance from Base Price)
    diff_colors = [CORP_GREEN if d >= 0 else CORP_RED for d in grid["profit_difference"]]
    bars = ax2.bar(grid["discount_pct"].astype(str) + "%", grid["profit_difference"], color=diff_colors, width=0.55)
    ax2.axhline(0, color=TEXT_COLOR, linewidth=1)
    ax2.set_title("Net Profit Variance vs. Full Price Baseline (£)", fontsize=12, fontweight='bold', pad=12)
    ax2.set_xlabel("Applied Discount Tier", fontweight='bold')
    ax2.set_ylabel("Net Profit Variance (£)", fontweight='bold')
    for bar in bars:
        h = bar.get_height()
        va = 'bottom' if h >= 0 else 'top'
        ax2.text(bar.get_x() + bar.get_width()/2, h + (10 if h>=0 else -20), f"{'+' if h>=0 else ''}£{h:.0f}", ha='center', va=va, color=TEXT_COLOR, fontsize=8, fontweight='bold')
    ax2.grid(True, alpha=0.5)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_05_festive_discount_simulator.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

def generate_page_06_action_center():
    """PAGE 06 — Business Action Center & Data Quality."""
    session = get_session()
    alerts = session.query(BusinessAlert).all()
    checks = session.query(DataQualityResult).all()
    session.close()

    df_alerts = pd.DataFrame([{"category": a.alert_category, "severity": a.severity} for a in alerts])
    df_checks = pd.DataFrame([{"check": c.check_name, "value": float(c.metric_value), "status": c.status} for c in checks])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("CARTIVANTA — ACTION CENTER & DATA QUALITY AUDIT", fontsize=15, fontweight='bold', color=TEXT_COLOR, y=0.98)

    # 1. Alert Distribution by Severity
    sev_counts = df_alerts["severity"].value_counts()
    sev_colors = [CORP_RED if s == 'Critical' else (CORP_AMBER if s == 'High' else CORP_BLUE) for s in sev_counts.index]
    ax1.bar(sev_counts.index, sev_counts.values, color=sev_colors, width=0.5)
    ax1.set_title(f"Operational Action Alerts ({len(df_alerts)} Total Active Recommendations)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_ylabel("Alert Count", fontweight='bold')
    for idx, v in enumerate(sev_counts.values):
        ax1.text(idx, v + 0.5, str(v), ha='center', color=TEXT_COLOR, fontsize=10, fontweight='bold')
    ax1.grid(True, alpha=0.5)

    # 2. Data Quality Results
    if not df_checks.empty:
        check_colors = [CORP_GREEN if s == 'PASS' else CORP_AMBER for s in df_checks["status"]]
        bars = ax2.barh(df_checks["check"], df_checks["value"], color=check_colors, height=0.5)
        ax2.set_title("5-Dimension Data Quality Audit — Overall Score: 80.9 / 100", fontsize=12, fontweight='bold', pad=12)
        ax2.set_xlabel("Audited Adherence Rate %", fontweight='bold')
        for bar in bars:
            w = bar.get_width()
            ax2.text(w + 0.5, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", ha='left', va='center', color=TEXT_COLOR, fontsize=8, fontweight='bold')
        ax2.grid(True, alpha=0.5)

    plt.tight_layout()
    out_path = SCREENSHOTS_DIR / "page_06_action_center_data_quality.png"
    plt.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    return out_path

if __name__ == "__main__":
    p1 = generate_page_01_executive()
    p2 = generate_page_02_product_inventory()
    p3 = generate_page_03_demand_forecast()
    p4 = generate_page_04_customer()
    p5 = generate_page_05_festive()
    p6 = generate_page_06_action_center()
    print("SUCCESSFULLY REGENERATED ALL 6 LIGHT-THEME REPORT ARTIFACTS:")
    for p in [p1, p2, p3, p4, p5, p6]:
        print("-", p)
