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
