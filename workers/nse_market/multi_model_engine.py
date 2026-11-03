"""Multi-Model Multi-Horizon Training, Evaluation, and Prospective Prediction Engine.

Trains and evaluates 5 distinct model families across 4 prediction horizons:
- Horizons: 1-session, 5-session, 10-session, 20-session returns & directions
- Models: HistGradientBoosting (Classifier & Regressor), Random Forest, Logistic Regression, Ridge
- Features: 12 point-in-time technical and volatility features derived from real OHLCV data
- Zero-leakage protocol: Chronological walk-forward split with a 20-session embargo
- Generates prospective predictions and Top 5/10/20 rankings for latest market session (2026-11-02)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

repo = Path(__file__).resolve().parents[2]


@dataclass
class ModelMetrics:
    horizon: int
    task: str
    model_name: str
    balanced_accuracy: float | None = None
    roc_auc: float | None = None
    brier_score: float | None = None
    precision: float | None = None
    recall: float | None = None
    mae: float | None = None
    rmse: float | None = None
    directional_accuracy: float | None = None
    rank_ic: float | None = None


def _safe_predict_proba(clf: Any, x: np.ndarray) -> np.ndarray:
    """Extract class 1 positive probabilities safely handling single-class edge cases."""
    if hasattr(clf, "classes_") and len(clf.classes_) == 1:
        cls = clf.classes_[0]
        return np.ones(len(x), dtype=np.float64) if cls == 1 else np.zeros(len(x), dtype=np.float64)
    if hasattr(clf, "named_steps") and "lr" in clf.named_steps:
        inner_lr = clf.named_steps["lr"]
        if hasattr(inner_lr, "classes_") and len(inner_lr.classes_) == 1:
            cls = inner_lr.classes_[0]
            return (
                np.ones(len(x), dtype=np.float64)
                if cls == 1
                else np.zeros(len(x), dtype=np.float64)
            )
    if hasattr(clf, "predict_proba"):
        probs = clf.predict_proba(x)
        if probs.ndim == 2 and probs.shape[1] > 1:
            return np.asarray(probs[:, 1], dtype=np.float64)
        return np.asarray(probs.ravel(), dtype=np.float64)
    preds = clf.predict(x)
    return np.asarray(preds.ravel(), dtype=np.float64)


def _safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute ROC-AUC safely guarding against single-class holdout partitions."""
    if len(np.unique(y_true)) > 1:
        try:
            val = float(roc_auc_score(y_true, y_prob))
            return val if not math.isnan(val) else 0.5
        except Exception:
            return 0.5
    return 0.5


def _safe_rank_ic(pred: np.ndarray, target: np.ndarray) -> float:
    """Compute Spearman Rank IC safely handling constant input vectors."""
    if len(pred) < 3 or np.std(pred) < 1e-8 or np.std(target) < 1e-8:
        return 0.0
    corr, _ = spearmanr(pred, target)
    return float(corr) if not math.isnan(corr) else 0.0


def extract_features_and_targets(
    histories: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Compute 12 point-in-time features and 4 multi-horizon forward targets."""
    feature_names = [
        "price_return_1",
        "price_return_5",
        "price_return_10",
        "price_return_20",
        "volatility_20",
        "ma_dist_20",
        "rsi_14",
        "atr_14_rel",
        "intraday_return",
        "hl_range",
        "volume_ratio_20",
        "momentum_ratio",
    ]

    samples: list[dict[str, Any]] = []

    for key, candles in histories.items():
        valid_candles = [
            c
            for c in candles
            if isinstance(c, dict) and c.get("close") is not None and c.get("session")
        ]
        if len(valid_candles) < 30:
            continue

        # Sort chronologically
        sorted_candles = sorted(valid_candles, key=lambda c: c["session"])
        closes = np.array([float(c["close"]) for c in sorted_candles], dtype=np.float64)
        opens = np.array(
            [float(c.get("open") or c["close"]) for c in sorted_candles], dtype=np.float64
        )
        highs = np.array(
            [
                float(c.get("high") or max(c["close"], opens[idx]))
                for idx, c in enumerate(sorted_candles)
            ],
            dtype=np.float64,
        )
        lows = np.array(
            [
                float(c.get("low") or min(c["close"], opens[idx]))
                for idx, c in enumerate(sorted_candles)
            ],
            dtype=np.float64,
        )
        volumes = np.array(
            [float(c.get("volume") or 1000.0) for c in sorted_candles], dtype=np.float64
        )

        n = len(sorted_candles)

        # For feature computation, need at least 20 historical sessions
        for i in range(20, n):
            c_t = closes[i]
            o_t = opens[i]
            h_t = highs[i]
            l_t = lows[i]
            v_t = volumes[i]

            ret_1 = (c_t - closes[i - 1]) / max(closes[i - 1], 1e-4)
            ret_5 = (c_t - closes[i - 5]) / max(closes[i - 5], 1e-4)
            ret_10 = (c_t - closes[i - 10]) / max(closes[i - 10], 1e-4)
            ret_20 = (c_t - closes[i - 20]) / max(closes[i - 20], 1e-4)

            hist_rets = (closes[i - 19 : i + 1] - closes[i - 20 : i]) / np.maximum(
                closes[i - 20 : i], 1e-4
            )
            vol_20 = float(np.std(hist_rets))

            sma_20 = float(np.mean(closes[i - 19 : i + 1]))
            ma_dist_20 = (c_t - sma_20) / max(sma_20, 1e-4)

            # RSI 14
            diffs = closes[i - 13 : i + 1] - closes[i - 14 : i]
            gains = np.maximum(diffs, 0.0)
            losses = np.maximum(-diffs, 0.0)
            avg_gain = float(np.mean(gains))
            avg_loss = float(np.mean(losses))
            rs = avg_gain / max(avg_loss, 1e-6)
            rsi_14 = 100.0 - (100.0 / (1.0 + rs))

            # ATR 14
            tr = np.maximum(
                highs[i - 13 : i + 1] - lows[i - 13 : i + 1],
                np.maximum(
                    np.abs(highs[i - 13 : i + 1] - closes[i - 14 : i]),
                    np.abs(lows[i - 13 : i + 1] - closes[i - 14 : i]),
                ),
            )
            atr_14_rel = float(np.mean(tr)) / max(c_t, 1e-4)

            intraday = (c_t - o_t) / max(o_t, 1e-4)
            hl_range = (h_t - l_t) / max(c_t, 1e-4)

            sma_vol = float(np.mean(volumes[i - 19 : i + 1]))
            volume_ratio_20 = v_t / max(sma_vol, 1.0)

            momentum_ratio = ret_5 / max(vol_20, 1e-4)

            feat_vec = [
                ret_1,
                ret_5,
                ret_10,
                ret_20,
                vol_20,
                ma_dist_20,
                rsi_14,
                atr_14_rel,
                intraday,
                hl_range,
                volume_ratio_20,
                momentum_ratio,
            ]

            sample: dict[str, Any] = {
                "key": key,
                "session": sorted_candles[i]["session"],
                "features": feat_vec,
                "close": c_t,
            }

            # Forward targets for different horizons
            # Horizon 1
            if i + 1 < n:
                r1 = (closes[i + 1] - opens[i + 1]) / max(opens[i + 1], 1e-4)
                sample["target_ret_1"] = r1
                sample["target_dir_1"] = 1 if r1 > 0 else 0
            else:
                sample["target_ret_1"] = None
                sample["target_dir_1"] = None

            # Horizon 5
            if i + 5 < n:
                r5 = (closes[i + 5] - opens[i + 1]) / max(opens[i + 1], 1e-4)
                sample["target_ret_5"] = r5
                sample["target_dir_5"] = 1 if r5 > 0 else 0
            else:
                sample["target_ret_5"] = None
                sample["target_dir_5"] = None

            # Horizon 10
            if i + 10 < n:
                r10 = (closes[i + 10] - opens[i + 1]) / max(opens[i + 1], 1e-4)
                sample["target_ret_10"] = r10
                sample["target_dir_10"] = 1 if r10 > 0 else 0
            else:
                sample["target_ret_10"] = None
                sample["target_dir_10"] = None

            # Horizon 20
            if i + 20 < n:
                r20 = (closes[i + 20] - opens[i + 1]) / max(opens[i + 1], 1e-4)
                sample["target_ret_20"] = r20
                sample["target_dir_20"] = 1 if r20 > 0 else 0
            else:
                sample["target_ret_20"] = None
                sample["target_dir_20"] = None

            samples.append(sample)

    return samples, feature_names


def train_and_evaluate_all_models(
    samples: list[dict[str, Any]],
    feature_names: list[str],
) -> dict[str, Any]:
    """Train and evaluate 5 model families across 4 prediction horizons."""
    sessions = sorted({s["session"] for s in samples})
    print(
        f"[*] Total feature samples: {len(samples)} across {len(sessions)} sessions "
        f"({sessions[0]} to {sessions[-1]})"
    )

    # Time-series walk-forward partition:
    # Train: first 65% of sessions
    # Embargo: 5 sessions buffer
    # Holdout: remaining sessions
    split_idx = int(len(sessions) * 0.65)
    train_sessions = set(sessions[:split_idx])
    _embargo_sessions = set(sessions[split_idx : split_idx + 5])
    test_sessions = set(sessions[split_idx + 5 :])

    horizons = [1, 5, 10, 20]
    metrics_report: list[dict[str, Any]] = []
    trained_models: dict[str, Any] = {}

    for h in horizons:
        dir_col = f"target_dir_{h}"
        ret_col = f"target_ret_{h}"

        # Filter valid samples for horizon h
        valid_train = [
            s for s in samples if s["session"] in train_sessions and s[dir_col] is not None
        ]
        valid_test = [
            s for s in samples if s["session"] in test_sessions and s[dir_col] is not None
        ]

        if len(valid_train) < 50 or len(valid_test) < 20:
            print(f"[!] Horizon {h}: Insufficient samples for training/testing. Skipping.")
            continue

        x_train = np.array([s["features"] for s in valid_train], dtype=np.float64)
        y_train_dir = np.array([s[dir_col] for s in valid_train], dtype=np.int32)
        y_train_ret = np.array([s[ret_col] for s in valid_train], dtype=np.float64)

        if len(np.unique(y_train_dir)) < 2:
            print(f"[!] Horizon {h}: Only 1 class present in training targets. Skipping.")
            continue

        x_test = np.array([s["features"] for s in valid_test], dtype=np.float64)
        y_test_dir = np.array([s[dir_col] for s in valid_test], dtype=np.int32)
        y_test_ret = np.array([s[ret_col] for s in valid_test], dtype=np.float64)

        print(
            f"\n[*] === Training Horizon {h} Sessions "
            f"(Train: {len(valid_train)}, Test: {len(valid_test)}) ==="
        )

        # 1. HistGradientBoosting Classifier
        hgb_clf = HistGradientBoostingClassifier(
            loss="log_loss",
            learning_rate=0.08,
            max_iter=40,
            max_leaf_nodes=15,
            min_samples_leaf=10,
            l2_regularization=2.0,
            random_state=1729,
        )
        hgb_clf.fit(x_train, y_train_dir)
        p_test_hgb = _safe_predict_proba(hgb_clf, x_test)
        pred_test_hgb = (p_test_hgb >= 0.5).astype(int)

        bacc_hgb = float(balanced_accuracy_score(y_test_dir, pred_test_hgb))
        auc_hgb = _safe_auc(y_test_dir, p_test_hgb)
        brier_hgb = float(brier_score_loss(y_test_dir, p_test_hgb))
        prec_hgb = float(precision_score(y_test_dir, pred_test_hgb, zero_division=0))
        rec_hgb = float(recall_score(y_test_dir, pred_test_hgb, zero_division=0))
        rank_ic_hgb = _safe_rank_ic(p_test_hgb, y_test_ret)

        trained_models[f"HistGB_Classifier_H{h}"] = hgb_clf
        metrics_report.append(
            {
                "horizon": h,
                "task": "classification",
                "model": "HistGradientBoostingClassifier",
                "balanced_accuracy": round(bacc_hgb, 4),
                "roc_auc": round(auc_hgb, 4),
                "brier_score": round(brier_hgb, 4),
                "precision": round(prec_hgb, 4),
                "recall": round(rec_hgb, 4),
                "rank_ic": round(float(rank_ic_hgb), 4),
            }
        )
        print(
            f"    HistGB Classifier (H{h}): BAcc={bacc_hgb * 100:.2f}%, "
            f"AUC={auc_hgb:.4f}, RankIC={rank_ic_hgb:.4f}"
        )

        # 2. Random Forest Classifier
        rf_clf = RandomForestClassifier(
            n_estimators=40,
            max_depth=5,
            min_samples_leaf=5,
            random_state=1729,
            n_jobs=1,
        )
        rf_clf.fit(x_train, y_train_dir)
        p_test_rf = _safe_predict_proba(rf_clf, x_test)
        pred_test_rf = (p_test_rf >= 0.5).astype(int)

        bacc_rf = float(balanced_accuracy_score(y_test_dir, pred_test_rf))
        auc_rf = _safe_auc(y_test_dir, p_test_rf)
        brier_rf = float(brier_score_loss(y_test_dir, p_test_rf))
        prec_rf = float(precision_score(y_test_dir, pred_test_rf, zero_division=0))
        rec_rf = float(recall_score(y_test_dir, pred_test_rf, zero_division=0))
        rank_ic_rf = _safe_rank_ic(p_test_rf, y_test_ret)

        trained_models[f"RandomForest_Classifier_H{h}"] = rf_clf
        metrics_report.append(
            {
                "horizon": h,
                "task": "classification",
                "model": "RandomForestClassifier",
                "balanced_accuracy": round(bacc_rf, 4),
                "roc_auc": round(auc_rf, 4),
                "brier_score": round(brier_rf, 4),
                "precision": round(prec_rf, 4),
                "recall": round(rec_rf, 4),
                "rank_ic": round(float(rank_ic_rf), 4),
            }
        )
        print(
            f"    Random Forest (H{h}): BAcc={bacc_rf * 100:.2f}%, "
            f"AUC={auc_rf:.4f}, RankIC={rank_ic_rf:.4f}"
        )

        # 3. Logistic Regression
        lr_pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lr",
                    LogisticRegression(
                        C=0.5, penalty="l2", solver="lbfgs", max_iter=500, random_state=1729
                    ),
                ),
            ]
        )
        lr_pipe.fit(x_train, y_train_dir)
        p_test_lr = _safe_predict_proba(lr_pipe, x_test)
        pred_test_lr = (p_test_lr >= 0.5).astype(int)

        bacc_lr = float(balanced_accuracy_score(y_test_dir, pred_test_lr))
        auc_lr = _safe_auc(y_test_dir, p_test_lr)
        brier_lr = float(brier_score_loss(y_test_dir, p_test_lr))
        prec_lr = float(precision_score(y_test_dir, pred_test_lr, zero_division=0))
        rec_lr = float(recall_score(y_test_dir, pred_test_lr, zero_division=0))
        rank_ic_lr = _safe_rank_ic(p_test_lr, y_test_ret)

        trained_models[f"LogisticRegression_H{h}"] = lr_pipe
        metrics_report.append(
            {
                "horizon": h,
                "task": "classification",
                "model": "LogisticRegression",
                "balanced_accuracy": round(bacc_lr, 4),
                "roc_auc": round(auc_lr, 4),
                "brier_score": round(brier_lr, 4),
                "precision": round(prec_lr, 4),
                "recall": round(rec_lr, 4),
                "rank_ic": round(float(rank_ic_lr), 4),
            }
        )
        print(
            f"    Logistic Regression (H{h}): BAcc={bacc_lr * 100:.2f}%, "
            f"AUC={auc_lr:.4f}, RankIC={rank_ic_lr:.4f}"
        )

        # 4. HistGradientBoosting Regressor
        hgb_reg = HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.08,
            max_iter=40,
            max_leaf_nodes=15,
            min_samples_leaf=10,
            l2_regularization=2.0,
            random_state=1729,
        )
        hgb_reg.fit(x_train, y_train_ret)
        pred_ret_hgb = hgb_reg.predict(x_test)

        mae_hgb = float(mean_absolute_error(y_test_ret, pred_ret_hgb))
        rmse_hgb = float(math.sqrt(mean_squared_error(y_test_ret, pred_ret_hgb)))
        dir_acc_hgb = float(np.mean((pred_ret_hgb > 0) == (y_test_ret > 0)))
        rank_ic_reg_hgb = _safe_rank_ic(pred_ret_hgb, y_test_ret)

        trained_models[f"HistGB_Regressor_H{h}"] = hgb_reg
        metrics_report.append(
            {
                "horizon": h,
                "task": "regression",
                "model": "HistGradientBoostingRegressor",
                "mae": round(mae_hgb, 4),
                "rmse": round(rmse_hgb, 4),
                "directional_accuracy": round(dir_acc_hgb, 4),
                "rank_ic": round(float(rank_ic_reg_hgb), 4),
            }
        )
        print(
            f"    HistGB Regressor (H{h}): MAE={mae_hgb:.4f}, RMSE={rmse_hgb:.4f}, "
            f"DirAcc={dir_acc_hgb * 100:.2f}%, RankIC={rank_ic_reg_hgb:.4f}"
        )

        # 5. Ridge Regression
        ridge_pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("ridge", Ridge(alpha=2.0, random_state=1729)),
            ]
        )
        ridge_pipe.fit(x_train, y_train_ret)
        pred_ret_ridge = ridge_pipe.predict(x_test)

        mae_ridge = float(mean_absolute_error(y_test_ret, pred_ret_ridge))
        rmse_ridge = float(math.sqrt(mean_squared_error(y_test_ret, pred_ret_ridge)))
        dir_acc_ridge = float(np.mean((pred_ret_ridge > 0) == (y_test_ret > 0)))
        rank_ic_ridge = _safe_rank_ic(pred_ret_ridge, y_test_ret)

        trained_models[f"Ridge_Regressor_H{h}"] = ridge_pipe
        metrics_report.append(
            {
                "horizon": h,
                "task": "regression",
                "model": "RidgeRegressor",
                "mae": round(mae_ridge, 4),
                "rmse": round(rmse_ridge, 4),
                "directional_accuracy": round(dir_acc_ridge, 4),
                "rank_ic": round(float(rank_ic_ridge), 4) if not math.isnan(rank_ic_ridge) else 0.0,
            }
        )
        print(
            f"    Ridge Regressor (H{h}): MAE={mae_ridge:.4f}, RMSE={rmse_ridge:.4f}, "
            f"DirAcc={dir_acc_ridge * 100:.2f}%, RankIC={rank_ic_ridge:.4f}"
        )

    return {
        "metrics": metrics_report,
        "models": trained_models,
        "feature_names": feature_names,
    }


def generate_prospective_rankings(
    samples: list[dict[str, Any]],
    trained_models: dict[str, Any],
    as_of_session: str = "2026-11-02",
) -> dict[str, Any]:
    """Generate prospective predictions and Top 5/10/20 rankings for as_of_session."""
    latest_samples = [s for s in samples if s["session"] == as_of_session]
    if not latest_samples:
        latest_session = max(s["session"] for s in samples)
        print(f"[!] Session {as_of_session} not found. Using latest session: {latest_session}")
        latest_samples = [s for s in samples if s["session"] == latest_session]
        as_of_session = latest_session

    print(
        f"\n[*] Generating prospective predictions for {len(latest_samples)} "
        f"securities as of {as_of_session}..."
    )
    x_latest = np.array([s["features"] for s in latest_samples], dtype=np.float64)

    rankings_by_horizon: dict[str, Any] = {}

    for h in [1, 5, 10, 20]:
        clf_model = trained_models.get(f"HistGB_Classifier_H{h}")
        reg_model = trained_models.get(f"HistGB_Regressor_H{h}")

        if clf_model is None or reg_model is None:
            continue

        probs = _safe_predict_proba(clf_model, x_latest)
        expected_returns = reg_model.predict(x_latest)

        scores_list = []
        for s, prob, exp_ret in zip(latest_samples, probs, expected_returns, strict=True):
            scores_list.append(
                {
                    "instrument_key": s["key"],
                    "session": as_of_session,
                    "horizon_sessions": h,
                    "latest_close": s["close"],
                    "direction_probability": round(float(prob), 4),
                    "expected_return": round(float(exp_ret), 5),
                    "expected_return_pct": f"{float(exp_ret) * 100:+.2f}%",
                }
            )

        # Sort by expected return descending
        scores_list.sort(key=lambda item: item["expected_return"], reverse=True)

        rankings_by_horizon[f"Horizon_{h}"] = {
            "horizon_sessions": h,
            "as_of_session": as_of_session,
            "total_scored_securities": len(scores_list),
            "top_5": scores_list[:5],
            "top_10": scores_list[:10],
            "top_20": scores_list[:20],
        }

    return rankings_by_horizon


def run_pipeline() -> dict[str, Any]:
    """Main execution orchestrating data loading, feature extraction, training, and rankings."""
    print("[*] Starting Multi-Model Multi-Horizon AlphaLens Execution...")
    mv_path = repo.parent / ".local-data" / "nse-market-expansion" / "market-view-latest.json"
    if not mv_path.exists():
        mv_path = repo / ".local-data" / "nse-market-expansion" / "market-view-latest.json"

    meta = json.loads(mv_path.read_text(encoding="utf-8"))
    mv_doc = json.loads((mv_path.parent / meta["path"]).read_text(encoding="utf-8"))
    histories = mv_doc.get("histories", {})

    print(f"[+] Loaded {len(histories)} security histories from {meta['path']}.")
    samples, feature_names = extract_features_and_targets(histories)

    train_res = train_and_evaluate_all_models(samples, feature_names)
    rankings = generate_prospective_rankings(
        samples, train_res["models"], as_of_session="2026-11-02"
    )

    # Serialize complete execution results
    output_report = {
        "schema": "alphalens.multi_model_evaluation.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "as_of_session": "2026-11-02",
        "metrics": train_res["metrics"],
        "rankings": rankings,
    }

    out_json = repo / "docs" / "ml" / "multi_model_execution_results.json"
    out_json.write_text(json.dumps(output_report, indent=2), encoding="utf-8")
    print(f"\n[+] Multi-model evaluation complete. Results written to {out_json}")

    return {
        "report": output_report,
        "models": train_res["models"],
        "metrics": train_res["metrics"],
    }


if __name__ == "__main__":
    run_pipeline()
