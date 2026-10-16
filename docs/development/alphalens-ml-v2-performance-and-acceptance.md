# AlphaLens V2 performance and acceptance

V2 now runs a separate, genuine NSE price-return experiment and produces 31
current experimental research scores. **NO_DEMONSTRATED_EDGE**: the selected
model does not credibly outperform its predeclared baselines. Accepted Top 5/10/20
rankings remain zero. This report does not present numerical inference as proof
of profitability or independent acceptance.

Branch: `ml-v2-predictive-edge-research`, from
`30283d7dd9158d4507aeb7b99c8290b1d7092eda`. No main merge. Verified software commit,
CI links and native delivery receipt are recorded in the final delivery section.

## Genuine observations and source compatibility

The fixed cohort expanded from the original 30 to a predeclared 50 equities;
selection was documented before acquisition and was not based on historical
winners. Historical capture used 71 bounded GET requests: one current instrument
master, 20 additional historical series and 50 corporate-action reference
responses. The original 30 series were byte-copied and verified, not downloaded
again. Historical coverage is **59,350 daily candles / 1,187 observed dates**,
3 January 2022–15 October 2026. A separate 55-request after-close batch returned
all 50 genuine 16 October daily candles, bringing coverage to **59,400 candles /
1,188 observed dates**. No missing cohort slots or cross-security identical-OHLCV
groups were detected. One unexplained price discontinuity above 40% was
quarantined; no adjustment factor was invented.

Identity is exact current NSE_EQ/EQ key, symbol and ISIN. This is a current fixed
cohort retrospective study, **not** a survivorship-free NSE universe, historical
index membership or historical point-in-time publication archive. Missingness
checks use the observed-date union; they do not certify the full NSE calendar.

The [source audit](../data/ml-v2-source-and-target-audit.md) pins the official
Upstox staff evidence for split/bonus-adjusted historical OHLC, consistent daily
and intraday basis, and exclusion of dividend adjustment. Source-compatible
price-component returns are possible; total shareholder returns and complete
economic compatibility remain unverified. Rights, demergers, exhaustive action
history, adjustment factors and historical revision/publication clocks remain
unknown. We do not treat an empty reference response as proof of no action.

The narrow private noncommercial historical retention/features/ML scope follows
the specific official reply in topic 17302/post 3 and the existing Analytics
Token. This does not grant public market-data redistribution or investment
adviser approval. Raw corporate-action response bodies remain transient; only
minimal dated exclusion facts, checksums and receipt metadata are retained
privately under the disclosed derived-research interpretation. No raw prices,
model artifacts or feature vectors are committed or included in the public demo.

Original provider candle timestamps, retrieval times, immutable raw-body hashes,
exact decimal OHLC and volume remain in independent private V2 snapshots.
16 October's current daily candle uses the documented official `days/1` endpoint
after independently verified session close. Its classification is
`PROVIDER_AFTER_SESSION_CLOSE_NOT_CERTIFIED_FINAL`, not a certified final close.
Official dated timing responses establish 19 October's next opening and the
17–18 October closures. No weekday or guaranteed publication-time assumption was
used.

## Target, features and registered experiments

The primary target is **adjusted fifth-subsequent-session close / next-session
open − 1**. Decisions occur after the observation session and before a later
verified opening. This is a holding-price component, unlike V1's compounded
intraday target. An opening print is a hypothetical entry reference, not proof
of a fill. Dividends, actual costs, cash profit and execution capacity are not
invented. Ten- and twenty-session targets have availability diagnostics only;
they were not additional model-selection searches.

The [primary protocol](ml-v2-registered-protocol.md), baseline transforms and
[exact formulas](ml-v2-feature-contract.md) were committed before genuine fits.
The 20-feature contract covers 1/5/20/60-session price returns, 20/60-session
volatility, SMA distances, simple RSI14, normalized MACD, drawdown, normalized
ATR/range, intraday return summaries and four fixed-cohort context features.
It requires complete 61-slot histories, all known action-window exclusions and
at least 80% eligible contemporaneous cohort context. It generated no current
eligible vectors: 31 action-safe stocks are below the required 40. That failure
and its 13 genuine fits are preserved.

Before inspecting those performance metrics, commit `43340c2` registered the
[price-only companion](ml-v2-price-only-registered-protocol.md). Contract
`nse.adjusted-price-only.16.v2` contains exactly the first 16 features with the
same formulas and order, omitting all cross-sectional features. It retains
every per-security action, lookback, missingness and chronology exclusion; it
does not claim to pass the original context gate. The choice addressed observed
source availability, not which feature set scored best. Its separate immutable
models/evaluation/protocol are shown in the dashboard. No acceptance requirement
was reduced.

Both experiments use four fixed CPU configurations: balanced logistic
regression, ridge regression, histogram gradient boosting and random forest.
There is no hyperparameter search. Preprocessing fits only training rows.
Shared-date expanding annual development folds apply 20 observed-date purging
and 20-date embargo. Selection uses mean 2023–2025 fold date-rank correlation;
the already-known 2026 V1 period is explicitly diagnostic. None of these dates
is an untouched V2 independent test. The primary has three eligible annual folds
and 13 fits; the companion has four and 17 fits. Completed artifacts replay
without refitting. Failed candidates are retained.

## Measured development results

The companion's 39,847 evaluated security/date rows span 2 January 2023–8 October
2026. Model selection used the predeclared date-rank criterion, not the best
balanced accuracy in this table.

| Companion model / baseline | Balanced accuracy |
| --- | ---: |
| Selected histogram gradient boosting | 50.1085% |
| Logistic regression | 50.2819% |
| Random forest | 49.9634% |
| Ridge regression | 49.2773% |
| Majority baseline | 50.0000% |
| Momentum baseline | 48.8842% |
| Mean-reversion baseline | 51.1131% |

Selected companion mean date-rank IC is **0.001997**. Its moving-block
20-whole-date / 1,000-draw fixed-seed Bonferroni intervals for balanced-accuracy
improvement are **[−0.009336, +0.012414]** against majority and
**[−0.033308, +0.010308]** against mean reversion. They do not establish positive
improvement. These intervals control the registered 12 model/baseline
comparisons within each experiment; the two experiments add selection risk and
are not asserted to provide a global independent significance result.

The preserved primary selected gradient booster measured **49.7970%**, versus
majority **50.0000%** and mean reversion **51.8290%**, over 34,908 rows / 702 dates
ending 30 October 2025. Its mean date-rank IC was 0.024326. No primary 2026 fold
was fabricated when context-compatible rows were unavailable.

[Machine-readable aggregate evidence](ml-v2-observed-evidence.json) contains all
four candidates, exact fold boundaries, baselines, precision/recall, AUC, Brier
scores, calibration bins, date-rank IC, quantile separation, quarterly stability,
feature missingness/redundancy diagnostics and date-block uncertainty. Scores
remain uncalibrated model outputs; empirical probability calibration is not
established.

## Economic evidence

The nonoverlapping five-session reference-price simulation reports equal-weight
eligible cohort, model Top 5/10/20, momentum, mean-reversion and low-volatility
selections. Costs are explicit sensitivity assumptions: 10/25/50/100 bps round
trip plus 0/5/10 bps per side slippage. They are not verified broker charges.

For the companion at 25 bps round trip plus 5 bps per side, cumulative conditional
reference-price results were **−23.5106% Top 5**, **−29.2569% Top 10** and
**−28.1988% Top 20**; equal eligible cohort was **−33.5133%**. Model membership
turnover averaged 62.58%, 53.50% and 39.79% respectively. Endpoint drawdown,
volatility and assumed-period Sharpe are included in the aggregate evidence.
Within-holding path drawdown, actual fills, liquidity/capacity, dividend
entitlements and an independent source-compatible benchmark are unresolved.
These simulations do **not** establish executable profit or economic edge.

## Current research and forward evidence

The exact saved 16-feature gradient booster was securely reloaded from bounded,
checksum-pinned scalar/tree JSON. It produced **31 actual current scores**, using
genuine 16 October vectors. The remaining 19 securities retain explicit quality
exclusions. The dashboard displays genuine Top 5/10/20 from these 31 only; it
never pads coverage. Model ID:
`05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`.

All **31 forecasts were frozen at actual inference/recording time before
19 October 09:15 IST**, with original source hashes/times, immutable vectors,
model/data/feature/protocol versions and predeclared baseline scores. An
independent per-run clock bound was checked. Repeating inference inserted zero
records and replayed 31. No historical forecast was backdated into prospective
evidence. **Matured outcomes: zero.** The first required future session is
19 October; four further genuinely eligible subsequent sessions and their
actual observations/publication/timing evidence are still required. An exact
fifth-session date is not guessed from weekdays.

Maturity is conservative: the current worker requires a source snapshot retrieved
on a later local date than the fifth exit session, plus its verified session
chain. It does not mature an outcome from a same-day provisional candle. This
can delay reporting beyond the fifth session; it does not extend or change the
frozen five-session target.

The bounded clock evidence uses explicitly disclosed unauthenticated NTP
assumptions. Original network/local times remain unchanged; neither these
research checks nor delayed quote display promote a strict quote classification.
The private model/source evidence exposes the actual collection and decision
clock records.

Prospective reconciliation checks identity, chronology, later opening, five
complete slots, known actions and dated official session evidence. Corrections
append revisions; original forecasts/outcomes cannot be updated or deleted.
The companion does not manufacture the unavailable original cohort-regime
feature: regime acceptance remains missing until compatible evidence exists.
Actual independent economic/benchmark and calibration review are also pending.

The page links the real stock key to charts/Evidence Passport, preferences,
watchlists, Decision Desk and the preserved V1 workspace. Supported filters use
genuine dated momentum, RSI, SMA/MACD, volatility, drawdown, volume and observed
price; unsupported sector/fundamental or calibrated-risk requests remain
explicit. Portfolio holdings are contextual, not instructions or ledger marks.
Verification applied declared TEST_ONLY preference choices to genuine observations
without writing operator preferences: 31 broad supported matches and 31
zero-budget exclusions. The authenticated browser also checks the saved user's
actual filtering, without requiring that their preferences match a stock.

## Acceptance states

| Required status | State | Observed result / usability / remaining evidence |
| --- | --- | --- |
| V2_REAL_DATA_READY | PASS | 50 identities, 59,400 genuine candles; usable fixed-cohort research. Complete historical PIT membership/action/calendar evidence remains unavailable. |
| V2_FINANCIALLY_VALID_TARGET | PASS | Correct later-open to fifth-close adjusted price component; usable with stated assumptions. Dividend-inclusive executable economic validity remains pending. |
| V2_FEATURES_COMPLETE | PASS | Exact 16-feature companion runs on 31 current securities; primary 20-feature historical contract retained, current context shortage explicit. |
| V2_MODEL_TRAINED | PASS | Four algorithms in each experiment, 30 genuine fits total; secure saved/reloaded selected models. |
| V2_CHRONOLOGICAL_EVALUATION | PASS | Registered purged/embargoed shared-date development evaluation; no untouched historical V2 test claim. |
| V2_BASELINE_OUTPERFORMANCE | FAIL | Selected companion does not credibly beat all baselines; NO_DEMONSTRATED_EDGE. |
| V2_ECONOMIC_EDGE | FAIL | Net conditional reference-price scenarios lose money at the documented 35-bps scenario; complete executable economic evidence also pending. |
| V2_CURRENT_EXPERIMENTAL_RANKINGS | PASS | 31 genuine scores; Top 5/10/20 usable as unvalidated research, not accepted recommendations. |
| V2_PROSPECTIVE_FORECASTING | PASS | 31 actual-time forecasts before verified future opening; append-only/replay workflow operates. |
| V2_MATURED_PROSPECTIVE_OUTCOMES | PENDING | Zero; five subsequent eligible sessions and actual outcome evidence must arrive. |
| V2_INDEPENDENT_ACCEPTANCE | PENDING | Requires 126 matured decision dates, 1,000 outcomes, 30 securities, two quarters, registered statistical/economic gates and actual external reviewer. |
| V2_ACCEPTED_TOP_5_10_20 | PENDING | Zero; original accepted publication service is isolated and its gates remain unchanged. |

## Operations, preservation and verification

Collection and inference are separate manual operations. No V2 unattended task
is enabled and no material recurring provider load is authorized by this report.
The original Limited/Interactive 08:30 IST RELIANCE task remains enabled and
unchanged. A logged-on operator/machine and valid protected token are still
required; this task does not collect the 50-stock cohort.

The manual V2 capture workflow now appends separately hashed dated attempts,
preserves the legacy capture bytes, verifies its parent chain and never fills a
missed day. Full same-day replay makes zero market requests; publication-pending
attempts remain explicit and permit a later manual recheck. Missing-only retries
do not redownload already retained candles. Fresh derived action references are
queried under a maximum 110-request shared-quota budget; disappearing reference
events cannot erase earlier known hazards. No automatic polling was enabled.
Outcome maturity additionally verifies the official next-session chain, so an
entirely missed market day cannot disappear inside the observed-date union.

The first preservation receipt verified 2,485 original frozen files totaling
8,505,278,241 bytes; all 47 original alerts; operator/password hashes and personal
records; the pinned V1 model/evaluation; 33 byte-exact copied source files; and
30 preserved V1 scores. The existing Upstox transport AST is unchanged except
the exactly audited bounded read-only current daily endpoint addition. No
credentials were read by the verifier. Final restart/preservation verification,
CI, security and test receipts are appended below.

Local verification: all Ruff/format/mypy checks pass; V2 Bandit passes; 101
targeted backend/regression cases pass, plus separate 19-case model/feature and
16-case source/transport suites. A later 29-case forward/workspace run passes
after adding official maturity and companion-contract protections. These
overlap and are not summed into a fictitious distinct-suite count. Frontend:
97 tests, full ESLint and typecheck pass. Actual compiled Windows browser:
V2 Top 5/10/20 backend/DOM identity-score alignment and preserved V1 both pass.
The final results below distinguish these overlapping runs.

Software review subsequently found and fixed three forward-workflow defects:
score entry must match the frozen official timing; current inference receives
the immutable original-training baseline rather than requiring revised old
labels; and an action-unscorable resolved outcome is no longer counted pending.
The fixes have 53 passing targeted engine/forward/workspace cases. They changed
no model, forecast, historical metric, protocol or research acceptance criterion.

The first implementation run
[38931145686](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38931145686)
passed **1,252 backend cases / eight skips**, but the overall run **failed**.
Its container build omitted the two protocol documents because `docs` was
excluded, so that attempt never reached scanning. The build context now permits
only those two documents. The initial full-history TruffleHog scan also failed
with **three pre-existing unverified findings / zero verified secrets**, matching
the previously documented V1 history result. That failure is retained; it is
not called a pass, suppressed, or repaired by rewriting history. Later normal
push-difference scan results are identified separately.

The rebuilt container in
[38931722249](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38931722249)
passed non-root/native/authentication checks and the unchanged strict scan:
**zero HIGH / zero CRITICAL**. Its actual scanner artifact SHA256 is
`2d879c34d513d7872d42790fd46de03b88c7e7922a5d223ec6af8c45c5070700`.
Scanner severity, exit policy and suppressions are unchanged. Frontend CI
[38931722341](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38931722341)
passed. The software-review fixes have the separate final CI evidence below.

### Final verified delivery

Verified software commit **`c4f8e564f1fe501fa660c50a975ac3642a304147`** is pushed on
`ml-v2-predictive-edge-research`. Its
[foundation CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38932944205)
and [frontend CI](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38932944259)
both passed. Actual Linux/PostgreSQL integration and backend result:
**1,257 passed / eight skips**. Ruff, formatting, mypy, Bandit, dependency audit,
container runtime/authentication and the unchanged strict security controls passed.
The final normal push-difference secret scan found **zero verified / zero
unverified** detections. This does not replace the separately reported failed
initial full-history scan.

The final rebuilt container again has **0 HIGH / 0 CRITICAL**; scanner artifact
SHA256:
`9e73e049dbd3c701052c7065b0f0c6013a0a591bacf5aec4e9db1ac902cc3cc5`.
Frontend verification includes **97 tests**, typecheck, ESLint, build, dependency
audit and four synthetic-demo browser cases. Local Windows verification includes
one coherent **151-case** backend/portfolio/daily/API run, separate final
**53-case** model/forward/workspace and **22-case** source/transport runs, and
**52** targeted delivery cases. These overlap and are not added together.

Five distinct actual authenticated compiled browser scenarios passed: genuine V2
ranking/rendering and preferences; preserved V1 research; funded manual lots,
FIFO realized P&L **1,585**, remaining basis **600**, what-if exit and export;
the genuine-stock Decision Desk; and alert lifecycle/ownership. The last two
V1/V2 read scenarios were repeated successfully after the final backend restart.
The V2 browser confirms **31 actual supported preference matches**, exact
backend/DOM scores and stock links, Top 5/10/20 coverage, zero accepted ranks and
zero provider market requests from the research page. Four checks against the
existing published synthetic demo also passed. Manual financial test records
belong only to the isolated test operator and are not brokerage executions.

The actual native application was restarted on **127.0.0.1:8017** with the latest
backend and compiled V2 UI. The served index matches SHA256
`76d5105d729d5672ac84579ed12446c5eb766ec95a55052aa3b912776a499f4d`.
Login, V2 shell and liveness return 200; anonymous V1/V2 research and personal
APIs return 401. The authenticated browser uses the same compiled build and real
saved research under a separate existing test operator on port 8029. That owned
test application is now stopped; native 8017 and PostgreSQL remain running.
The original operator password was never reset or impersonated.

After the final restart, preservation again passed all **2,485 frozen files /
8,505,278,241 bytes**, 47 original alerts, original account/password hashes and
personal records, V1 model/evaluation and source snapshots. The original 31 V2
forecast IDs remain exact and outcomes remain zero. Training replay repeated
zero fits; inference replay inserted zero and replayed 31; genuine current-source
replay made zero provider GETs with a fresh independent clock check. A request
stub would have raised if replay had attempted transport, while the underlying
59,400 genuine observations and source files remained unchanged.

The original RELIANCE task remains Ready, Limited/Interactive, last result zero,
with its next 08:30 IST trigger unchanged. No expanded cohort task was registered.
The operator configuration has a byte-preserved backup; only compiled frontend
root and the new isolated V2 root changed. Protected credentials, database roots,
provider settings and original records are preserved. Aggregate delivery receipts
are included in [the evidence JSON](ml-v2-observed-evidence.json). The final
report-only commit adds these receipts; it does not change verified runtime code.

## Windows operation

The final local URL is `http://127.0.0.1:8017/experimental-ai-v2` (authentication
required). Start the owned native app and PostgreSQL:

```powershell
Set-Location 'D:\al-research\p28-worktree'
.\scripts\windows\start-p33-alphalens.cmd
```

Stop the owned native app and its owned PostgreSQL process:

```powershell
Set-Location 'D:\al-research\p28-worktree'
.\scripts\windows\stop-p33-alphalens.cmd
```

Manual saved-model inference/replay and research status, with no market requests:

```powershell
.\scripts\windows\project-python.cmd -m workers.experimental_nse_v2 infer --root .local-data/experimental-nse-v2
.\scripts\windows\project-python.cmd -m workers.experimental_nse_v2 status --root .local-data/experimental-nse-v2
```

Explicit manual after-close collection for the already approved fixed cohort;
this performs bounded provider requests only when observations are missing:

```powershell
.\scripts\windows\project-python.cmd -m workers.experimental_nse_v2 capture --root .local-data/experimental-nse-v2 --provider-root D:/al-research/p28-runtime/provider-state
```

This command is **not registered as a scheduled task**. On a holiday, before
verified close, with clock failure, or without provider publication it cannot
produce a new eligible session. Run `infer` separately after a successful new
capture; it freezes eligible forecasts and reconciles older ones. A missed
session remains missing and prevents maturity until genuine authorized evidence
is supplied. The first multi-date chain/retry tests use declared TEST_ONLY
fixtures; today's genuine capture/replay is separately evidenced, not presented
as observation of future sessions.

Training replay verifies and reuses completed artifacts; it does not rerun the
registered fits:

```powershell
.\scripts\windows\project-python.cmd -m workers.experimental_nse_v2 train --root .local-data/experimental-nse-v2
.\scripts\windows\project-python.cmd -m workers.experimental_nse_v2 train --root .local-data/experimental-nse-v2 --price-only
```
