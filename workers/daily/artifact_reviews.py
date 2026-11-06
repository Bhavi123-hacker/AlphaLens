"""Exact-byte local artifact review; never a global serializer allowlist change."""

from collections.abc import Set

XGBOOST_SHA256 = "e418c80ae33c8f41ba48900e312bedaffd34705d0cab1437dde93a3acaebbc03"
XGBOOST_TYPES = frozenset({"xgboost.core.Booster", "xgboost.sklearn.XGBClassifier"})


def scoped_review(model_hash: str, unknown: Set[str], reviewed: Set[str]) -> frozenset[str]:
    extra = frozenset(unknown - reviewed)
    if model_hash == XGBOOST_SHA256 and extra == XGBOOST_TYPES:
        return XGBOOST_TYPES
    return frozenset()
