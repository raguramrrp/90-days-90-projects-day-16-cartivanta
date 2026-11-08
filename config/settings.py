"""
CARTIVANTA - Configuration and Environment Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv(BASE_DIR / "config" / "settings.example.env")

APP_NAME = os.getenv("APP_NAME", "CARTIVANTA")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Database Engine Selection
DB_ENGINE = os.getenv("DB_ENGINE", "postgresql").lower()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "cartivanta_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# SQLite fallback
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "data" / "cartivanta.db")))

def get_db_url(force_sqlite: bool = False) -> str:
    """Return appropriate database connection string."""
    if not force_sqlite and DB_ENGINE == "postgresql":
        # Check if password is provided
        pw_str = f":{DB_PASSWORD}" if DB_PASSWORD else ""
        return f"postgresql+psycopg2://{DB_USER}{pw_str}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{SQLITE_DB_PATH}"

# Paths
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
SAMPLES_DATA_DIR = DATA_DIR / "samples"
REPORTS_DIR = BASE_DIR / "reports"
DOCS_DIR = BASE_DIR / "docs"

# Core Analytics Parameters
DATASET_CURRENCY = os.getenv("DATASET_CURRENCY", "GBP")
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "50000"))
