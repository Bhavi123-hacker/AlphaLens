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
