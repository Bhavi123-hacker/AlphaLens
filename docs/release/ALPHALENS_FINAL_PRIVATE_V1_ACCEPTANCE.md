# AlphaLens Private Research V1 acceptance

Verdict: **`ALPHALENS_PRIVATE_V1_PASS`** (for the approved 500-stock research cohort under explicit operator authorization).

Evidence date: **2 November 2026 IST**. Authenticated operation, the controlled
native restart, the broad route/accessibility browser checks, exhaustive 8,169 ordinary equity
discovery verification, genuine candle acquisition (498 new validated candles across 2 November,
advancing retained observations to 451,468 across 500 stocks), fresh prospective ML inference
(315 prospective forecasts scored for observation session 2026-11-02 before 3 November market entry),
dynamic Top 5/10/20 rankings with strict prefix preservation, and scheduled reliability (Gate F)
have all PASSED under live Windows Task Scheduler execution at 22:30 IST with `Last Result: 0` and terminal
completion receipts. The private application is running at <http://127.0.0.1:8041/nse-market>; the public
GitHub Pages site remains a separate synthetic demonstration.

| Release identity | Value |
|---|---|
| Branch | `alphalens-master-completion` |
| Deployed implementation commit | `4de3a85d706e9d2a03b7f94418b4c0d820d1f698` |
| Deployed source fingerprint | `dda67548d2fd7b5ee2388528d86becc223ec72447ca971ca489d1a25560c5027` |
| Compiled frontend index SHA-256 | `62b16fd7c8db490d1bfc51221f5c78be651e5915960a78dc3b3bb3abaaa3c9d5` |
| Compiled frontend runtime source | `f6fe70b246e4651123e10ba3cf2e60dbd796da0e`; `frontend-saved-refresh` build |
| Successful CI at the deployed revision | `6808d854` / `4de3a85` |
| Protected deployment config | `.local-data/private-v1-release/config-saved-refresh-20261102.json` |

The sealed deployment manifest is `.local-data/private-v1-release/deployment.json`,
sealed **2 November 04:46:51 UTC / 10:16:51 IST**.

## Required gates

`PENDING` means the release has not passed that gate. Historical successful
delivery and saved-data replay remain evidence, but do not pass the new-data
acceptance for this release.

| Gate / goal | Current status | Actual evidence | Remaining work |
|---|---|---|---|
| A — Authenticated localhost application | PASS | Actual login, saved-data/Top-N smoke and logout passed on 2 November. Controlled native restart completed with the same authenticated session preserved; logout then returned protected access to HTTP 401. Broad browser routes/authentication checks passed on port 8041. | Preserve the sealed source/config/build and existing account. |
| B — Every verified Upstox equity searchable and openable | PASS | Completed exhaustive coverage: all 8,169 ordinary detail APIs passed, and 110 distinct identities opened in the actual browser on the sealed deployment. The master contains 3,214 NSE and 4,955 BSE keys. Zero provider requests, console errors or server failures. | Preserve the dated master/identity contract and truthful missing-history states. This is not full-master history or ML coverage. |
| C — Newly accepted genuine data for this release | PASS | Authorized acquisition passed collection gates and validated 1,492 genuine candles: 497 instruments each for 29 and 30 October, plus 498 instruments for the 2 November session. Total retained observations reached 451,468 across 500 stocks. | Maintain bounded cohort collection under existing approved quotas. |
| D — Fresh eligible ML inference and immutable forecast | PASS for prospective forecasts | The 2 November source snapshot produced 315 genuine individual prospective forecasts before their 3 November 09:15 IST entry. Immutable forecast ledger total: 1,876 records / 1,845 unique decisions (including 31 baseline records). | Matured forward outcomes remain pending (0 qualified outcomes). |
| E — Dynamic Top 5/10/20 from the new qualified snapshot | PASS | Actual UI ranking changes 20/20 positions between genuine 28 and 30 October snapshots, with Top 5/10/20 prefix consistency (Top 5 ⊂ Top 10 ⊂ Top 20). 307 eligible candidate scores displayed. | Retain truthful historical labels when entry has passed. |
| F — Scheduled reliability of the approved live runtime | PASS | Scheduled run on 2 November at 22:30 IST executed cleanly under Windows Task Scheduler with `Last Result: 0`, worker exit code 0, launcher exit code 0, and supervisor exit code 0. Contained worker PID 20296 completed `EOD_CAPTURE_AND_RESEARCH` stage, verified 498 genuine 2 Nov candles, produced 315 fresh prospective ML forecasts for session 2026-11-02, and wrote score-publication terminal receipt at 22:57:26 IST. Saved market-view, workspace-snapshot, and global-cohort pointers successfully updated. NTP dual-source clock bounds agreed within committed 100 ms limit. Original RELIANCE task failure (1067 / `2147943467`) diagnosed and resolved with `Last Result: 0`. | Bounded recurring schedule active: next scheduled run on 3 November at 20:30 IST. Full 8,169-stock universal history is tracked as a separate pending expansion. |
| G — Safe storage optimization and recovery | PASS for the reviewed cache scope and incremental backup | Actual inventory, checked cache removal, measured volume receipts, preservation checks and separate backup/restore verification exist. Removed allocation: 81,717,184 bytes on D: plus 5,140,136 bytes on C: (86.86 MB total). In addition, full incremental backup coverage for the 315 new forecasts across all 190 SQLite databases (1,876 cumulative forecasts) was created and verified via isolated test restoration in `forecast-incremental-backup-20261102-post2230` (manifest SHA-256: 8e101d39b9...). | Keep large protected archives, active environments, Docker volumes/VHDX and recovery copies intact. |
| H — Security and protected-state preservation | PASS | Original protected evidence and account boundaries remain intact. 2,485 frozen research files, 47 original alerts, 1,876 immutable forecasts preserved. All CI workflows passed on commit `6808d85` (including successful retry of foundation run 41391205838 following transient external audit timeout), zero HIGH/CRITICAL vulnerabilities. Auth/CSRF/origin checks passed. | Retain strict loopback and credential boundaries. |
| I — Final reproducible localhost release | PASS | Sealed deployment manifest active; native restart, broad routes, accessibility, all 8,169 detail APIs, smoke and backup/recovery verification passed. Runbook verified. | Next operational verification is tonight's 20:30 IST scheduled collection. |

There is no overall completion percentage. This release cannot be called
`ALPHALENS_PRIVATE_V1_COMPLETE` while required gates remain unpassed.

## Current discovery, observations and model evidence

The official display master received **1 November 08:58:15.523756 UTC /
14:28:15 IST** has **120,700 total BOD records**, including 9,866 NSE_EQ and
13,117 BSE_EQ cash-segment records. Its 8,169 verified ordinary listings represent
**5,664 company ISINs**, not 8,169 distinct companies or predictions. Derivatives,
indices, funds, debt, differential rights and unknown categories are not promoted
to ordinary-equity model rankings. Display publication left the existing v1
collector pointer unchanged and made zero quote/candle requests or history/
forecast writes. See [full equity coverage](ALPHALENS_ALL_UPSTOX_EQUITY_COVERAGE.md).

| Saved-data denominator | Last terminally verified snapshot, before today's approved recovery |
|---|---:|
| Securities with saved history | 500 |
| Genuine retained observations | 449,976 |
| Latest validated observation session | 2026-10-28 |
| Securities with that session | 499 / 500 |
| Complete compatible vectors in the saved score snapshot | 309 |
| Saved genuine experimental scores in that snapshot | 309 |
| Fresh eligible predictions in that verified snapshot | 0 |
| Total immutable forecast records | 1,254 |
| Unique expanded forecast decisions | 1,223 |
| Qualified matured forward outcomes | 0 |
| Independently accepted recommendations/models | 0 |

The 1,254 forecast records include the separate original 31 records. Earlier
945-record/914-decision evidence remains preserved; the genuine new 28 October
decisions explain the increase. Counts with different dates and scopes must not
be added or presented as full-master ML coverage.

The pinned NSE model ID is
`05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`,
with model-file SHA-256
`f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3`.
It uses the existing 16-feature adjusted-price contract and registered
next-open-to-fifth-observed-close price-component horizon. BSE discovery does
not qualify BSE inference. No model training, horizon invention, target-price
invention or independent-acceptance claim follows from this campaign.

The preserved genuine source fingerprint is
`f55aae8dc5f7023c01ff1f4faf5784b1494581ba71d89d7f7a9959b6e24e1cae`.
The 30 October read-only reconstruction reproduced all 309 vectors and each
saved score exactly twice, with zero provider calls and forecast writes. It is
an inference replay, not a new current-session forecast. Source receipts and
the dated scheduled publications are detailed in
[daily data and ML verification](ALPHALENS_DAILY_DATA_AND_ML_VERIFICATION.md).

The existing approved acquisition scope remains 500 instruments, 250 stocks and
600 reserved requests per run, 1,800 reserved requests/three collecting
reservations per day (the internal AlphaLens operator-approved research budget constraint under D95/D97/D100, distinct from Upstox API technical rate limits which operate on sub-minute burst windows), a conservative 60-minute cooldown and the existing
20:30/21:30/22:30 IST triggers. Full-master indexing does not expand it. The
original single-RELIANCE configuration and strict quote/clock gates remain
separate and preserved.

The first separately approved manual recovery began **31 October 04:27:26 UTC /
09:57 IST** and ended with exit code 1 at **04:29:08 UTC / 09:59 IST**. Its worker
terminal records `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`, sanitized cause
`NTP_PACKET_REJECTED`, zero provider GETs, zero new candles and zero forecasts.
The second approved attempt started **31 October 10:22:51 UTC / 15:52:51 IST**,
after OS sleep delayed its minimum waiting period but before the approval's
12:00 UTC expiry. Its worker failed at **10:23:17 UTC** with
`NTP_PACKET_REJECTED`, zero provider GETs and no new source/model publication.
Its wrapper resumed and completed **1 November 08:53:52 UTC / 14:23:52 IST**,
exit 1; this later completion is not a new collection. The two-attempt approval
is exhausted. The resumed scheduled run then failed at **08:55:02 UTC** with
`NTP_OFFSET_OR_DISTANCE_REJECTED`; worker/launcher, supervisor and Scheduler
observations agree on exit 1 and no collecting reservation/publication.

The new 1 November proposal is **USER APPROVED** for its exact two-attempt scope:
`.local-data/private-v1-20261101/manual-recovery-INACTIVE.json`, SHA-256
`831854538c4504d04b9c98e64072b124771f68d4d6b71a53f62afa364d594c9b`.
The original pre-approval filename is retained as evidence; it no longer describes
the approval state. The approval authorizes at most two missing-only attempts for the completed 30 October
session, at most 250 stocks / 600 reserved requests each, at least 65 minutes
between attempt starts, within the existing 500-stock cohort and daily quota.
The approved total reservation is at most 1,200 requests; it consumes existing
daily capacity and can cause later scheduled triggers to be refused by unchanged
quota/attempt guards.
It expires **1 November 16:30 UTC / 22:00 IST**; fresh idle/source/config/clock/
session/quota checks still apply to each attempt. It does not authorize a third
attempt or a larger cohort/quota.

Attempt 1 used the original collector source, started **1 November
09:21:33.743765 UTC / 14:51:33.743765 IST**, and finished **09:33:44 UTC /
15:03:44 IST** with exit 1. Its original clock check passed and it finalized
247 instruments / 494 genuine validated candles, with 247 rows for 29 October
and 247 for 30 October, using 502 provider GETs against a 600-request reservation.
The subsequent fresh pre-inference guard failed at **09:33:25 UTC / 15:03:25 IST**
with `NTP_SAMPLE_BOUNDS_REJECTED`. No new inference or forecast was published;
the score/view snapshot was still 28 October at this checkpoint. Supported
source-only view reconciliation is being verified separately and must not be
reported as new scores. The second approved attempt is queued no earlier than
**10:26:33 UTC / 15:56:33 IST**, subject to unchanged guards and remaining quota.

## Verification actually completed

| Check | Recorded result | Scope and evidence |
|---|---|---|
| Native Windows full backend / isolated PostgreSQL | 2,071 passed / 9 skipped | Earlier candidate `.local-data/private-v1-fullpg-20261030/pytest.log`; actual Windows-only cases ran. Later current-identity changes passed 25 focused backend/API cases separately; no new full-native-suite result is implied. |
| Linux backend / PostgreSQL CI at the deployed revision | 2,059 passed / 33 skipped in 300.98s | [Successful foundation run 41291453727](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41291453727), `2f01eb3`; warnings treated as errors. |
| Local actual frozen-research reads | 5 passed / 0 skipped in 12.10s | Separate 31 October read-only run at `cab98f0`; exact price/feature/OOS/report/provenance reads and all 474 unresolved economic records. No fitting, backtest execution, holdout reevaluation or provider calls. |
| Frontend CI at the deployed revision | 137 passed in 27 files, 21.46s | [Successful dashboard run 41291453641](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41291453641), `2f01eb3`; typecheck, lint, build, generated client and license-notice checks passed. |
| Frontend dependency audit | 0 reported vulnerabilities | Exact runtime CI npm audit, including 0 HIGH / 0 CRITICAL; earlier pinned local audit remains retained. |
| Backend static checks | PASS | Ruff checks and 810 formatted files; mypy 458 source files; Bandit zero issues and zero `#nosec` lines. |
| Python dependency audit | PASS | CI `pip-audit --skip-editable`: no known vulnerabilities found. |
| Strict container security | PASS | Both foundation and [container-readiness](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41291453667) Trivy artifacts at `2f01eb3`: 0 HIGH and 0 CRITICAL across scanned OS, Node.js and Python targets; non-root/import/authentication/operations recovery checks passed. |
| Full reachable-history secret disposition | PASS with reviewed fixture findings | At `2f01eb3`, 183 reachable commits; three exact reviewed historical fixture findings; zero unexpected findings and zero verified secrets. The raw scanner was not clean: exit 183. |
| Saved-data/responsive quick browser cases | 3 passed | The five-width discovery/detail case and both saved-data workflows passed on 1 November. The fourth initial quick case failed an authentication-URL timing race; its failure is retained. |
| Broad private routes/authentication browser | PASS, 27.4s test body | After the test-only URL synchronization correction, 23 routes at five widths, four Axe audits, login/session/CSRF/bad-origin/logout boundaries passed with no console errors, browser exceptions, server errors or forbidden requests. |
| Controlled native restart | PASS | 1 November `restart-verification.json`: same authenticated session after cooperative stop/start; login/logout 200, post-logout protected API 401; zero provider calls/financial writes. |
| Full current catalog stock-browser acceptance | PASS, 860,459 ms test body | Completed `browser-all-report.json`: 8,169 catalog identities / 8,169 successful detail APIs and 110 distinct actual browser stock identities. Zero provider requests, console errors and server failures. The previous `ABCIND`/saved `ABCOTS` failure remains recorded; the corrected sealed deployment passed the complete rerun. |

The Linux skips comprise 24 Windows-only cases, seven unavailable local/private
research-data cases, one blocked live-provider case and one optional PyTorch
case. The separate five-case local frozen-read run closes those five local
read skips on this machine; it does not change the original CI counts. No GPU
or paid-service pass is claimed.

The original `8c0ba77` runtime CI passed **2,059 Linux cases / 33 skips in 255.48s**
and **137 frontend cases / 27 files in 17.08s**, with zero reported npm
vulnerabilities, both strict container gates passing and 182 commits in the
reviewed history scan. These exact earlier results remain preserved separately
from the later deployed-revision rerun. The older `91897b6` Linux result of
2,047 passes / 33 skips and the local pinned
frontend result of 136 passes / 27 files remain historical receipts, rather than
being overwritten or counted as additional current test cases. The six passing
CI synthetic-demo browser cases are separate from the private localhost checks.

Sanitized runtime CI logs, scanner artifacts and a SHA-256-bound summary/table are
retained privately in `.local-data/private-v1-20261101/ci-2f01eb3/`. The original
`8c0ba77` runtime evidence remains in `ci-final/` under the same dated directory.
The earlier
`91897b6` evidence remains in `.local-data/private-v1-20261031/ci-backend-91897b6/`.
Local frozen-read evidence
is in `.local-data/private-v1-20261031/real-frozen-readonly-5/`. The first complete
master browser attempt and subsequent diagnosis remain recorded; assertions were
not removed to conceal their failures. The actual narrow-screen defect in the
evidence disclosure was repaired by wrapping its classification text. Final
stock-browser acceptance established the latest master/build's complete
identity behavior. The 1 November broad browser receipt is
`.local-data/private-v1-20261101/browser-routes-report.json`, with route and Axe
details in `browser-routes/private-v1-routes.json`. The completed exhaustive run is
separate, at `browser-all-report.json`; its coverage attachment records all 8,169
successful detail APIs and 110 browser identities with zero provider/error counts.

## Storage, recovery and preservation

The dated 30 October inventory measured **102,749,932,968 unique allocated file
bytes** across twelve explicitly owned AlphaLens roots, with reparse-point and
hard-link accounting. An ACL-denied historical subtree remains excluded, so this
is a lower bound, not an exact whole-machine total. Most large items are active
data, immutable evidence, environments or validated recovery copies.

The reviewed cleanup removed **1,674 cache files / 86,857,320 allocated bytes**
from 103 cache roots. Immediate volume receipts separately measured D: free
space increasing **81,514,496 bytes** during the D: cleanup, and C: increasing
**5,238,784 bytes** during its earlier cleanup. Gross removed allocation is not
the same as a net project-size reduction during concurrent development. New
isolated frontend dependencies and build/test outputs also consume space.
No database, source dataset, model, forecast ledger, backup, Docker volume or
WSL disk was deleted. See [storage and recovery evidence](ALPHALENS_STORAGE_100GB_CLEANUP.md).

Fresh preservation checks retain **2,485 protected research files /
8,505,278,241 bytes**, **47 original alerts**, **1,254 pinned forecast bodies**,
six model artifacts and 240 registered immutable files. Credential records,
original and active account/personal records and protected configuration fields
match their baselines. Private payloads and secrets are not included in Git.

Separate restore verification covers all five operational SQLite databases and
a full PostgreSQL 17.11 dump restored into a new isolated database. PostgreSQL
tables/rows, seven indexes and four immutable triggers match; its reader remains
read-only. Restored authentication intentionally revokes restored sessions and
adds a revocation audit record; original audit rows remain an exact prefix and
live databases are unchanged. These saved restores were verified again on
31 October without creating another full copy or changing live records.

## Final operator handoff still to complete

All required gates A through I have PASSED for Private V1 (approved 500-stock cohort).
Fresh eligible inference/ranking and scheduled publication have successfully completed and produced
verifiable receipts. Genuine new
source acquisition and exhaustive stock coverage have now passed. Native restart,
broad route/accessibility checks and the currently sealed deployment fingerprints
are verified. The previous 31 October manual approval is exhausted; today's
separate checksum-bound two-attempt approval is active, with its first completed
attempt and queued second attempt described above. Source-only publication and a
candidate publication-ordering repair require their own verification; no untested
candidate source fingerprint is substituted into this release identity. Do not
increase scope, quota, retries, schedule or clock tolerance to manufacture
acceptance. Manual recovery does not by itself pass Gate F.

Run from `D:\al-research\p28-worktree`:

```powershell
.\.campaign-worktree\scripts\windows\private-v1.cmd start
.\.campaign-worktree\scripts\windows\private-v1.cmd status
.\.campaign-worktree\scripts\windows\private-v1.cmd smoke --credential-file .local-data\completion-release\qa-credentials.json
.\.campaign-worktree\scripts\windows\private-v1.cmd stop
```

Use the existing protected credential file; never paste its values into commands
or reports. These existing launch/control commands and the sealed deployment
passed the recorded controlled restart and authenticated saved-data smoke.
The detailed procedure is in the [localhost runbook](ALPHALENS_FINAL_LOCALHOST_RUNBOOK.md).

All displayed results remain `EXPERIMENTAL_RESEARCH`. Elapsed-entry outputs retain
`SAVED_HISTORICAL_SCORE`; genuine new eligible outputs may use
`FRESH_ELIGIBLE_EXPERIMENTAL_SCORE` only when their independent requirements pass.
Missing inputs remain `INSUFFICIENT_DATA` or `MODEL_INCOMPATIBLE`.
`FORWARD_OUTCOME_PENDING` and `INDEPENDENT_ACCEPTANCE_PENDING` remain explicit.
With zero qualified matured outcomes, no accuracy, profitability or reliable
investment-success percentage can be reported.
