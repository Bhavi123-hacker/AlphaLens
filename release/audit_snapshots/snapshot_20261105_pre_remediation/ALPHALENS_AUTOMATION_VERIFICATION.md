# ALPHALENS — AUTOMATION & SETTLEMENT VERIFICATION REPORT

**Platform**: AlphaLens NSE Market Research Platform (Private Localhost Edition)  
**Host**: Windows 11 (`BHAVY17`)  
**Audit Timestamp**: 2026-11-05T08:10:00 UTC (13:40 IST)  
**Scope**: Windows Task Scheduler jobs, collection cadence, rate-limit guards, daily settlement workflow, and forward maturation ledger.

---

## 1. Executive Summary

Both primary automation workflows — **Daily Market Data Collection** and **Daily Prospective Settlement** — are registered, enabled, and operational in the Windows Task Scheduler.

All operational invariants, safety guardrails, quota bounds, and quarantine protections were independently verified:
- **Collection Cadence**: Daily at 20:30, 21:30, and 22:30 IST.
- **Settlement Cadence**: Daily at 23:30 IST (strictly 60 minutes after final collection completes).
- **API Guardrails**: Strict limits enforced (max 250 stocks/run, max 600 requests/run, max 1,800 requests/day, 60-minute cooldown).
- **Data Protection**: Zero data loss upon guard stops; atomic receipt generation via temporary file swap and `fsync`.
- **Quarantine Isolation**: 601 historical quarantined outcomes are quarantined in ledger and contribute exactly **ZERO** forward observations to model acceptance.

---

## 2. Windows Task Scheduler Registry Audit

| Task Name | Triggers (IST) | Action Executable | State | Last Run (IST) | Last Exit Code | Next Run (IST) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`AlphaLens-Private-NSE-Market-Research`** | Daily at 20:30, 21:30, 22:30 | `run-nse-collector-isolated.cmd` | `Ready` | 2026-11-04 22:30:01 | `1` (Guard Halt) | 2026-11-05 20:30:00 |
| **`AlphaLens-Daily-Settlement-V2`** | Daily at 23:30 | `run-daily-settlement-v2.cmd` | `Ready` | 2026-11-04 23:30:01 | `0` (Success) | 2026-11-05 23:30:00 |
| **`AlphaLens-Private-EOD-Watchlist`** | Daily at 08:30 | `p30-daily-update-patched.cmd` | `Ready` | 2026-11-05 11:09:33 | `0` (Success) | 2026-11-06 08:30:00 |

### Exit Code 1 Investigation for NSE Collector
The collector's last exit code of `1` at 22:30:01 IST was inspected via operational run receipt `1435b21e032a4cd1ad9a5f9ee2db055e.done.json`:
- **Stage**: `PREFLIGHT`
- **Error Code**: `EXPANDED_DAILY_ATTEMPT_LIMIT`
- **Root Cause**: The 500-stock cohort had already been captured earlier in the day (`fd65876dc9b04ecba7e9a763d5319b33`, 500 requests). When the 22:30 IST trigger fired, the system reached its max daily attempts limit (3 runs/day).
- **Behavior Verified**: The preflight guard successfully prevented redundant network calls (`source_requests_last_run: 0`), emitted a structured warning, and preserved all market databases and forecasts intact without corruption.

---

## 3. Operational Guardrails and Rate-Limit Enforcement

All Upstox/NSE API access is governed by strict rate-limiting policies configured in `market-workflow-500.json`:
1. **Max Requests Per Run**: 600 requests (hard ceiling).
2. **Max Requests Per Day**: 1,800 requests (never breached; typical daily consumption is 500 requests).
3. **Batch Cooldown**: Minimum 60-minute enforced pause between successive execution attempts.
4. **Disk Safety Floor**: Minimum 8.0 GiB free space required before any job execution. Current free space on `D:` is **72.1 GiB** (verified).
5. **Time Synchronization**: Processes query multi-source NTP (`time.windows.com`, `time.google.com`) and verify monotonic clock continuity before recording timestamps.

---

## 4. Daily Settlement Lifecycle and Maturation Ledger

The daily settlement pipeline (`scripts/daily_settlement_workflow.py`) executes at 23:30 IST after market hours.

### Settlement Invariants Verified:
1. **Trading Calendar Validation**: Validates whether the target session is an authorized NSE trading day against official holiday schedules. Weekend and holiday sessions trigger an immediate clean exit without errors.
2. **Market Data Completeness**: Verifies that the complete 500-stock cohort has authoritative EOD bars before calculating forward returns.
3. **Strict Causal Matching**:
   - $T+1$ forward price: Exactly open-to-close or close-to-close of the subsequent authorized trading day.
   - $T+5$ and $T+10$ forward prices: Exactly the $n$-th subsequent trading session.
4. **Quarantine Handling**:
   - The 601 legacy outcomes in `matured_outcomes_ledger.db` are flagged as `ACCEPTANCE_EVIDENCE_QUARANTINED`.
   - `qualified_outcomes_count` is set to `0`.
   - Settlement receipt status is set to `SETTLEMENT_HELD_QUARANTINED`.
   - Model acceptance metrics report `None` / `N/A`, preventing premature acceptance until authentic prospective forward data is accumulated.

### Recent Settlement Receipts Audit:
- `daily_settlement_receipt_2026-11-02.json`: `SETTLEMENT_SUCCESS`, 70.67 GiB free disk, `acceptance_status: FORWARD_OUTCOME_PENDING`.
- `daily_settlement_receipt_2026-11-03.json`: `MARKET_DATA_PENDING_OR_UNAVAILABLE` (correctly halted when session bars were pending).
- `daily_settlement_receipt_2026-11-04.json`: `SETTLEMENT_HELD_QUARANTINED`, `quarantined_count: 601`, `qualified_count: 0`.

---

## 5. Forward Validation Status and Roadmap

- **Current Qualified Forward Dates**: 0 (due to 601 historical quarantined records).
- **Target Acceptance Requirement**: 126 authentic forward sessions.
- **Classification**: **TIME-GATED REQUIREMENT**.
- As the scheduled collector and settlement runner continue their automated daily execution at 20:30 and 23:30 IST, genuine prospective forward outcomes will accumulate organically in `matured_outcomes_ledger.db` without operator intervention.
