# AlphaLens — Windows One-Click Operations Guide

**Repository:** `Bhavi123-hacker/AlphaLens`  
**Branch:** `alphalens-master-completion`  
**Platform URL:** `http://127.0.0.1:8041/nse-market`  
**Environment:** Windows 11, Python 3.12.4  

---

## 1. Quick Start Guide

AlphaLens provides two primary, idempotent Windows batch scripts located in the root directory:

```
alphalens/
├── start_alphalens.bat        <-- One-click platform launcher (API & Dashboard)
└── run_daily_pipeline.bat     <-- One-click daily research & settlement orchestrator
```

### 1.1 Launching the Platform

To start the API service and launch your default web browser to the interactive dashboard, simply double-click `start_alphalens.bat` or run from PowerShell / Command Prompt:

```cmd
start_alphalens.bat
```

**What it does automatically:**
1. Detects the repository root and locates the Python virtual environment (`.local-data\completion-runtime\venv` or `.venv`).
2. Confirms Python $\ge 3.11$ and all required quantitative and ML packages (`fastapi`, `uvicorn`, `scikit-learn`, `joblib`, `numpy`).
3. Runs read-only database integrity checks on PostgreSQL and the SQLite catalog.
4. Checks whether the server daemon is already listening on port 8041.
   - If **already running**: Reuses the existing instance without spawning duplicate processes.
   - If **stopped**: Spawns the background server daemon and polls the health endpoint (`/api/v1/health/live`) until healthy.
5. Launches your default web browser directly to `http://127.0.0.1:8041/nse-market`.

**CLI Flags:**
- `--no-browser`: Start the server without opening the web browser.
- `--timeout SECONDS`: Override startup health timeout (default: 25s).
- `--config PATH`: Provide custom sealed config JSON path.

---

### 1.2 Running the Daily Research & Settlement Pipeline

To run the complete end-to-end daily market processing cycle after NSE market close (recommended post 16:00 IST), run:

```cmd
run_daily_pipeline.bat
```

**CLI Flags:**
- `--session YYYY-MM-DD`: Target a specific historical trading session (defaults to today's date in IST).
- `--dry-run`: Execute the pipeline and simulate settlement without committing database mutations.
- `--force-holiday-run`: Force pipeline execution even if the calendar classifies the date as an exchange holiday.

---

## 2. The 15 Daily Pipeline Stages

When you run `run_daily_pipeline.bat`, the orchestrator executes the following 15 stages in strict dependency order:

| Stage | Operation | Verification & Action | Failure Behavior |
| :---: | :--- | :--- | :--- |
| **01** | **Database & Storage Reserve** | Verifies PostgreSQL connectivity and ensures drive free space $\ge 8.0\text{ GiB}$. | **Fails Fast**: Aborts immediately if storage $< 8.0\text{ GiB}$. |
| **02** | **Market Session & Calendar** | Validates session against authentic NSE trading calendar (`trading_calendar.py`). | **Safe Skip**: If holiday or weekend, exits with code 0 (no wasted computation). |
| **03** | **Collect EOD Market Data** | Ingests or verifies authentic 500-equity EOD candle view from approved provider. | **Fails Fast**: Never synthesizes or fabricates missing data. |
| **04** | **Validate Collection Receipts** | Verifies provider receipt hashes and SHA-256 checksums (`daily_receipt_status`). | Validates audit trail integrity. |
| **05** | **Candle Completeness & Provenance** | Checks 500 equities for valid OHLCV invariants ($0 < \text{Low} \le \text{Open}, \text{Close} \le \text{High}, \text{Vol} \ge 0$). | Rejects corrupt or truncated candle payloads. |
| **06** | **Technical & Candlestick Signals** | Computes 11 candlestick patterns, EMA/SMA, RSI, MACD, ADX, Supertrend, ATR, OBV, Support/Resistance zones. | Generates quantitative technical score ($0-100$). |
| **07** | **20 ML Model Inferences** | Executes batch predictions across all 20 trained models across 4 horizons ($H_1, H_5, H_{10}, H_{20}$). | Verifies models are loaded from `data/models/*.joblib`. |
| **08** | **Candidate Rankings** | Ranks equities by predicted expected alpha, win probability, and technical alignment. | Generates prospective candidates. |
| **09** | **Top-5, Top-10, Top-20 Lists** | Sorts and filters candidate cohorts for active monitoring and execution. | Outputs ranked candidate structures. |
| **10** | **Entry, Stop, Target & R/R** | Generates dynamic volatility-based Trade Plans with stop loss, Target 1, Target 2, and R/R ratio. | Enforces minimum Risk/Reward $\ge 1.5$. |
| **11** | **Order-Level Transaction Costs** | Applies Indian equity delivery tariff model: Brokerage ($\le ₹20$), STT (0.1%), turnover charges, GST, and DP charges ($₹15.93$). | Deducts exact ticket frictions ($₹10\text{k}$ to $₹5\text{L}$). |
| **12** | **Settle Matured Forecasts** | Matches historical forecasts against actual subsequent closing prices at exact exchange-session horizons. | Records realized gross and net performance. |
| **13** | **Preserve 601 Quarantine** | Verifies SHA-256 of `matured_outcomes_ledger.db` and enforces **0** acceptance credit. | Quarantined legacy records never leak into model gates. |
| **14** | **Record Prospective Predictions** | Records new qualified forecasts for future forward maturation. | Gated for independent prospective walk-forward tracking. |
| **15** | **Generate Daily Completion Report** | Writes complete JSON execution artifact with per-stage timing and metrics. | Saved to `docs/operations/daily_pipeline_runs/pipeline_report_{session}.json`. |

---

## 3. Concurrency Protection & Locking

To prevent race conditions, corrupted settlements, or multiple overlapping instances:
- Both scripts enforce process-level mutual exclusion using `D:\al-research\p28-worktree\.local-data\daily_pipeline.lock`.
- If an instance is already running, subsequent invocations immediately abort with exit code `3` (`DUPLICATE_RUN_DETECTED`).
- If an existing process crashed, the orchestrator detects the stale PID and automatically cleans up the lock.

---

## 4. Log Locations & Audit Artifacts

All logs and receipts are written to the high-capacity D-drive research paths:

- **Startup Daemon Logs**: `D:\al-research\p28-worktree\.local-data\alphalens_startup.log`
- **Daily Pipeline Reports**: `docs/operations/daily_pipeline_runs/pipeline_report_{session}.json`
- **Settlement Receipts**: `docs/ml/daily_settlement_receipt_{session}.json`
- **Multi-Model Predictions**: `docs/ml/multi_model_execution_results.json`
- **Quarantine Outcome Ledger**: `data/forecasts/matured_outcomes_ledger.db`

---

## 5. Failure Recovery & Safe Retry Instructions

AlphaLens operations are built with **strict restart-safety and idempotency**:

1. **If a pipeline stage fails:**
   - Review the console error or the generated `pipeline_report_{session}.json`.
   - Resolve the underlying issue (e.g. freeing disk space if drive fell below 8 GiB).
   - Re-run `run_daily_pipeline.bat --session {session}`.
   - The pipeline will safely re-evaluate the stages without duplicating settlement records or fabricating data.

2. **Distinguishing Software Success from Market-Data Success:**
   - **Software Success**: The Python runtime, model artifacts, and database connectors pass all verification checks.
   - **Market-Data Success**: Authentic EOD candles are published by the exchange. If the market is closed or on holiday, Stage 2 will report `SKIPPED_HOLIDAY`, which is an operational success (exit code 0), but correctly indicates no new market trades occurred.
