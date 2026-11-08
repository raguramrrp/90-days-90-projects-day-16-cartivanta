"""
CARTIVANTA - Customer Intelligence & RFM Segmentation Module (Module 03)
Performs Recency, Frequency, and Monetary (RFM) calculation, applies StandardScaler
and K-Means clustering, and profiles customers into actionable segments:
- Champions
- Loyal Customers
- Potential Loyalists
- New Customers
- At Risk
- Hibernating
- Lost Customers
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session
from database.models import CustomerSegment

logger = logging.getLogger("cartivanta.customer_segmentation")

class CustomerSegmentationEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def compute_rfm_metrics(self) -> pd.DataFrame:
        """
        Extract customer transactions and compute Recency, Frequency, Monetary metrics.
        Filters out GUEST transactions to focus on registered customer relationships.
        """
        query = text("""
            SELECT
                o.customer_id,
                MAX(o.invoice_date) AS last_purchase_date,
                COUNT(DISTINCT o.invoice_no) AS frequency,
                COALESCE(SUM(oi.line_total), 0) AS monetary,
                (SELECT MAX(invoice_date) FROM orders) AS max_dataset_date
            FROM orders o
            JOIN order_items oi ON o.invoice_no = oi.invoice_no
            WHERE o.customer_id IS NOT NULL AND o.customer_id NOT LIKE 'GUEST-%'
            GROUP BY o.customer_id
            HAVING SUM(oi.line_total) > 0
        """)
        rows = self.session.execute(query).mappings().all()
        if not rows:
            logger.warning("No customer records found to segment.")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"])
        df["max_dataset_date"] = pd.to_datetime(df["max_dataset_date"])
        
        # Recency in days relative to latest invoice in dataset
        df["recency_days"] = (df["max_dataset_date"] - df["last_purchase_date"]).dt.days
        df["frequency"] = df["frequency"].astype(int)
        df["monetary"] = df["monetary"].astype(float)
        df["avg_order_value"] = np.round(df["monetary"] / df["frequency"], 2)
        df["lifetime_revenue"] = df["monetary"]

        # R, F, M Quintile Scores (1 to 5)
        # Higher Recency days = lower score
        df["r_score"] = pd.qcut(df["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
        df["f_score"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        df["m_score"] = pd.qcut(df["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

        return df

    def perform_kmeans_clustering(self, rfm_df: pd.DataFrame, n_clusters: int = 5, random_state: int = 42) -> pd.DataFrame:
        """
        Apply log-transform, StandardScaler, and KMeans clustering.
        """
        df = rfm_df.copy()
        features = ["recency_days", "frequency", "monetary"]
        
        # Log-transform to handle right skew in retail distributions
        log_features = np.log1p(df[features])
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(log_features)

        kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        df["cluster_id"] = kmeans.fit_predict(scaled_features)

        # Profile clusters based on mean R, F, M to assign business segment names
        cluster_profile = df.groupby("cluster_id").agg(
            mean_r=("recency_days", "mean"),
            mean_f=("frequency", "mean"),
            mean_m=("monetary", "mean")
        ).reset_index()

        # Dynamic mapping based on cluster centroids
        segment_map = {}
        for _, r in cluster_profile.iterrows():
            cid = int(r["cluster_id"])
            rec = r["mean_r"]
            freq = r["mean_f"]
            mon = r["mean_m"]

            if rec < 50 and freq >= 5 and mon >= 2000:
                segment_map[cid] = "Champions"
            elif rec < 90 and freq >= 3:
                segment_map[cid] = "Loyal Customers"
            elif rec < 60 and freq <= 2:
                segment_map[cid] = "Potential Loyalists"
            elif rec > 180 and freq >= 3:
                segment_map[cid] = "At Risk"
            elif rec > 250:
                segment_map[cid] = "Lost Customers"
            else:
                segment_map[cid] = "Hibernating"

        df["segment_name"] = df["cluster_id"].map(segment_map)
        return df

    def run_and_persist_segmentation(self, n_clusters: int = 5) -> Dict[str, Any]:
        """Compute RFM, run KMeans, and save to customer_segments table."""
        rfm_df = self.compute_rfm_metrics()
        if rfm_df.empty:
            return {"status": "NO_DATA", "records": 0}

        segmented_df = self.perform_kmeans_clustering(rfm_df, n_clusters=n_clusters)
        
        # Delete existing segments
        self.session.query(CustomerSegment).delete()
        self.session.commit()

        records = []
        for _, row in segmented_df.iterrows():
            records.append(CustomerSegment(
                customer_id=str(row["customer_id"]),
                recency_days=int(row["recency_days"]),
                frequency=int(row["frequency"]),
                monetary=float(row["monetary"]),
                r_score=int(row["r_score"]),
                f_score=int(row["f_score"]),
                m_score=int(row["m_score"]),
                cluster_id=int(row["cluster_id"]),
                segment_name=str(row["segment_name"]),
                avg_order_value=float(row["avg_order_value"]),
                lifetime_revenue=float(row["lifetime_revenue"]),
                last_calculated_at=datetime.utcnow()
            ))

        self.session.bulk_save_objects(records)
        self.session.commit()
        logger.info(f"Saved {len(records)} customer segments to database.")

        # Summary statistics
        segment_summary = segmented_df["segment_name"].value_counts().to_dict()
        return {
            "total_customers_segmented": len(records),
            "segment_distribution": segment_summary,
            "avg_recency": round(float(segmented_df["recency_days"].mean()), 1),
            "avg_frequency": round(float(segmented_df["frequency"].mean()), 1),
            "avg_monetary": round(float(segmented_df["monetary"].mean()), 2)
        }
