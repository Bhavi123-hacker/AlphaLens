# Daily automation — 24 October 2026

Audit branch: `alphalens-master-completion`; starting HEAD `da4382242371c17ebdf2cecc620541931b91e313`. These checks include the local candidate changes described below; final delivery commit belongs in the release report.

**Software: PARTIAL with verified offline safeguards. Live daily completion: BLOCKED_EVIDENCE.** Existing tasks remain registered and enabled under their original approval; this campaign changed neither task, launch path, recurring quota nor source policy.

## Existing pipeline

`scripts/windows/run-nse-market.cmd` → in-process diagnostic launcher → `operational.run` under kernel lock → exact approval/operator/credential/independent-clock checks → conservative cooldown wait (scheduled path only, at most 60 seconds) → immutable 600-GET capacity reservation → dated identity check → latest officially completed session → bounded daily capture → raw/normalized/action validation → snapshot → append-only outcome reconciliation → compatible pinned-model scoring only before the future entry → forecast shard persistence → saved workspace publication. The private dashboard reads saved evidence. A catch-up after entry is `NO_FUTURE_ENTRY`, never a backdated forecast.

| Stage | Implemented protection | Current evidence |
| --- | --- | --- |
| Launch/concurrency | Synchronous launcher, kernel lock, IgnoreNew task policy, allowlisted diagnostics | Interrupted launcher/worker terminal gaps remain visible |
| Preflight | Exact scope/cadence policy, private credential availability boolean, independent bounded clock | Latest terminal fails `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE` before GET |
| Reservations | Immutable `*.started.json`; max three collecting attempts/1,800 reserved per IST day | Crash does not refund capacity |
| Session completion | Official dated timing, lower receipt bound, 31-day selection limit | Missing schedule evidence fails closed |
| Persistence/recovery | Separate immutable response/action/record files; deterministic replay and revision conflict guards | 747 accepted daily records retained; latest session incomplete |
| Features/inference | Frozen schema/model lineage; complete vectors; future-entry and no-backdating gates | Latest catch-up produces zero forecasts correctly |
| Evaluation | Verified session links, later source receipts and per-shard validated bodies | 633 retained records, zero outcomes in existing audit; no accuracy claim |
| Monitoring | Shared GET accounting separate from reservations and accepted source records | Current uncommitted display repair additionally identifies missing launcher terminal evidence |

The retained 633 records contain 602 unique model/security/observation decisions; this is not 633 independent observations. Research extrapolation and independently accepted recommendations remain separate.

## Current Windows observation

Read-only `Get-ScheduledTask` and `Get-ScheduledTaskInfo` on 24 October reproduced:

| Task | Last start (IST) | Result | Next trigger (IST) | Settings |
| --- | --- | --- | --- | --- |
| `AlphaLens-Private-NSE-Market-Research` | 23 October 22:50:33 | `3221225786 / 0xC000013A`; Ready | 24 October 20:30 | Interactive Dell; limited privilege; IgnoreNew; 30-minute execution limit |
| `AlphaLens-Private-EOD-Watchlist` | 24 October 09:21:09 | `3221225786 / 0xC000013A`; Ready | 25 October 08:30 | Separate original RELIANCE/watchlist task; 10-minute limit |

Both are configured to start when available, prohibit battery starts, stop on transition to batteries and not wake the machine. These dependencies limit unattended reliability. An interruption code does not identify its cause. The latest saved expanded terminal is from 22 October 23:42; newer Windows starts therefore do not prove provider capture or a completed job. No power/audit/task setting was changed.

## Bounded offline integration verification

Executed from `D:\al-research\p28-worktree`, using the existing project Python environment, with no provider transport or scheduler mutation:

```powershell
$env:ALPHALENS_TEST_TEMP_ROOT='D:\al-tests'
.\scripts\windows\project-python.cmd -m pytest -q tests/unit/test_nse_market_operational.py tests/unit/test_nse_scheduled_preflight.py tests/unit/test_shared_provider_budget.py tests/unit/test_operational_daily_clock.py tests/unit/test_nse_market_forward_cohort.py tests/unit/test_nse_dashboard_readiness.py -W error
# 56 passed in 11.59 s; exit 0

.\scripts\windows\project-python.cmd -m pytest -q tests/unit/test_nse_market.py tests/unit/test_nse_universe.py tests/unit/test_nse_process_diagnostics.py tests/unit/test_nse_task_observation.py -W error
# 60 passed in 21.96 s; exit 0
```

The first attempted command, before setting the short temporary root, exited **1 before collection** with `ALPHALENS_TEST_TEMP_ROOT needs a short absolute root (<=32 chars)`; it is not represented as a passing run. The corrected commands use independently owned pytest children under D: and retain the tests' existing deadlines and assertions.

These suites cover approved-cohort mismatch, rejected unapproved scheduling, persisted daily reservations, cooldown boundary/rollback/midnight handling, fresh-clock rechecking after bounded wait, kernel concurrency, source/action interruption recovery, duplicate-free zero-GET replay, empty responses remaining pending, date rejection, oldest-missing ordering, no future leakage, immutable checksum conflicts, no-backdating, shared-client rate windows, global cohort membership, deterministic expansion selection and task/launcher diagnostics. The integrated daily fixtures mock model scoring; they **do not establish current compatible live inference, actual Upstox availability, final model acceptance, PostgreSQL deployment or browser behavior**. Separate campaign runtime/model checks must supply those results.

## Derived saved-market publication

The campaign adds a presentation stage after accepted daily capture: `saved_market.publish(root, current, at=...)` reuses the already validated frame to create a separate immutable market view and pointer. It makes no provider request, changes no model or forecast, and avoids forcing dashboard GETs to rebuild the full private history. Empty/no-new-observation runs leave the view unchanged; completed zero-GET replay creates no duplicate publication. A projection/storage failure is recorded as `SAVED_MARKET_PUBLICATION_FAILED` without discarding accepted source records or reporting the derived stage as successful.

The new `tests/unit/test_nse_daily_market_publication.py` exercises publication success and failure isolation alongside verified frame membership and unchanged zero-GET replay. The focused new/existing daily suite passed **26 cases in 17.47 s**, `-W error`, exit 0; this includes 24 cases already present in the earlier 60-case run and **two new distinct cases**, not 26 additional independent tests. Ruff and diff checks passed. Current source/model/forecast and task permissions remain unchanged.

One explicitly authorized saved-only publication completed on the genuine local store: **448,230 qualified rows /500 securities**, latest **21 October /248 securities**, zero provider calls, source/model/forecast records unchanged. Full reconstruction took **230.690 s**, projection/persistence **4.439 s**. Its private audit is `.local-data/completion-20261024/saved-market-publication.private.json`; dashboard reads use the separate checked market-view pointer rather than repeating that expensive reconstruction. This is verified saved-data publication, not a new daily market update or model prediction.

## Operator run and approval boundaries

1. Inspect task state alongside the last immutable worker terminal and current shared usage. Keep missing terminal evidence explicit; do not infer GETs from task result alone.
2. Read per-security target-session coverage and raw/action/source validity. Keep older retained coverage separate from the current target.
3. Preserve all started reservations and diagnostics across restarts. Diagnose source availability and independent-clock readiness separately.
4. Let only the unchanged approved trigger policy collect. Read terminal/provider/candle evidence afterward; no manual campaign request is authorized by a remaining reservation slot.
5. Before any task change, present exact reviewed cadence, cohort, request/storage ceiling, task XML diff, backup and rollback. A safer endpoint implementation still needs bounded real-source qualification before activation.

No new recurring task, 1,000-stock activation, production migration or public real-data deployment was performed. Full reliable automatic fresh data → accepted ML recommendations → matured live evaluation is **not verified** by these software tests.
