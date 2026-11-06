# AlphaLens operational acceptance — 16 October 2026

Delivery branch: `operational-acceptance`, based on verified P34
`5de2c2d618214e02aa5061ac7dc0705b8fa9600f`. D88 authorizes this work.
This is operational completion work, not a new research phase. Original operator
records and frozen research remain separate from the isolated browser test owner.
Sanitized clocks, classifications, counts, checksums, browser outcomes and private
collection receipts are in [the acceptance evidence](alphalens-operational-evidence.json).

| Required status | Actual observed result and evidence | Usable now | Exact remaining dependency |
| --- | --- | --- | --- |
| AUTHENTICATED_NSE_PRICES | Six exact NSE_EQ/EQ identities resolved: RELIANCE, BAJFINANCE, TCS, INFY, HDFCBANK, ICICIBANK. A single authenticated Full Quote V3 GET returned six displayable prices; Decimal previous-close arithmetic checked for all six. | Yes, authenticated private selected-stock view. | Valid read-only token, provider availability, fresh bounded receipt evidence. |
| DELAYED_PROVIDER_DISPLAY | `DELAYED_AUTHENTICATED_PROVIDER_PRICE` waits until at least one second after actual network receipt. Six-stock compiled-browser/backend price equality passed. Delay label, original receipt, provider generation, last trade and separate classification are displayed. | Yes. | Explicit refresh after quote expiry; additional network/chart latency can exceed one second. |
| STRICT_VERIFIED_QUOTES | Validator source unchanged. The compiled strict browser test failed **0/6**; an independent subsequent one-GET batch passed **6/6**. Both observations are retained; inconsistent strict acceptance is not reported as a universal pass. Indicative classification remains separate. | Per-observation only. | Generation must precede independent LOWER receipt bound; uncertain interval overlap remains indicative, generation beyond upper bound is rejected. |
| LATEST_EOD_CHARTS | Genuine selected-stock provider OHLCV, indicators, volume and interactive chart work. Latest available prior session is 15 October in this morning's observations. Archive switch remains independent. | Yes. | Today's finalized candle cannot exist before its actual session/publication; complete economic adjustment/final-close certification remains unavailable. |
| DAILY_RETAINED_INGESTION | Genuine RELIANCE **15 October** captured with two GETs (dated session timing + candle); original 14 October capture preserved. Replay returned identical run IDs with **zero GETs**. | Yes, private operational staging. | Narrow private noncommercial permission; unknown publication instant, basis/actions and historical eligibility remain explicit. |
| DAILY_AUTOMATION | `AlphaLens-Private-EOD-Watchlist` registered/enabled, `Limited`/`Interactive`, **08:30 IST**, prior sessions only. Actual task invocation returned **LastTaskResult=0**, **zero provider GETs**. Next scheduled run: 17 October 08:30 IST. | Yes, selected RELIANCE scope. | Computer running and operator logged on; independent clock/date/source checks must pass every run. Schedule is conservative, not a publication guarantee. |
| NSE_DISCOVERY | Current master actually resolved **2,699** NSE_EQ/type-EQ identities, differing from the earlier 2,697 snapshot. Search and pagination do not fetch market-wide prices. | Yes. | Current discoverability does not establish dated historical common-equity or model eligibility. |
| OBSERVED_COHORT_SCREENER | Actual selected-watchlist heatmap, technical screener and comparison passed browser regression. Quote batch local limit remains 50; historical requests stay explicit. | Yes, observed cohorts only. | Stocks without loaded candle evidence remain absent/unavailable; no full-NSE performance claim. |
| PERSONALIZED_RESEARCH | Preferences, watchlists, supported numerical technical/volatility/drawdown/liquidity constraints and descriptive Decision Desk passed actual compiled-browser checks. Candidates/exclusions retain source/date and missing evidence. | Yes, descriptive research. | Risk-category suitability and unsupported sector/history evidence are not inferred; no approved adviser claim. |
| PORTFOLIO_ACCOUNTING | Actual manual multi-lot/partial-sale browser workflow: 10 shares at 100 + 10 fees; 5 at 200; sell 12 at 250 with 5 fees. Exact FIFO realized P&L **1,585**, remaining 3 shares/basis **600**; hypothetical reduction leaves ledger unchanged. These are TEST_ONLY bookkeeping inputs, not executions. | Yes, user-recorded ledger. | User-entered transactions/fees; no invented broker confirmation, dividends or verified cash balance. |
| PORTFOLIO_RISK_REVIEWS | Concentration, dated provider EOD indicative marks, user threshold reviews and cost-aware what-if scenarios passed. Uncertain display quotes remain excluded from ledger valuation, alerts and analytics. | Yes, indicative and descriptive. | Corporate-action reconciliation and compatible economic valuation remain separate; no uncertain-quote P&L preview was enabled. |
| HISTORICAL_LEADERBOARD | Genuine archive historical leaders, historical ML evidence, passport and explanation passed browser checks. Missing-path risk stays unavailable; observed-endpoint movement is labelled. | Yes, historical research. | Archive ends 6 October; frozen model evidence is not current predictive acceptance. |
| CURRENT_MODEL_FEATURES | All four saved artifacts re-audited: four checksum passes, exact ordered **38** inputs, three ordinary type reviews and one exact-artifact XGBoost review. Every feature's formula/lookback/input gaps exposed. Current model-eligible vectors: **0**. | Inspection and descriptive indicators: yes. Current scoring inputs: no. | Compatible basis/action evidence, complete trailing official sessions, authorized known-at observations and dated full peer return20 cohort. Original momentum-percentile formula is unchanged. |
| EXPERIMENTAL_ML_RESEARCH | Separate `workers.daily.experimental` workflow implemented and tested as `EXPERIMENTAL_UNVALIDATED_RESEARCH`. Requires complete finite ordered inputs, per-feature availability, source permission, checksum-bound compatibility/action/calendar/peer reviews and pinned artifacts before loading. Actual exploratory predictions: **0**. | Software prepared; real scoring waits for qualifying input bundle. | Missing genuine compatible vectors above. Review references are trusted local evidence, not a public attestation service. |
| ACCEPTED_CURRENT_ML | No model accepted or promoted. Existing prospective store/maturity/baseline software is tested; prospective protocol remains separately versioned. | No accepted current predictions. | Independently signed numerical/power registration, genuine prospective sessions and matured outcomes, calibration/stability/statistical/economic evidence and independent review. |
| TOP_5_10_20_ML_RANKINGS | Accepted ranking service remains unavailable and unpopulated; descriptive candidates and historical leaders are separately accessible. | No accepted current ML lists. | Complete eligible inputs and independent acceptance plus unchanged P11–P14 publication gates. |
| PUBLIC_SYNTHETIC_DEMO | Existing separate synthetic demo preserved; no private provider payloads or user records added. Final demo regression recorded below. | Existing synthetic demo only. | No real market backend/public redistribution authorized. |
| PRODUCTION_SECURITY | Default runtime migrated to digest-pinned supported Ubuntu 24.04/Python 3.12 after genuine comparison: old trixie **44 HIGH/0 CRITICAL**; candidate and new normal container gate **0 HIGH/0 CRITICAL**. Frozen application dependencies unchanged; native imports, non-root/auth/recovery smoke passed. | Container HIGH/CRITICAL gate: passed. Native loopback: yes. | Scans are dated evidence, not permanent guarantees or public-production approval. First full-history secret scan retained three unverified historical test/documentation URI/Postgres findings; final changed ranges have separate evidence below. |

## Implemented operational behavior

The delay uses the original monotonic network-receipt anchor; it never changes
provider or local timestamps, adds tolerance or proves chronology by waiting.
The existing strict validator remains byte-identical. Expiry removes indicative
payloads and returns the dated EOD fallback without polling. Uncertain quotes
cannot enter internal analytics caches, alerts, ML, economic valuations or ingestion.

Collection is independent from intraday quote classification. Each actual CLI
run verifies independently bounded NTP evidence/date agreement, rejects clock
rollback/discontinuity, and rechecks before/after acquisition. Public NTP is
unauthenticated and this assumption is visible. One intervening clock-evidence
failure stopped collection; it was not counted as a successful replay.

Daily configuration supports **one to six explicitly selected verified keys**,
at most three GETs per key/eighteen per run. Activation deliberately retains one
stock, not the whole master. Bounded catch-up scans missing dated session facts,
including official responses with no open NSE session; unknown/malformed responses
do not become trading dates. No weekday-based calendar reconstruction is used.
Catch-up is limited to 30 days and flags older gaps for explicit review. Empty
candles remain pending and can be retried on a later run; they never freeze an
empty accepted capture. Completed captures replay without re-downloading.
An explicit single-stock correction review fetches at most one candle, preserves
the original capture and stages changed values as a separate immutable revision.
No periodic correction polling is enabled.

Source basis/action/publication and dated-universe gaps remain attached to
operational observations; retained staging does not join or rewrite frozen
canonical research. Discoverable identities, queried keys, observed EOD coverage,
dated common-equity eligibility and model eligibility are distinct counts/states.

The approved private-use evidence remains the specific
[Upstox private research reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3),
with its [recorded narrow scope](../data/p34-private-upstox-use-decision.md).
The [official quote contract](https://upstox.com/developer/api-documentation/get-full-market-quote-v3/)
defines previous-session close; the
[dated market timing endpoint](https://upstox.com/developer/api-documentation/get-market-timings/)
identifies exchanges open on a requested date. No provider promise of a fixed EOD
publication time is invented. NSE's
[official market timing/calendar page](https://www.nseindia.com/resources/exchange-communication-holidays?apiversion=v2)
and dated provider timing evidence remain distinct from candle publication.

## Verification record

* Targeted backend regression: **246 passed**, warnings treated as errors. Later
  correction/calendar tests: **28 passed**, overlapping the earlier set.
* Frontend unit/component tests: **90 passed**; TypeScript/build and ESLint passed.
* Initial compiled operational browser suite: **6 passed, 1 failed**. Failure is
  the preserved strict six-quote criterion (0/6), not delayed-price display.
* Broader compiled regression: **23 passed, 2 failed**. One expiry-injection test
  lacked its isolated auth-root environment setting; one legacy chart test assumed
  only strict/EOD states and local-receipt chronology. Its assertions now explicitly
  cover the already-authorized indicative state and independent LOWER bound.
  Final verification is recorded separately below; these failures are not erased.
* Initial sandbox-only targeted attempt: 43 passed, 13 temporary-directory access
  errors. With correct filesystem access the same set passed **56/56**. A first
  browser invocation lacked the existing D-drive browser path and ran no tests.
* Four real model checksums/type/order audits passed without estimator execution.
  Prospective results needing future sessions have not been generated early.

## Windows operation

The newest compiled application is served at **http://127.0.0.1:8017/login**.
From CMD, keep the start console running:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p33-alphalens.cmd
```

Cooperative stop from a second CMD:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p33-alphalens.cmd
```

Stop drains only the owned application, then smart-stops its owned PostgreSQL
cluster. Do not stop that cluster while an isolated verification instance uses it.
The P33-named launcher selects the updated existing private runtime configuration;
it preserves original authentication, records, credentials and database roots.

Task inspection/disable from PowerShell:

```powershell
Get-ScheduledTask -TaskName 'AlphaLens-Private-EOD-Watchlist'
Get-ScheduledTaskInfo -TaskName 'AlphaLens-Private-EOD-Watchlist'
Disable-ScheduledTask -TaskName 'AlphaLens-Private-EOD-Watchlist'
```

Manual bounded collection/replay from CMD:

```bat
scripts\windows\project-python.cmd -m workers.providers.daily --config .local-data\p34-runtime\daily-config.json
```

Private online backup and isolated restore retain the existing safe commands in
[the Windows operations guide](p33-windows-commands.md). Restore never overwrites
active personal stores; provider payloads and Credential Manager secrets are not
copied into personal backups. Verification below records actual backup/restore
and restart equality.

Inspect experimental readiness without loading an estimator:

```bat
scripts\windows\project-python.cmd -m workers.daily.experimental --config .local-data\p34-runtime\daily-config.json --model-root D:\al-research\tejhq-research-evaluation-v2-fit-parallel
```

Actual result: `COMPATIBLE_CURRENT_BUNDLE_REQUIRED`, four verified artifacts,
ordered 38-column contract and four required review families; zero predictions
and no estimator deserialization. The inputs-required exit status is deliberate.
A trusted local `--bundle` permits preflight; only explicit `--execute` can score
after complete identity/source/basis/action/calendar/peer/availability checks,
fresh independent decision-time evidence and exact artifact loading checks. No
bundle was fabricated. Results cannot populate accepted rankings or alerts.

## Final delivery evidence

* **Native delivery:** compiled index SHA256
  `8fa25c71fd25459029c55b4733c8ecb64e296d6dd601949f5c6da4ecfe8f6dfa`.
  Actual port8017 responses matched the compiled index on eight routes. Four
  private anonymous endpoints, including collection status, returned401.
  Original account/password hashes and original personal records matched the
  pre-existing P33 preservation baseline; no password reset or credential writes.
* **Financial persistence:** actual online backup/isolated restore passed for
  auth, alerts, operations, prospective and personal stores. Restored sessions
  revoked; source untouched. The isolated browser owner's1profile,25portfolios,
  14watchlists,12journal entries,11rules and4recent records survived restart
  byte-equivalently. The restarted authenticated socket returned the same owned
  records and exact FIFO event summaries. These are isolated TEST_ONLY records,
  not invented records in the original operator's empty personal workspace.
* **Frozen preservation:**2,485files/8,505,278,241bytes and47original alerts
  rehashed read-only; all byte-exact. Inventory SHA256
  `608201403f2e4f3b41bae9d8d1ed670b4accfefb691158fedefeb9104cf43c17`;
  original alert hash
  `dc32f54d31c0f683ef5a1566bc60bc9324a68d974ac446640aad8ee1177f5e41`.
  No frozen fit, holdout or historical backtest was rerun. No main merge.
* **Final local targeted backend:**253passed, warnings treated as errors,
  including independent date guards, fresh identity refresh, pending publication,
  corrected-revision deduplication, zero-GET replay, experimental input rejection,
  original FIFO/research contracts and authenticated API integration. This
  overlaps earlier targeted runs; counts must not be summed.
* **Actual compiled browser:**27/27regression cases passed after the two
  documented harness/legacy-expectation corrections. Final delivery build's
  four changed cases passed: selected three-stock chart/price equality, six
  delayed provider prices, independent qualified daily status and inactive
  accepted ML, plus research diagnostics/accessibility. These overlap earlier
  cases. The separately preserved strict0/6failure is still a failure; it was
  explicitly excluded from the later display regression and is not counted passed.
* **Frontend:**90unit/component cases passed; three affected daily-component
  cases passed again after label clarification. TypeScript, ESLint and compiled
  delivery build passed. Published unchanged synthetic demo:4/4browser cases.
* **Private security:**903source/build files scanned against actual protected
  credential values and encodings, zero matches. Real foreign Origin rejected;
  actual PostgreSQL reader remained SELECT-only with zero financial write
  privileges and unchanged empty financial tables. Final source/build refresh
  is included in the evidence file when collected.
* **CI migration evidence:**
  [initial comparison run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38851650265)
  passed1116tests/eight expected skips, static checks, Bandit and dependency audit;
  old default container failed44HIGH while the supported Ubuntu candidate passed
  the same strict severity gate. Its first-new-branch whole-history secret scan
  failed on three unverified historical findings in two test files and the
  command log, zero verified findings. No finding was suppressed or history rewritten.
* [First fully green migrated foundation run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38852279138):
  1116passed/eight skips, static checks/Bandit/dependency audit, native/auth/recovery
  container smoke,0HIGH/0CRITICAL and unchanged TruffleHog changed-range scan
  with0verified/0unverified findings. The later
  [experimental identity hardening run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38852524499)
  also completed green. One intervening import-order lint failure was corrected;
  it is not represented as a passing run.
* Final correction/CLI implementation commit:
  `bcdd0805f8f0a33922193e2af4abf60d884be33a`.
  [Final foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38863777549)
  **PASSED:1118tests/eight expected skips,280.66seconds**, actual PostgreSQL17,
  frozen lock/sync, Ruff/format/mypy, Bandit, dependency audit, unchanged strict
  TruffleHog changed-range scan with0verified/0unverified findings, container
  build/native/auth/recovery smoke and **0HIGH/0CRITICAL**. The eight skips are
  absent local archive/research-sample integrations and the production/live gate;
  they are not replaced with invented observations.
  [Final frontend](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38863777459)
  **PASSED**, including90tests, lint/types/build, dependency audit, synthetic build
  and four synthetic-browser checks. Final report/artifact-privacy-only commits
  do not change the tested application implementation; their automatic runs are
  separate from these completed receipts.
* **Generated-artifact privacy:** two failure DOM snapshots containing transient
  prices were sanitized and one failed-login trace was removed. Original test
  verdicts/errors and sanitized timing/count metadata remain intact. Private
  authentication tests now disable trace/screenshot/video capture. No original
  research or pre-existing P34 artifact was removed.

The application is left running on127.0.0.1:8017 with the delivery build. The
isolated8029verification server is stopped. Daily collection remains enabled
only for the selected private scope; outbound notification delivery, orders,
accepted ML/rankings and public market-data deployment remain inactive.
