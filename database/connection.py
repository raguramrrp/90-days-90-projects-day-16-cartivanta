"""
CARTIVANTA - Database Connection and Session Management
Supports PostgreSQL with transparent SQLite fallback for resilient local development and testing.
"""
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config.settings import get_db_url, DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logger = logging.getLogger("cartivanta.database")
Base = declarative_base()

_engine = None
_SessionFactory = None

def get_engine(force_sqlite: bool = False):
    """Obtain or initialize the SQLAlchemy engine."""
    global _engine, _SessionFactory
    if _engine is not None and not force_sqlite:
        return _engine

    url = get_db_url(force_sqlite=force_sqlite)
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    try:
        engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False
        )
        if "sqlite" in url:
            from sqlalchemy import event
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.close()

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database engine connected successfully using {url.split('@')[-1] if '@' in url else 'SQLite'}")
        _engine = engine
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine
    except Exception as exc:
        logger.warning(f"Failed to connect to primary engine ({url}): {exc}")
        if not force_sqlite and DB_ENGINE == "postgresql":
            logger.info("Falling back to local SQLite database engine for resilience.")
            return get_engine(force_sqlite=True)
        raise exc

def get_session(force_sqlite: bool = False) -> Session:
    """Provide a new SQLAlchemy session."""
    global _SessionFactory
    if _SessionFactory is None or force_sqlite:
        engine = get_engine(force_sqlite=force_sqlite)
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory()

def get_db() -> Generator[Session, None, None]:
    """Dependency helper for FastAPI endpoints."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()

def init_db(force_sqlite: bool = False):
    """Execute DDL statements to create database schema, indexes, and views."""
    from pathlib import Path
    import database.models  # Ensure all ORM models are registered
    base_dir = Path(__file__).resolve().parent.parent
    views_file = base_dir / "database" / "views.sql"

    engine = get_engine(force_sqlite=force_sqlite)
    is_sqlite = "sqlite" in str(engine.url)

    # 1. Create all ORM tables cleanly
    Base.metadata.create_all(engine)
    logger.info("Base ORM tables created.")

    # 2. Create Analytical Views
    if views_file.exists():
        with open(views_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # If SQLite, adjust specific postgres syntax
        if is_sqlite:
            # Replace TO_CHAR(col, 'YYYY-MM') with strftime('%Y-%m', col)
            content = content.replace("TO_CHAR(o.invoice_date, 'YYYY-MM')", "strftime('%Y-%m', o.invoice_date)")
            content = content.replace("EXTRACT(YEAR FROM o.invoice_date)", "CAST(strftime('%Y', o.invoice_date) AS INTEGER)")
            content = content.replace("EXTRACT(MONTH FROM o.invoice_date)", "CAST(strftime('%m', o.invoice_date) AS INTEGER)")
            content = content.replace("::NUMERIC", "")
            content = content.replace("CREATE OR REPLACE VIEW", "CREATE VIEW IF NOT EXISTS")

        with engine.begin() as conn:
            for stmt in content.split(";"):
                stmt_clean = stmt.strip()
                if stmt_clean:
                    try:
                        conn.execute(text(stmt_clean))
                    except Exception as e:
                        logger.debug(f"View creation note: {e}")

    logger.info("Database schema and views initialized successfully.")
