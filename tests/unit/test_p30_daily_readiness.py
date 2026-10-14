"""Constructed TEST_ONLY evidence; never a live ingestion or model acceptance claim."""

import json
from pathlib import Path

import pytest
from scripts.build_p19_test_evidence import AT, DAY, request
from workers.daily.artifact_reviews import XGBOOST_SHA256, XGBOOST_TYPES, scoped_review
from workers.daily.engine import Worker
from workers.providers import daily, upstox
from workers.providers.store import ProviderStore

from alphalens_data.daily.contracts import Request
from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.providers.multi_contracts import Access, Instrument


def fixture_release(path: Path, *, close: int = 101) -> Request:
    instrument = Instrument(
        provider="upstox",
        provider_key="NSE_EQ|INE000A01001",
        exchange="NSE",
        segment="NSE_EQ",
        symbol="TEST_ONLY",
        isin="INE000A01001",
        observed_at=AT,
        revision_sha256="a" * 64,
        identity_evidence="CONSTRUCTED_TEST_ONLY_CURRENT_MASTER",
    )
    response = json.dumps(
        {
            "status": "success",
            "data": {
                "candles": [
                    [str(DAY) + "T00:00:00+05:30", 100, 102, 99, close, 1000],
                ]
            },
        }
    )
    path.write_bytes(
        stable_json(
            {
                "version": "p30.upstox.operational-release.v1",
                "instrument": instrument.model_dump(mode="json"),
                "received_at": AT.isoformat(),
                "response": response,
            }
        )
    )
    req = request(path)
    return req.model_copy(
        update={
            "mode": "DAILY",
            "provider": req.provider.model_copy(
                update={
                    "source": "upstox",
                    "dataset": "TEST_ONLY_CONSTRUCTED_OPERATIONAL_RELEASE",
                    "status": "SOURCE_APPROVED_FOR_RESEARCH",
                    "automation_permitted": True,
                    "retention_permitted": True,
                    "research_permitted": True,
                }
            ),
            "calendar": req.calendar.model_copy(
                update={
                    "sessions": tuple(
                        s.model_copy(update={"evidence_type": "OFFICIAL_VERIFIED_SESSION"})
                        for s in req.calendar.sessions
                    )
                }
            ),
        }
    )


def test_exact_artifact_review_never_extends_other_artifacts_or_extra_types() -> None:
    assert scoped_review(XGBOOST_SHA256, XGBOOST_TYPES, set()) == XGBOOST_TYPES
    assert not scoped_review("a" * 64, XGBOOST_TYPES, set())
    assert not scoped_review(XGBOOST_SHA256, XGBOOST_TYPES | {"unreviewed.Type"}, set())
    assert not scoped_review(XGBOOST_SHA256, {"xgboost.core.Booster"}, set())


@pytest.mark.parametrize(
    "flag", ["retention_permitted", "research_permitted", "automation_permitted"]
)
def test_operational_worker_does_not_read_payload_when_rights_not_cleared(
    tmp_path: Path, flag: str
) -> None:
    req = fixture_release(tmp_path / "TEST_ONLY.json")
    req = req.model_copy(update={"provider": req.provider.model_copy(update={flag: False})})
    result = Worker(tmp_path / "worker").run(req, tmp_path / "never-created.json")
    assert result["state"] == "BLOCKED_SOURCE" and not result["products"]


@pytest.mark.parametrize("interrupted", [False, True])
def test_operational_staging_replays_and_recovers_without_canonical_or_forecasts(
    tmp_path: Path, interrupted: bool
) -> None:
    path = tmp_path / "TEST_ONLY.json"
    req = fixture_release(path)

    def fail(stage: str) -> None:
        if stage == "provider_observations":
            raise OSError("CONSTRUCTED_TEST_ONLY_INTERRUPTION")

    if interrupted:
        with pytest.raises(DataContractError, match="RETRYABLE"):
            Worker(tmp_path / "worker", hook=fail).run(req, path)
    worker = Worker(tmp_path / "worker")
    result = worker.run(req, path)
    assert result == worker.run(req, path)
    product = worker.store.product(req.run_id, "provider_observations")
    assert product["rows"][0]["price_basis"] == "UNKNOWN"
    assert not product["canonical_join_permitted"] and not product["feature_eligibility"]
    assert result["counts"]["observations"] == 1 and result["counts"]["predictions"] == 0
    assert len(worker.store.receipts()) == 1
    changed = fixture_release(tmp_path / "TEST_ONLY-correction.json", close=102)
    assert changed.run_id != req.run_id
    worker.run(changed, tmp_path / "TEST_ONLY-correction.json")
    assert (
        worker.store.product(changed.run_id, "provider_observations")["rows"][0]["observation_id"]
        != product["rows"][0]["observation_id"]
    )


def test_corrupted_operational_release_never_publishes(tmp_path: Path) -> None:
    path = tmp_path / "TEST_ONLY.json"
    req = fixture_release(path).model_copy(update={"payload_sha256": checksum(b"wrong")})
    result = Worker(tmp_path / "worker").run(req, path)
    assert result["state"] == "FAILED" and not result["products"]


def test_actual_config_gates_prevent_network_and_price_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Uncleared retention must prevent genuine network access")

    monkeypatch.setattr(upstox.UpstoxClient, "get", forbidden)
    req = fixture_release(tmp_path / "TEST_ONLY.json")
    result = daily.run(
        Access(
            provider="upstox",
            credential_configured=True,
            nse_verified=True,
            token_kind="READ_ONLY_ANALYTICS",
        ),
        req.calendar,
        tmp_path / "provider",
        tmp_path / "operational",
        at=AT,
    )
    assert result["api_calls"] == 0 and result["state"] == "BLOCKED_SOURCE"
    assert not (tmp_path / "operational").exists()


def test_full_worker_orchestration_offline_replay_uses_no_second_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    req = fixture_release(tmp_path / "TEST_ONLY.json")
    provider = ProviderStore(tmp_path / "provider")
    provider.initialize()
    instrument = Instrument(
        provider="upstox",
        provider_key=upstox.KEY,
        exchange="NSE",
        segment="NSE_EQ",
        symbol="RELIANCE",
        isin="INE002A01018",
        observed_at=AT,
        revision_sha256="a" * 64,
        identity_evidence="CONSTRUCTED_TEST_ONLY_IDENTITY",
    )
    (provider.root / "master-identity-1.json").write_text(instrument.model_dump_json())
    calls = []

    def response(*args: object, **kwargs: object) -> upstox.Reply:
        calls.append(True)
        body = json.dumps(
            {
                "status": "success",
                "data": {
                    "candles": [
                        [str(DAY) + "T00:00:00+05:30", 100, 102, 99, 101, 1000],
                    ]
                },
            }
        ).encode()
        return upstox.Reply(200, body, AT, "ACCEPTED")

    monkeypatch.setattr(upstox.UpstoxClient, "get", response)
    access = Access(
        provider="upstox",
        account_status="ACTIVE",
        credential_configured=True,
        permission_reference="TEST_ONLY_PERMISSION",
        automation_permitted=True,
        retention_permitted=True,
        research_permitted=True,
        nse_verified=True,
        token_kind="READ_ONLY_ANALYTICS",
        operator_activation=True,
    )
    first = daily.run(access, req.calendar, provider.root, tmp_path / "operational", at=AT)
    second = daily.run(access, req.calendar, provider.root, tmp_path / "operational", at=AT)
    assert first["sessions"] == second["sessions"] and len(calls) == 1
    assert first["sessions"][0]["counts"]["predictions"] == 0
