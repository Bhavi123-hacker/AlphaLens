# ML model readiness — 24 October 2026

Status: **PARTIAL** for research serving; **BLOCKED_EVIDENCE** for independently validated recommendations and production promotion. Audit baseline: `alphalens-master-completion`, `da43822`. No model fit, final-holdout evaluation or replacement was performed.

The additive [model registry](model-readiness-manifest.json) identifies seven selected saved artifacts, their versions/checksums, ordered features, dataset IDs, horizons, training cutoffs, saved validation references and production eligibility. It is a selected-serving registry rather than an inventory of all 152 frozen fits. Existing original registries remain authoritative.

| Family | Saved contract and serialization | Serving and calibration decision |
| --- | --- | --- |
| Original historical arena | 38 features; logistic/ridge, forest/histogram boosting, LightGBM/XGBoost/CatBoost; checksum-pinned reviewed skops artifacts | Frozen 1/5/10/20-session research models; current compatible complete vectors and independent acceptance unavailable; no promotion |
| Experimental V1 | Separate 11-feature scalar JSON logistic; five-day daytime-chain target | Different target; cannot substitute for V2 or original holding-return models |
| Experimental V2 context | Ordered 20-feature numeric JSON; five observed-session price-component target | Source/context compatibility required; uncalibrated experimental classifier |
| Experimental V2 price-only | `nse.adjusted-price-only.16.v2`; ordered 16-feature numeric JSON; five-session target | Actual expanded-cohort research serving exists; no calibrated gain probability or accepted investment recommendation |
| Sequence benchmark | 20 × 8 sequence, one-layer 8→16 LSTM, train-only scaling, numeric JSON state | 43 saved dated scores; fixed-current-cohort development experiment; no arbitrary horizon/cohort extension |

Independently read saved model bytes: price-only SHA256 `f24bacaa178f63af22d85e3840a95d19890d419c0a84be7ee580b283edec27d3`; sequence SHA256 `062caac5753ec836208e82514e27c0b270f339c2709c1f4ea3b4a63a73626733`. These match the pre-existing manifest. Original frozen canonical/supervised IDs and source limitations are documented in [historical integrity](04-historical-data-integrity.md).

Source-qualified private research retention does not establish production redistribution rights or historical point-in-time publication evidence. Current-cohort selection is not survivorship-free historical membership. Corporate-action and total-return limitations remain. Known V1/V2 dates are development information for later experiments, never fresh independent holdouts. The original twelve logistic fits reached their fixed iteration limits; convergence is unestablished.

Validators enforce feature version/order, finite inputs, model identity/checksum and numeric state shape. Experimental scalar/tree JSON avoids arbitrary estimator deserialization. The accepted original ranking service remains separate. Independent V2 acceptance requires 126 future decision dates, 1,000 eligible matured outcomes, 30 securities, two quarters, registered date-block baseline improvements, rank/calibration/economic checks and externally pinned independent review. Acceptance code does not itself configure the accepted publication adapter.

Serving software regression is reported in [prediction engine](05-prediction-engine.md); [saved evaluation evidence](07-forecast-performance.md) remains available unchanged. No model is currently production eligible.
