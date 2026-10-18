# AlphaLens investment evidence completion

18 October 2026. Branch `alphalens-investment-evidence-completion`, based on
`4a0d61c2c988289ea49c3021df0fb0852bf68501`. Main and the prior branch are unchanged.
Engineering: `64582a4` protocol before evaluation; `2752fe0` integration and
reconciliation fix; `a7903f5` durable publication evidence and targeted worker stop.
Application: <http://127.0.0.1:8017/nse-market>.

## Actual outcomes

| Deliverable | Result / usable now | Evidence and exact remaining condition |
|---|---|---|
| Current common-equity search | PASS; yes | Official master refreshed with one GET at 11:07:14 UTC: 3,198 current verified common equities. This is not historical membership. |
| Genuine retained history | PASS for cohort; full market PARTIAL | 500 securities / 447,483 qualified candles, 3 January 2022–16 October 2026. Six non-trading-date rows remain quarantined. Zero newly acquired historical candles this execution; remaining 2,698 current identities are outside retained coverage. |
| Authenticated delayed display | PASS; yes, private | Six actual compiled displays match provider/backend identity and values, with one-second mode. No quote prices retained in test artifacts. |
| Strict quote acceptance | PARTIAL, 3/6 in current batch | Other three explicitly indicative. Previous batch was 0/6; no threshold change or universal clock fix is claimed. Actual generation/receipt ordering varies. A later single-stock shared-budget diagnostic was indicative; it is not added to or substituted for the six-stock batch. |
| Experimental Top 5/10/20 | PASS; experimental only | 300 actual V2 scores, exact backend/dashboard order and score matching, no padding, accepted publication still empty. |
| Horizon and personalization | PASS for declared scope | Five-session model ordering; ten/twenty-session descriptive volatility ordering explicitly has no trained forecast. Lazy saved budget/risk/volatility/drawdown editor and existing full preferences/filtering are connected. |
| Stock historical comparisons | PASS; known-period research | Observed holding returns, Ridge return estimates and LSTM scores have distinct axes. Returned-window MAE/RMSE compare compatible return targets with a zero-return baseline, never invented rupee prices. |
| Candidate explanation and scenarios | PASS; hypothetical only | Qualification, risks, compatible LSTM context and missing evidence; exact Decimal sizing plus 5/10/20% adverse moves, costs, budget allocation and loss-budget exceedance. Existing portfolio context uses remaining FIFO cost, not invented market weights. |
| Historical economic audit | PASS; yes | Original economics reproduced within 1e-12; costs, slippage, losing periods, concentration, turnover and four registered sparse-entry policies inspectable. |
| Positive strategy edge | FAIL: NO_DEMONSTRATED_EDGE | All four new policies remain negative at original costs; all eight paired baseline intervals contain zero. No new model fit or favorable post-hoc search. |
| Approved expanded registration | PASS; enabled | Exact 500-stock policy explicitly approved by user. Separate limited InteractiveToken task registered. RELIANCE unchanged. Registration is separate from successful capture. |
| Complete scheduled 500-stock capture | PARTIAL | First real run used five successful GET attempts, then was stopped for reconciliation scalability. Fixed reconciliation/inference recovered without acquisition. 499 stocks have the 16 October row; one remains incomplete. A complete new published session and successful scheduled run remain necessary. |
| Forecast preservation | PASS | 31 original plus 300 expanded bodies match backup byte-for-byte. Overlap does not establish 331 independent decisions. No new forecasts created. |
| Matured prospective outcomes | PENDING, zero | Real opening 19 October 2026 09:15 IST, five eligible subsequent sessions, qualified later retrieval, original exit rule and action/revision checks required. |
| Independent models / accepted rankings | PENDING, zero / zero | 126 matured decision dates, 1,000 outcomes, 30 securities, two quarters and all registered statistical/economic/calibration/stability criteria plus independent human review remain unchanged. |

## Root causes and fixes

| Issue | Cause supported by evidence | Action / boundary |
|---|---|---|
| Near-baseline ML | Weak information and period instability. LSTM BA 51.7606% in 2025 →47.5747% in 2026; XGBoost 53.0557%→48.3592%; reversal 52.2778%→47.3531%. | Preserve failures; no repeat fit or known-period optimization. |
| LSTM behind trees | Same-sample LSTM 51.1185% versus XGBoost 52.1928%; relevant paired uncertainty includes zero. | No established architecture advantage; retain all candidates. |
| Negative net returns | 84 full five-session liquidation/re-entry charges compound heavily; weak gross selection and 2026 losses also matter. | Reproduced original economics, separated costs/slippage and gross-period effects. |
| Turnover | Unstable top ranks and mandatory liquidation. LSTM membership turnover about 48.57%; original cost rule also liquidates unchanged names. | Four registered lower-frequency entries; no claim to have evaluated continuous carry positions. |
| Unclear product evidence | Raw diagnostics lacked connected interpretation. | Candidate explanations, stock comparisons, cost curves/tables, saved preferences and adverse scenarios in existing pages. |
| Only 500 histories | Deliberate bounded scope, not an undiscovered software switch. | Existing incremental engine retained; no unapproved bulk acquisition of remaining 2,698 identities. |
| Only 43 LSTM scores | Registered sequence study used first 100, not all 500; requires 20 consecutive complete eight-feature states with compatible evidence. | Preserve model applicability, exact inputs and missing-score states. No imputation. |
| Expanded daily bottleneck | Approval was absent; first approved run exposed full-history validation repeated per forecast shard. | Exact task registered. Partitioned reconciliation keeps full session clock and verified forecast identities; actual recovery 5.47 seconds. |
| Quote ambiguity | Provider generation may fall inside conservative receipt bounds; waiting does not prove ordering. | Strict validator unchanged. Nanosecond-preserving frontend explanation of bound position and older-trade versus fresh-response distinction. |
| Windows delays | Cancelled reads remained in two-slot queue; queue time excluded from deadline. Concurrent jsdom startup oversubscribed machine. Cold-browser timeout also remains intermittent. | Immediate queue cancellation and total 40-second deadline, same two permits. Two isolated Windows test workers; no deadline increase. Earlier failures retained. |

## Registered economic research

[Protocol](investment-frequency-v1-registered-protocol.md) committed `64582a4`
before execution. New private immutable report SHA-256:
`0a55dd7c1483fd0da79db5e2b849132fc612f8a707f70a76a9be91d4f387c09f`.
Exactly four policies, zero GETs and zero fits; the search is closed. Inputs are
27,820 saved known-period pairs / 97 securities. Original 2022–2023 training and
2024 validation remain unchanged; previously inspected 2025–October 2026 is
development evidence, not a newly untouched or prospective test.

| Original selection | Gross compounded | Net, central costs |
|---|---:|---:|
| LSTM Top 5 | −8.7210% | −44.9781% |
| XGBoost Top 5 | +13.0354% | −31.7746% |
| Mean reversion Top 5 | +23.2056% | −25.6199% |
| Equal eligible cohort | −2.0444% | −40.9300% |

Costs remain 50 bps round trip plus 5 bps slippage per side at each full allocated
round trip, including unchanged names. This is consistent with liquidation/re-entry,
not turnover-proportional carrying. LSTM end-point drawdown is about −47.88%; it
omits intervening daily losses. Gross losing LSTM references increase 47/84→58/84
after costs; XGBoost 42→55, reversal 42→52. Costs alone do not explain losses.

| New saved-score policy | Entry spacing | Gross | Net, unchanged costs |
|---|---:|---:|---:|
| LSTM Top 5 | 10 decision dates | −19.8437% | −37.8326% |
| LSTM Top 5 | 20 decision dates | −8.4586% | −19.3703% |
| XGBoost Top 5 | 10 decision dates | −8.0492% | −28.6249% |
| XGBoost Top 5 | 20 decision dates | −7.1054% | −18.1717% |

Holdings remain next observed open→fifth observed close. Cash gaps assume zero
return; approximate active fractions 50% / 25% are not continuous market exposure.
Each compares with same-schedule reversal and equal cohort. All eight paired 95%
intervals contain zero (500 four-decision moving-block replicates, seed 1729).
Intervals are exploratory without four-policy/two-comparator multiplicity correction.
Original 25/50/100 bps sensitivities and all failures are retained. No qualified
independent NSE index benchmark, verified fills, spreads or capacity evidence exists.
Current-fixed-cohort survivorship, final-vintage publication, incomplete actions
and dividends remain limitations. These are hypothetical reference results.

Original V2 remains BA 50.1085% versus reversal 51.1131%. Sequence experiment:
LSTM 51.1185%, forest 52.0173%, histogram boosting 52.1404%, XGBoost 52.1928%,
reversal 50.6571%; differences are not statistically established. Date rank IC
approximately 0.0601 / 0.0864 for LSTM/XGBoost; Brier approximately 0.250148 /
0.251245 and no established calibration. No model was retrained this execution.

## Data rights and actual operations

Existing private retention/derived research relies on the
[specific official reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3),
not unlimited polling, commercial use or public redistribution.
[Standard provider quotas](https://upstox.com/developer/api-documentation/rate-limiting/)
remain 50/second, 500/minute and 2,000/30 minutes. The audit found separate quote/daily quota stores for the same account; a protected single-hop quota link now routes both to the approved daily store. All 532 prior quote attempt records were copied without rewriting the original store. A genuine RELIANCE request verified four transport GETs and four shared reservations, zero new local reservations. Chained/invalid links fail closed, shared backoff applies, and approved task caps are unchanged.
Split/bonus-adjusted OHLC is not complete corporate-action or dividend-inclusive
total-return evidence. Historical availability and membership remain incomplete.
The prior 1,320-row older TCS probe stays outside models; no bulk older history
was downloaded. No qualified historical PIT fundamentals/news archive was found;
current public information cannot silently become past features. Public/personalized
advice needs appropriate review under the applicable
[SEBI framework](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&smid=0&ssid=3).

User approved exactly 500 stocks; 20:30/21:30/22:30 IST; maximum 250 stocks and
600 reserved GETs/run, 1,800/day, 60-minute cooldown and 31-day catch-up. Estimated
growth 5–20 MB/session, 110–440 MB/22 sessions excluding backups. Task
`AlphaLens-Private-NSE-Market-Research` is enabled/Ready, limited privilege,
InteractiveToken, IgnoreNew; first regular trigger 19 October 2026 20:30 IST.
Original RELIANCE task remains Ready, 08:30 IST.

Failures and recovery are preserved:

- Initial registration rejected a UTF-8 declaration on a Unicode COM XML argument.
  The script incorrectly continued and wrote a success receipt. Both remain in
  private evidence, explicitly superseded by a failure correction and later real
  registration. Fixed terminating errors and encoding; verified actual task before
  append-only registration evidence. No failed attempt is presented as successful.
- First manual scheduled trigger 16:25:55 IST used five successful source GETs;
  stopped for repeated full-history reconciliation. Windows exit 267014 is an
  interruption, not successful completion. Python redirector children outlived
  task stop; exact owned descendants were stopped, and a targeted helper now handles
  that case. The 600-request reservation/cooldown remain consumed.
- Actual recovery: snapshot 8.704 seconds, reconciliation 5.468 seconds, 300 pending,
  zero matured, zero GETs. Saved model inference/workspace recovery: 300 scores,
  zero new forecasts/GETs, 44.703 seconds. Original scores and forecasts preserved.
- History checkpoint replay: all 500 retained stocks, 450 additional checkpoints
  plus original seed; zero GETs/new securities, raw source fingerprint unchanged.
  This is not a complete new daily-session capture.
- Empty/incomplete publication now records immutable raw/checksum attempts before
  downstream work, never completed candles. Full-cohort new capture remains PARTIAL;
  its next real eligible publication/run must be observed. No cooldown bypass.

## Tests, security and preservation

- Local backend: 103 targeted passes; later pending-evidence additions separately
  covered by 22 focused passes. Ruff/format/mypy and targeted Bandit passed.
- Frontend: final 108/108. Initial Windows full run 107 pass/one search timeout;
  two bounded isolated workers reduced aggregate jsdom startup 124.22→24.78 seconds.
  Search test now waits for rendered options before keyboard selection. No timeout
  was increased; no failure was removed from evidence.
- Real compiled browser final: six/six in 1.5 minutes, including backend ranking/
  preferences/identity matching, horizon/economic/risk views, stock LSTM/history,
  FIFO/indicative exit and six actual quotes. Earlier two-pass/one 90-second cold
  timeout remains recorded; intermittent cold-browser behavior is not claimed fixed.
- API timing: fresh-process workspace 0.641 seconds; measured reads 0.75–1.375
  seconds. No page-load acquisition/training. Build passed with existing chunk warning.
- Native 8017 verification: latest compiled index, new economic route returns 401
  anonymously, original account/password/personal records unchanged. Online five-DB
  backup and isolated restore passed; restored sessions revoked.
- 2,485 frozen files / 8,505,278,241 bytes and 47 alerts byte-exact; V1 artifacts and
  protected Upstox AST unchanged. 240 immutable original files, 61 V1/V2 forecast
  bodies and four credential fingerprints verified without exposing values.
- All 331 original/expanded forecast bodies across 183 ledgers and 23 original
  sequence files match prior backup. Existing 5,005-file research backup reverified.
  No broad cleanup repeated; zero additional reclaimed bytes claimed.

Private metadata receipts: `.local-data/investment-evidence-*`, notably
`browser-final/report.json`, `quote-summary.json`, `history-replay.json`,
`partitioned-reconciliation.json`, `workflow-recovery.json`,
`expanded-preservation.json`, `frozen-preservation.json`, `native-verification.json`.
No private provider bodies or credentials are committed in this report.

CI `2752fe0`: [dashboard](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39121520212)
passed; [foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39121520222)
passed PostgreSQL/backend **1,450 tests / eight skips in 294.21 seconds**, all static/dependency checks, and rebuilt strict container with **zero HIGH / zero CRITICAL**, but failed its
whole-history secret stage. That failure is not a pass. Local verified all-result
branch-range TruffleHog found zero findings, exit 0. The
[three historical findings](../security/final-secret-history-audit.md) remain
audited unverified fixture/configuration detections; no suppression/history rewrite.

Latest engineering CI `a7903f5`:
[dashboard](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39121942921),
[foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39121942970).
Both completed successfully. Final source changes for shared quotas have their own subsequent CI, recorded below; an earlier successful run is not a claim about untested changes.
Public synthetic-demo isolation remains a separate CI check; no private deployment.

## Handoff

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\start-p33-alphalens.cmd
# In a second PowerShell window when stopping is intended:
.\scripts\windows\stop-p33-alphalens.cmd
```

These start/stop owned PostgreSQL and the compiled native app without resetting
records. Scheduled collection has a separate lifecycle. See the
[runbook](../operator/alphalens-runbook.md) for status, dry run, targeted worker
stop, backups and recovery. Login <http://127.0.0.1:8017/login>; original V2
<http://127.0.0.1:8017/experimental-ai-v2>.

Next empirical event: actual 19 October opening, then five genuine eligible sessions
and qualified later observations. No software can create those outcomes or
independent approval early. Experimental research is usable; proven profitability
and accepted investment rankings remain unavailable.

## Shared-budget completion

The separate quota-store issue was an engineering defect, not source permission
or a reason to widen any limit. Owner-protected linking preserves original data
and attempt records; same-account quotes, master refresh and scheduled collection
now reserve against one atomic SQLite ledger. Migration was performed while the
app was stopped and collecting workers idle. No source prices or credentials were
moved. User-approved cohort/cadence/quota hash is unchanged. The genuine four-GET
probe proves actual transport routing; test fixtures separately prove aggregate
quota exhaustion and backoff across clients. Optional LSTM context additionally
requires the same security and observation date as the displayed V2 candidate.

The 17 source GET attempts recorded before that diagnostic include five from the
first scheduled attempt, one identity refresh and eleven from the six-stock browser
verification. The diagnostic added four: 21 total, all successful HTTP outcomes.
No new historical acquisition or model training requests were made. A successful
HTTP response is not proof of a complete 500-stock session.
