# P31 current-price terminal — execution record

Baseline: clean p30-upstox-final-integration at c8a085bb71e4f2729b736bd78757b83497a88398.
Feature branch: p31-current-price-terminal. Original C checkout, frozen research,
model artifacts, databases, credentials, 47 alerts and published synthetic demo preserved.

User authorizes bounded read-only current-master/candle/quote validation and an
original private-terminal redesign. No retraining, archive/provider price blending,
retention gate weakening, brokerage mutations or private-data public redistribution.

Confirmed cause: primary StockWorkspace consumes frozen /stocks/{id}/history;
Upstox is an appended RELIANCE-only component. Provider price cannot become the
primary header/chart. Display precision and pervasive small typography also need repair.

Implementation order: verified reusable provider identity/quote/candle API; primary
source selection/header/chart; scoped watchlist and diagnostics separation; visual
terminal polish; compiled live browser/security/preservation tests; commits/push/report.

Clock evidence: Windows time service reports unsynchronized; three bounded Windows
NTP stripchart samples are approximately +0.42 seconds. No system-clock mutation or
arbitrary future-timestamp tolerance is authorized or applied.

## Checkpoint 1 — genuine source and integrated primary chart

- Actual branch verified p31-current-price-terminal at delivered P30 c8a085b;
  original untracked execution record preserved. D82 records the current user task.
- Reusable exact current-master NSE_EQ/ISIN/symbol mapping, protected generic
  search/snapshot APIs, up to three-equity explicit batch and transient cache added.
  Source failures never fall back to archive prices under a provider label.
- Bounded seven-GET live check: BAJFINANCE INE296A01032, RELIANCE INE002A01018,
  TCS INE467B01029. All latest daily candles13Oct;14Oct candle pending.
  Full Quote V3 accepted at22:03:41.074IST, BAJ last trade15:55:02.905IST;
  exact documented prev_close_price used for change. Current OHLC available;
  provider prev_ohlc absent, retained as unavailable. No prices/bodies saved.
- Additional Windows clock check: unsynchronized; three NTP samples+0.5187991,
  +0.5209717,+0.5237598seconds. No OS clock mutation or future tolerance.
- Compiled browser batch later22:25:51.286IST was+0.598567seconds ahead of
  receipt and rejected. UI used13Oct provider close with explicit non-LTP label.
  This does not negate earlier verified token access; no current quote invented.
- Provider primary source/header/chart; archive independently selectable with
  eight-calendar-day age. SMA/EMA/RSI/MACD/Bollinger/volume, expanded chart,
  selected-cohort heatmap/screener/comparison, readable typography and private
  stylesheet added. Homepage research blockers collapsed; research gates intact.
-31targeted Python cases passed8.90s;84frontend cases passed31.29s after a
  test assertion was corrected for equal previous/EOD fixture values. Mypy/Bandit/
  Ruff passed. Six actual compiled browser cases passed46.8s, no interception;
  UI currency compared with the identical backend observation using boolean-only
  receipts. Desktop1600/laptop1366/mobile390 overflow and home WCAG checks passed.
- Screenshots mask transient provider values/canvas; archive screenshot retained
  privately under ignored local storage. Public synthetic demo was not republished.

## Checkpoint 2 — final compiled verification and delivery

- Final current-master/candle batch at15October00:18:55.802IST now returned
  BAJFINANCE14October EOD. RELIANCE/TCS remained13October. Quote generation was
  0.947373seconds ahead of receipt; correctly rejected without weakening clocks.
  All three displayed prices matched the identical provider candle snapshots.
- Fixed the archive read bottleneck with checksum-preserving, exact DATE row-group
  pruning and coarse-file batch sizing. Full64partition row SHA parity passed for
  canonical/features; actual bounded regime/market/drift HTTP reads now200.
  Original30second limits, financial formulas and gates remain unchanged.
-171case regression plus new targeted58case run cover190distinct Python cases.
  Frontend85tests passed; final private28browser run27passed/1mobile failure.
  Corrected long-caption wrapping, rebuilt and reran the failing case: passed.
  Thus28distinct private cases passed across documented runs; published-demo3
  cases also passed. Earlier failures are documented in the final report.
- Desktop1600/laptop1366/mobile390 provider layouts and actual canvas-tooltip
  precision passed. Final390research document width390. Price screenshots masked;
  fresh final screenshots and sanitized date/identity receipts are local only.
- Actual secret scan936source/build files passed; protected API responses clean,
  foreign origin403, real PostgreSQL reader SELECT-only and financial counts0.
  Original C read-only preservation check passed2485files/8,505,278,241bytes and47
  original alerts. Protected research/locks/demo diff against P30 remains empty.
- Final report: `p31-final-verification-report.md`; API contract and native Windows
  start/stop runbook added. Git/CI verification follows the implementation commit.
