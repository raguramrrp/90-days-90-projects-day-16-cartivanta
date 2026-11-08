# CARTIVANTA — System Architecture & Data Model

> **Enterprise Data Platform Architecture for High-Volume Retail Analytics**

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph INGESTION["1. Data Ingestion & Extraction"]
        RawExcel["UCI Online Retail II (.xlsx / .csv)<br/>1,067,371 Raw Records"]
        ChunkETL["Chunk-Based Vectorized ETL Ingestion"]
        RawExcel --> ChunkETL
    end

    subgraph CLEANSING["2. Transformation & Quality Engine"]
        Dedup["Deduplication (34,335 rows removed)"]
        Valid["Price & Quantity Validation"]
        Cancel["Cancellation & Return Isolation"]
        Impute["Guest Customer ID Imputation"]
        Audit["5-Dimensional Data Quality Audit (Score: 80.9/100)"]
        
        ChunkETL --> Dedup
        Dedup --> Valid
        Valid --> Cancel
        Cancel --> Impute
        Impute --> Audit
    end

    subgraph WAREHOUSE["3. Resilient Dual-Engine Warehouse"]
        DualConn["Resilient SQLAlchemy Dual-Engine"]
        Postgres["Primary: PostgreSQL 18 Warehouse"]
        SQLite["Fallback: Local SQLite WAL Engine"]
        
        Audit --> DualConn
        DualConn --> Postgres
        DualConn --> SQLite
    end

    subgraph ANALYTICS_ML["4. Analytics & ML Core Engines"]
        SalesEng["Sales & Margin Analytics Engine"]
        RFMEng["Customer RFM & K-Means Clustering"]
        InvEng["Inventory Health & Stockout Predictor"]
        DemandEng["Demand Forecasting (RF vs Seasonal Naive)"]
        FestiveSim["Diwali & Festive Discount Simulator"]
        ActionRules["Business Recommendation Rules Engine"]
        
        DualConn --> SalesEng
        DualConn --> RFMEng
        DualConn --> InvEng
        DualConn --> DemandEng
        DualConn --> FestiveSim
        DualConn --> ActionRules
    end

    subgraph PRESENTATION["5. Delivery & User Interfaces"]
        FastAPIApp["FastAPI REST & Analytics Engine"]
        WebDashboard["Interactive Analytics Web Workstation"]
        PowerBIReport["Power BI Desktop (Star Schema & DAX)"]
        ExportReports["Automated High-Resolution Visual Reports"]
        
        SalesEng --> FastAPIApp
        RFMEng --> FastAPIApp
        InvEng --> FastAPIApp
        DemandEng --> FastAPIApp
        FestiveSim --> FastAPIApp
        ActionRules --> FastAPIApp
        
        FastAPIApp --> WebDashboard
        DualConn --> PowerBIReport
        SalesEng --> ExportReports
    end
```

---

## 2. Pipeline Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Analyst / Operator
    participant Pipeline as etl.pipeline
    participant Clean as etl.transform
    participant Synth as etl.generate_synthetic
    participant DB as Warehouse (PostgreSQL / SQLite)
    participant ML as ML & Analytics Engines
    participant UI as Web & Power BI

    User->>Pipeline: Execute run_pipeline()
    Pipeline->>Clean: Ingest 1,067,371 raw transaction rows
    Clean->>Clean: Filter invalid rows, flag cancellations & returns
    Clean-->>Pipeline: Return 1,029,247 cleaned records
    Pipeline->>Synth: Generate deterministic costs & inventory (seed 42)
    Synth-->>Pipeline: Return product_costs & inventory_snapshot
    Pipeline->>DB: Ingest normalized entities (orders, order_items, products)
    DB-->>Pipeline: Commit transaction tables
    Pipeline->>ML: Run CustomerSegmentationEngine (RFM + K-Means)
    ML->>DB: Persist customer_segments
    Pipeline->>ML: Run DemandForecastingEngine (Top SKUs)
    ML->>DB: Persist demand_forecasts
    Pipeline->>ML: Run BusinessRecommendationEngine
    ML->>DB: Persist business_alerts
    Pipeline-->>User: Pipeline Complete (Execution summary & metrics)
    User->>UI: Launch web workstation / Open Power BI
    UI->>DB: Query analytical views (vw_executive_kpis, etc.)
    DB-->>UI: Return aggregated insights
```

---

## 3. Relational Schema & Entity-Relationship Model

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    CUSTOMERS ||--o{ CUSTOMER_SEGMENTS : categorized_as
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : sold_in
    PRODUCTS ||--|| PRODUCT_COSTS : has_cost
    PRODUCTS ||--|| INVENTORY_SNAPSHOT : has_stock
    PRODUCTS ||--o{ DEMAND_FORECASTS : forecasted_for
    PRODUCTS ||--o{ PROMOTION_TRANSACTIONS : discounted_in
    PROMOTION_CAMPAIGNS ||--o{ PROMOTION_TRANSACTIONS : includes
    PRODUCTS ||--o{ BUSINESS_ALERTS : targets

    CUSTOMERS {
        string customer_id PK
        string country
        string customer_type
        timestamp first_purchase_date
        timestamp last_purchase_date
        int total_orders
        float total_spend
    }

    ORDERS {
        string invoice_no PK
        string customer_id FK
        timestamp invoice_date
        string country
        boolean is_cancellation
        int total_items
        float gross_amount
        float return_amount
        float net_amount
    }

    ORDER_ITEMS {
        int id PK
        string invoice_no FK
        string stock_code FK
        string description
        int quantity
        float unit_price
        float line_total
        boolean is_return
        string category
    }

    PRODUCTS {
        string stock_code PK
        string description
        string category
        float unit_price
        int total_units_sold
        float total_revenue
    }

    PRODUCT_COSTS {
        string stock_code PK, FK
        float estimated_unit_cost
        string cost_category
        float estimated_gross_margin
        boolean is_synthetic
    }

    INVENTORY_SNAPSHOT {
        string stock_code PK, FK
        int available_stock
        int safety_stock
        int supplier_lead_time_days
        int target_stock
        float daily_demand_rate
        int reorder_point
        string stock_status
        boolean is_synthetic
    }

    CUSTOMER_SEGMENTS {
        string customer_id PK, FK
        int recency_days
        int frequency_orders
        float monetary_spend
        string segment_name
        int cluster_id
    }

    DEMAND_FORECASTS {
        int id PK
        string stock_code FK
        date forecast_date
        float predicted_demand
        float lower_bound
        float upper_bound
        string model_used
        float holdout_mae
        float holdout_rmse
        float holdout_wape
    }

    BUSINESS_ALERTS {
        int id PK
        string alert_type
        string severity
        string stock_code FK
        string customer_id FK
        string title
        string description
        string recommendation
        float potential_impact_gbp
    }
```

---

## 4. Analytical Views Layer

CARTIVANTA exposes 11 optimized database views to decouple analytics consumption from raw transactional schemas:

1. `vw_executive_kpis`: Reconciled high-level scorecards (Gross Sales, Net Revenue, COGS, Profit, Margins, AOV).
2. `vw_monthly_sales`: Aggregated monthly time-series of gross revenue, net revenue, returns, and order volumes.
3. `vw_product_performance`: Product ranking by volume, revenue, estimated margin, and return frequency.
4. `vw_customer_rfm`: Joined customer master with calculated RFM percentiles and K-Means segment labels.
5. `vw_inventory_health`: Combined stock on hand, daily velocity, reorder thresholds, and risk classifications.
6. `vw_profitability`: Category and product-level gross profit margin rankings and loss-leader detection.
7. `vw_forecast_results`: Machine learning demand forecasts merged with product metadata.
8. `vw_festival_performance`: Historical transaction trends intersecting with festival windows.
9. `vw_promotion_performance`: Marketing campaign discount depth, unit lift, and net ROI.
10. `vw_business_recommendations`: Filtered actionable recommendations sorted by potential financial impact.
11. `vw_data_quality`: Latest ETL data quality audit dimensions and scores.

---

## 5. Technology Stack Specifications

| Layer | Component | Version / Library | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.12 | Core execution environment |
| **Data Processing** | Pandas / NumPy | 3.1.1 / 2.5.4 | High-performance vectorized transformation & cleaning |
| **Relational ORM** | SQLAlchemy | 2.1.8 | Database abstraction layer with session pooling |
| **Primary Warehouse** | PostgreSQL | 18 | Production relational database engine |
| **Embedded Engine** | SQLite (WAL mode) | 3.x | Zero-configuration local database fallback |
| **Machine Learning** | Scikit-learn / SciPy | 1.9.1 / 1.18.1 | K-Means clustering, StandardScaler, RandomForestRegressor |
| **Web Server** | FastAPI / Uvicorn | 0.162.2 / 0.54.0 | High-performance asynchronous API & web interface |
| **Front-End Styling** | Tailwind CSS / ApexCharts | CDN | Editorial dashboard visualization workstation |
| **Reporting** | Power BI Desktop | Latest | Business intelligence semantic model, star schema, DAX |
| **Visualizer** | Matplotlib / Seaborn | 3.11.2 / 0.13.2 | Automated high-resolution report artifact generation |
| **Testing** | Pytest / Pytest-Cov | 9.2.0 / 7.1.0 | Unit, integration, and mathematical reconciliation tests |
