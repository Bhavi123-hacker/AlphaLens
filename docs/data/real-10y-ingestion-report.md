# TejHQ real NSE acquisition and research readiness (D69, 2026-10-08)

Source permission is USER-AUTHORIZED NONCOMMERCIAL RESEARCH; no further
clarification is pending. DATA_REALITY = REAL_MARKET_OBSERVATIONS;
USAGE_CLASSIFICATION = RESEARCH_ONLY. P1 clearance OPEN, production market-data
use NOT_CLEARED. This records the user's research-use decision, not an exchange
grant or production approval. P17 and P11-P14 calibration remain unstarted.

## Source, integrity and immutable originals

Dataset `tejhq/indian-markets`, exact revision
`14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98`. Public Hub `/resolve/<revision>/...`
file endpoints only; no HTML scraper, viewer samples/conversion, authentication,
controls bypass or paid service. No switch to another source or newer revision.

17 publisher-native NSE price Parquets: **192,163,454 bytes**. Additional 17 NSE
action-year files and one NSE symbol-history file: **1,004,385 bytes**. Total:
**35 files / 193,167,839 bytes**. Every size and SHA256 matched publisher LFS
metadata; all 17 price hashes matched the audited revision. No mismatches accepted.
[Acquisition manifest](tejhq-acquisition-manifest.json) records native-vs-converted,
dataset/revision/subset/exchange, undefined split with its partition explanation,
filename/reference, partition year, acquisition time, hashes, classification and
P2 raw-manifest IDs. No signed CDN URLs or credentials were retained.

Incoming originals: `data/incoming/tejhq/14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98/`.
Exact bytes entered existing P2 RawLanding under `data/tejhq-research/p2/`, with
exclusive immutable capture, checksum replay and FileMetadataRepository metadata.
Schema/profile preceded row normalization. Raw storage does not manufacture
historical availability; acquisition clocks stay acquisition clocks.
Large original/derived files remain outside Git. No CSV conversion was performed.

## Actual raw profile

[Profile](dataset-profile.json): **7,225,761 rows**, **4,128 observed dates**,
**2010-01-04 through 2026-10-06**, 17 calendar years represented. Every yearly
partition was profiled with PyArrow batches; only one partition's duplicate keys
was retained. Schema has date/symbol/series/isin/name/OHLCV plus last, prev_close,
turnover, trades, year and month. Historical publication/availability/completion
and revision-vintage columns are absent.

4,378 distinct symbols, 4,381 distinct ISINs, 6,367 source observation keys.
The keys mix observed ISINs with unresolved pre-ISIN symbol/series scopes and are
**not a count of reconciled companies or permanent P4 identities**. Latest session
has 2,942 observed keys; 3,425 historical keys are absent on it. Absence can mean
identifier changes or incomplete observations, not proven delisting. Confirmed
terminal/departed company count is UNAVAILABLE. Nothing was filtered to a 2026
constituent list and later ISINs were not backfilled into older source rows.

ISIN present: 6,710,159 rows; missing: 515,602. Name missing: 5,601,161 rows.
552 symbols have multiple observed ISINs; 438 ISINs have multiple symbols.
52 keys have explicit ETF name evidence. Other keys remain UNKNOWN for standard
common-equity eligibility; EQ series or a plausible ISIN pattern is not an
automatic P4 type upgrade. No authoritative common-equity count is established.
Per-year rows/security-key counts and all three series are in the profile.

Measured OHLC/volume nulls, negative/zero prices, nonfinite OHLC, negative/zero
volume, duplicate identity/session rows, symbol/session duplicate rows, conflicting
duplicates and impossible OHLC relations: **0**. 1,531 close/prev_close movements
exceed the configured 50% diagnostic threshold; 3,534 high/low ratios exceed 1.5.
These are raw diagnostics, not a predictive or profit result. Publisher caveat:
anomalous/zero-volume rows were already removed upstream; deleted counts unknown.

1,823 source keys have internal gaps against the dataset's observed-date union,
with 289,497 missing slots. These are candidate gaps, not confirmed listing or
security-specific holiday facts. Observed weekends are 2024-01-20 and 2025-02-01.

## Calendar, actions, identity and benchmark limitations

The observed union is RESEARCH evidence, not a complete authoritative calendar.
**Five documented Muhurat trading dates have zero price rows:** 2013-11-03,
2016-10-30, 2019-10-27, 2020-11-14 and 2023-11-12. NSE's
[November 2024 Market Pulse](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Market%20Pulse_November%202024_FINAL_3.pdf)
printed page 86 records the CM Muhurat sessions; its
[2023 circular](https://nsearchives.nseindia.com/content/circulars/ISC59313.pdf)
confirms the Sunday 2023-11-12 special trading session. The source union therefore
cannot turn absent dates into VERIFIED_NON_TRADING_SESSION or supply complete
session offsets. An observed-session Parquet is retained locally with explicit
RESEARCH basis; no weekday calendar or missing OHLCV was fabricated.

[Reference profile](tejhq-reference-profile.json): 34,612 actions, 2010-01-04 to
2026-10-06; 21,043 dividends, 11,108 AGMs, 662 splits, 587 bonuses, 348 rights,
347 buybacks, 118 demergers, four mergers and 395 other events. 22,037 missing
record dates, 72 missing action ISINs; no historical announcement/availability
fields. Exact symbol/ex-date matches coincide with 756 of 1,531 raw
large movements; 775 have no exact match. This is retrospective evidence only.
Where multiple actions share that key, the reference profile counts the last
source-row type once; its type breakdown is not causal attribution.
No authoritative announcement clock, adjustment factor or dividend accounting
was invented. Publisher adjusted data uses later action factors; it was inspected
through its documentation and **not downloaded/used as PIT input**. Prices retain
RAW_UNADJUSTED basis and float64 source-precision limitations.

4,886 source symbol-history intervals cover 4,381 ISINs; 438 have multiple symbols.
Retrospective valid_to is not a contemporaneously known departure/listing date.
NIFTY benchmark UNAVAILABLE; the pinned tree has no identified benchmark archive.
Fundamental PIT data UNAVAILABLE. No synthetic benchmark is called NIFTY 50.

## P2-P10 status and frozen source identity

P2 normalization / scoped P3 replay: **COMPLETE**, native exit 0. It uses the existing P2 normalizer
and unchanged P3 engine/policy, with bounded, deterministic source-identity shards
and backward-only temporal context. Global identity/session and symbol/session
ambiguities were checked before partitioning. Complete trailing repeated-OHLC
runs are preserved across batches/years. Source-scoped fallback identity remains
explicit when ISIN is missing. No quality threshold or severity was loosened.

[Final P2/P3 summary](tejhq-p2-p3-summary.json): **7,225,761 normalized rows**,
**5,288,138 VALID**, **1,937,623 DEGRADED**, **0 REJECTED**, **0 quarantined
source rows**. These are row-level results, not historical eligibility. Four
source-identity shards produced 68 yearly derived Parquets (**1,294,714,624 bytes**)
and 7,069 immutable scoped P3 reports under
`D:/al-research/tejhq-14d81bba-p2-p3-v3/`. Each derived checksum, metadata row count
and every row's reality/usage classification was checked against the final summary.
All 35 incoming originals and their 35 immutable P2 copies were rehashed again.
The independent complete raw-profile replay matched the committed profile exactly.

P3 current-record issue occurrences: OBSERVATION_GAP 1,795,547; VOLUME_SPIKE
193,780; EXTREME_RETURN 1,122; REPEATED_OHLC 862; EXTREME_RANGE 3,531. These
may overlap and are not unique degraded-row counts. CALENDAR_UNAVAILABLE and
UNIVERSE_READINESS appear in all 7,069 scoped reports. Raw diagnostic thresholds
and P3 rules have different definitions, so their extreme-movement counts differ.
No scoped report is represented as a complete calendar/universe validation.
Source prices are documented raw/unadjusted; normalized adjustment-basis metadata
remains unknown rather than receiving an unsupported P5 eligibility upgrade.

[Source identity](dataset-identity.json):
`d35679e28e34fb66b6f0f2e34be30478987891344ee4e30baf67ec70c67b250e`.
It pins 35 raw hashes, source revision, P2-P7 versions and feature definitions;
it explicitly marks the P7-aligned training dataset **NOT READY**.

**P4-P10 historical research replay is BLOCKED by missing knowledge/calendar/type
facts.** P4 observations cannot be backdated to presumed publication; P5 has no
eligible historical cutoff dataset. P6 requires completed sessions and complete
calendar evidence. P7 requires evidenced future maturity/availability. No P6/P7
matrix or P8 model was produced. SMA100/SMA200 availability is unmeasured, not 0%.
No random splits, final holdout model/target inspection, fitted scaler, OOS prediction,
backtest, paper fill, target history, equity curve or performance claim was made.

[Pre-results evaluation plan](../ml/real-research-evaluation-plan.json) locks
observed year boundaries: early 2010-2014 history, development training 2015-2021,
OOS 2022-2024, confirmation 2025 and final holdout 2026. Exact executable P9 folds
remain dependent on historical knowledge/maturity/purge/embargo evidence.
Native verified OHLCV files can support raw RESEARCH price-history inspection;
P5-canonical chart history, prediction/target/equity/drawdown/trade-marker series
are unavailable. No frontend charts were implemented.

## Verification and attempt history

Final current-code Windows-safe/PostgreSQL 17 regression **PASSED**, native exit 0:
**506 passed, one production/live-provider skip**, 1,632.48s (27:12). Package/new
research-script Bandit, Ruff, format, mypy (including research scripts), frozen
lock/sync and dependency audit pass. A broader scan including historical
verification helpers found 13 existing low findings (assert/subprocess use),
zero medium/high; these were not introduced or suppressed by this sprint.

Ten initial adapter cases passed; after deterministic shard coverage, 11 focused
cases pass. An intermediate full run passed 505/one live skip, 1599.88s, native
exit 0. Current-code full replay includes the latest adapter/classification/schema
changes and the added case. Disposable PostgreSQL 17 ingestion, immutable P5
fixture CLI replay (twice) and container/network/volume teardown all exited 0.
This is schema/software regression, not a real P5 market-data projection.
No new dependency was introduced. The nine package Bandit scan and three new
research-script scan passed; mypy checked 154 sources plus the new scripts.
Ruff checked/formatted 247 Python files; dependency audit found no known
vulnerabilities. Lock check resolved 97 packages and frozen sync checked 96.
Ignored final log: `data/tejhq-research/final-regression.log`.

Superseded local attempts are not accepted output: v1 was stopped after review
found missing ISINs labelled with explicit source IDs; fixed to existing P2
SOURCE_SCOPED_SYMBOL semantics. A corrected serial v2 attempt was stopped for
bounded four-worker v3 replay, preserving identical IDs/offsets and full per-ID
past context. Originals unchanged; incomplete derived folders remain ignored.
PyArrow hive year-column inference conflicted with native int32; direct
ParquetFile reads resolved it without source changes. Initial formatting/type
checks were corrected; explicit-package-bases resolved a script-module mypy
invocation ambiguity. No test or data rule was weakened.

Original DOCX and main are protected. Earlier audit-only report follows historically.

---

# Real 10+ year ingestion status

Status: **NOT_RUN_SOURCE_GATE_BLOCKED**. No selected source, no new market archive
download and no P2-P7 replay in this sprint. This report records the stop explicitly;
it is not an ingestion success or a zero-row dataset.

Baseline: clean P16 `3634b920e7e1d090b3fbf18af3548afb419e7b71`, P15
`2db5f157a00a682070cf2c1cf6cbb9f65d9827f3`, both DEVELOPMENT PASSED.
Branch `real-data-10y-training`. `main` and original DOCX remain unchanged.
No P17, P11-P14 recalibration, broker, paid service or prohibited scraper added.

Reviewed existing P2 raw ingestion, P3 validation, P4 PIT universe, P5 canonical,
P6 features, P7 labels, P8 training, P9 evaluation and P10 backtesting contracts.
They require source-specific rights, stable identities, known historical clocks,
calendar evidence, preserved exclusions and cutoff-specific data. A large price
file alone cannot establish those facts. Unknown availability remains unknown.

[Source audit](real-data-source-audit.md), [source-audit.json](source-audit.json)
and [dataset-profile.json](dataset-profile.json) distinguish publisher metadata
from unperformed artifact measurements. Actual earliest/latest date, sessions,
securities/common equities/departures, raw/canonical rows, disk bytes, dataset
identity, OHLCV anomalies/nulls, gaps, type contamination, corporate actions,
benchmark and calendar completeness are **UNAVAILABLE**, not zero.

The best coverage candidate has 17 metadata-listed year files (2010-2026) totaling
192,163,454 bytes. Publisher LFS digests are pinned; no actual-download checksum
has been verified. This is potential coverage, not an acquired AlphaLens dataset.
No artifact is classified PRODUCTION or silently converted from TEST_ONLY.
Fundamentals remain UNAVAILABLE; production clearance OPEN/use NOT_CLEARED.

Quality verification completed on 2026-10-08: the complete Windows-safe suite
passed with **495 passed, one production/live-provider skip**, 1237.42 seconds,
using `pytest -W error -ra` and `ALPHALENS_TEST_TEMP_ROOT=D:/al-tests`.
The real PostgreSQL 17 runner completed ingestion, two identical canonical CLI
replays and container/network/volume teardown with explicit native **exit 0**.
PowerShell represented native Docker stderr as NativeCommandError in the redirected
log; this was not a failing process exit. The captured native exit and completed
pytest/replay/teardown establish the result.

Frozen lock/sync, Ruff check/format (236 files), mypy (152 sources), Bandit
(nine Python roots, 15,462 lines, zero findings), dependency audit (no known
vulnerabilities) and diff checks passed. All eight requested result/status JSONs
parse; source records preserve unknown measurements and metadata checksums.
Main remains `9fa82284936f8b7a34f5409ba25cdce3538747b6`; original DOCX SHA256 is
`196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a`.
Only documentation/audit metadata changed; no dependencies, financial logic,
broker connection or market-data scraper was introduced. Staged text was checked
for narrow credential/private-key patterns; no such secrets were found.
These gates validate existing software, not data rights or new market performance.
Historical P15/P16 reports are unchanged.

Next action: resolve a source-specific zero-cost research grant using
[the prepared access request](real-data-access-request.md), then P2 immutable raw
capture and independent profile before ingestion. No manual download of an
unapproved candidate is requested.
