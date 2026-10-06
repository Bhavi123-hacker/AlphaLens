# P12 opportunity ranking

Authorized under D59/D61 only after P11 passed and was committed as
b50314b2dc3eba55581f6e4d5792f0369019d635. This is historical analytical ranking,
not ENTRY/HOLD/EXIT, portfolio allocation, live recommendations or P14 product
explanations. Stop before P13. TEST_ONLY — NOT A PERFORMANCE CLAIM.

## Evidence and model choice

The engine consumes verified P5/P6 historical evidence, P3 source quality, P4
historical identity/membership, target-free P9 predictions and P11 risk snapshots.
Supplied risk snapshots must exactly match the decision, versions and configured
P11 policy; the engine replays P11 to verify that boundary. A missing snapshot
excludes the security. Complete historical candidates are retained as either
ranked or explicitly excluded. Current constituents never replace that universe.
P4 audit catalogs can contain future-only placeholders; those are not historical
candidates merely because their IDs exist somewhere in a full input file. P12
requires known facts, P4's explicit known-membership exclusion reasons or prices
whose availability is evidenced by the cutoff. Known ineligible securities stay
in exclusions; unknown future-only names do not appear in earlier output.
P7 realized targets are absent from the predictive input contract.

Each versioned policy describes exactly one existing horizon: 1, 5, 10 or 20.
Classification and regression use one fixed family per task/horizon for every
security. The initial engineering configuration is logistic/ridge, not an
empirically selected market winner. Random forest, HistGradientBoosting, LightGBM,
CatBoost and XGBoost counterparts are also configurable. No most-optimistic
per-security family selection, accuracy-only winner, model fitting or tuning occurs.
All visible model families may contribute P11 disagreement, even when not chosen
as the raw-score input.

The comparison summary retains all twelve task/family slots, known fold/sample
counts, Brier/MAE primary metrics, naive improvement, worst fold, mean/standard
deviation, calibration status and the other declared P9 metrics when available.
Verified P9 aggregate ranking diagnostics become usable only after every scored
target contributing to that family report is available. They remain descriptive
target diagnostics, not profit. Verified P10 MODEL runs map back to the matching
P9 evaluation/task and retain net hypothetical return, drawdown, turnover, counts,
unresolved outcomes and separate cost scenarios. Economic availability is
conservatively the end of the final local session date. Later reports cannot
enter earlier comparisons. Unknown/incomplete metrics remain null/unavailable.
Economic context does not automatically pick a winner or change configured models.

Selection evidence remains INSUFFICIENT_EVIDENCE in v1. On authored fixtures the
configuration is TEST_ONLY_SELECTED_CANDIDATE; this is not a best real-market model.
Insufficient selection evidence blocks all non-TEST_ONLY ranking. Research
classification cannot bypass that gate and PRODUCTION is rejected. A future
reviewed research-selection policy will require genuine evidence, a new version
and authorization rather than promoting a fixture candidate.

## Transparent scoring policy

The raw score is a weighted mean of observed normalized components:

| Component | Formula | Initial weight |
| --- | --- | --- |
| Probability | Configured classifier probability in [0,1] | 0.45 |
| Return strength | 0.5 + 0.5 × tanh(predicted return / 0.05) | 0.45 |
| Historical context | Existing P6 momentum_percentile_20, historical eligible peers only | 0.10 |

The return scale is a disclosed engineering assumption, not a market estimate.
No probabilities and raw return units are added directly. Missing components
remain null, are omitted from the weighted mean with remaining weights
renormalized, and incur an explicit missing-component penalty. At least one
positively weighted predictive component is required; feature context alone
cannot establish model opportunity. P6 cross-sectional features are never
recomputed using the full dataset or current universe.

Risk-adjusted score = raw score minus all disclosed penalties:

| Penalty | Initial formula |
| --- | --- |
| Risk | 0.35 × worst P11 component severity; unavailable optional dimensions use the pinned P11 uncertainty floor |
| Model uncertainty | 0.20 × P11 uncertainty severity; unavailable means 1 |
| Source quality | 0.10 for actual DEGRADED P3 source quality, 0 for VALID |
| Selection evidence | 0.10 while selection remains insufficient |
| Missing components | 0.05 per unavailable raw component |

The worst-component penalty already includes model uncertainty; the separate
uncertainty penalty deliberately gives insufficient validation/disagreement
additional influence. This overlap is disclosed, not hidden. Scores may be
negative; they are ordering measures, not calibrated confidence, probability of
loss or expected profit. Every weight/scale is serialized. Risk and uncertainty
weights must be positive. No weights were optimized against fixture outcomes.
Tests establish that an optimistic VERY_HIGH-risk prediction can rank below a
more moderate LOW-risk candidate. Raw and adjusted scores are both retained.

## Gating, output and history

Rejected source observations, absent historical identity, ineligible historical
membership, missing/unavailable risk, core insufficient history, known unadjusted
economic actions or unavailable configured predictions exclude candidates with
sorted reason codes. Unknown action coverage, unavailable benchmark/calibration
and degraded data retain P11 uncertainty/penalties. Missing evidence never means
LOW risk. Long-indicator warmup is distinct from actual rejected source quality.

Ranking covers the complete observed historical candidate set. Descending
adjusted score and ascending stable security ID break ties, with ordinal ranks.
Top-N is presentation only and never changes the persisted complete snapshot ID.
The latest strictly earlier snapshot with the same policy/horizon/classification
and universe definition supplies previous rank and previous-minus-current change.
Ambiguous historical vintages are rejected. Future/incompatible history is ignored
before identity calculation; no future rank influences current order.

The snapshot SHA256 pins session/cutoff, horizon, universe, P5/P6 identities,
visible prediction set, P11 risk snapshot set, ranking/model-selection policy,
available model comparison, prior snapshot and classification. Immutable JSON
snapshot/manifests verify schema, identity and SHA256 on local replay. Checksums
provide integrity, not authenticity; these remain trusted local inputs.

Candidate records expose rank, symbol/ID, probability/return, component scores,
penalties, risk, quality, model confidence/evidence, observed availability,
reason codes and model/feature/data/risk references. Sector remains UNAVAILABLE.
Versioned references support future price/benchmark, P9 prediction, P10 hypothetical
P&L, P11 risk and P12 rank histories; no charts, API/UI or fabricated values exist.

Developer CLI: `alphalens-rank --canonical INPUT --features FEATURES --date DATE
--horizon 5 --top 10 --evaluation P9_DIRECTORY --output data/ranking`, with repeated
evaluation, risk, history or backtest directories and an optional serialized policy.
Output prints the classified disclaimer, complete exclusions and Top-N diagnostics,
never BUY NOW, guaranteed profit or actual rupee-profit estimates.

Real NSE ranking still requires permitted price/universe/calendar/action/benchmark
evidence and independently validated model selection, calibration and sufficient
history/security counts. See real-data-readiness.md. P1_PRODUCTION_DATA_CLEARANCE
= OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED. No real trading edge is established.
