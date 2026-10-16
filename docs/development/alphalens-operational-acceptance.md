# AlphaLens operational acceptance — 16 October 2026

Delivery branch: `operational-acceptance`, based on verified P34
`5de2c2d618214e02aa5061ac7dc0705b8fa9600f`. D88 authorizes this work.
This is operational completion work, not a new research phase. Original operator
records and frozen research remain separate from the isolated browser test owner.
Final deployment, CI and preservation receipts are appended below as they finish.

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
| PRODUCTION_SECURITY | Native private application operates independently of container deployment. Strict scanning remains unchanged. Previous trixie scan: 44 HIGH/eight CVEs/zero CRITICAL; supported Ubuntu 24.04/Python 3.12 candidate added for genuine rebuild/import/auth/scan comparison. | Native loopback: yes. Production clearance: not established. | Final strict scan below; no severity waiver, scanner removal or unstable Debian package mixing. |

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

## Final delivery evidence

Pending the final CI, native restart, security and preservation receipts. This
section will be completed before final delivery; no pending check is called passed.
