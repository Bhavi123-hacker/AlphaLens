# AlphaLens master market intelligence delivery

This report supersedes the earlier consolidation checkpoint. It distinguishes current identity discovery, actually observed history, experimental model applicability and independently accepted predictions. The application is private and local; no brokerage order capability or public real-data service is introduced.

Branch: `alphalens-market-intelligence-master`, based on verified `b1b69086a234a62aaf3f69a2508086958d9818b7`. The separate sequence protocol was committed as `8b65e8b` before execution. Final delivery commit, CI links and the new compiled application verification are **PENDING** until their genuine receipts are available.

## Measured market and source coverage

The official Upstox NSE master was received on 17 October 2026 at `11:30:28.220996+00:00`. Its preserved compressed body is 1,982,987 bytes, SHA-256 `d6670c143b6e6e4b0260e9f6fec2decf0e2c979b3c4b9d2df3cc729cf265a38d`. The derived identity snapshot is `2d257a4edbd999e6e7bf86ae7a387139a6458ebfa22e25041d300c914fb8b210`.

| Scope | Actual observation |
|---|---:|
| All rows in official NSE master, including derivatives/indexes | 79,580 |
| Discoverable NSE cash-segment identities, including debt/funds | 9,832 |
| Discoverable type-EQ identities | 2,706 |
| Positively classified ordinary common equities across supported series | 3,198 |
| Original immutable V2 cohort | 50 securities / 59,400 candles |
| Configured expanded retrospective cohort | 500 securities |
| New securities in controlled historical acquisition | 450 |
| Instrument historical/action GETs across expansion checkpoints | 900 |
| Qualified expanded observations at the normalization checkpoint | 447,483 |
| Original V2 scored securities and immutable prospective forecasts | 31 / 31 |
| New expanded V2 scored securities / separate new forecasts | 300 / 300 |
| Genuine current sequence-model scores / sequence prospective forecasts | 43 / 0 |
| Matured prospective outcomes / independently accepted models / accepted rankings | 0 / 0 / 0 |

The checkpoints below are measured private acquisition receipts. Master, independent calendar and the separate older-history probe are outside these instrument GET counts. Original V2 data, models, evaluation and forecasts were not enlarged or overwritten.

| Cumulative configured/validated historical securities | Added securities | Instrument GETs | Capture elapsed seconds | Added checkpoint storage bytes | Capture-time reported observations |
|---|---:|---:|---:|---:|---:|
| 100 | 50 | 100 | 38.844 | 2,856,250 | 102,782 |
| 250 | 150 | 300 | 167.453 | 9,396,969 | 246,598 |
| 500 | 250 | 500 | 533.078 | 13,201,833 | 447,483 |

The 500-stock replay used **zero API requests** and reported the same 447,483 observations. Capture-time receipt counts are not retroactively rewritten after quality qualification: the first 100-stock capture reported 102,782 rows, whereas the later calendar-qualified sequence dataset contains 102,780, excluding two non-session rows. The current qualified full-cohort count is reported separately above. The capture-storage figures exclude later normalized snapshots, model/forecast evidence and compiled builds. Source dates span 3 January 2022 through 16 October 2026; unequal history and missing slots remain visible. Completed source normalization used zero provider requests and took 92.86 seconds. Actual full-universe historical coverage remains 500 of 3,198, not the entire market.

An additional bounded TCS history probe observed **1,320 genuine candles from 25 August 2004 to 29 December 2009** with one GET. Its isolated private exploratory archive is not a V1/V2/sequence training input and is not included in the 447,483 qualified cohort count. The initial proposed 2012–2021 range was refused before transport by the existing 3,650-day bound (zero requests); a corrected 2000–2009 request respected that guard. The documented V3 daily capability reaching January 2000 and supporting decade windows does not imply every security has data since 2000 or that a complete older market archive was collected.

History is a current fixed-cohort retrospective study, not a survivorship-free NSE backtest. Search covers positively verified current equities, including ordinary shares in supported surveillance/SME series; it does not prove every discovered equity has candles, technical history or model eligibility. Exact key/ISIN/symbol/series classification, exclusions, identity changes and the private source-use evidence are in the [source and universe audit](../data/full-nse-source-and-universe-audit.md).

The official staff reply supporting private noncommercial historical retention and derived ML was rechecked byte-for-byte. It does not grant public redistribution, commercial use, raw permanent Fundamentals archives or unlimited polling. The user-authorized staged manual expansion remains separate from recurring acquisition approval.

## Data correctness and observation availability

The engine retains immutable raw candle responses, actual retrieval timestamps, exact identity, checksum sidecars and minimal derived corporate-action exclusions. It checkpoints each instrument and resumes completed source work without downloading it again. Missing listings/history and incomplete action evidence remain explicit. A successful empty response is pending coverage, not a completed historical capture: its original body is preserved and a later bounded attempt can append new evidence.

An independently checked provider date, **26 April 2025**, was an official non-trading session and was quarantined from the expanded qualified dataset. The original frozen V2 dataset remains byte-exact. Official dates are checked where genuinely observed; the system does not claim a complete historical official calendar merely because a cohort supplied bars. Missing slots are never filled with invented sessions or prices. Revision conflicts require new evidence and are not silently overwritten.

Upstox source evidence supports split/bonus-adjusted OHLC, not dividend-inclusive total returns. Known incompatible actions exclude affected lookbacks/targets. Complete historical rights/demerger coverage, price vintages, availability clocks, historical membership and executable fills remain unverified. UNKNOWN is not upgraded to adjustment compatibility.

## Models, measured weakness and the separately registered sequence experiment

The original V2 companion remains the unchanged 16-feature price-only model. Selected histogram boosting measured **50.1085% balanced accuracy**, versus **51.1131% mean reversion** and 50.0000% majority. Its date-wise rank information coefficient was approximately 0.00200. Its scores are uncalibrated; increasing coverage does not improve those frozen metrics or establish out-of-training-cohort validity. The preserved conclusion is **NO_DEMONSTRATED_EDGE**.

The [measured weakness audit](ml-v2-weakness-audit.md) retains instability, calibration and cost evidence. For example, its saved nonoverlapping Top 5 price-reference simulation changes from +47.1775% gross price component to −23.5106% under the registered 25 bps round-trip cost plus 5 bps per-side slippage assumptions. These are hypothetical price-reference calculations, not executed profits, total shareholder returns or verified full-path drawdown.

The [sequence benchmark protocol](ml-sequence-v1-registered-protocol.md) defines one separate, fixed-budget experiment before model execution:

- Fixed first 100 current equities from the predeclared expansion plan; no winner selection or replacement of missing stocks.
- Twenty consecutive feature states with eight inputs in order: one/five/twenty-session return, twenty-session return SD, MA20 distance, RSI14, ATR14/close and open-to-close return. These reuse the unchanged V2 formulas and reject missing or action-excluded states.
- Target: fifth subsequent observed close divided by first subsequent observed open, minus one; positive versus nonpositive price-component direction. No same-close execution assumption, invented dividends or synthetic target.
- Training: 2022–2023, matured targets before 2024. Validation: 2024, twenty-date embargo and targets before 2025. Reporting: 2025 onward with a twenty-date embargo. These known historical years are **development evidence**, not an untouched or prospective test.
- One LSTM: eight inputs, one sixteen-unit recurrent layer, output dropout 0.1 and one logit; Adam 0.001, batch 512, at most twenty epochs, validation patience three, gradient clipping one, seed 1729 and two CPU threads. Scaling uses training observations only.
- Matched eligible observations for logistic regression, random forest, histogram boosting, ridge and XGBoost when already supported, plus majority, momentum and reversal baselines. No parameter sweep or post-result model selection.
- Report classification, ranking, stability, twenty-date-block uncertainty and nonoverlapping Top 5/10/20 cost sensitivity under the predeclared 25/50/100 bps assumptions plus slippage.

The registered run completed on **18 October 2026 at 00:34:26 UTC**, in **74.812 seconds**, using 102,780 qualified observations from the predeclared 100-stock cohort. It fitted one LSTM and five traditional models, with three non-fitted baselines: nine comparisons, not nine independently validated models. Four epochs were executed; validation selected epoch one. The numeric-only saved-model reload matched PyTorch within **4.378 × 10⁻⁸** absolute score difference.

| Split | Eligible sequences | Securities | Actual decision dates |
|---|---:|---:|---|
| Training | 31,665 | 81 | 29 April 2022–21 December 2023 |
| Validation | 18,693 | 88 | 30 January–23 December 2024 |
| Known-period development report | 27,820 | 97 | 29 January 2025–9 October 2026 |

| Candidate/baseline on the same 27,820 report sequences | Balanced accuracy | Date-wise rank IC |
|---|---:|---:|
| LSTM | 51.1185% | 0.06012 |
| Logistic regression | 51.2665% | 0.07642 |
| Random forest | 52.0173% | 0.08471 |
| Histogram boosting | 52.1404% | 0.07172 |
| XGBoost | 52.1928% | 0.08642 |
| Ridge return ranking | 49.9594% | 0.01766 |
| Training-majority baseline | 50.0000% | Constant score; IC unavailable |
| Five-session momentum | 49.3150% | −0.03719 |
| Five-session mean reversion | 50.6571% | 0.03719 |

The LSTM's paired twenty-date-block 95% balanced-accuracy improvement interval versus reversal is **[−2.2673, +2.9785] percentage points**; XGBoost's is **[−0.3825, +3.1743] points**. Both include zero. These exploratory comparisons retain model-selection/multiple-comparison risk. The positive point estimates do not demonstrate a credible independent edge. No winning historical comparator replaces the pinned V2 model automatically.

The LSTM generated **43 real current experimental scores**, with **zero new sequence prospective forecasts**. These overlap the 300 expanded V2 scored securities; 43 plus 300 is not a unique-stock count. All scores are uncalibrated. The LSTM's Brier score is 0.250148 versus majority 0.251810, but no probability calibration is established. Ridge's return MAE/RMSE are 0.0352835/0.0497071 in return units, not price error.

Across 84 nonoverlapping five-session reference decisions, at 50 bps assumed round-trip cost plus 5 bps per-side slippage:

| Reference strategy | Gross price-component return | Net assumed-cost reference return |
|---|---:|---:|
| LSTM Top 5 | −8.7210% | −44.9781% |
| XGBoost Top 5 | +13.0354% | −31.7746% |
| Mean-reversion Top 5 | +23.2056% | −25.6199% |
| Equal observed cohort | −2.0444% | −40.9300% |

The LSTM Top 5 endpoint drawdown was −47.8801% and mean membership turnover 48.5714%. LSTM and XGBoost Top 5/10/20 reference results remained negative at all registered 25/50/100 bps cost levels. These are assumed reference prices, not verified fills, net investment profits or complete intraperiod portfolio risk. The new study retains **NO_INDEPENDENTLY_DEMONSTRATED_EDGE**.

An engineering review found that the original report incorrectly included Brier/calibration diagnostics for Ridge's transformed return-ranking score and lacked a separately enforced current-score timing guard. No fit was repeated. The exact executing source, original report, model and historical predictions are preserved. The checksummed `report-final.json` removes only the inapplicable Ridge probability diagnostics and adds an explicit later engineering timing attestation; all scores and other metrics are unchanged. It attested all 43 saved current scores before the official 19 October opening using fresh independent bounds, source identity/price and saved session evidence. It explicitly does **not** claim the original process executed this later guard or that this is independent model approval. Future code now withholds optional current scoring when its source/future-entry guard fails.

Original model SHA-256: `062caac5753ec836208e82514e27c0b270f339c2709c1f4ea3b4a63a73626733`. Original report: `f6f89442853a9205c1f3302be63781f1e023c03fceb3c77fcc35b802a9195696`. Corrected derivative: `632d002e6c9fd1eb12d4e1b5d8240d288feb4b2d88412af75ebefbdd53c07eb8`. The optional isolated PyTorch 2.14.1 wheel was checksum verified after a normal download timeout and resumable recovery; its isolated dependency audit reported zero vulnerabilities. The main dependency lock/runtime is unchanged. An initial optional-environment Windows ACL/bootstrap failure occurred before an attempt/fit and was corrected; it is not represented as a successful fit.

The [five-reference audit](alphalens-reference-project-audit.md) records useful principles and rejected shortcuts. Historical fundamental/news features remain unavailable without source rights and point-in-time evidence; the existing current transient company/action references do not become historical training data.

## Research application and genuine shortlists

`/nse-market` presents saved universe discovery, separate coverage counts, paginated experimental candidates and explicit exclusions. `/analysis` provides bounded selected-stock authentic observations and historical chart sources; `/experimental-ai-v2` preserves the original experiment and forward ledger. Preferences, watchlists, Evidence Passport, portfolio and Decision Desk remain linked research tools.

The authenticated `/api/v1/nse-market/research`, `/status` and `/universe` routes read saved evidence only. They make zero provider requests, generate no inference on GET and append no forecast. Candidate and nested per-security arrays are bounded to at most 100 per page. Saved candidates receive company identity, observation date, exact existing model score, historical/technical evidence and supported preference matching; portfolio concentration uses remaining FIFO cost, not a silently assumed current market value.

The expanded model genuinely scored **300 securities**, producing exactly populated Top 5/10/20 research lists. Three authenticated compiled-browser cases passed in 40.5 seconds, including exact dashboard/backend ranking matching and read-only FIFO research. The exact private leaderboard bodies are available through authenticated `/nse-market` and private acceptance evidence, rather than redistributed through this public Git report. The 300-score receipt SHA-256 is `e84449eb672333f7d276bde38602412d6c9c1014adc7965e74a46b8a12ba8d5a`. No list is padded and no old score is relabelled with a newer capture date. Out-of-training-cohort scores remain experimental extrapolation, not calibrated probabilities of profit or approved buy/sell instructions.

The real 18 October 00:35:05 UTC six-stock quote batch used **one provider GET**: all six authenticated indicative displays and previous-close arithmetic checks passed. Strict VERIFIED ordering remained unproven, **0/6 accepted**, and was not relaxed. Source timestamps and truthful delayed/indicative labels remain separate from source-qualified EOD charts and stored historical observations.

## Daily operations and prospective evidence

The original `AlphaLens-Private-EOD-Watchlist` RELIANCE task remains separate at 08:30 IST. The expanded engine supports explicit identity scope, official session checks, actual source publication, bounded missing-only capture, quality gates, unchanged compatible feature generation, pinned inference, append-only forecasts and genuine maturity reconciliation. Independent EOD clock checks are separate from intraday quote chronology.

The proposed expanded recurring policy is **not approved, registered or activated**. Its actual zero-provider-request dry run verified protected credentials, matching Windows operator and independent clock readiness for the fixed 500-stock plan. The precise proposal is:

- Fixed 500 verified equities from the pinned plan; master refresh cannot silently add securities.
- 20:30, 21:30 and 22:30 IST, at most three attempts per IST day and at least sixty minutes between independent receipt bounds.
- At most 250 securities and 600 reserved GET attempts per run; at most 1,800 GET attempts per day. Each crashed attempt keeps its reserved ceiling.
- Missing-trigger recovery at the same operator's next login, potentially outside the evening slots, under the same caps. The machine, logged-in operator and protected token must be available.
- At most 1,071 requests for one complete 500-stock session under conservative two-request-per-stock, seventy-calendar-request and one-master-refresh bounds, assuming publication succeeds; failures remain pending. Publication time is not guaranteed.
- Catch-up is bounded to thirty-one calendar days per instrument, oldest eligible missing evidence first; source replay avoids unchanged redownloads. The complete 3,198-stock universe would need thirteen 250-stock batches and is **not** a complete daily job under the proposed three-run limit.

The disabled proposal XML is under `.local-data/full-nse-runtime/task-proposal-20261018/`; the policy configuration is `.local-data/full-nse-runtime/market-workflow-500.json`. Activation requires the user's explicit approval of these exact cadence/quota/scope/storage terms. The older 50-stock 120 GET/run, 360 GET/day proposal does not authorize this broader workload. Actual storage consequences are the measured source pilot growth above; retained daily observations, versioned normalized snapshots and forecasts add storage, and no automatic deletion policy is implied.

All **31 original V2 forecasts** remain frozen before the documented 19 October 2026 09:15 IST opening. The expanded cohort separately recorded **300 genuine new forecasts**; its global cohort declaration was frozen on 18 October at 00:32:10 UTC before that opening. These are distinct experimental stores; overlapping securities are not combined into inflated independent evidence. LSTM current scores created no prospective records. There are **zero matured outcomes**. Five genuine subsequent eligible observations, qualified next-open/fifth-close references, later retrieval/publication conditions and action/calendar/revision checks must occur before outcome calculation. No fifth date is guessed from weekdays. Historical predictions are not backdated prospective records.

Independent acceptance retains the registered **126 matured decision dates, at least 1,000 eligible outcomes, at least thirty securities, two quarters of qualifying evidence**, statistical/economic requirements and independent reviewer approval. Codex does not supply that independent review. Accepted ML services remain empty.

## Acceptance statuses

| Status | Result | Evidence and usable scope | Exact unmet prerequisite |
|---|---|---|---|
| FULL_NSE_DISCOVERY | PASS | One genuine dated official master; 3,198 positively classified common equities and bounded saved search. | Historical membership and observation coverage are separate. |
| FULL_NSE_HISTORICAL_COVERAGE | PARTIAL | 500 of 3,198 have genuine qualified history: 450 new securities, 900 instrument requests, 447,483 observations and zero-request replay. | Remaining genuinely accessible equities and qualified controlled acquisition; no complete-market historical membership claim. |
| VERIFIED_MARKET_DATA | PASS | Actual identity/hash-validated source responses; six authenticated indicative displays/arithmetic checks passed in one GET; 500 qualified historical securities. | Strict intraday VERIFIED remains 0/6; historical calendar/action completeness remains limited. |
| AUTOMATED_DAILY_EOD | PARTIAL | Original bounded RELIANCE schedule preserved; expanded guarded engine implemented. | Exact expanded policy approval and real scheduler readiness/activation evidence. |
| CORPORATE_ACTION_COMPATIBILITY | PARTIAL | Split/bonus basis evidence and known hazard exclusions; original methodology unchanged. | Complete historical actions, revision/availability evidence, dividend/rights/demerger compatibility. |
| IMPROVED_FEATURE_PIPELINE | PASS | Three hundred expanded stocks have complete frozen 16-feature inputs; actual 20×8 sequences, anti-lookahead and review safety tests passed. | Insufficient history, known actions and missing sessions still exclude other stocks; historical publication remains unverified. |
| LSTM_TRAINING | PASS | One registered genuine LSTM fit, four epochs/selected first, secure numeric reload parity 4.378e−8 and 43 current scores. | Engineering success is not predictive or independent acceptance. |
| FAIR_MODEL_COMPARISON | PASS | Six models/three baselines on identical 27,820 known-period development samples; train-only scaling, embargo, purging and paired date-block uncertainty. | Exploratory comparisons require genuinely unseen confirmation; no untouched-final-test claim. |
| MODEL_BASELINE_OUTPERFORMANCE | PARTIAL | LSTM 51.1185% and XGBoost 52.1928% exceed reversal 50.6571% point estimates in development; improvement intervals include zero. Original V2 failure preserved. | Credible statistical robustness and independent future evidence; no demonstrated edge. |
| HISTORICAL_STRATEGY_BACKTESTING | PASS | Eighty-four actual nonoverlapping reference decisions with predeclared 25/50/100 bps cost sensitivity and baseline comparisons. | Hypothetical price-reference arithmetic only; verified fills, capacity and full economic path remain absent. |
| POSITIVE_NET_STRATEGY_EVIDENCE | FAIL | New LSTM/XGBoost Top 5/10/20 net reference returns are negative at all registered cost levels. Original V2 cost failure remains unchanged. | Positive robust source-compatible economic evidence and genuine prospective confirmation. |
| EVIDENCE_BACKED_STOCK_SHORTLIST | PASS | Three hundred actual V2 scores, identity/technical/risk context, saved-only paginated authenticated workspace and compiled browser parity. | Cohort/model extrapolation remains experimental; unsupported facts are excluded. |
| PERSONALIZED_RESEARCH | PASS | Actual PersonalStore budget preference filtering preserved score/order; compiled candidate/FIFO research checks passed. | Unsupported sector/PIT/risk-category evidence remains explicitly missing. |
| EXPERIMENTAL_TOP_5_10_20 | PASS | Three hundred genuinely scored V2 candidates; exact Top 5/10/20 backend/browser checks passed. Separate LSTM cohort has 43 scores. | Not independently accepted or calibrated; overlapping scores are not unique-stock sums. |
| PROSPECTIVE_FORECASTING | PASS | Original 31 V2 forecasts preserved; 300 separate expanded forecasts and global declaration frozen before October 19 entry; LSTM created zero. | Real future session observations are required for outcomes; no backdating. |
| PROSPECTIVE_OUTCOMES_MATURED | PENDING | Zero matured outcomes; pending lifecycle remains usable today. | Real next opening, five subsequent eligible sessions and documented later source evidence. |
| INDEPENDENT_MODEL_ACCEPTANCE | PENDING | Registered minimum evidence and review gates preserved. | 126 dates/1,000 outcomes/thirty securities/two quarters, statistical/economic criteria and independent human review. |
| ACCEPTED_ML_RANKINGS | PENDING | Accepted model/ranking counts remain zero; experimental publication is isolated. | Genuine independent model acceptance and existing publication gates. |
| SECURITY_AND_PRIVACY | PARTIAL | Existing strict severity/secret policies preserved; saved-only authenticated APIs and private data boundaries maintained. | New full CI/container/secret-scan receipts; three historical unverified fixtures remain disclosed. |
| PROJECT_CLEANUP | PASS | Thirty-five cache roots/467 files removed, 36,910,341 logical and 37,719,616 allocated file bytes; private data untouched. | Final post-acquisition/build inventory pending, distinct from gross deletion. |
| APPLICATION_OPERATIONAL_READINESS | PARTIAL | Actual compiled 300-candidate browser checks and six real indicative quotes passed; original stores preserved. | Final delivery restart, full backend/PostgreSQL/frontend/backup/restore and CI receipts. |

## Tests, preservation, cleanup and delivery

Completed focused checks at this checkpoint: **28 combined sequence/review/market-API cases passed in 22.43 seconds**; four cleanup safety cases including a real Windows junction; thirty-seven expanded operational/forward cases; seven compiled-asset boundary cases. Relevant Ruff/mypy/Bandit checks passed. An intermediate new review test had a misplaced fixture assertion causing a NameError; that test defect was corrected before the final 28-case run. No model was retrained. Three actual compiled authenticated browser cases passed in 40.5 seconds. The initial route 404 was fixed by extending the existing private frontend allowlist and tested. An early frontend run failed with 97 passes and three component timeouts under concurrent heavy builds; it is retained and is not described as a clean 100-case pass. Final frontend/full backend/PostgreSQL/container/secret-scan results remain **PENDING** the completed delivery runs.

The prior verified baseline had 1,304 backend passes/eight skips, 98 frontend passes and zero HIGH/CRITICAL container findings. Those are prior evidence, not results for this new source revision. Historical full-history scanning flagged three audited unverified test/configuration fixtures; no suppression or history rewrite is used to claim a pass. New push-range and container scans must retain the unchanged severity policy.

The [cleanup inventory](alphalens-cleanup-inventory.md) records the exact removed paths and bytes. Reviewed worktree size was 1,619,513,154 logical bytes; immediately after cleanup it was 1,582,679,130 bytes. All private storage, backups, forecasts, PostgreSQL and external dependency junctions stayed intact. Subsequent real acquisition, optional isolated training dependencies, builds and tests have storage consequences; final folder size is **PENDING** and must not be confused with gross bytes deleted.

Actual preservation verification passed: **2,485 original frozen files / 8,505,278,241 bytes**, all 47 original alerts, V1/V2 artifacts/evaluations, 240 immutable original evidence files and 61 original forecast bodies (30 V1 / 31 V2). Four protected credential fingerprints, operator password/account records, financial records and protected configuration fields matched. No credential values appear in the receipts. Evidence: private `full-nse-frozen-preservation.json` and `full-nse-personal-preservation.json`. Final new backup/isolated-restore and delivery restart receipts remain **PENDING**; no claim is inferred from unit fixtures.

Use the [operator runbook](../operator/alphalens-runbook.md). Working existing native commands:

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\start-p33-alphalens.cmd
# From a second PowerShell window, when stopping is intended:
.\scripts\windows\stop-p33-alphalens.cmd
```

Private URL: <http://127.0.0.1:8017/nse-market>. Existing V2 URL: <http://127.0.0.1:8017/experimental-ai-v2>. Final compiled/new-backend availability is verified by the delivery run, not by this documentation link. The synthetic [public demo](https://bhavi123-hacker.github.io/AlphaLens/) remains separate and receives no private NSE data, credentials, models or financial records.

Final delivery commit and complete CI links: **PENDING genuine completed runs**. No main merge or public private-data deployment is authorized or performed.
