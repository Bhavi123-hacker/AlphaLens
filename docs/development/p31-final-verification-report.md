# P31 current-price terminal verification

Feature branch: `p31-current-price-terminal`, based on delivered P30
`c8a085bb71e4f2729b736bd78757b83497a88398`. The actual branch, worktree and remote
P30 head were checked before editing. Original C checkout remains clean.

## Corrected price experience

The main StockWorkspace previously always read frozen `/stocks/{id}/history`.
The separate RELIANCE-only Upstox component could not replace its primary header
or chart. Consequently BAJFINANCE prominently showed the October6 archive close
even while manual Upstox access worked. This was source wiring, not evidence of
an Upstox price error.

The main stock workspace now defaults to Upstox, with explicit authenticated
loading. Current official-master NSE_EQ/EQ, ISIN, key and symbol must agree.
Canonical identity requires both ISIN and symbol; company name never establishes
identity. Missing mapping is blocked, with current-master selection available.
Provider header/chart precede any archive chart. The independent archive switch
shows its frozen October6 date and actual age. No provider candles enter research.

The large chart provides1M/3M/6M/1Y/3Y/5Y/ALL, candles/line, volume, crosshair,
expanded view, SMA20/50/200, EMA12/26, RSI14, MACD and Bollinger Bands where
computable. Provider requests are bounded to five years; ALL means all returned
observations. Missing dates/warm-up values are not fabricated. Currency/tooltips
display two decimals without modifying exact source values. Technical indicators
reuse P6 formulas and confer no model eligibility.

Original dark/light private styling covers overview, analysis, watchlist,
heatmap/screener, comparison, ML research, Evidence Passport, Intelligence,
diagnostics, accounts, alerts and settings. Shared typography, navigation and
cards were improved across private pages. The primary provider layout includes
left watchlist, central chart and right OHLC/technical details. Market indices
remain explicitly unavailable; selected-cohort movers are never the NSE market.
Detailed retained P19 restrictions are collapsed and separate from manual Upstox
observations. No ingestion, automation or prediction success was fabricated.

## Actual BAJFINANCE investigation

Official current master verified `BAJFINANCE`, `INE296A01032`,
`NSE_EQ|INE296A01032`, NSE_EQ/EQ. RELIANCE and TCS were independently verified as
regression cases. These identities came from the fetched master, not constants
in production mapping.

| Check | Actual observation |
| --- | --- |
| Initial bounded verification | Seven GETs on14October, all three latest candles13October |
| Initial accepted quote generation |14October2026,22:03:41.074IST |
| BAJFINANCE accepted last trade |14October2026,15:55:02.905IST |
| Previous close/change | Full Quote V3 supplied prev_close_price; LTP minus that field, divided by the same field |
| Current-session OHLC |14October available; separate provider previous-session OHLC absent |
| Final compiled-browser observation |15October2026,00:18:55.802IST reported quote generation |
| Latest BAJFINANCE provider daily candle | **14October2026**, now published |
| Final quote validation | Rejected: generation0.947373seconds ahead of local receipt |
| Final primary price | Provider14October EOD close, exactly equal to the identical backend snapshot after display formatting |
| Final RELIANCE/TCS latest candles |13October, explicitly shown; their quotes also rejected for clock skew |

Today is15October at final verification. A safely accepted15October quote is
**unavailable** in the final sample. An accepted14October quote was genuinely
available earlier; later invalid timestamps are not accepted merely to label the
dashboard live. Quote generation and last-trade timestamps remain distinct.
The current-session candle is unavailable at this overnight check. No independent
official final-close verification is claimed. No prices or response bodies are
saved in the verification receipts; comparison assertions save only booleans.

Windows time service reported unsynchronized. Three bounded trusted NTP samples
were+0.5187991,+0.5209717,+0.5237598seconds. HTTPS Date headers are also reported
with their one-second precision, but do not correct the clock. No system-clock
change, future tolerance or validation weakening was applied. Earlier quote
rejections at22:25 and23:05 are retained as separate evidence.

The official NSE split circular identifies a June16,2025 face-value2-to1 split:
[CML68426](https://nsearchives.nseindia.com/content/circulars/CML68426.pdf).
The June11 bonus corrigendum identifies the new ISIN01032:
[CML68469](https://nsearchives.nseindia.com/content/circulars/CML68469.pdf).
The October6 archive already uses that same current ISIN. These2025 actions alone
do not establish adjustment compatibility or explain an October6/14 price gap.
Provider historical adjustment/corporate-action coverage remains UNKNOWN/
UNVERIFIED. No inconsistency is declared by comparing different sources or dates.
Official endpoint and retention contract: [P31 API](../api/p31-provider-terminal.md).

## Verification and preservation

- Backend:171-case provider/P28/P29/P21 regression passed80.93s; subsequent
  financial mapping/envelope/projection additions verified in58cases22.72s.
  Combined190distinct targeted Python cases; not a full local suite claim.
- Frontend:85tests across14files passed32.72s; TypeScript, ESLint and private
  compiled production build passed. Existing chart bundle-size warning remains.
- Real compiled private browser: final28-case run27passed/1mobile failure;
  corrected caption wrapping, rebuilt and reran the failed case successfully.
  Thus28distinct final cases passed across documented runs, not one zero-failure
  full run. Earlier selector/session/read-budget failures are superseded by these
  verified fixes, not omitted. No synthetic market interception was used.
- Actual browser coverage includes BAJFINANCE/RELIANCE/TCS current master, bounded
  quote/candles, primary-price equality, canvas tooltip precision, chart controls,
  independent archive, scoped heatmap/screener/comparison,1600/1366/390layouts,
  WCAG checks, P19 separation, real ML/backtest reads, database status, auth/logout.
- Published synthetic demo: all3actual browser cases passed; publication workflow
  is not triggered by this feature branch. Public demo code/config unchanged.
- Ruff/format, mypy280sources and Bandit passed. npm production audit and Python
  pip-audit (explicit local-editable exclusion) reported no known vulnerabilities.
  No dependency locks or scanner settings changed.
- Actual protected-credential scan of source/private/public builds and API
  responses passed; no raw/encoded credentials found or printed. Foreign-origin
  request rejected; real PostgreSQL reader lacks INSERT/UPDATE/DELETE grants.
  Financial tables remain empty. P21 authentication/session/origin rules retained.
- Read-only preservation check passed2485frozen files,8,505,278,241bytes and all47
  original alerts. Original DOCX, models,504backtests, financial modules, database
  migrations and dependency locks are unchanged against P30. The original C
  verifier was used read-only because D's older verifier expects pre-P20 metadata;
  that stale check failure is not called a pass or silently modified.
- Original dataset scan repeatedly exceeded the unchanged30second archive budget.
  Checksum-verified metadata pruning now skips only provably disjoint DATE row
  groups; unknown statistics stay included and an exact date mask is applied.
  Full64partition row SHA parity passed for canonical and features. In one matched
  canonical run original21.709s vs new8.013s; timings vary with cache/storage.
  Actual HTTP regime2/market reads now200 in17.841s/17.544s; drift200 in0.360s.
  No archive, calculation, missingness rule, max-row or read deadline changed.

Screenshots are ignored local artifacts. Provider prices/canvas/details are
masked to respect transient retention; archive/research screenshots remain local:
`.local-data/p31-browser-runtime/complete-results/provider-1600-redacted.png`,
`provider-1366-redacted.png`, `provider-390-redacted.png`, `archive-desktop.png`,
`real-overview-desktop.png`, `real-research-desktop.png`, `real-backtest-desktop.png`.
Final mobile research screenshot is in `mobile-final/real-research-mobile.png`.

## Delivery and remaining limits

The actual application uses original operator authentication/credentials and
database on loopback8017, with the new compiled `.local-data/p31-web-build`.
An isolated test operator on8029 was used for browser checks; it never reset the
original account. Native start/stop commands: [P31 Windows runbook](p31-windows-commands.md).

Retained ingestion, scheduling, model acceptance/current inference, independently
verified official close, current index data, full-NSE coverage and provider
adjustment/retained-training rights remain unavailable or blocked. Private
observations expire after600seconds without reacquisition; no provider prices are
written to disk. Existing strict container findings remain production blockers.
Git commit/push and actual CI outcomes are recorded in the execution record.
