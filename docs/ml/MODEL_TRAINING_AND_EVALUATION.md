# AlphaLens Machine Learning Training and Evaluation Protocol

This document defines the formal methodology, model architectures, time-series splitting rules, feature definitions, and acceptance gates used across all predictive modeling pipelines in AlphaLens.

---

## 1. Supported Model Families

AlphaLens trains and benchmarks six distinct model families under strict CPU-bounded execution:

| Family Name | Task | Library / Implementation | Hyperparameters / Architecture | Scaler / Preprocessing | Resource Limits |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | Binary Classification | `sklearn.linear_model.LogisticRegression` | $C=1.0$, L2 penalty, lbfgs solver, max_iter=1000, tol=$10^{-8}$ | `StandardScaler` + `SimpleImputer(median)` | Single-threaded (CPU), memory < 100 MB |
| **Random Forest** | Binary Classification | `sklearn.ensemble.RandomForestClassifier` | n_estimators=32, max_depth=4, min_samples_leaf=3, max_features=1.0 | `SimpleImputer(median)` | Single-threaded (CPU), memory < 200 MB |
| **HistGradientBoosting Classifier** | Binary Classification | `sklearn.ensemble.HistGradientBoostingClassifier` | loss="log_loss", lr=0.1, max_iter=32, max_leaf_nodes=7, min_samples_leaf=5 | Native histogram binning + `SimpleImputer` | CPU, memory < 150 MB |
| **Ridge Regression** | Continuous Return Regression | `sklearn.linear_model.Ridge` | alpha=1.0, solver="svd", tol=$10^{-8}$ | `StandardScaler` + `SimpleImputer(median)` | CPU, memory < 100 MB |
| **HistGradientBoosting Regressor** | Continuous Return Regression | `sklearn.ensemble.HistGradientBoostingRegressor` | loss="squared_error", lr=0.1, max_iter=32, max_leaf_nodes=7 | Native histogram binning + `SimpleImputer` | CPU, memory < 150 MB |
| **Sequence LSTM (CPU)** | Sequence Classification / Scoring | Pure CPU NumPy matrix execution (`workers.nse_market.sequence`) | Layer 1: LSTM($8 \to 16$, batch_first=True); Dropout(0.1); Dense($16 \to 1$) with Sigmoid | Training-only feature z-score scaling | Pure CPU matrix multiply, zero GPU/VRAM |

---

## 2. Prediction Target Horizons

Every model is mapped to an explicit forward target horizon. Mixing horizon labels or confusing direction probabilities with expected returns is strictly prohibited.

1. **Horizon 1 (1-Session Forward Return)**:
   $$R_{t+1} = \frac{C_{t+1} - O_{t+1}}{O_{t+1}}$$
   - Entry: Open of session $t+1$; Exit: Close of session $t+1$.
2. **Horizon 5 (5-Session Return — Primary Frozen V2 Benchmark)**:
   $$R_{t+5} = \frac{C_{t+5} - O_{t+1}}{O_{t+1}}$$
   - Direction Label: $Y = \mathbb{I}(R_{t+5} > 0)$.
3. **Horizon 10 (10-Session Forward Return)**:
   $$R_{t+10} = \frac{C_{t+10} - O_{t+1}}{O_{t+1}}$$
4. **Horizon 20 (20-Session Forward Return)**:
   $$R_{t+20} = \frac{C_{t+20} - O_{t+1}}{O_{t+1}}$$

---

## 3. Strict Time-Series Splitting & Embargo Protocol

To eliminate lookahead bias, survivorship bias, and label leakage, AlphaLens forbids random cross-validation. All evaluations use chronological walk-forward partitions:

```
[ TRAINING PERIOD ]              [ EMBARGO ]  [ VALIDATION PERIOD ]         [ EMBARGO ]  [ TEST / DEVELOPMENT REPORT ]
< 2024-01-01                     20 sessions  2024-01-01 to 2024-12-31      20 sessions  2025-01-29 to 2026-10-09
Target session must < 2024-01-01              Target session < 2025-01-01                Matured targets only
```

- **Target Purging**: Samples whose forward label window overlaps a partition boundary are purged from the earlier partition.
- **20-Session Embargo**: A 20-trading-session buffer is placed immediately following every partition boundary to eliminate autocorrelation leakage from rolling indicators (e.g. 20-day moving averages and return standard deviations).

---

## 4. Input Features & Provenance

The 8-dimensional sequence input space and 16-dimensional tabular space are derived exclusively from point-in-time adjusted OHLCV data:
1. `price_return_1`: 1-session return $\frac{C_t - C_{t-1}}{C_{t-1}}$
2. `price_return_5`: 5-session momentum $\frac{C_t - C_{t-5}}{C_{t-5}}$
3. `price_return_20`: 20-session momentum $\frac{C_t - C_{t-20}}{C_{t-20}}$
4. `return_sd_20`: 20-session rolling return standard deviation
5. `ma_distance_20`: Normalized distance to 20-session SMA $\frac{C_t - \text{SMA}_{20}}{\text{SMA}_{20}}$
6. `rsi_14`: 14-session Relative Strength Index
7. `atr_14_over_close`: 14-session Average True Range normalized by close
8. `open_close_return`: Intraday price trajectory $\frac{C_t - O_t}{O_t}$

---

## 5. Model Lifecycle & Acceptance Criteria

Every trained model artifact progresses through explicit gates:
1. `TRAINED_EXPERIMENTAL`: Fitted on chronological training partition with recorded SHA-256 model digest.
2. `BACKTEST_EVALUATED`: Out-of-sample metrics computed on holdout test partition.
3. `FORWARD_OUTCOME_PENDING`: Deployed to daily prospective inference pipeline; awaiting future session maturity.
4. `INDEPENDENT_ACCEPTANCE_PENDING`: Baseline gate for Private V1 serving.
5. `ACCEPTED`: Conferred **only** after surviving 126 prospective daily decisions, 1,000 qualified matured outcomes, across at least 30 securities over two full calendar quarters without performance collapse.
