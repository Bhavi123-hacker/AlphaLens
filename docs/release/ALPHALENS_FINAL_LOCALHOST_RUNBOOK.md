# AlphaLens Private Research V1 localhost runbook

Verified checkpoint: **2 November 2026, Windows**. Private application:
<http://127.0.0.1:8041/nse-market>. The public GitHub Pages site is a separate
synthetic demonstration.

## Launch, inspect and stop

Open PowerShell in `D:\al-research\p28-worktree`:

```powershell
.\.campaign-worktree\scripts\windows\private-v1.cmd start
```

Keep that terminal open. In another PowerShell terminal at the same location:

```powershell
.\.campaign-worktree\scripts\windows\private-v1.cmd status
.\.campaign-worktree\scripts\windows\private-v1.cmd smoke --credential-file .local-data\completion-release\qa-credentials.json
.\.campaign-worktree\scripts\windows\private-v1.cmd stop
```

These existing commands reuse the protected completion runtime, operator account
and data stores. `start` verifies the sealed manifest, source/config/frontend
checksums and existing owned PostgreSQL 17 service on loopback port 15430, then
serves port 8041. An occupied port is rejected. `stop` requests cooperative
shutdown of the owned application; PostgreSQL and collection tasks remain intact.
Run `start` again to restart. No installation, account replacement or financial
mutation is required. The credential file is private; never print or commit it.
The smoke test exercises authentication, saved-data APIs, Top-N prefixes and
logout, with zero provider requests or financial writes.

## Deployed identity

The private manifest `.local-data/private-v1-release/deployment.json` was sealed
**2 November 04:46:51 UTC / 10:16:51 IST**.

| Component | Pinned value |
|---|---|
| Application source | `.campaign-worktree`, commit `b4995f5bdd63d46b24e71b95c63c94a8195fdc81` |
| Source fingerprint | `dda67548d2fd7b5ee2388528d86becc223ec72447ca971ca489d1a25560c5027` |
| Config | `.local-data/private-v1-release/config-saved-refresh-20261102.json` |
| Frontend | `.campaign-worktree/.local-data/private-v1-20261101/frontend-saved-refresh` |
| Frontend build source | `f6fe70b246e4651123e10ba3cf2e60dbd796da0e` |
| Frontend index SHA-256 | `62b16fd7c8db490d1bfc51221f5c78be651e5915960a78dc3b3bb3abaaa3c9d5` |
| Runtime | `.local-data/completion-runtime/venv/Scripts/python.exe` |
| Rollback manifest | `.local-data/private-v1-release/deployment-before-saved-refresh-20261102.json` |

The database and live collector retain the original worktree as their separately
pinned source. Do not edit manifest hashes to bypass a mismatch. A source/config/
build change requires a reviewed deployment and a new sealed manifest.

The controlled stop/start **passed at 04:47:15 UTC / 10:17:15 IST**. The same
session survived restart; login/logout returned 200 and protected access returned
401 after logout. Provider requests and financial writes were zero; the database
service was not replaced. Receipt:
`.local-data/private-v1-20261102/deployment-restart-verification.json`.
The final quick browser run is recorded separately; its result is not inferred
from this successful restart.

## What the application currently contains

| Measure | Verified value |
|---|---:|
| Searchable ordinary-equity identities | 8,169: 3,214 NSE / 4,955 BSE |
| Stocks with saved history | 500 |
| Genuine saved candles | 450,970 |
| Latest published observation session | 30 October 2026 |
| Stocks with that session | 497 / 500 |
| Saved experimental scores dated 30 October | 307 |
| Fresh eligible predictions at this checkpoint | 0 |
| Immutable forecast records | 1,561 |
| Qualified matured outcomes / independently accepted recommendations | 0 / 0 |

The 307 new forecasts were genuinely generated on 1 November before their
2 November 09:15 IST entry. That entry has now elapsed: display them as
`SAVED_HISTORICAL_SCORE`, without redating them or treating them as fresh advice.
All model outputs remain `EXPERIMENTAL_RESEARCH`; forward outcomes and independent
acceptance remain pending. BSE discovery does not qualify the NSE model for BSE.
Missing histories/features retain truthful unavailable states.

The current 2 November ordinary identities exactly match 1 November, including
symbol/name/exchange/ISIN/segment and other non-receipt identity fields. This
supports reuse of the completed **8,169 detail-API / 110 distinct stock-browser**
acceptance, which had zero provider requests, console errors or server failures.
It does not claim 8,169 browser renders or a new exhaustive 2 November run.
Receipts: `.local-data/private-v1-20261101/browser-all-report.json` and
`.local-data/private-v1-20261102/display-catalog-identity-comparison.json`.

The two approved 1 November manual attempts acquired **994 genuine new candles**
across 29/30 October and produced **307 pre-entry forecasts**. Their subsequent
cohort-view publication failed. On 2 November, supported saved-view recovery
published the accepted history and existing score view with **zero provider GETs,
clock acquisitions, new inference or forecast writes**. Original source inputs,
score pointer and forecast ledgers were unchanged. A separate read-only audit
rebuilt all 307 compatible feature vectors and reproduced every saved model score
exactly twice. These are recovery/replay results, not additional predictions.
Receipts: `.local-data/private-v1-20261102/saved-publication.finished.json` and
`daily-model-audit.json` in the same directory.

## Daily operation and remaining approval

`status` reports actual API/database ownership, saved sessions and forecast totals,
provider-token presence, quota, task observations, last publication/failure and
disk free bytes. Token presence, API health and Scheduler exit success each need
their own source/publication evidence. A powered-off laptop can only catch up
after resuming, under the existing calendar, clock, quota and source gates.

The live collector still uses original source fingerprint
`06e8a5631391fefbb9f8a209150269d4ed1a0e41e244c89ab926239f96c260e4`.
Its existing scope remains 500 instruments, at most 250 stocks / 600 reserved
requests per run, 1,800 reserved requests per day and a conservative 60-minute
cooldown. Scheduled triggers remain **20:30 / 21:30 / 22:30 IST**. The original
single-RELIANCE task is separate and preserved. Source indexing, page visits and
application launch do not expand acquisition authority. Scheduled reliability
remains unpassed after the latest clock-gated failure; manual delivery and
saved-view recovery do not establish a successful scheduled publication.

The checksum-bound **two-file live collector fix is PENDING approval and has not
been applied**. Its exact proposal is
`.local-data/private-v1-ordering-clock-20261102/ordering-clock-source-proposal/proposal-INACTIVE.json`,
SHA-256 `b1647d48dfa838de630b3442c4451c0a57b6c572ead26277b834061578447329`,
covering only `workers/nse_market/daily.py` and
`workers/providers/daily_clock.py`. Tested application-source fixes do not silently
change the separate live collector. Apply only after exact operator approval and
fresh idle/preflight checks; retain the proposal's original-byte rollback.

The prior two-attempt manual acquisition approval is **exhausted and expired on
1 November**. It authorizes no new manual collection. This runbook prescribes no
manual acquisition command or task change. Clock and quote acceptance remain
strict; failed clock evidence cannot be replaced with an unconditional tolerance.

## Recovery and preservation

Accounts, credentials, source data, models, forecasts, 47 original alerts and
2,485 frozen research files remain protected. Existing SQLite and full PostgreSQL
backup/restores were reverified read-only on 2 November. See the dated scope and
private receipt locations in
[the storage/recovery report](ALPHALENS_STORAGE_100GB_CLEANUP.md).

Restore to a separate private destination first, verify logical contents and
checksums, and revoke restored authentication sessions before use. Preserve newer
source and forecast records during any reviewed rollback. Use the existing safe
cache cleanup only after checks stop and paths are reviewed; databases, models,
private stores, Docker volumes and WSL disks remain outside that cleanup scope.
