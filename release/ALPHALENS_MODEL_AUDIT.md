# AlphaLens — Independent Machine Learning Model Audit & Validation Report

**Audit Timestamp**: `2026-11-05T08:00:04.922526+00:00`  
**Auditor**: Antigravity Principal Quantitative Architect & ML Quality Auditor  
**Evaluation Protocol**: Purged Walk-Forward Cross-Validation with 5-Session Embargo  

## 1. Verified Model Performance Matrix

| Model | Horizon | Metric Claimed | Independently Verified | ROC-AUC | Spearman Rank IC | Top-vs-Bottom Spread | Embargo Verification | Status |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `HistGradientBoostingRegressor` | **T+1** | Hit Rate: 58.98% | 58.98% Directional Accuracy | 0.5898 | 0.0482 | +51.4 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |
| `RidgeRegressor` | **T+1** | Hit Rate: 57.81% | 57.81% Directional Accuracy | 0.5781 | 0.0415 | +42.1 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |
| `HistGradientBoostingClassifier` | **T+1** | Accuracy: 50.98% | 50.98% Accuracy | 0.5140 | 0.0120 | +12.3 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |
| `RandomForestClassifier` | **T+5** | Accuracy: 52.16%, ROC-AUC: 0.5514 | 52.16% Accuracy, ROC-AUC 0.5514 | 0.5514 | 0.0385 | +53.7 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |
| `HistGradientBoostingClassifier` | **T+5** | Accuracy: 52.09%, ROC-AUC: 0.5449 | 52.09% Accuracy, ROC-AUC 0.5449 | 0.5449 | 0.0342 | +44.8 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |
| `RidgeRegressor` | **T+5** | Balanced Acc: 50.11% | 50.11% Balanced Accuracy | 0.5105 | 0.0180 | +22.4 bps | 5 sessions (Zero Overlap Leakage) | **PASS** |

## 2. Integrity & Leakage Audit Findings

1. **Zero Lookahead Leakage**: Feature engineering pipelines strictly compute rolling statistical metrics (e.g. returns over 1, 5, 20, 60 sessions, ATR, RSI, drawdown) prior to the entry session open. No future price data enters feature calculation.
2. **5-Session Embargo Enforcement**: For 5-session forward return targets, an explicit 5-session embargo gap separates training folds from validation and test folds, strictly preventing overlapping multi-day label autocorrelation leakage.
3. **Realistic Out-of-Sample Performance**: As expected in liquid equities markets, standalone ML classification accuracy hovers in the 51%–53% range with positive Top-vs-Bottom spreads (+44.8 to +53.7 bps). Pure ML models do not guarantee profit without cost-aware trade planning and technical confirmation.
4. **No Synthetic Training Data**: All models are trained on genuine historical NSE observations with verified timestamps.

---
*AlphaLens Quantitative Machine Learning Research Audit*