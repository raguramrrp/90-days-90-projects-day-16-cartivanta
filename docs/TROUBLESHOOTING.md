# CARTIVANTA — Troubleshooting & Diagnostics Guide

> **Common Issues, Workarounds & Diagnostic Procedures**

---

## 1. PostgreSQL Connection Failures (Socket / Permission Denied)

### Symptom
```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: Permission denied (0x0000271D/10013)
```

### Cause
In standard Windows non-administrator command sessions or sandboxed environments, opening local server sockets or accessing `NT AUTHORITY\NetworkService` resources is restricted by operating system security policies.

### Solution
**Zero action required!** CARTIVANTA includes an automatic dual-engine fallback in `database/connection.py`. When PostgreSQL is unreachable or blocked, the platform immediately redirects all reads, writes, and views to the embedded SQLite WAL engine at `data/cartivanta.db`. Both engines share identical schema DDL and view definitions.

If you have Windows administrative privileges and wish to run PostgreSQL 18 explicitly:
```cmd
net start postgresql-x64-18
```

---

## 2. Port 8000 Already in Use

### Symptom
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): only one usage of each socket address is normally permitted
```

### Cause
Another web application, background uvicorn task, or local dev server is listening on port 8000.

### Solution
Launch CARTIVANTA on an alternative port (such as 8080 or 8501):
```cmd
call .venv\Scripts\activate.bat
uvicorn web.app:app --host 127.0.0.1 --port 8080
```
Then open `http://127.0.0.1:8080` in your web browser.

---

## 3. Matplotlib Cache Directory Permission Warning

### Symptom
```
UserWarning: Matplotlib created a temporary cache directory at C:\Users\...\AppData\Local\Temp\matplotlib-... because there was an issue with the default path
```

### Cause
Windows user profile permissions prevent writing directly to `%USERPROFILE%\.matplotlib`.

### Solution
This is an informational warning that does not halt execution. To suppress it in your shell session, set:
```cmd
set MPLCONFIGDIR=%TEMP%\matplotlib
```

---

## 4. SQLite Database Locked (`sqlite3.OperationalError: database is locked`)

### Symptom
```
sqlite3.OperationalError: database is locked
```

### Cause
Multiple concurrent write processes attempting to access SQLite in traditional rollback journal mode.

### Solution
CARTIVANTA automatically configures SQLite in **Write-Ahead Logging (WAL)** mode upon initialization:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 30000;
```
This enables concurrent readers without blocking write operations. Ensure background ETL processes complete before running intensive bulk updates.

---

## 5. Slow Ingestion on First Run

### Symptom
Initial startup takes 60–90 seconds.

### Cause
The first run unzips `online_retail_ii.zip` and parses 1,067,371 rows across two Excel worksheets to create the flat CSV cache `data/raw/online_retail_ii_unified.csv`.

### Solution
Subsequent executions read the pre-built flat CSV cache in **0.83 seconds**. For rapid development or test cycles, run in sample mode:
```cmd
python -m etl.pipeline --sample --sample-size 25000 --sqlite
```
