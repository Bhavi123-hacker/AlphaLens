# AlphaLens real ML activation — 16 October 2026

The private application now trains and runs a genuine separate NSE experimental
model and displays its actual scored Top 5/10/20 lists. **The model did not beat
either predeclared baseline. It has no demonstrated predictive edge.** This
failure is visible on the research page. Numerical scores are available to inspect
the experiment, not as independently validated investment recommendations.

Running application: <http://127.0.0.1:8017/login>; after signing in, open
<http://127.0.0.1:8017/experimental-ai>. Original accepted ML services remain empty.
Branch: `experimental-real-nse-ml`, from `8d931ed0fbabce24f0b84c161134ff19b3554626`.
Implementation commit: `c51956cacc76f960220722297f585a088cce4c5a`; no main merge.

## Required statuses

| Status | Actual result and genuine evidence | Usable now | Exact remaining dependency |
|---|---|---|---|
| REAL_TRAINING_DATA_READY | 30/30 predeclared current NSE_EQ/type-EQ identities; 35,610 validated provider daily candles; 1,187 observed dates, 2022-01-03–2026-10-15. Immutable originals, identity/request linkage, receipt times and SHA-256 checksums replay with zero GETs. | Yes, private fixed-cohort retrospective study. | Exhaustive official historical session, membership, adjustment and publication/revision evidence is not established; no unbiased market-wide/PIT claim. |
| REAL_FEATURE_PIPELINE_READY | `nse.same-session-ratios.11.v1`: 35,040 complete vectors, 34,890 matured five-observed-session labels. Exact rational sign audit: zero differences across all matured original labels. | Yes, for this documented daytime-movement target. | Cross-session adjusted holding-return, volume-adjustment and original 38-feature compatibility remain separate. |
| EXPERIMENTAL_MODEL_TRAINED | One genuine StandardScaler + balanced logistic-regression fit on 20,760 actual training samples. Two real-data baselines: training-majority direction and trailing-five daytime direction. Reviewed scalar JSON model saved and reloaded; all 35,040 vectors agree with independent sklearn inference to 1.67e-16. | Yes, as unvalidated research. | Model failed final baseline comparisons; no predictive-edge or profitability claim. |
| CHRONOLOGICAL_EVALUATION_COMPLETE | Shared-date 60/20/20 partition; five-slot purge and five-slot embargo, train-only scaling, fixed parameters, no final-period selection. Final: 6,840 samples/228 dates, model balanced accuracy 48.0617%, majority 50.0000%, momentum 50.6259%. | Yes, actual unsuccessful evaluation and diagnostics visible. | More credible evidence would require a separately predeclared future study and independent review; this final period must not become a tuning set. |
| EXPERIMENTAL_CURRENT_INFERENCE | 30 actual model scores from latest supported complete observations dated 2026-10-15; genuine saved model and complete ordered vectors. A score-only replay generated no fit, holdout reevaluation, market GETs or duplicate forecasts. | Yes, explicitly dated prior-EOD experimental inspection. | 16 October historical daily candles were not returned in the one bounded after-close check; their publication remains pending. Current scores are not live quotes or wholly prospective full-horizon forecasts. |
| EXPERIMENTAL_TOP_5_10_20 | Actual 30-security scored cohort. Compiled browser verified list sizes 5/10/20, backend-score equality and exact provider-key chart links; page loading makes zero provider market requests. | Yes, separate experimental lists. | Not full NSE coverage; no independently validated ranking or calibrated confidence. |
| PROSPECTIVE_TRACKING_ACTIVE | Protected append-only ledger contains 30 actual-time research forecasts; **zero full-horizon eligible prospective forecasts and zero matured outcomes**. Duplicate replay: 0 inserts/30 replays. Reconciliation excludes all 30 partly elapsed initial horizons. | Tracking software and dashboard are usable; genuine prospective performance is unavailable. | A forecast created after newly available EOD inputs and before its first future daytime session, followed by five actual observed sessions and independently reviewed evidence. No records are backdated. |
| INDEPENDENT_MODEL_ACCEPTANCE | Not accepted. Final candidate underperformed both baselines; original four candidates and their acceptance contracts remain unchanged. | No accepted investment model. | Genuine independent review, stronger predeclared future evidence, calibration/stability/uncertainty and compatible source/economic evidence. |
| ACCEPTED_CURRENT_RANKINGS | Exactly zero; original accepted Top 5/10/20, signals, alerts and valuation services receive no experimental outputs. | No accepted current ML rankings. | Their independent model-selection/publication conditions must genuinely pass; this experiment does not promote them. |

## Source, cohort and methodology

The [predeclared study](experimental-nse-v1-predeclared-study.md) names the 30
securities and fixes features, target, split and model before training. This is
a manually declared diverse **current fixed watchlist**, not a historical NSE
universe and not a survivorship-free backtest. All 30 symbols resolved exactly;
no replacements were selected using measured returns.

Data came from the official Upstox V3 historical daily endpoint, bound to each
exact verified instrument key/ISIN/symbol. Retention and private derived ML use
rely on the [specific official private noncommercial research reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3),
with residual scope limits described in the [source audit](../data/experimental-nse-source-audit.md)
and [existing source-use decision](../data/p34-private-upstox-use-decision.md).
This is staff support evidence, not a public redistribution/adviser licence.
Raw data, model coefficients, individual scores and financial records remain in
protected ignored private storage; only code and aggregated evidence are committed.

Training snapshot ID:
`3c386bf53e253be3145d40cccb32c44c239b80db01fafa4e927fc1d6af92a875`.
Model ID:
`75790c2eabdb1c62d140775f66282a4d625cecd5a62c11fcdcb29203ff79d22f`.
Original training timestamp: `2026-10-16T07:24:28.545097+00:00`.
The later actual score-only run preserved that model and its evaluation bytes.

The initial capture used **31 GETs**: one master and 30 historical requests, no
retries. All candles passed positive finite OHLC/range, integer volume, timezone,
date, duplicate and exact master/request identity checks. The response itself
does not echo instrument identity; that limitation is explicit. Every instrument
has all 1,187 dates in the observed union: zero missing cohort slots, not proof
of an exhaustive exchange calendar. No missing date was filled.

Adjustment basis, exhaustive corporate-action coverage and original historical
availability/revision clocks remain **UNKNOWN**. Eleven features use only current
open-to-close return, intraday range/open, and trailing 5/10/20 mean, population
standard deviation and positive fraction of open-to-close returns. A uniform
positive multiplier of a candle's OHLC cancels in these ratios. This assumption
does not certify adjustment correctness or invariance to additive/inconsistent
adjustments. No overnight price jump, peer feature, cross-date raw level or volume
ratio is invented. The target compounds the next five observed-session C/O ratios;
it describes five separate daytime movements, **not buy-and-hold total return**.

Excluded: 570 initial rows lacking 20 observed slots; 150 feature rows with
unmatured five-slot targets. Duplicate/malformed/future observations fail closed.
Missing per-security slots and gaps over seven days invalidate affected windows.
The original archive and all its assumptions remain untouched.

## Measured evaluation

| Partition | Decision dates | Shared dates | Samples | Last target |
|---|---|---:|---:|---|
| Training | 2022-01-31–2024-11-12 | 692 | 20,760 | 2024-11-21 |
| Validation | 2024-11-29–2025-10-21 | 223 | 6,690 | 2025-10-29 |
| Untouched final evaluation | 2025-11-07–2026-10-08 | 228 | 6,840 | 2026-10-15 |

Fixed logistic parameters: C=1, balanced classes, seed 42, max_iter=1000;
convergence was checked. Validation balanced accuracy: 50.1759%.
Final precision: 42.8372%; recall: 50.3110%; Brier score: 0.253088;
score/future-daytime-movement Spearman correlation: −0.042632. These scores are
**uncalibrated**, not verified probabilities of success.

Whole-date-cluster bootstrap (300 draws, seed 42) final balanced-accuracy
improvement interval: versus momentum **[−4.6134, −0.2284] percentage points**;
versus majority **[−3.2918, −0.4691] points**. These intervals do not remove serial
dependence, current-cohort bias or final-vintage limitations. Quarterly results,
calibration bins, Top-5 membership turnover and 0/10/25/50 bps daily-exposure cost
sensitivity/drawdown arithmetic are saved and accessible in the evaluation panel.
Those scenarios assume separate observed daily exposures; they are not verified
fills, executable investment P&L or a portfolio backtest. No tuning followed the
poor final result. See the [numerical audit](experimental-nse-numerical-audit.json).

## Personalization, forward tracking and updates

The page links preferences, watchlists, exact stock charts/Evidence Passport,
Decision Desk and Historical ML Leaderboard. Existing manual holdings are read
through the FIFO engine; held/watchlisted identities and concentration-review
context are shown without trading instructions. Supported budget/dated-price and
volume constraints are evaluated. Unsupported close-to-close holding risk,
RSI/trend, sector and horizon compatibility remain missing; daytime-chain
drawdown is never substituted for holding drawdown. The authentic browser's
strict preference filter returned **zero complete matches** because requested
evidence was missing. This was displayed honestly, without padding lists.

Forecasts freeze actual record/inference time, vector/hash, feature order, model,
input dataset and original receipt lineage. SQL rejects updates/deletes. Outcomes
require genuine later complete observations, exact rational five-session C/O
arithmetic and post-forecast retrieval. Corrections create separate outcome
revisions; original forecasts and first frozen outcomes remain intact. Baseline
comparisons, accuracy/precision/recall/Brier and time-period summaries populate
only after eligible real outcomes mature. No prospective accuracy is claimed now.

The original **08:30 IST RELIANCE task remains enabled, Limited/Interactive**,
with its original selected-stock config and guards. No cohort acquisition or
inference task was enabled. New manual refresh supports at most 30 original
identities, a 30-day catch-up bound, shared quotas, immutable append-only source
snapshots, zero-request repeated/pending runs and explicit publication rechecks.
It does not silently revise old rows or establish exhaustive correction coverage.

After the session closed, one independently clock-guarded check retained the
official 16 October NSE timing evidence and queried all 30 daily candle endpoints:
**32 GETs, zero new candles**. No empty candle body was retained as market data;
metadata records publication/coverage pending. The run plus initial acquisition
used 63 GETs. No further provider recheck was made to force acceptance. The
zero-request up-to-date and pending replay paths were verified.

## Verification and preservation

- Windows full backend run: **1,156 passed, 19 skipped**, 1,255.36 seconds.
  Skips include unavailable isolated PostgreSQL test connection/optional research
  fixtures and existing live-production gates; they are not passing evidence.
- Actual Linux/PostgreSQL 17 implementation CI: **1,178 passed, 8 skipped**,
  215.78 seconds. Full Ruff/format/mypy/Bandit, frozen dependency checks and audit
  passed. Changed-range TruffleHog: **0 verified / 0 unverified** detections.
- Later final targeted checks covering new ML/acquisition/inference/prospective
  logic, personalization, API and native shell: **65 passed**. Ruff/format/mypy
  and the scoped Bandit checks passed. The full run predates those last additions.
- Frontend: **94 passed** in the complete run; final four experimental component
  cases, TypeScript, targeted ESLint and compiled build separately verified.
- Actual compiled Windows browser: **9 passed**, including six genuine NSE
  provider identities/charts, preferences, FIFO/multiple lots/partial sale/what-if,
  alerts, journal, import and archive leaders, plus experimental backend-to-rendered
  score equality, exact identity links and all three shortlist sizes.
- Published synthetic demo: **4 passed**, including private-API isolation and
  synthetic preferences/FIFO/journal. No real data was published to it.
- Original **2,485 frozen files / 8,505,278,241 bytes** checksum-exact; **47 original
  alerts** exact; account/password hash and personal records unchanged. All 193
  original protected tracked sources/schemas match Git content; three existing
  Windows CRLF checkouts were explicitly reported, not newly modified or used
  to normalize frozen artifacts. Credentials were never written/reset.
- Native restart verified the final compiled shell at port 8017 and anonymous
  private API rejection (401). The authenticated real UI test uses an isolated
  operator on port 8029 with the same compiled build and genuine shared source
  evidence; it does not reset or impersonate the original operator.

Development failures remain disclosed: the first genuine browser attempt exposed
a missing native shell allowlist entry for `/experimental-ai`; this was fixed with
regression coverage. A future-retrieval test's expected error text and a constructed
same-day clock fixture were corrected; the actual rejection gates were retained.
Initial new-branch full-history secret scan **failed** with zero verified and
three unverified historical URI/Postgres detections. It was not suppressed, waived
or made green by rewriting history. Changed-range and container results are
reported separately below.

Implementation CI evidence:
[foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38919239420),
[frontend](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38919239355).
The actual rebuilt strict container passed: **0 HIGH / 0 CRITICAL**, with non-root
runtime/import/authentication checks. Its scanner and severity policy are unchanged.
Frontend implementation CI passed (94 tests, four synthetic browser cases and
zero npm audit vulnerabilities). Foundation quality also passed, including the
actual PostgreSQL tests and unchanged security checks. These results cover
`c51956c`; the final freshness-label-only UI change has separate local component,
typecheck, lint, compiled-browser and delivery CI evidence. Initial full-history failure evidence:
[initial run](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38867588207).
Aggregated machine-readable evidence: [activation evidence](experimental-nse-activation-evidence.json).

## Exact Windows commands

```powershell
Set-Location 'D:\al-research\p28-worktree'
.\scripts\windows\start-p33-alphalens.cmd
```

Stop the owned native application and its owned PostgreSQL process:

```powershell
Set-Location 'D:\al-research\p28-worktree'
.\scripts\windows\stop-p33-alphalens.cmd
```

Explicit manual private experimental update; this does not register a task or
retrain the saved model:

```powershell
.\scripts\windows\project-python.cmd -m workers.experimental_nse refresh --root .local-data/experimental-nse-v1 --provider-root .local-data/p30-upstox-validation --permission-reference UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN
.\scripts\windows\project-python.cmd -m workers.experimental_nse infer --root .local-data/experimental-nse-v1
.\scripts\windows\project-python.cmd -m workers.experimental_nse reconcile --root .local-data/experimental-nse-v1
.\scripts\windows\project-python.cmd -m workers.experimental_nse status --root .local-data/experimental-nse-v1
```

`refresh --include-completed-today` additionally requires that dated official
session to have ended according to the independent lower clock bound; it still
cannot guarantee provider publication. `--retry-pending` is an explicit operator
recheck, not a polling loop. `train` refuses to refit an already initialized study;
future alternatives require a separately versioned predeclared experiment.
