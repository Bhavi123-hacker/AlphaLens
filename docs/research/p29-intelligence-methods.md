# P29 research intelligence: descriptive evidence, not model promotion

Version `p29.descriptive-intelligence.v1`. These new deterministic diagnostics are
separate from the frozen P11-P14 rules, forecasts and model selection. They do
not train, score the holdout again, place orders or claim an investment edge.

## Market regime intelligence

Read a bounded1-10 session window from existing P5 canonical observations and
stored P6/P7 feature projections. Preserve missing observations and original
feature states. Each session uses its own observed security identities; current
constituents never reconstruct past membership. The denominator is the actual
observed research-equity source cohort, not all NSE securities. Duplicate
identities are rejected. Only positive finite VALID/DEGRADED prices are eligible.

Predeclared exploratory interpretation assumptions: at least128 eligible
observed identities and80% coverage for return1, return20, volatility20,
distanceSMA20 and drawdown20. Broad observed uptrend requires median20-session
raw return >3% and at least60% above stored SMA20; downtrend requires <-3% and
at most40% above. Stress requires median daily volatility20 >3% and at least20%
of observed drawdowns below-10%. Otherwise mixed/sideways. Insufficient inputs
produce INSUFFICIENT_EVIDENCE. These thresholds were recorded before the new
diagnostic read; they are not calibrated strategies, significance tests or
forecast acceptance thresholds. Volatility uses original P6 daily units.

Two distinct assessments: RETROSPECTIVE_FINAL_VINTAGE_DESCRIPTION and
EVIDENCE_GATED_PIT. Strict PIT needs actual timezone-aware availability <=cutoff;
unknown source clocks cannot pass. A descriptive archival label never proves
historical decision-time knowledge. VALID-only sensitivity reports its own
coverage and does not substitute for unavailable corporate-action evidence.

## Evidence Passport and why not recommended

Authenticated stock/Intelligence views report selected observation identity and
ISIN separately from all-time discovery metadata. Report actual date, source,
raw price basis, observed/missing source slots, quality states/reasons, original
38 feature states, recorded candidate hashes and eligibility exclusions. Source
calendar completeness and current action coverage remain unknown. Hashes are
recorded artifact identities, not a new artifact-loading approval. No confidence
percentage is calculated. Exact source/freshness/availability/actions/model/
peer/policy/feature blockers are filterable with a keyboard-accessible drawer.

Default interval remains the latest stored trailing year; intentional older
selection remains possible. Current shortlist and inference stay UNAVAILABLE.

## Reliability Matrix

Read preserved evaluation reports only. Separate development,2025 confirmation
and locked2026 display. Show recorded accuracy/balanced accuracy/ROC AUC/AP/
Brier/F1, calibration, class distribution, confusion matrix, scored samples and
naive comparisons where present. Development fold mean/population standard
 deviation excludes confirmation/holdout. Missing metrics remain missing.128 is
a display guard, not a validated statistical-power threshold. Mixed metric
 evidence does not grant model acceptance. Full-path economic outcomes and
current inference remain unresolved/not eligible. Common-prediction model
 disagreement is explicitly unavailable until valid aligned OOS evidence exists.

## Drift and stability

Two ordered historical reference sessions; finite values of the exact same P6
features. At least128 observations in each empirical distribution for
Wasserstein-1 in original feature units. Quantiles, missingness and paired-ID
median change use their actual denominators. Observed Jaccard, entered/departed
counts describe source-cohort coverage, not verified listings/delistings or
survivorship control. No p-value, significance claim, recalibration or automated
model action. Reference is earlier than current, never a future fitted baseline.
See [SciPy primary method documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html).

## Three implemented evidence-gap diagnostics

1. Availability/identity: strict-PIT regime vs archival description plus selected
   identity Passport. Research question: which outputs remain descriptive when
   original knowledge clocks cannot be established?
2. Cohort/missingness: unpaired distances vs common-ID change and VALID-only
   regime sensitivity. Question: how much apparent feature change co-occurs with
   observed coverage change? This is diagnostic, not causal attribution.
3. Model/economic evidence: reliability dimensions and precise shortlist blocker
   lineage. Question: which recorded statistical facts can be inspected without
   implying current eligibility or validated full-path profit?

All are experimental deterministic research diagnostics. No2026 result is used
 to choose new features, thresholds or strategies. Full observed findings stay in
operator-protected runtime storage; no restricted market archive is redistributed.
