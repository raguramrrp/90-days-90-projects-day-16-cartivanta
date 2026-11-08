"""
CARTIVANTA - End-to-End Orchestration Pipeline
Executes the full data engineering, machine learning, and retail intelligence pipeline:
1. Extract (Unified raw dataset or sample)
2. Transform (Cleaning, cancellations, returns, normalization)
3. Synthetic Generation (product_costs, inventory_snapshot, campaigns, calendar)
4. Load (Transactional load into analytical tables)
5. Customer Segmentation (RFM + K-Means)
6. Demand Forecasting (Seasonal Naive + RandomForestRegressor evaluation)
7. Business Action Center (Rule-based recommendations)
8. Data Quality Intelligence (Audit scores and verification)
"""
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from config.settings import (
    RAW_DATA_DIR, SAMPLES_DATA_DIR, SYNTHETIC_DATA_DIR, 
    PROCESSED_DATA_DIR, CHUNK_SIZE
)
from etl.extract import locate_source_file, generate_sample_dataset
from etl.transform import clean_raw_dataframe, build_normalized_entities
from etl.generate_synthetic import (
    generate_product_costs, generate_inventory_snapshot,
    generate_promotion_campaigns, generate_promotion_transactions,
    generate_all_synthetic
)
from etl.load import load_entities_to_database
from quality.data_quality import DataQualityEngine
from models.customer_segmentation import CustomerSegmentationEngine
from models.demand_forecasting import DemandForecastingEngine
from recommendations.business_rules import BusinessRecommendationEngine
from database.connection import get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cartivanta.pipeline")

def run_pipeline(use_sample: bool = False, sample_size: int = 50000, force_sqlite: bool = False) -> Dict[str, Any]:
    """Execute complete end-to-end CARTIVANTA data intelligence pipeline."""
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("STARTING CARTIVANTA RETAIL INTELLIGENCE PIPELINE")
    logger.info("=" * 70)

    dq_engine = DataQualityEngine()

    # Step 1: Extract
    logger.info("--- PHASE 1: DATA EXTRACTION ---")
    if use_sample:
        data_file = generate_sample_dataset(sample_size=sample_size)
        logger.info(f"Using sample dataset: {data_file.name} ({sample_size:,} rows)")
        raw_df = pd.read_csv(data_file, low_memory=False)
    else:
        # Full unified dataset
        data_file = RAW_DATA_DIR / "online_retail_ii_unified.csv"
        if not data_file.exists():
            data_file = locate_source_file()
        logger.info(f"Loading primary source dataset: {data_file.name}")
        raw_df = pd.read_csv(data_file, low_memory=False)

    raw_row_count = len(raw_df)
    logger.info(f"Raw source records loaded: {raw_row_count:,}")

    # Step 2: Transform
    logger.info("--- PHASE 2: DATA TRANSFORMATION & DATA QUALITY AUDIT ---")
    cleaned_df, dq_metrics = clean_raw_dataframe(raw_df)
    logger.info(f"Transformation complete. Valid processed records: {len(cleaned_df):,}")

    min_date = cleaned_df["invoice_date"].min()
    max_date = cleaned_df["invoice_date"].max()
    dq_summary = dq_engine.evaluate_dataset(raw_row_count, dq_metrics, date_min=min_date, date_max=max_date)
    logger.info(f"Data Quality Score computed: {dq_summary['data_quality_score']} / 100")

    # Step 3: Synthetic Supporting Data Generation
    logger.info("--- PHASE 3: SYNTHETIC DATA GENERATION ---")
    # Base synthetic generation on actual products in the dataset
    products_prelim = cleaned_df[["stock_code", "description", "category", "unit_price"]].drop_duplicates("stock_code")
    costs_df = generate_product_costs(products_prelim)
    inv_df = generate_inventory_snapshot(products_prelim)
    camp_df = generate_promotion_campaigns()
    promo_txns_df = generate_promotion_transactions(camp_df, products_prelim)

    from festive.festival_calendar import DEFAULT_FESTIVALS
    fest_df = pd.DataFrame([
        {
            "festival_name": f.festival_name,
            "start_date": f.start_date,
            "end_date": f.end_date,
            "festival_category": f.festival_category,
            "demand_uplift_assumption": f.demand_uplift_assumption,
            "notes": f.notes,
            "is_synthetic": True
        }
        for f in DEFAULT_FESTIVALS
    ])

    # Save synthetic CSVs to disk
    SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    costs_df.to_csv(SYNTHETIC_DATA_DIR / "product_costs.csv", index=False)
    inv_df.to_csv(SYNTHETIC_DATA_DIR / "inventory_snapshot.csv", index=False)
    camp_df.to_csv(SYNTHETIC_DATA_DIR / "promotion_campaigns.csv", index=False)
    promo_txns_df.to_csv(SYNTHETIC_DATA_DIR / "promotion_transactions.csv", index=False)
    fest_df.to_csv(SYNTHETIC_DATA_DIR / "festival_calendar.csv", index=False)
    logger.info("Synthetic supporting CSV files written to disk.")

    synthetic_package = {
        "product_costs": costs_df,
        "inventory_snapshot": inv_df,
        "festival_calendar": fest_df,
        "promotion_campaigns": camp_df,
        "promotion_transactions": promo_txns_df
    }

    # Build normalized relational entities
    entities = build_normalized_entities(cleaned_df, costs_df)

    # Step 4: Load to Database
    logger.info("--- PHASE 4: DATABASE INGESTION ---")
    load_counts = load_entities_to_database(
        entities=entities,
        synthetic_data=synthetic_package,
        dq_engine=dq_engine,
        force_sqlite=force_sqlite
    )

    # Step 5: Customer Segmentation
    logger.info("--- PHASE 5: CUSTOMER INTELLIGENCE (RFM & K-MEANS) ---")
    seg_engine = CustomerSegmentationEngine()
    seg_results = seg_engine.run_and_persist_segmentation()
    logger.info(f"Customer segmentation complete: {seg_results}")

    # Step 6: Demand Forecasting
    logger.info("--- PHASE 6: MACHINE LEARNING DEMAND FORECASTING ---")
    forecast_engine = DemandForecastingEngine()
    forecast_results = forecast_engine.run_top_product_forecasts(limit=5)
    logger.info(f"Demand forecasting complete for {len(forecast_results)} products.")

    # Step 7: Business Action Center
    logger.info("--- PHASE 7: BUSINESS ACTION CENTER RECOMMENDATIONS ---")
    rec_engine = BusinessRecommendationEngine()
    alerts = rec_engine.generate_all_recommendations()
    logger.info(f"Generated {len(alerts)} actionable business alerts.")

    elapsed = round(time.time() - start_time, 2)
    logger.info("=" * 70)
    logger.info(f"CARTIVANTA PIPELINE COMPLETED SUCCESSFULLY IN {elapsed}s")
    logger.info("=" * 70)

    return {
        "status": "SUCCESS",
        "elapsed_seconds": elapsed,
        "source_rows": raw_row_count,
        "loaded_counts": load_counts,
        "data_quality_score": dq_summary["data_quality_score"],
        "customer_segments": seg_results,
        "forecasted_products": len(forecast_results),
        "alerts_generated": len(alerts)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CARTIVANTA ETL & Intelligence Pipeline")
    parser.add_argument("--sample", action="store_true", help="Run in fast sample mode")
    parser.add_argument("--sample-size", type=int, default=50000, help="Number of rows for sample")
    parser.add_argument("--sqlite", action="store_true", help="Force SQLite engine")
    args = parser.parse_args()

    run_pipeline(use_sample=args.sample, sample_size=args.sample_size, force_sqlite=args.sqlite)
