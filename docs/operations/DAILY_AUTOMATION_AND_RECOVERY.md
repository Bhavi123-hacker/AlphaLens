# AlphaLens Daily Automation, Scheduling and Recovery Runbook

This document describes the unattended daily market data collection, prospective model inference, and fault recovery architecture on Windows 11 host `BHAVY17`.

---

## 1. Production Scheduler Configuration

AlphaLens operates unattended daily pipelines via the native Windows Task Scheduler. The task configuration is cryptographically signed and protected from unapproved edits.

| Parameter | Operational Setting | Rationale & Constraint |
| :--- | :--- | :--- |
| **Task Name** | `AlphaLens Daily Market Ingestion` | Registered in Windows Task Scheduler under `\AlphaLens` |
| **Execution Windows** | **20:30, 21:30, 22:30 IST** | Aligned with post-market vendor settlement bar publication |
| **Batch Size** | **250 stocks / run** | Splits the 500-stock cohort into two 250-stock batches |
| **Per-Run Request Budget** | **600 GET requests** | 250 primary requests + up to 350 retry/backfill requests |
| **Daily Reservation Budget**| **1,800 GET requests** | Strict internal research limit across all runs (D95/D97/D100) |
| **Inter-Run Cooldown** | **60 minutes** | Prevents rapid API bursts and allows upstream vendor replication |
| **Execution Timeout** | **30 minutes (`PT30M`)** | Windows watchdog automatically halts hung worker processes |
| **NTP Clock Guard** | **`MAX_WIDTH <= 100 ms`** | Prevents time-skew attacks and lookahead entry errors |

---

## 2. Process Architecture & Watchdog Lifecycle

```
[ Windows Task Scheduler ] (20:30 / 21:30 / 22:30 IST)
           │
           ▼ Spawns
[ Supervised Launcher ] (scripts.windows.supervised_launcher)
           │
           ├─ 1. Preflight Validation:
           │     - Pinned Python runtime check
           │     - Pinned config & credential verification
           │     - NTP date proof (MAX_WIDTH <= 100 ms)
           │     - Rate budget verification (<= 1,800 attempts today)
           │
           ├─ 2. Worker Spawning:
           │     - Spawns worker process (workers.nse_market.engine)
           │     - Streams diagnostic receipts to `.local-data/daily/runs/<id>/`
           │     - Supervises 30-minute hard execution limit
           │
           ├─ 3. Terminal Reconciler:
           │     - Validates worker exit code (0 = SUCCESS)
           │     - Atomic publication pointer update (`market-view-latest.json`)
           │     - Prospective forecast ledger append
           │
           ▼ Clean Termination
[ Exit Code 0 Recorded in Windows Event Log ]
```

### Windows Status Code Clarification
- **`0x00041301` (`267009`)**: Indicates the task is **currently running** in the background. It is **not** an error or termination code.
- **`0x00041306`**: Indicates the task was terminated by the operator or timeout watchdog.
- **`0x00000000` (`0`)**: Indicates successful completion.

---

## 3. Fault Recovery & Idempotent Resumes

AlphaLens pipelines are designed to survive unexpected machine reboots, network drops, and process termination:

1. **Idempotent Storage**:
   - Every candle is uniquely indexed by `(instrument_key, session_date)`.
   - Re-running an interrupted batch never creates duplicate rows or shifts historical values.
2. **Checkpoint-Based Ingestion**:
   - Checkpoint receipts are committed to disk after every 25 stocks.
   - If a batch is interrupted at stock 180, the subsequent recovery run resumes from stock 181 without re-querying completed items.
3. **Vendor Lag vs Defect Discrimination**:
   - If a provider returns no candle for an active session, the engine distinguishes between upstream vendor publication delay (`VENDOR_SESSION_PENDING`) and code/transport errors (`COLLECTOR_NETWORK_ERROR`).
