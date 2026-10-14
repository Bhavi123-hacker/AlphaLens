# AlphaLens P30 final verification — 2026-10-14

The private local application and separate synthetic public demonstration work.
The original full objective is **PARTIAL**: durable daily collection and current
ML rankings remain evidence-gated. A genuine API response is not full-market,
model-acceptance or production-security clearance.

## 1. Upstox

- New credential imported/readback verified in a separate current-user Windows
  Credential Manager target. Alpha Vantage was preserved. Plaintext file unchanged.
- Local operator identified it as an Analytics Token. This category is operator
  evidence, not server-side token-scope introspection. No account/order/trade API
  was used to probe it. Only fixed official read-only market endpoints are implemented.
- Authenticated Historical Candle V3, Full Quote V3 and calendar/timing GETs
  returned200. Actual NSE master matched RELIANCE/INE002A01018/NSE_EQ exactly.
- Five-year private chart response:1,240 observed dates, earliest2021-10-13,
  latest2026-10-13. Initial bounded9dates:2026-09-30,10-01,10-05,10-06,10-07,
  10-08,10-09,10-12,10-13. Values were genuine and validated; no raw prices in Git.
- Final three-GET check used the current code: official master200,14Oct timings200
  and elapsed;13–14Oct candles200 returned only13Oct. The newest available provider
  daily close is13Oct;14Oct was closed with its EOD candle pending at verification.
  Provider close is distinct from independently verified official final close.
- Quote identity matched but its timestamp was about2seconds ahead of local receipt;
  it was rejected. No fabricated quote/close or clock-tolerance relaxation.
- Current central ledger recorded18live transport successes. An initial static
  download/network attempt occurred before central-ledger integration and is not
  falsely included. No live401/403/429 observed, no quota-exhaustion experiment.
  Initial network/master-validation failures remain in the earlier receipt history.
- Official historical/other-standard limits:50/second,500/minute,2000/30minutes
  per API/user. Quote V3's500-instrument batch size does not establish identical
  endpoint/user quotas. Conservative aggregate ledger, request budgets, bounded
  retries, Retry-After handling and redacted failures are enforced.

## 2. Daily data and exact remaining requirements

One verified watchlist identity was actually tested; its response coverage is1/1.
The current master contains2,701EQ-type candidates, not2,701historically eligible
common equities. A historical/common-equity eligible denominator is unavailable.
No full-NSE coverage or missing-session completeness claim follows.

Manual private descriptive observations are enabled. Durable retained provider
sessions acquired: **zero**. Raw market bodies/prices stay in transient memory.
The existing frozen archive remains a separate final-vintage historical source.

The unconditional DAILY software block and calendar-update replay identity issue were repaired. The existing P19 worker now
stages versioned Upstox observations after source/calendar/checksum gates; a bounded
acquisition command uses P28's existing provider ledger. Replay, recovery, correction
identities, partial/missing response and source-gate behavior are verified offline.
An unchanged replay makes no second GET; original session calendar facts are pinned, and unknown prior-day timing is refreshed from the official API within the same budget. Unknown dates are never filled by weekday assumptions. These fixture tests are not a live retained
session pass. Actual current configuration returns BLOCKED_SOURCE before network
or price storage. No pipeline root containing retained Upstox prices was created.

Official announcements support automated read-only analytics. Indefinite local
retention, private ML use and public market-data redistribution were not established
by the supplied answer or reviewed terms. The terms' customer-data retention clause
is not evidence of a licence for this project's market-data storage. Collection and
model acceptance are separate. See the
[component/evidence/next-action matrix](p30-daily-and-model-readiness.md).

The daily task XML passed actual Windows Task Scheduler COM parsing, disabled,
least privilege and unregistered. Its command is the guarded daily worker, not a
frontend full-market loop. Activation requires the applicable source-use clause,
current explicit official calendar facts and one successful permitted retained live
session. Source end-of-session timings do not establish a publication SLA.

## 3. Machine learning

All four stored candidates have verified checksums and identical38-column order:
HGB horizons1/5/20 and XGBoost horizon10.37numerical inputs can be described from
the genuine provider-observed slots. `momentum_percentile_20` needs a complete
eligible dated peer universe and peer return20 values; RELIANCE alone cannot supply
it. **Zero of38inputs are currently eligible for model inference.**

Additional blockers: compatible raw/adjusted basis; corporate-action coverage;
authoritative missing-session slots; publication/point-in-time availability;
dated common-equity identity/membership; source ML-use evidence; independently
accepted models and contemporaneous risk/universe snapshots.

The exact frozen XGBoost artifact's serializer issue was repaired using a checksum-
scoped type review. Actual deserialization verified38inputs/nativeXGBoost3.0.5,
zero predictions, unchanged artifact and unchanged global allowlist. This is
technical compatibility, not model acceptance.

All four candidate statuses remain REAL_RESEARCH_INSUFFICIENT_EVIDENCE. Stored
economic outcomes remain unresolved for474backtests;30have scoped raw-path
diagnostics. Three development folds do not establish strong significance, frozen
final-vintage timing is unknown, and prospective forecast/outcome count is zero.
There is no approved real-model promotion threshold/API in the existing contract.
No accuracy cutoff was invented and the holdout/thresholds were not rerun/retuned.

Actual forecasts:zero. Accepted current models:none. Genuine experimental
Top5/10/20lists:unavailable. Frozen P12 excludes non-TEST_ONLY ranking while
model-selection evidence is insufficient. Synthetic interface behavior is separate.
Exact feature order and acceptance requirements are in the audit; the
[new compatibility receipt](p30-model-compatibility.json) supersedes prior technical
type-readiness conclusions without overwriting their historical receipts.

## 4. Private application and PostgreSQL

- App running at http://127.0.0.1:8017/login with the existing operator account.
  Actual existing login/logout passed through a local dialog, no password reset.
- Real private RELIANCE candlestick/volume/SMA/RSI/MACD/ATR charts, date ranges,
  source/basis/date labels, exact feature exclusions and Passport passed in browser.
- Historical market maps/screener/Research Intelligence and Evidence Passport work.
  A separate private one-instrument watchlist heatmap/screener exposes actual scoped
  metrics. Historical reliability is not labelled current accuracy. Unverified
  current indices/full-market breadth remain unavailable.
- Portable PostgreSQL17.11/SCRAM/loopback15430 verified. Dedicated P29-guarded
  database/read-only role, migrations and actual write rejection passed. Financial
  account/transaction/paper-account/event counts are genuinely zero. No financial
  fixtures were created in the operator database. Isolated restoration and four
  immutability triggers passed; unrelated services/databases were preserved.
- Owned application/database combined stop/restart passed; latest-code app and owned
  database left running, temporary TEST_ONLY8028 application stopped.
- Latest launcher check: API/authentication/PostgreSQL/storage/research HEALTHY;
  acquisition/inference policy blocks displayed separately, prospective count zero.

## 5. Public project

[Published demo](https://bhavi123-hacker.github.io/AlphaLens/) is live. No one-time
publication action remains. Pages deployment used the independent synthetic static
artifact, fixed P30 branch permission and OIDC. Default branch preserved. No private
backend, PostgreSQL, operator credentials or real provider values are public.

Desktop/mobile charts, filters, Passport, keyboard/accessibility and connect-src-none
isolation passed on the actual published URL. README includes safe synthetic
screenshots, limitations and project links. Large chart bundle warnings remain
visible; no warning threshold was raised to hide them.

## 6. Verification and security

Verified implementation commit:
[`142c94115adbe3a5fa4e6a98eb0e67d678f938b1`](https://github.com/Bhavi123-hacker/AlphaLens/commit/142c94115adbe3a5fa4e6a98eb0e67d678f938b1).

- [Foundation CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38589346828):
  **938passed/8skipped,274.98s**, actual Linux/PostgreSQL17, zero test failures.
  Frozen lock, Ruff/format/mypy/Bandit/Python dependency audit passed. Scoped
  TruffleHog passed; container build/non-root imports/auth/runtime checks passed.
  Overall workflow FAILED at the strict container vulnerability scan.
- Local Windows focused source/daily/model/API checks:final119passed; earlier26focused
  current P30 cases passed after the current-session UI change. Actual isolated
  PostgreSQL integration:8passed. Runs overlap and are not added together.
- [Frontend CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38589346547):
 78tests/13files passed; TypeScript/ESLint/private/static build/licence/client
 generation/npm audit passed, plus3static desktop/mobile browser cases.
- Private actual browser runs:9passed; additional13passed/1failed at an isolated
  auth-expiry path guard; safe test-root correction rerun8passed; genuine database
  browser1passed; final genuine private-source/database rerun2passed. Every failed
  scenario was corrected/retested; no clean whole-browser-suite claim is made.
  Archive/market/screener/ML/Intelligence/Passport/login/logout/mobile paths covered.
- [Public deployment CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38586699708):
  success,3static browser cases. Final actual published URL:3passed/11.0s.
- Actual protected credential value/encoding scan:857current source/private/static
  build files passed before final evidence files; no values/fingerprints printed.
  Backend-only token, no-store responses, fixed HTTPS hosts, auth/CSRF/origin/Host
  controls retained. No orders, account reset, paid services or public backend.
- Full original research checksum verification:2,485files/8,505,278,241bytes,
  original47alerts,152fits/504backtests/stored OOS evidence preserved. Final SHA
  reread passed15.718s; original C checkout clean and D frozen domains/locks unchanged.
- Fresh actual Trivy: **44HIGH/eightCVEs/zeroCRITICAL** on Debian13.7, no supplied
  fixed versions. [New sanitized scan receipt](p30-container-security.json).
  CVEs:2026-76642,78408,78409,78410,54369,16742,9538 and2025-69720.
  Current official stable-package status was reviewed; no compatible stable fix
  established. No OS mixing, suppressions, gate waiver or production-security pass.
- Initial new-branch whole-history TruffleHog run found3previously documented
  unverified TEST_ONLY examples, zero verified findings. The later scoped push scan
  passed. This does not erase or claim a clean complete historical scan.

## 7. Delivery and operator actions

Branch: [p30-upstox-final-integration](https://github.com/Bhavi123-hacker/AlphaLens/tree/p30-upstox-final-integration).
Milestones:
[`2346043b64d703b7568d0e71b30c0cec7839c685`](https://github.com/Bhavi123-hacker/AlphaLens/commit/2346043b64d703b7568d0e71b30c0cec7839c685)
and6efcfcc, followed by the verified restart correction
[`142c94115adbe3a5fa4e6a98eb0e67d678f938b1`](https://github.com/Bhavi123-hacker/AlphaLens/commit/142c94115adbe3a5fa4e6a98eb0e67d678f938b1).
Final evidence-only commit follows this report; implementation CI evidence remains
explicitly tied to142c941, not attributed to a later documentation commit.

From `D:\al-research\p28-worktree`:

```powershell
.\scripts\windows\start-p30-alphalens.cmd
.\scripts\windows\stop-p30-alphalens.cmd
```

Start is foreground; use another terminal for stop. The application is already
running. See [Windows runbook](p30-windows-runbook.md) for checks and safe daily
commands. No database administrator credential or new login is required now.

The operator may manually delete the original plaintext `apii.txt` and unnecessary
OneDrive copies following successful secure migration/test. No file was deleted
automatically. The remaining operator/evidence actions are the applicable source
retention/ML clauses and independently reviewed model/universe/action/risk evidence;
they are not another blanket permission request to continue engineering.

| Requested status | Result | Evidence scope |
| --- | --- | --- |
| UPSTOX_AUTHENTICATION | PASSED | Genuine market GETs; protected credential |
| VERIFIED_NSE_DATA_ACCESS | PASSED | Verified RELIANCE NSE_EQ only |
| NEW_EOD_INGESTION | BLOCKED_EVIDENCE | Transient live observations passed; durable retention unavailable |
| MARKET_DASHBOARD | PASSED | Frozen historical dashboard plus genuine one-stock private watchlist |
| DAILY_DATA_AUTOMATION | BLOCKED_EVIDENCE | Technical fixture pipeline and disabled Windows task prepared; no retained live pass |
| CURRENT_ML_INFERENCE | BLOCKED_EVIDENCE | 37descriptive/38required,0eligible; no accepted model |
| EXPERIMENTAL_RESEARCH_SHORTLIST | BLOCKED_EVIDENCE | Real rankings unavailable; separate synthetic demo works |
| POSTGRESQL_LOCAL_READINESS | PASSED | Real PostgreSQL17.11, read-only role, migrations, backup/restore |
| PUBLIC_STATIC_DEMO | PASSED | Actual deployed synthetic URL/browser checks |
| PRODUCTION_SECURITY | FAILED | Strict44HIGH CVEs; historical example scan limitation |
| OVERALL_LOCAL_RESEARCH_APP | PARTIAL | Verified manual/private historical research; full daily/ML objective remains gated |

Stable-package review references: [util-linux](https://security-tracker.debian.org/tracker/CVE-2026-78409), [ACL](https://security-tracker.debian.org/tracker/CVE-2026-54369), [ncurses](https://security-tracker.debian.org/tracker/CVE-2025-69720), [systemd](https://security-tracker.debian.org/tracker/CVE-2026-16742), [Perl](https://security-tracker.debian.org/tracker/CVE-2026-9538). No unsupported cross-distribution upgrade was applied.
