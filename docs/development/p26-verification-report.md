# P26 verification and delivery checkpoint

Baseline bcd3306129ae3436c899455ab12a688c37f6ac15, branch p26-visual-analytics-terminal.

## Implemented

See docs/dashboard/p26-visual-terminal.md for the page/chart/API matrix and honest
unavailable modules. Canonical RELIANCE search, trailing-year range, dated historical
close, bounded market map/screener/comparison, stored stock/ML/backtest/account
analytics, keyboard palette/watchlist rail and disabled provider readiness.
The later explicit Alpha Vantage credential request was completed alongside P26:
Windows Credential Manager readback verified; one successful symbol-search request,
RELIANCE.BSE India/Bombay, NSE not established, zero price downloads/new sessions.
Original input file remains unchanged and can now be removed by the operator.

## Executed verification

* Targeted P17/P21/P26/credential tests:79 passed; P24/P26/credential26 passed,
  overlapping21 cases:84 distinct targeted Python cases. Later empty-search fix
  P17/P26:40 passed. These are targeted runs, not a fresh full-suite claim.
* Frontend:67 unit/component tests passed. First run58 passed/one async route-load
  timeout; the explicit lazy-page wait is corrected and the complete67 run passed.
* Ruff,391-file format check, strict mypy235 sources, Bandit, pip-audit (zero known
  vulnerabilities; editable workspace packages skipped), npm audit (zero),103-package
  frozen lock and whitespace passed. No dependencies/lock versions changed.
* Compiled frontend build passed. Rich chart engine681.15kB /228.27kB gzip retains
  its size warning; all graph pages and the engine are lazy chunks.
* Actual deployed browser22-case run:19 passed/3 legacy selector failures after
  charts became multi-panel. All five new P26 scenarios passed in that run.
  Focused four-case legacy regression passed (22.3s), including the three corrected
  selectors and one overlapping prediction case:22 distinct browser cases verified.
  This is combined evidence, not a zero-exit22-case run. Receipts retained outside Git.
* Initial P26 browser attempts exposed/fixed compiled-route allowlisting, cold-read
  capacity starvation and ECharts overwriting historical accessibility labels.
  Subsequent test fixes distinguish hidden date options, exact combobox labels,
  hydrated shortcut registration and completed logout. Failure/interruption reports
  remain under D:/al-research/p26-runtime; retries are not presented as one clean run.
* Actual local compiled CMD startup/cooperative shutdown/restart passed on loopback.
  Tests use a separate generated TEST_ONLY account and online-cloned alert store;
  no real operator credential/alert mutation. PostgreSQL is NOT_CONFIGURED locally;
  account chart renderers therefore remain unavailable in normal local browsing.

## Integrity and unchanged gates

Read-only streaming SHA256 verified all2,485 frozen files /8,505,278,241 bytes,
152 fits/504 stored backtests/46,072,188 OOS rows via their unchanged approved
inventory and reports, plus47 original alert payloads. Inventory SHA:
608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17.
Alert SHA:dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41.
Main remains9fa82284936f8b7a34f5409ba25cdce3538747b6. DOCX, P11-P16, model
configuration/thresholds, final holdout, dataset hashes and dependency locks unchanged.

No training, holdout evaluation, backtest execution, current prediction or fabricated
market observation. P19 live activation/current inference/signals/shortlist remain
BLOCKED; P1 OPEN/production use NOT_CLEARED. Existing474 economic outcomes remain
unresolved. Strict container baseline44 HIGH/eight CVEs/zero CRITICAL remainsFAILED;
new actual GitHub receipts will be linked after push, without waivers.

P26_VISUAL_DEVELOPMENT = PASSED. Focused browser regression and source review
completed; GitHub delivery/CI remain separately recorded below. Live-provider/sector/benchmark/PG/attribution limitations are
separate from software acceptance. Later user requests authorize subsequent unified
provider work; it must branch from completed P26 without discarding these changes.
