"""Fixed CPU-only model arena; outer tests never supplied to estimator fitting."""

from importlib.metadata import version
from typing import Any

from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.base import BaseEstimator
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier, XGBRegressor

from alphalens_evaluation.contracts import Family
from alphalens_training.contracts import TrainingConfig
from alphalens_training.engine import environment, pipeline


class CatBoostAdapter(BaseEstimator):  # type: ignore[misc]
    """Use sklearn's public estimator protocol without trusting CatBoost's old tags."""

    def __init__(self, task: str, parameters: dict[str, Any]) -> None:
        self.task = task
        self.parameters = parameters

    def fit(self, x: Any, y: Any) -> "CatBoostAdapter":
        factory = CatBoostClassifier if self.task == "classification" else CatBoostRegressor
        self.model_ = factory(**self.parameters)
        self.model_.fit(x, y)
        if self.task == "classification":
            self.classes_ = self.model_.classes_
        return self

    def predict(self, x: Any) -> Any:
        return self.model_.predict(x)

    def predict_proba(self, x: Any) -> Any:
        return self.model_.predict_proba(x)


def versions() -> dict[str, str]:
    return {
        **environment(),
        **{name: version(name) for name in ("lightgbm", "catboost", "xgboost-cpu", "pyarrow")},
    }


def build_model(family: Family, config: TrainingConfig) -> Pipeline:
    classifier = config.task == "classification"
    seed = config.random_seed
    estimator: Any
    if family == "lightgbm":
        factory = LGBMClassifier if classifier else LGBMRegressor
        estimator = factory(
            objective="binary" if classifier else "regression",
            n_estimators=32,
            learning_rate=0.1,
            num_leaves=7,
            max_depth=3,
            min_child_samples=5,
            reg_alpha=0.0,
            reg_lambda=1.0,
            subsample=1.0,
            colsample_bytree=1.0,
            random_state=seed,
            n_jobs=1,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
        )
    elif family == "catboost":
        estimator = CatBoostAdapter(
            config.task,
            dict(
                iterations=32,
                depth=3,
                learning_rate=0.1,
                l2_leaf_reg=1.0,
                loss_function="Logloss" if classifier else "RMSE",
                random_seed=seed,
                thread_count=1,
                task_type="CPU",
                verbose=False,
                allow_writing_files=False,
                bootstrap_type="No",
                random_strength=0.0,
                use_best_model=False,
                boosting_type="Plain",
            ),
        )
    elif family == "xgboost":
        factory = XGBClassifier if classifier else XGBRegressor
        estimator = factory(
            objective="binary:logistic" if classifier else "reg:squarederror",
            n_estimators=32,
            max_depth=3,
            learning_rate=0.1,
            min_child_weight=3,
            reg_alpha=0.0,
            reg_lambda=1.0,
            subsample=1.0,
            colsample_bytree=1.0,
            tree_method="hist",
            device="cpu",
            random_state=seed,
            n_jobs=1,
            eval_metric="logloss" if classifier else "rmse",
            verbosity=0,
        )
    else:
        return pipeline(config.model_copy(update={"model_family": family}))
    imputer = SimpleImputer(strategy="median", add_indicator=False, keep_empty_features=False)
    if family == "lightgbm":
        # Preserve matching names through fit/predict; never suppress the warning.
        imputer.set_output(transform="pandas")
    return Pipeline(
        [
            (
                "imputer",
                imputer,
            ),
            ("estimator", estimator),
        ]
    )
