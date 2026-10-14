"""TEST_ONLY transport, credential isolation and private observed-data contracts."""

import gzip
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from workers.providers import credentials, private_view, upstox
from workers.providers.store import ProviderStore
from workers.providers.validation import status

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_contracts import Instrument

AT = datetime(2026, 10, 14, 14, tzinfo=UTC)
SECRET = "TEST_ONLY_PRIVATE_CREDENTIAL_VALUE" * 4


def identity() -> Instrument:
    return Instrument(
        provider="upstox",
        provider_key=upstox.KEY,
        exchange="NSE",
        segment="NSE_EQ",
        symbol="RELIANCE",
        isin="INE002A01018",
        observed_at=AT,
        revision_sha256="a" * 64,
        identity_evidence="TEST_ONLY_CURRENT_MASTER",
    )


@pytest.fixture
def store(tmp_path: Path) -> ProviderStore:
    result = ProviderStore(tmp_path / "private")
    result.initialize()
    return result


def test_labeled_multiline_import_preserves_legacy_key_and_requires_unique_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "input.txt"
    path.write_text("Alpha Vantage: TESTONLY123456789\nUpstox: " + SECRET, encoding="utf-8")
    assert credentials.select_file_token(path) == SECRET
    path.write_text(SECRET + "\n" + "OTHER_TEST_ONLY_TOKEN_" * 9, encoding="utf-8")
    with pytest.raises(ValueError, match="LOCAL_TOKEN_SELECTION"):
        credentials.select_file_token(path)
    path.write_text("Upstox: " + SECRET, encoding="utf-16")
    assert credentials.select_file_token(path) == SECRET


def test_existing_different_upstox_credential_is_never_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Module:
        CRED_TYPE_GENERIC = 1

        def CredRead(self, *args: Any) -> dict[str, Any]:
            return {"CredentialBlob": "EXISTING_DIFFERENT_TEST_ONLY"}

        def CredWrite(self, *args: Any) -> None:
            pytest.fail("Different existing credential must be preserved")

    monkeypatch.setattr(credentials, "credential_module", lambda: Module())
    with pytest.raises(ValueError, match="EXISTING_ANALYTICS_CREDENTIAL_PRESERVED"):
        credentials.store_token(SECRET)


@pytest.mark.parametrize(
    "code,state",
    [
        (401, "AUTH_REJECTED"),
        (403, "PERMISSION_OR_SEGMENT_REJECTED"),
        (429, "RATE_LIMITED"),
        (503, "PROVIDER_OUTAGE"),
        (302, "REDIRECT_REJECTED"),
    ],
)
def test_transport_redacts_failure_bodies_and_counts_requests(
    store: ProviderStore, monkeypatch: pytest.MonkeyPatch, code: int, state: str
) -> None:
    calls = []

    class Response:
        status = code

        def getheader(self, *args: Any) -> str:
            return "0"

        def read(self, *args: Any) -> bytes:
            return b"Untrusted error body: account and request details"

    class Connection:
        def __init__(self, host: str, **kwargs: Any) -> None:
            assert host == "api.upstox.com"

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            assert method == "GET" and "order" not in path and SECRET not in path
            assert headers["Authorization"] == "Bearer " + SECRET
            calls.append(path)

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(upstox, "HTTPSConnection", Connection)
    monkeypatch.setattr(upstox, "load_token", lambda: SECRET)
    client = upstox.UpstoxClient(store, budget=1)
    reply = client.get("quote")
    assert reply.body == b"" and reply.status == code
    assert reply.state == state
    assert len(calls) == client.calls == 1
    with pytest.raises(DataContractError, match="BUDGET"):
        client.get("quote")
    assert store.status(AT.timestamp())["collection_enabled"] is False


def test_arbitrary_endpoint_bse_and_invalid_dates_never_reach_transport(
    store: ProviderStore,
) -> None:
    client = upstox.UpstoxClient(store)
    for key in ("BSE_EQ|INE002A01018", "NSE_EQ|bad?token", "https://attacker.invalid"):
        with pytest.raises(DataContractError):
            client.get("quote", key=key)
    with pytest.raises(DataContractError):
        client.get("orders")  # type: ignore[arg-type]
    with pytest.raises(DataContractError):
        client.get("candles", start=date(2026, 10, 15), end=date(2026, 10, 14))
    assert client.calls == 0


def test_retry_after_is_respected_without_truncation_or_automatic_auth_retry(
    store: ProviderStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        status = 429

        def getheader(self, *args: Any) -> str:
            return "120"

        def read(self, *args: Any) -> bytes:
            return b"quota"

    class Connection:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def request(self, *args: Any, **kwargs: Any) -> None:
            pass

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(upstox, "HTTPSConnection", Connection)
    monkeypatch.setattr(upstox, "load_token", lambda: SECRET)
    client = upstox.UpstoxClient(store, retries=2)
    assert client.get("quote").state == "RATE_LIMITED" and client.calls == 1
    with pytest.raises(DataContractError, match="BACKOFF"):
        client.get("quote")


def test_master_keeps_current_identity_separate_from_historical_membership() -> None:
    body = gzip.compress(
        json.dumps(
            [
                {
                    "segment": "NSE_EQ",
                    "exchange": "NSE",
                    "instrument_type": "EQ",
                    "instrument_key": upstox.KEY,
                    "isin": "INE002A01018",
                    "trading_symbol": "RELIANCE",
                }
            ]
        ).encode()
    )
    instruments, summary = upstox.instrument_master(upstox.Reply(200, body, AT, "ACCEPTED"))
    assert len(instruments) == 1 and instruments[0].series is None
    assert instruments[0].canonical_security_id is None
    assert summary["eligible_historical_common_equities"] is None


def test_private_chart_uses_p6_formulas_without_eligibility_promotion_or_disk_prices(
    store: ProviderStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    (store.root / "master-identity-1.json").write_text(identity().model_dump_json())
    body = json.dumps(
        {
            "status": "success",
            "data": {
                "candles": [
                    ["2026-10-13T00:00:00+05:30", 100, 110, 99, 105, 1000],
                    ["2026-10-12T00:00:00+05:30", 100, 110, 99, 100, 1000],
                ]
            },
        }
    ).encode()
    calls = []

    def fake_get(self: Any, *args: Any, **kwargs: Any) -> upstox.Reply:
        calls.append(True)
        return upstox.Reply(200, body, AT, "ACCEPTED")

    monkeypatch.setattr(upstox.UpstoxClient, "get", fake_get)
    result = private_view.view(store.root, now=AT)
    assert result["latest_close"] == "105" and result["change"] == "5"
    assert result["price_basis"] == "UNKNOWN" and result["retained"] is False
    assert result["indicators"]["sma_20"]["points"][0]["value"] is None
    assert result["passport"]["current_inference"] == "UNAVAILABLE"
    assert private_view.view(store.root, now=AT) is result and len(calls) == 1
    assert not list(store.root.glob("*candle*"))


def test_validation_projection_rejects_arbitrary_secret_fields(store: ProviderStore) -> None:
    data = {
        "schema": "p30.upstox.validation.v1",
        "authentication": "ACCEPTED",
        "verified_at": AT.isoformat(),
        "credential_readback": True,
        "token": SECRET,
        "requests": [{"operation": "quote", "state": SECRET, "http_status": 200}],
    }
    (store.root / "validation-1.json").write_text(json.dumps(data))
    projected = status(store.root)
    assert SECRET not in json.dumps(projected) and projected["requests"] == []
    assert projected["ongoing_collection"] == "DISABLED"
