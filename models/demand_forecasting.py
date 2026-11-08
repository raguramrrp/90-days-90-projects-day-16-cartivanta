"""
CARTIVANTA - Demand Forecasting Pipeline (Module 05)
Implements chronological train-test splits, feature engineering (lags, rolling stats, calendar harmonics),
trains both Seasonal Naive baseline and RandomForestRegressor, evaluates via MAE, RMSE, WAPE,
and persists 30-day demand predictions into PostgreSQL/SQLite.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import get_session
from database.models import DemandForecast

logger = logging.getLogger("cartivanta.forecasting")

def calculate_wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Weighted Absolute Percentage Error: sum(|y - y_hat|) / sum(y)."""
    sum_actual = np.sum(actual)
    if sum_actual == 0:
        return 0.0
    return float(np.sum(np.abs(actual - predicted)) / sum_actual * 100)

class DemandForecastingEngine:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    def get_top_eligible_products(self, limit: int = 5) -> List[str]:
        """Identify top products with sufficient continuous transaction history."""
        query = text("""
            SELECT
                oi.stock_code,
                COUNT(DISTINCT DATE(o.invoice_date)) AS active_days,
                SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS total_units
            FROM order_items oi
            JOIN orders o ON oi.invoice_no = o.invoice_no
            WHERE oi.quantity > 0 AND oi.stock_code NOT IN ('POST', 'M', 'D')
            GROUP BY oi.stock_code
            HAVING COUNT(DISTINCT DATE(o.invoice_date)) >= 10
            ORDER BY total_units DESC
            LIMIT :limit
        """)
        rows = self.session.execute(query, {"limit": limit}).mappings().all()
        return [r["stock_code"] for r in rows]

    def build_product_daily_series(self, stock_code: str) -> pd.DataFrame:
        """Extract and reindex daily demand series for a product."""
        query = text("""
            SELECT
                DATE(o.invoice_date) AS date,
                SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS demand
            FROM order_items oi
            JOIN orders o ON oi.invoice_no = o.invoice_no
            WHERE oi.stock_code = :stock_code
            GROUP BY DATE(o.invoice_date)
            ORDER BY date ASC
        """)
        rows = self.session.execute(query, {"stock_code": stock_code}).mappings().all()
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        
        # Fill missing calendar days with zero demand (essential for true retail velocity)
        full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
        df = df.reindex(full_idx, fill_value=0).reset_index().rename(columns={"index": "date"})
        df["demand"] = df["demand"].astype(float)
        return df

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer lag features, rolling averages, and calendar variables without lookahead leakage."""
        data = df.copy()
        # Lag features with fallback for shorter series
        data["lag_1"] = data["demand"].shift(1)
        data["lag_7"] = data["demand"].shift(7).bfill()
        data["lag_14"] = data["demand"].shift(14).bfill()
        data["lag_28"] = data["demand"].shift(28).bfill()

        # Rolling statistics (using closed='left' equivalent via shift to prevent leakage)
        data["rolling_mean_7"] = data["demand"].shift(1).rolling(window=7, min_periods=1).mean()
        data["rolling_mean_14"] = data["demand"].shift(1).rolling(window=14, min_periods=1).mean()
        data["rolling_std_7"] = data["demand"].shift(1).rolling(window=7, min_periods=1).std().fillna(0)

        # Calendar features
        data["day_of_week"] = data["date"].dt.dayofweek
        data["is_weekend"] = data["day_of_week"].isin([5, 6]).astype(int)
        data["month"] = data["date"].dt.month
        data["week_of_year"] = data["date"].dt.isocalendar().week.astype(int)

        # Drop only the first row where lag_1 is NaN
        data = data.dropna(subset=["lag_1"]).reset_index(drop=True)
        return data

    def train_and_evaluate_models(self, stock_code: str, test_days: int = 30) -> Dict[str, Any]:
        """
        Perform chronological train/test split.
        Compare Seasonal Naive baseline against RandomForestRegressor.
        """
        daily_df = self.build_product_daily_series(stock_code)
        if len(daily_df) < 15:
            return {"status": "INSUFFICIENT_DATA", "stock_code": stock_code}

        feat_df = self.create_features(daily_df)
        effective_test_days = min(test_days, max(3, len(feat_df) // 5))
        if len(feat_df) <= effective_test_days:
            return {"status": "INSUFFICIENT_FEATURE_ROWS", "stock_code": stock_code}

        # Chronological Split
        train_df = feat_df.iloc[:-effective_test_days].copy()
        test_df = feat_df.iloc[-effective_test_days:].copy()

        feature_cols = [
            "lag_1", "lag_7", "lag_14", "lag_28", 
            "rolling_mean_7", "rolling_mean_14", "rolling_std_7",
            "day_of_week", "is_weekend", "month", "week_of_year"
        ]

        X_train, y_train = train_df[feature_cols], train_df["demand"].values
        X_test, y_test = test_df[feature_cols], test_df["demand"].values

        # 1. Baseline: Seasonal Naive (7-day seasonal lag)
        naive_preds = test_df["lag_7"].values
        naive_mae = float(mean_absolute_error(y_test, naive_preds))
        naive_rmse = float(np.sqrt(mean_squared_error(y_test, naive_preds)))
        naive_wape = float(calculate_wape(y_test, naive_preds))

        # 2. Machine Learning: RandomForestRegressor
        rf = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        rf_preds = np.maximum(0, rf.predict(X_test))

        rf_mae = float(mean_absolute_error(y_test, rf_preds))
        rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_preds)))
        rf_wape = float(calculate_wape(y_test, rf_preds))

        # Select best model based on WAPE
        best_model_name = "RandomForestRegressor" if rf_wape <= naive_wape else "SeasonalNaive"

        return {
            "status": "SUCCESS",
            "stock_code": stock_code,
            "training_samples": len(train_df),
            "test_samples": len(test_df),
            "models": {
                "SeasonalNaive": {
                    "mae": round(naive_mae, 2),
                    "rmse": round(naive_rmse, 2),
                    "wape": round(naive_wape, 2)
                },
                "RandomForestRegressor": {
                    "mae": round(rf_mae, 2),
                    "rmse": round(rf_rmse, 2),
                    "wape": round(rf_wape, 2)
                }
            },
            "best_model": best_model_name,
            "fitted_model": rf,
            "feature_cols": feature_cols,
            "latest_data": feat_df.iloc[-1:].copy()
        }

    def generate_30_day_forecast(self, stock_code: str, eval_res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate recursive forward 30-day forecast.
        """
        rf = eval_res["fitted_model"]
        feature_cols = eval_res["feature_cols"]
        latest_row = eval_res["latest_data"].copy()

        daily_df = self.build_product_daily_series(stock_code)
        demand_history = list(daily_df["demand"].values)
        last_date = daily_df["date"].max()

        metrics = eval_res["models"]["RandomForestRegressor"]
        forecast_rows = []

        for day in range(1, 31):
            target_date = last_date + timedelta(days=day)
            
            lag_1 = demand_history[-1]
            lag_7 = demand_history[-7] if len(demand_history) >= 7 else lag_1
            lag_14 = demand_history[-14] if len(demand_history) >= 14 else lag_1
            lag_28 = demand_history[-28] if len(demand_history) >= 28 else lag_1

            roll_7 = float(np.mean(demand_history[-7:]))
            roll_14 = float(np.mean(demand_history[-14:]))
            roll_std_7 = float(np.std(demand_history[-7:]))

            row_features = pd.DataFrame([{
                "lag_1": lag_1,
                "lag_7": lag_7,
                "lag_14": lag_14,
                "lag_28": lag_28,
                "rolling_mean_7": roll_7,
                "rolling_mean_14": roll_14,
                "rolling_std_7": roll_std_7,
                "day_of_week": target_date.dayofweek,
                "is_weekend": int(target_date.dayofweek in [5, 6]),
                "month": target_date.month,
                "week_of_year": target_date.isocalendar().week
            }])[feature_cols]

            pred_val = float(max(0, rf.predict(row_features)[0]))
            demand_history.append(pred_val)

            # 90% confidence bounds based on RMSE
            lower_bound = max(0.0, round(pred_val - 1.645 * metrics["rmse"], 2))
            upper_bound = round(pred_val + 1.645 * metrics["rmse"], 2)

            forecast_rows.append({
                "stock_code": stock_code,
                "forecast_date": target_date.date(),
                "model_name": "RandomForestRegressor",
                "predicted_demand": round(pred_val, 2),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "wape": metrics["wape"]
            })

        return forecast_rows

    def run_top_product_forecasts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Run full evaluation and persistence for top eligible products."""
        top_codes = self.get_top_eligible_products(limit=limit)
        logger.info(f"Forecasting demand for top {len(top_codes)} products: {top_codes}")

        all_results = []
        
        # Clean previous forecasts for these codes
        if top_codes:
            self.session.query(DemandForecast).filter(DemandForecast.stock_code.in_(top_codes)).delete(synchronize_session=False)
            self.session.commit()

        for code in top_codes:
            eval_res = self.train_and_evaluate_models(code)
            if eval_res.get("status") != "SUCCESS":
                continue

            predictions = self.generate_30_day_forecast(code, eval_res)
            
            db_objects = [
                DemandForecast(
                    stock_code=p["stock_code"],
                    forecast_date=p["forecast_date"],
                    model_name=p["model_name"],
                    predicted_demand=p["predicted_demand"],
                    lower_bound=p["lower_bound"],
                    upper_bound=p["upper_bound"],
                    mae=p["mae"],
                    rmse=p["rmse"],
                    wape=p["wape"]
                )
                for p in predictions
            ]
            self.session.bulk_save_objects(db_objects)
            self.session.commit()

            all_results.append({
                "stock_code": code,
                "best_model": eval_res["best_model"],
                "metrics": eval_res["models"],
                "forecast_days": len(predictions),
                "total_predicted_demand": round(sum(p["predicted_demand"] for p in predictions), 1)
            })

        logger.info(f"Successfully generated and saved demand forecasts for {len(all_results)} products.")
        return all_results
