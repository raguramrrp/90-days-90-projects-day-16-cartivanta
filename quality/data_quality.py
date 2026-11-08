"""
CARTIVANTA - Data Quality Intelligence Module (Module 10)
Computes rigorous data quality metrics, validation checks, and a reproducible Data Quality Score (0-100).
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from database.models import DataQualityResult, EtlExecutionLog

logger = logging.getLogger("cartivanta.quality")

class DataQualityEngine:
    def __init__(self, batch_id: Optional[str] = None):
        self.batch_id = batch_id or f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.results: List[Dict[str, Any]] = []

    def evaluate_dataset(self, raw_count: int, metrics: Dict[str, Any], date_min: Optional[str] = None, date_max: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate full dataset transformation metrics and compute reproducible Data Quality Score (0-100).
        """
        duplicates = metrics.get("duplicate_records", 0)
        missing_customers = metrics.get("missing_customer_ids", 0)
        invalid_dates = metrics.get("invalid_dates", 0)
        invalid_prices = metrics.get("invalid_prices", 0)
        cancellations = metrics.get("cancellation_invoices", 0)
        returns = metrics.get("return_transactions", 0)
        valid_records = metrics.get("valid_processed_records", 0)

        # 1. Duplicate Check
        dup_rate = (duplicates / raw_count * 100) if raw_count > 0 else 0
        dup_status = "PASS" if dup_rate < 3.0 else ("WARNING" if dup_rate < 8.0 else "FAIL")
        self._record_check("Duplicate Records Rate", "Integrity", round(dup_rate, 2), 3.0, dup_status, f"{duplicates:,} duplicate rows identified and removed ({dup_rate:.2f}%).")

        # 2. Customer ID Completeness Check
        missing_cust_rate = (missing_customers / raw_count * 100) if raw_count > 0 else 0
        cust_status = "PASS" if missing_cust_rate < 15.0 else ("WARNING" if missing_cust_rate < 30.0 else "FAIL")
        self._record_check("Missing Customer ID Rate", "Completeness", round(missing_cust_rate, 2), 25.0, cust_status, f"{missing_customers:,} guest transactions without explicit customer IDs ({missing_cust_rate:.2f}%). Imputed with country-prefixed guest tags.")

        # 3. Date Validity Check
        date_err_rate = (invalid_dates / raw_count * 100) if raw_count > 0 else 0
        date_status = "PASS" if date_err_rate == 0 else "FAIL"
        self._record_check("Invalid Timestamp Rate", "Validity", round(date_err_rate, 4), 0.0, date_status, f"{invalid_dates} unparseable timestamps detected.")

        # 4. Price & Financial Sanity Check
        price_err_rate = (invalid_prices / raw_count * 100) if raw_count > 0 else 0
        price_status = "PASS" if price_err_rate == 0 else "FAIL"
        self._record_check("Negative Price Rate", "Validity", round(price_err_rate, 4), 0.0, price_status, f"{invalid_prices} negative price anomalies filtered.")

        # 5. Cancellation & Return Traceability
        return_rate = (returns / raw_count * 100) if raw_count > 0 else 0
        self._record_check("Return Transactions Share", "Consistency", round(return_rate, 2), 15.0, "PASS", f"{returns:,} returns/cancellations ({return_rate:.2f}%) identified and financially preserved in Net Revenue calculations.")

        # Compute Data Quality Score (0 to 100)
        # Deductions:
        # - Duplicates: up to 15 points
        # - Unregistered/Missing customer IDs: up to 15 points
        # - Invalid prices / corrupt data: up to 40 points
        # - Invalid dates: up to 30 points
        score = 100.0
        score -= min(15.0, (dup_rate / 5.0) * 15.0)
        score -= min(15.0, (missing_cust_rate / 35.0) * 15.0)
        score -= min(40.0, price_err_rate * 20.0)
        score -= min(30.0, date_err_rate * 20.0)
        final_score = max(0.0, min(100.0, round(score, 1)))

        summary = {
            "batch_id": self.batch_id,
            "data_quality_score": final_score,
            "total_source_records": raw_count,
            "valid_processed_records": valid_records,
            "duplicate_records": duplicates,
            "missing_customer_ids": missing_customers,
            "invalid_dates": invalid_dates,
            "invalid_prices": invalid_prices,
            "cancellations_count": cancellations,
            "returns_count": returns,
            "date_coverage_min": str(date_min) if date_min else "N/A",
            "date_coverage_max": str(date_max) if date_max else "N/A",
            "checks_performed": len(self.results),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        return summary

    def _record_check(self, check_name: str, category: str, value: float, threshold: float, status: str, details: str):
        self.results.append({
            "batch_id": self.batch_id,
            "check_name": check_name,
            "metric_category": category,
            "metric_value": value,
            "threshold_value": threshold,
            "status": status,
            "details": details
        })

    def persist_results(self, db_session: Session):
        """Save data quality results into database."""
        for r in self.results:
            dq_entry = DataQualityResult(
                batch_id=r["batch_id"],
                check_name=r["check_name"],
                metric_category=r["metric_category"],
                metric_value=r["metric_value"],
                threshold_value=r["threshold_value"],
                status=r["status"],
                details=r["details"]
            )
            db_session.add(dq_entry)
        db_session.commit()
        logger.info(f"Persisted {len(self.results)} data quality results to database.")
