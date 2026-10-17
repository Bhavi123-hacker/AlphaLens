"""TEST_ONLY evidence boundary tests. No fixture is a genuine forecast."""

from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse_v2.pipeline import verified, write_checked
from workers.experimental_nse_v2.workspace import read_workspace, research_evidence


def test_absent_workspace_is_explicit_and_never_publishes(tmp_path: Path) -> None:
    for root in (None, tmp_path):
        result = read_workspace(root)
        assert result["available"] is False
        assert result["candidates"] == []
        assert result["accepted_current_rankings"] == 0
        assert result["status"] == "EXPERIMENTAL_UNVALIDATED"


def test_checked_evidence_rejects_tamper_and_preserves_immutable_original(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.json"
    write_checked(path, {"classification": "TEST_ONLY", "scores": []})
    assert verified(path)["classification"] == "TEST_ONLY"
    with pytest.raises((ValueError, FileExistsError)):
        write_checked(path, {"classification": "TEST_ONLY", "scores": [1]})
    path.write_text("{}")
    with pytest.raises(ValueError, match="CHECKSUM"):
        verified(path)


def test_company_identity_and_technical_evidence_use_exact_saved_inputs() -> None:
    identity = {
        "provider_key": "NSE_EQ|INE000000001",
        "isin": "INE000000001",
        "symbol": "TEST_ONLY",
        "name": "TEST_ONLY COMPANY",
        "segment": "NSE_EQ",
        "exchange": "NSE",
        "instrument_type": "EQ",
    }
    row = {
        "key": identity["provider_key"],
        "symbol": "TEST_ONLY",
        "session": "2025-01-01",
        "feature_names": ["price_return_5", "rsi_14"],
        "features": [0.05, 55.0],
        "risk": {"historical_price_drawdown_60": -0.1},
    }
    result = research_evidence(row, identity)
    assert result["company_name"] == "TEST_ONLY COMPANY"
    assert result["technical_evidence"][0]["value"] == 5.0
    assert result["technical_evidence"][1]["value"] == 55.0
    assert result["historical_evidence"]["maximum_observed_price_drawdown_percent"] == -10.0
    assert row["features"] == [0.05, 55.0]
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        research_evidence(row, {**identity, "isin": "INE000000002"})
    assert research_evidence(row, {**identity, "name": None})["company_name"] is None


@pytest.mark.parametrize("inference_dataset", ["TEST_ONLY_OLD_SNAPSHOT", "TEST_ONLY_FOREIGN"])
def test_newer_collection_preserves_only_verified_ancestral_saved_forecasts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inference_dataset: str
) -> None:
    from workers.experimental_nse_v2 import acceptance, data, models, workflow, workspace
    from workers.experimental_nse_v2.features import FEATURE_NAMES

    (tmp_path / "evaluation.json").write_text("TEST_ONLY")
    (tmp_path / "latest-inference.txt").write_text("20250102T120000000000Z.json")
    key = "NSE_EQ|INE000000001"
    model = {
        "model_id": "TEST_ONLY_MODEL",
        "protocol_id": "TEST_ONLY_PROTOCOL",
        "dataset_id": "TEST_ONLY_BASE",
        "feature_names": list(FEATURE_NAMES),
        "algorithm": "TEST_ONLY",
        "feature_version": "TEST_ONLY",
        "trained_at": "2025-01-01T12:00:00+00:00",
    }
    report = {
        "model_id": model["model_id"],
        "model_sha256": "TEST_ONLY",
        "candidate_summary": {},
        "baseline_summary": {},
        "evidence_conclusion": "NO_DEMONSTRATED_EDGE",
    }
    row = {
        "key": key,
        "symbol": "TEST_ONLY",
        "session": "2025-01-01",
        "observed_price": "105",
        "feature_names": list(FEATURE_NAMES),
        "features": [0.01] * len(FEATURE_NAMES),
        "score": 0.4,
        "inference_at": "2025-01-02T12:00:00+00:00",
        "risk": {"return_daily_sd_20": 0.01, "historical_price_drawdown_60": -0.1, "volume": 1000},
        "eligible_for_prospective": True,
    }
    inference = {
        "model_id": model["model_id"],
        "dataset_id": inference_dataset,
        "candidates": [row],
        "exclusions": [],
        "gap": None,
    }
    dataset: dict[str, Any] = {
        "dataset_id": "TEST_ONLY_NEW_SNAPSHOT",
        "base_dataset_id": "TEST_ONLY_BASE",
        "rows": [{"key": key, "session": "2025-01-01", "symbol": "TEST_ONLY", "close": "105"}],
        "identities": [
            {
                "provider_key": key,
                "isin": "INE000000001",
                "symbol": "TEST_ONLY",
                "name": "TEST_ONLY COMPANY",
                "segment": "NSE_EQ",
                "exchange": "NSE",
                "instrument_type": "EQ",
            }
        ],
        "sessions": ["2025-01-01", "2025-01-02"],
        "permission_reference": "TEST_ONLY",
        "quality": {},
        "source_observed_at": "2025-01-02T12:00:00+00:00",
        "clock": {},
    }
    monkeypatch.setattr(workspace, "verify", lambda path: None)
    monkeypatch.setattr(
        workspace, "verified", lambda path: inference if path.parent.name == "inference" else report
    )
    monkeypatch.setattr(workspace, "protocol_id", lambda price_only: "TEST_ONLY_PROTOCOL")
    monkeypatch.setattr(models, "load_model", lambda path, checksum: model)
    monkeypatch.setattr(models, "predict_vector", lambda model, values: (0.4, []))
    monkeypatch.setattr(data, "load_current", lambda root: dataset)
    monkeypatch.setattr(data, "load", lambda root: {"dataset_id": "TEST_ONLY_BASE"})
    monkeypatch.setattr(
        data,
        "dataset_versions",
        lambda root: {"TEST_ONLY_BASE", "TEST_ONLY_OLD_SNAPSHOT", "TEST_ONLY_NEW_SNAPSHOT"},
    )
    monkeypatch.setattr(data, "collected_timings", lambda root: {})
    monkeypatch.setattr(workspace, "summary", lambda *args, **kwargs: {"eligible_forecasts": 1})
    monkeypatch.setattr(acceptance, "evidence_bundle", lambda *args: {})
    monkeypatch.setattr(acceptance, "readiness", lambda bundle: {})
    monkeypatch.setattr(workflow, "read_status", lambda root: {"state": "TEST_ONLY_REPLAY"})
    if inference_dataset == "TEST_ONLY_FOREIGN":
        with pytest.raises(ValueError, match="LINEAGE_MISMATCH"):
            read_workspace(tmp_path)
    else:
        result = read_workspace(tmp_path)
        assert result["dataset"]["latest_collection_date"] == "2025-01-02"
        assert result["dataset"]["latest_scored_date"] == "2025-01-01"
        assert result["model"]["inference_dataset_id"] == "TEST_ONLY_OLD_SNAPSHOT"
        assert result["candidates"][0]["score"] == 0.4
        assert result["candidates"][0]["observation_date"] == "2025-01-01"
