"""
CARTIVANTA - ETL Extract Module
Handles unzipping, inspecting, chunked reading, and sample extraction for UCI Online Retail II.
Supports both .xlsx (original Excel sheets Year 2009-2010 & Year 2010-2011) and exported .csv.
"""
import zipfile
import logging
from pathlib import Path
from typing import Generator, Optional, Tuple, List
import pandas as pd
from config.settings import RAW_DATA_DIR, SAMPLES_DATA_DIR, CHUNK_SIZE

logger = logging.getLogger("cartivanta.etl.extract")

def extract_archive(zip_path: Optional[Path] = None, extract_to: Optional[Path] = None) -> List[Path]:
    """Unzip the raw dataset archive preserving source files."""
    if zip_path is None:
        zip_path = RAW_DATA_DIR / "online_retail_ii.zip"
    if extract_to is None:
        extract_to = RAW_DATA_DIR

    if not zip_path.exists():
        raise FileNotFoundError(f"Source archive not found at {zip_path}")

    logger.info(f"Extracting archive {zip_path.name} to {extract_to}...")
    extracted_files = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for file_info in zf.infolist():
            target_path = extract_to / file_info.filename
            if not target_path.exists():
                zf.extract(file_info, extract_to)
                logger.info(f"Extracted: {file_info.filename} ({file_info.file_size / (1024*1024):.2f} MB)")
            extracted_files.append(target_path)
    return extracted_files

def locate_source_file() -> Path:
    """Find the primary Excel or CSV dataset file in RAW_DATA_DIR."""
    candidates = list(RAW_DATA_DIR.glob("*.xlsx")) + list(RAW_DATA_DIR.glob("*.csv"))
    # Filter out temp/partial files
    valid_candidates = [f for f in candidates if not f.name.startswith("~$") and f.is_file()]
    if not valid_candidates:
        # Check if zip exists and extract
        zip_path = RAW_DATA_DIR / "online_retail_ii.zip"
        if zip_path.exists():
            extract_archive(zip_path, RAW_DATA_DIR)
            valid_candidates = [f for f in list(RAW_DATA_DIR.glob("*.xlsx")) + list(RAW_DATA_DIR.glob("*.csv")) if not f.name.startswith("~$")]
    if not valid_candidates:
        raise FileNotFoundError(f"No valid .xlsx or .csv dataset found in {RAW_DATA_DIR}")
    # Prioritize CSV if already converted or largest xlsx
    csv_candidates = [f for f in valid_candidates if f.suffix.lower() == ".csv"]
    if csv_candidates:
        return csv_candidates[0]
    return sorted(valid_candidates, key=lambda f: f.stat().st_size, reverse=True)[0]

def convert_excel_to_csv_if_needed(excel_path: Path, output_csv_path: Optional[Path] = None) -> Path:
    """
    Online Retail II Excel contains two sheets: 'Year 2009-2010' and 'Year 2010-2011'.
    Converts both sheets into a single unified CSV for ultra-fast chunk-based loading.
    """
    if output_csv_path is None:
        output_csv_path = RAW_DATA_DIR / "online_retail_ii_unified.csv"

    if output_csv_path.exists() and output_csv_path.stat().st_size > 1000000:
        logger.info(f"Unified CSV already exists: {output_csv_path.name} ({output_csv_path.stat().st_size / (1024*1024):.2f} MB)")
        return output_csv_path

    logger.info(f"Reading Excel sheets from {excel_path.name} (this takes ~1-2 min for 1M rows)...")
    xl = pd.ExcelFile(excel_path)
    sheet_dfs = []
    for sheet_name in xl.sheet_names:
        logger.info(f"Loading sheet: {sheet_name}...")
        df_sheet = pd.read_excel(xl, sheet_name=sheet_name)
        logger.info(f"Loaded {len(df_sheet):,} rows from sheet '{sheet_name}'")
        sheet_dfs.append(df_sheet)

    unified_df = pd.concat(sheet_dfs, ignore_index=True)
    logger.info(f"Writing unified dataset ({len(unified_df):,} rows) to {output_csv_path.name}...")
    unified_df.to_csv(output_csv_path, index=False)
    logger.info("CSV conversion complete.")
    return output_csv_path

def read_raw_chunks(chunk_size: int = CHUNK_SIZE) -> Generator[pd.DataFrame, None, None]:
    """Stream raw dataset in chunks."""
    source_file = locate_source_file()
    if source_file.suffix.lower() == ".xlsx":
        source_file = convert_excel_to_csv_if_needed(source_file)

    logger.info(f"Streaming data in chunks of {chunk_size:,} from {source_file.name}...")
    for chunk in pd.read_csv(source_file, chunksize=chunk_size, low_memory=False):
        yield chunk

def generate_sample_dataset(sample_size: int = 15000) -> Path:
    """Generate a lightweight sample dataset for instant local testing and demonstration."""
    sample_path = SAMPLES_DATA_DIR / "online_retail_sample.csv"
    if sample_path.exists() and sample_path.stat().st_size > 10000:
        return sample_path

    SAMPLES_DATA_DIR.mkdir(parents=True, exist_ok=True)
    source_file = locate_source_file()
    if source_file.suffix.lower() == ".xlsx":
        source_file = convert_excel_to_csv_if_needed(source_file)

    logger.info(f"Creating sample dataset of {sample_size:,} rows from {source_file.name}...")
    df = pd.read_csv(source_file, nrows=sample_size, low_memory=False)
    df.to_csv(sample_path, index=False)
    logger.info(f"Sample dataset saved to {sample_path}")
    return sample_path
