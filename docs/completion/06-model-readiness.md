# Model readiness — 24 October 2026

Status: **IMPLEMENTED_UNVERIFIED** for production eligibility;
experimental and historical software has substantial verified development
evidence. **No model is production-eligible or independently accepted.**

The additive [machine-readable manifest](model-readiness-manifest.json) records
seven selected saved artifacts, training data/periods, ordered features, horizons,
model checksums, saved evaluation references and blockers. It deliberately does
not pretend to enumerate all 152 original fits. Existing immutable registries
remain authoritative for individual runs. No checkpoints, fitted weights,
forecast bodies or training configurations were replaced.

| Model family | Implemented and saved evidence | Compatibility / limitation |
| --- | --- | --- |
| Frozen logistic / ridge | Original chronological P8/P9 arena | Train-only preprocessing, original 38-feature contract; all twelve historical logistic fits hit their fixed iteration limit, so convergence is unestablished |
| Frozen random forest / histogram boosting | Genuine classification and regression fits in 152-fit arena | Registered bounded forest fitting threads; no live substitution |
| LightGBM / XGBoost / CatBoost | Actual families in `ml/evaluation/src/alphalens_evaluation/models.py` | Chronological folds, frozen artifacts; presence does not establish acceptance, feature compatibility or deployment |
| Experimental NSE V1 logistic | Genuine separate 11-feature study and scalar JSON | Same-session ratio features and five-day daytime-chain target; incompatible with original 38-feature holding-return models |
| Experimental NSE V2 | Logistic, ridge, histogram boosting, forest; 13 context-feature and 17 price-only fits | 20-feature context and separate 16-feature price-only contracts; same-session data and exact feature ordering required |
| Sequence benchmark LSTM | Saved one-layer 8→16 LSTM, 20×8 state sequence; one bounded registered run | Numeric JSON, exact train scaling, 100-stock training cohort; no extension to arbitrary securities or horizons |
| Sequence matched traditional comparators | Saved logistic/forest/histogram/XGBoost and ridge predictions | Same 20×8 samples flattened, not additional live production models |

The frozen research canonical and supervised IDs are respectively
`37693f7796bc42b4c33fad117196c6a75545dd690d5edd7f597204bc7e24f490` and
`f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2`.
Training starts in 2015 with earlier warm-up; 2022–2024 development, 2025
confirmation and the once-evaluated 2026 final period remain immutable.
Selected final models cover 1/5/10/20 calendar-session horizons. The later V2
and sequence studies explicitly treat known V1/V2-era dates as development
information. They are not new untouched tests.

The saved selected V2 price-only model is
`05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525`;
model-file SHA256
`f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3`.
It uses `nse.adjusted-price-only.16.v2`, dataset
`a9be364478d6c80ee049e4523cb9d7f9adabffa701ae344db74f1a4ee5e84457`,
last training decision 2026-10-08 / target 2026-10-15. It predicts the fifth
subsequent adjusted close relative to next open; its score is not an invented
rupee target or calibrated success probability. The preserved primary context
model has a different 20-feature contract and is not silently interchanged.

Saved LSTM SHA256 is
`062caac5753ec836208e82514e27c0b270f339c2709c1f4ea3b4a63a73626733`,
dataset `6c52fbd6a34e40da09b561ed445ec49e2c62ecbc065753b3301fd96a770b444e`.
Actual training decisions: 2022-04-29–2023-12-21, 31,665 samples; validation:
2024-01-30–2024-12-23, 18,693 samples; known-period report:
2025-01-29–2026-10-09, 27,820 samples. Train-only scaling and target boundary
purges are explicit. The saved final report is an engineering correction of
report metadata, not a refit or independent review. It correctly omits Brier
and probability-calibration fields for ridge return predictions.

Serving uses the exact V2 formulas and feature order, conservative complete
61-slot/action exclusions, and complete consecutive sequence states. Missing
observations produce exclusions rather than imputed current predictions.
The model validators reject wrong feature versions/order, malformed numeric
state and nonfinite inputs. Bounded scalar/tree JSON avoids arbitrary pickle
loading in experimental serving; frozen skops models retain reviewed-type and
checksum gates. Feature lineage and source clocks remain separate from scores.

The original P8 registry (`ml/training/src/alphalens_training/artifacts.py`)
records feature/label/dataset IDs, cutoffs, evaluation and artifact checksums;
it offers TEST_ONLY/VALIDATED_BASELINE research states with no production
promotion API. V2 numeric models and append-only forecast ledgers add protocol,
source, decision-clock and complete input lineage. Current drift/reliability
diagnostics are descriptive; probability calibration and independent economic
edge remain unestablished. No recalibrator was fit in this campaign.

V2 acceptance remains unchanged in `workers/experimental_nse_v2/acceptance.py`:
126 future decision dates, 1,000 eligible matured outcomes, 30 securities,
two quarters, registered date-block baseline-improvement bounds, rank/economic
requirements and an externally pinned independent review. Self-authored agent
review is not independent research acceptance. Zero stored outcomes currently
preclude those sample gates. See `07-forecast-performance.md` for exact counts
and the campaign verification report for regression results.
