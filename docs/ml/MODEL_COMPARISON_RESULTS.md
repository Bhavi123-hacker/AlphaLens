# AlphaLens Out-of-Sample Model Comparison Results

This document records the verified empirical evaluation metrics for all benchmarked model families over the sealed holdout period (**29 January 2025 to 9 October 2026**, 420 trading dates, 27,820 evaluated security-date samples across 97 securities).

**Integrity Rule**: All models were evaluated on identical chronological holdout samples with fixed point-in-time features. No backdating, synthetic imputation, or retrospective tuning was applied.

---

## 1. Primary Empirical Comparison Table

| Model Identity | Family | Balanced Accuracy | ROC-AUC | Brier Score | Precision | Recall | Mean Daily Rank IC (Spearman $\rho$) | Top vs Bottom Quintile Spread | Independent Acceptance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **XGBoost Classifier** | Tree Ensemble | **52.19%** | **0.5308** | 0.2512 | 0.4858 | 0.6479 | **+0.0864** | **+0.675%** | `EXPERIMENTAL_INSUFFICIENT_EVIDENCE` |
| **HistGradientBoosting** | Tree Ensemble | **52.14%** | **0.5254** | 0.2542 | 0.4873 | 0.5852 | **+0.0717** | **+0.448%** | `EXPERIMENTAL_INSUFFICIENT_EVIDENCE` |
| **Random Forest** | Bagged Trees | **52.02%** | **0.5277** | 0.2513 | 0.4836 | 0.6786 | **+0.0847** | **+0.537%** | `EXPERIMENTAL_INSUFFICIENT_EVIDENCE` |
| **Logistic Regression** | Linear (L2) | **51.27%** | **0.5174** | 0.2532 | 0.4798 | 0.5645 | **+0.0764** | **+0.544%** | `EXPERIMENTAL_INSUFFICIENT_EVIDENCE` |
| **Sequence LSTM (CPU)** | Recurrent Neural Net | **51.12%** | **0.5115** | **0.2501** | 0.4785 | 0.5595 | **+0.0601** | **+0.215%** | `BLOCKED_MODEL_EVIDENCE` |
| **Mean Reversion Baseline** | Heuristic Rule | 50.66% | 0.5086 | 0.2814 | 0.4746 | 0.5258 | +0.0372 | +0.665% | `NON_ML_REFERENCE_BASELINE` |
| **Majority Class Baseline** | Constant Prior | 50.00% | 0.5000 | 0.2518 | 0.4683 | 1.0000 | N/A | -0.282% | `NON_ML_REFERENCE_BASELINE` |
| **Ridge Regression** | Linear (L2) | 49.96% | 0.4927 | N/A | 0.4680 | 0.6981 | +0.0177 | +0.279% | `EXPERIMENTAL_INSUFFICIENT_EVIDENCE` |
| **Momentum Baseline** | Heuristic Rule | 49.31% | 0.4914 | 0.2885 | 0.4613 | 0.4769 | -0.0372 | -0.665% | `NON_ML_REFERENCE_BASELINE` |

---

## 2. Key Findings & Research Insights

1. **Tree Ensembles Outperform Linear & Recurrent Models**:
   - `XGBoost` (52.19% balanced accuracy, +0.0864 Rank IC) and `HistGradientBoosting` (52.14% balanced accuracy, +0.0717 Rank IC) demonstrate the strongest out-of-sample directional sorting capacity.
   - Both models achieve positive monotonic separation across quintile buckets, with the top quintile outperforming the bottom quintile by 45–68 basis points over a 5-day horizon.

2. **Sequence LSTM Point Improvement is Statistically Indistinguishable from Zero**:
   - The CPU-bounded LSTM achieved 51.12% balanced accuracy and +0.0601 Rank IC.
   - A block bootstrap uncertainty test (moving block length 20, 500 draws, seed 1729) revealed a 95% confidence interval for balanced accuracy difference relative to baseline of **$[-0.012, +0.028]$**, which clearly spans zero.
   - Consequently, per project governance rules, the LSTM is classified as `BLOCKED_MODEL_EVIDENCE` and is **not** promoted over tree ensembles.

3. **Probability Calibration Disclosure**:
   - None of the candidate models exhibit well-calibrated posterior probabilities; Brier scores hover near 0.25 (the theoretical variance of an uninformative Bernoulli coin with $p \approx 0.5$).
   - Raw model outputs are therefore presented in research tools as **uncalibrated rank scores** and must **never** be interpreted as true win probabilities.

4. **Economic & Turnover Diagnostics**:
   - Gross Top-5 portfolio reference wealth achieved positive trajectories before costs.
   - However, when transaction costs (15 bps) and realistic slippage (10 bps) are incorporated, turnover severely degrades net compound growth. Active rebalancing requires minimum holding periods of 10–20 sessions to maintain positive expectancy.

---

## 3. Real Multi-Horizon Out-of-Sample Empirical Metrics (500-Stock Retained Cohort)

Executed across **47,508 samples** (100 sessions, 2026-06-08 to 2026-11-02) with strict 5-session embargo and chronological train/holdout partition (`workers/nse_market/multi_model_engine.py`):

### A. Classification Models (Directional Sorting)
| Horizon | Model | Balanced Accuracy | ROC-AUC | Brier Score | Rank IC (Spearman $\rho$) | Holdout Samples |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Session** | HistGradientBoosting | 50.98% | 0.5382 | 0.2395 | +0.0613 | 14,177 |
| **1 Session** | Random Forest | 50.47% | 0.5385 | 0.2391 | +0.0553 | 14,177 |
| **1 Session** | Logistic Regression | 50.22% | 0.5311 | 0.2400 | +0.0661 | 14,177 |
| **5 Sessions** | **Random Forest** | **52.16%** | **0.5514** | **0.2369** | **+0.0599** | 12,209 |
| **5 Sessions** | HistGradientBoosting | 52.09% | 0.5449 | 0.2374 | +0.0564 | 12,209 |
| **5 Sessions** | Logistic Regression | 51.18% | 0.5391 | 0.2355 | +0.0635 | 12,209 |
| **10 Sessions** | HistGradientBoosting | 51.38% | 0.5275 | 0.2381 | -0.0004 | 9,749 |
| **10 Sessions** | Random Forest | 51.30% | 0.5332 | 0.2376 | -0.0044 | 9,749 |
| **20 Sessions** | Random Forest | 50.24% | 0.5280 | 0.2389 | -0.0573 | 4,845 |
| **20 Sessions** | HistGradientBoosting | 50.21% | 0.5256 | 0.2394 | -0.0323 | 4,845 |

### B. Regression Models (Expected Forward Return)
| Horizon | Model | MAE | RMSE | Directional Accuracy | Rank IC (Spearman $\rho$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Session** | HistGradientBoosting Regressor | 0.0195 | 0.0277 | 58.98% | +0.0626 |
| **1 Session** | Ridge Regressor | 0.0195 | 0.0277 | 57.81% | +0.0794 |
| **5 Sessions** | HistGradientBoosting Regressor | 0.0454 | 0.0620 | 45.37% | +0.0210 |
| **5 Sessions** | Ridge Regressor | 0.0450 | 0.0615 | 46.02% | +0.0688 |
| **10 Sessions** | Ridge Regressor | 0.0632 | 0.0825 | 44.65% | +0.0040 |
| **20 Sessions** | Ridge Regressor | 0.0940 | 0.1186 | 45.22% | -0.0493 |

### C. Top 5 Prospective Predictions for As-Of Session `2026-11-02` (Horizon 5)
| Rank | Instrument Key | Latest Close (₹) | Direction Win Prob | Expected 5-Day Return |
| :--- | :--- | :--- | :--- | :--- |
| **#1** | `NSE_EQ\|INE00GO01025` | 113.81 | 59.17% | **+5.52%** |
| **#2** | `NSE_EQ\|INE09VQ01012` | 870.00 | 54.01% | **+2.94%** |
| **#3** | `NSE_EQ\|INE063E01061` | 381.40 | 54.82% | **+2.84%** |
| **#4** | `NSE_EQ\|INE0JA001018` | 1,753.80 | 55.26% | **+2.66%** |
| **#5** | `NSE_EQ\|INE055S01018` | 744.00 | 55.52% | **+2.24%** |

*(Complete prospective Top 5, 10, 20 rankings across Horizons 1, 5, 10, 20 serialized in `docs/ml/multi_model_execution_results.json`)*

