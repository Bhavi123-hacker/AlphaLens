# AlphaLens — Automated Model Acceptance & Strategy Performance Audit (Corrected)

**Evaluated At:** 2026-11-05T09:00:50.896731+00:00  
**Ledger Inspected:** `D:\al-research\p28-worktree\.campaign-worktree\data\forecasts\matured_outcomes_ledger.db`  
**Overall Acceptance Status:** **ACCEPTANCE_EVIDENCE_QUARANTINED**  
**Independently Approved Models:** **0 / 20**  
**Governance Posture:** **EXPERIMENTAL_RESEARCH**

---

## 1. Evidence Lineage Separation & Accounting Rules

| Evidence Tier | Total Records | Role in Acceptance | Contamination Safeguard |
| :--- | :--- | :--- | :--- |
| **Tier 1: Qualified Prospective** | 0 | Full Acceptance Credit | Authentic verified exchange sessions only |
| **Tier 2: Quarantined Historical** | 601 | ZERO Contribution (0) | Isolated; excluded from all acceptance metrics |
| **Tier 3: Experimental Backtest** | 47,552 samples | Hypothesis Fitting Only | Backtest cannot grant model acceptance |
| **Tier 4: Pending / Unverified** | In-flight sessions | Gated | Zero price fabrication enforced |

---

## 2. Quarantined Historical Ledger Audit (Zero Acceptance Contribution)

> [!IMPORTANT]
> All 601 records in `matured_outcomes_ledger.db` belong exclusively to legacy candidate model `05f801560820106f75a65702de6d8c53442eebcbeb1669d90e34877217a14525_H5`. Due to missing vendor sessions for October 26 and October 27, 2026, these outcomes are strictly quarantined. They contribute ZERO observations, ZERO decision dates, and ZERO performance credit toward independent model approval.

| Metric | Quarantined Value | Policy Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Quarantined Outcomes** | 601 records | — | QUARANTINED |
| **Directional Hit Rate** | 34.61% (208/601) | > 54.0% | NOT_SATISFIED (Fail) |
| **Mean Brier Score** | 0.2838 | <= 0.2500 | NOT_SATISFIED (Fail) |
| **Gross Excess Alpha** | -7.19 bps | > 0.0 bps | NOT_SATISFIED (Fail) |
| **Net Alpha (20 bps cost)** | -27.19 bps | > 0.0 bps | NOT_SATISFIED (Fail) |
| **Mean Rank IC** | -0.0683 | > +0.0200 | NOT_SATISFIED (Fail) |
| **Acceptance Credit Granted** | **0 observations** | >= 1,000 | ZERO_CREDIT |

---

## 3. Independent Per-Model Performance & Acceptance Matrix (20 Models)

> [!NOTE]
> Every model is evaluated strictly on its own authentic forward outcomes. Cross-model pooling, cross-horizon aggregation, and backtest-based acceptance are strictly prohibited.

| Model Key | H | Task | Qual. Out | Qual. Dates | Hit Rate | Net Alpha | Brier | Acceptance Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `HistGB_Classifier_H1` | H1 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `RandomForest_Classifier_H1` | H1 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `LogisticRegression_H1` | H1 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Regressor_H1` | H1 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `Ridge_H1` | H1 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Classifier_H5` | H5 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `RandomForest_Classifier_H5` | H5 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `LogisticRegression_H5` | H5 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Regressor_H5` | H5 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `Ridge_H5` | H5 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Classifier_H10` | H10 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `RandomForest_Classifier_H10` | H10 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `LogisticRegression_H10` | H10 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Regressor_H10` | H10 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `Ridge_H10` | H10 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Classifier_H20` | H20 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `RandomForest_Classifier_H20` | H20 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `LogisticRegression_H20` | H20 | classification | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `HistGB_Regressor_H20` | H20 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |
| `Ridge_H20` | H20 | regression | 0 | 0 | None | None | None | **FORWARD_OUTCOME_PENDING** |

---

## 4. Policy & Governance Statement

Quarantined forward outcomes contribute ZERO to independent ML acceptance. Currently 0 of 20 models meet all 7 independent conditions.

### Governance Checkpoints Verified:
1. **Zero Quarantine Contamination:** Adding, modifying, or auditing quarantined records has zero mathematical impact on prospective model acceptance metrics.
2. **Zero Cross-Model Pooling:** Each of the 20 models must independently accumulate $\ge 126$ prospective decision dates and $\ge 1,000$ qualified outcomes.
3. **Zero Backtest Promotion:** Models cannot be promoted from `EXPERIMENTAL_RESEARCH` to `ACCEPTED` based on historical backtest metrics alone.
4. **Friction Accounting:** Standard 20 bps roundtrip friction (brokerage, STT, turnover, GST, slippage) is deducted from all forward alpha evaluations.
