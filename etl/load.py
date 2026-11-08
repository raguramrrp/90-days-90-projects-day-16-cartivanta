"""
CARTIVANTA - ETL Load Module
Loads normalized entities and synthetic supporting data into PostgreSQL / SQLite.
Ensures idempotency, transactional safety, and execution logging.
"""
import uuid
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_engine, get_session, init_db
from database.models import (
    Customer, Product, Order, OrderItem, ProductCost, 
    InventorySnapshot, Calendar, FestivalCalendar, 
    PromotionCampaign, PromotionTransaction, EtlExecutionLog
)
from quality.data_quality import DataQualityEngine

logger = logging.getLogger("cartivanta.etl.load")

def populate_calendar_dimension(session: Session, start_date: str = "2009-01-01", end_date: str = "2012-12-31"):
    """Generate calendar date dimension if empty."""
    existing = session.query(Calendar).first()
    if existing:
        return

    logger.info("Populating calendar dimension table from %s to %s...", start_date, end_date)
    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)
    curr = start_dt
    records = []

    while curr <= end_dt:
        records.append(Calendar(
            date_id=curr,
            day_name=curr.strftime("%A"),
            day_of_week=curr.weekday() + 1,
            day_of_month=curr.day,
            day_of_year=int(curr.strftime("%j")),
            week_of_year=int(curr.strftime("%U")) + 1,
            month_number=curr.month,
            month_name=curr.strftime("%B"),
            quarter_number=(curr.month - 1) // 3 + 1,
            year_number=curr.year,
            is_weekend=(curr.weekday() >= 5)
        ))
        curr += timedelta(days=1)

    session.bulk_save_objects(records)
    session.commit()
    logger.info(f"Populated {len(records)} dates in calendar dimension.")

def load_entities_to_database(
    entities: Dict[str, pd.DataFrame],
    synthetic_data: Dict[str, pd.DataFrame],
    dq_engine: DataQualityEngine,
    force_sqlite: bool = False
) -> Dict[str, int]:
    """
    Safely load normalized entities into the database using chunking and execution logging.
    """
    batch_id = dq_engine.batch_id
    logger.info(f"Starting ETL load batch: {batch_id}")
    
    # Initialize schema first
    init_db(force_sqlite=force_sqlite)
    engine = get_engine(force_sqlite=force_sqlite)
    session = get_session(force_sqlite=force_sqlite)
    
    counts = {}
    
    try:
        # Step 1: Calendar
        log_step(session, batch_id, "Populate Calendar", "STARTED")
        populate_calendar_dimension(session)
        log_step(session, batch_id, "Populate Calendar", "SUCCESS", records_processed=1461)

        # Clear previous data for idempotent re-runs
        with engine.begin() as conn:
            for tbl in [
                "promotion_transactions", "promotion_campaigns", "order_items", 
                "orders", "inventory_snapshot", "product_costs", "products", 
                "customer_segments", "customers", "festival_calendar"
            ]:
                try:
                    conn.execute(text(f"DELETE FROM {tbl}"))
                except Exception as e:
                    pass

        # Step 2: Customers
        log_step(session, batch_id, "Load Customers", "STARTED")
        cust_df = entities["customers"]
        cust_df.to_sql("customers", engine, if_exists="append", index=False, chunksize=5000)
        counts["customers"] = len(cust_df)
        log_step(session, batch_id, "Load Customers", "SUCCESS", records_processed=len(cust_df))

        # Step 3: Products
        log_step(session, batch_id, "Load Products", "STARTED")
        prod_df = entities["products"]
        # Retain columns matching products table
        prod_cols = ["stock_code", "description", "category", "first_seen_date", "last_seen_date", "is_active"]
        prod_df[prod_cols].to_sql("products", engine, if_exists="append", index=False, chunksize=5000)
        counts["products"] = len(prod_df)
        log_step(session, batch_id, "Load Products", "SUCCESS", records_processed=len(prod_df))

        # Step 4: Product Costs (Synthetic)
        log_step(session, batch_id, "Load Product Costs", "STARTED")
        costs_df = synthetic_data["product_costs"]
        # Only load costs for products that exist
        valid_codes = set(prod_df["stock_code"].astype(str))
        costs_valid = costs_df[costs_df["stock_code"].astype(str).isin(valid_codes)]
        costs_valid.to_sql("product_costs", engine, if_exists="append", index=False, chunksize=5000)
        counts["product_costs"] = len(costs_valid)
        log_step(session, batch_id, "Load Product Costs", "SUCCESS", records_processed=len(costs_valid))

        # Step 5: Inventory Snapshot (Synthetic)
        log_step(session, batch_id, "Load Inventory Snapshot", "STARTED")
        inv_df = synthetic_data["inventory_snapshot"]
        inv_valid = inv_df[inv_df["stock_code"].astype(str).isin(valid_codes)]
        inv_valid.to_sql("inventory_snapshot", engine, if_exists="append", index=False, chunksize=5000)
        counts["inventory_snapshot"] = len(inv_valid)
        log_step(session, batch_id, "Load Inventory Snapshot", "SUCCESS", records_processed=len(inv_valid))

        # Step 6: Orders
        log_step(session, batch_id, "Load Orders", "STARTED")
        orders_df = entities["orders"]
        orders_df.to_sql("orders", engine, if_exists="append", index=False, chunksize=5000)
        counts["orders"] = len(orders_df)
        log_step(session, batch_id, "Load Orders", "SUCCESS", records_processed=len(orders_df))

        # Step 7: Order Items
        log_step(session, batch_id, "Load Order Items", "STARTED")
        items_df = entities["order_items"]
        items_df.to_sql("order_items", engine, if_exists="append", index=False, chunksize=10000)
        counts["order_items"] = len(items_df)
        log_step(session, batch_id, "Load Order Items", "SUCCESS", records_processed=len(items_df))

        # Step 8: Festival Calendar
        log_step(session, batch_id, "Load Festival Calendar", "STARTED")
        fest_df = synthetic_data["festival_calendar"]
        fest_df.to_sql("festival_calendar", engine, if_exists="append", index=False)
        counts["festival_calendar"] = len(fest_df)
        log_step(session, batch_id, "Load Festival Calendar", "SUCCESS", records_processed=len(fest_df))

        # Step 9: Promotion Campaigns & Transactions
        log_step(session, batch_id, "Load Promotions", "STARTED")
        camp_df = synthetic_data["promotion_campaigns"]
        camp_df.to_sql("promotion_campaigns", engine, if_exists="append", index=False)
        
        promo_txns_df = synthetic_data["promotion_transactions"]
        promo_valid = promo_txns_df[promo_txns_df["stock_code"].astype(str).isin(valid_codes)]
        promo_valid.to_sql("promotion_transactions", engine, if_exists="append", index=False, chunksize=5000)
        counts["promotion_campaigns"] = len(camp_df)
        counts["promotion_transactions"] = len(promo_valid)
        log_step(session, batch_id, "Load Promotions", "SUCCESS", records_processed=len(promo_valid))

        # Persist DQ Results
        dq_engine.persist_results(session)

    except Exception as exc:
        logger.error(f"ETL Load failed during execution: {exc}")
        log_step(session, batch_id, "ETL Pipeline", "FAILED", details=str(exc))
        session.rollback()
        raise exc
    finally:
        session.close()

    logger.info("ETL Load completed successfully: %s", counts)
    return counts

def log_step(session: Session, batch_id: str, step_name: str, status: str, records_processed: int = 0, records_failed: int = 0, details: str = ""):
    """Helper to record ETL execution status into etl_execution_logs."""
    try:
        log_entry = EtlExecutionLog(
            batch_id=batch_id,
            step_name=step_name,
            status=status,
            records_processed=records_processed,
            records_failed=records_failed,
            details=details,
            completed_at=datetime.utcnow() if status in ("SUCCESS", "FAILED") else None
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Could not write to etl_execution_logs: {e}")
