"""Small labeled TEST_ONLY provider bodies; no market observations or fitting."""

import json
from datetime import UTC, date, datetime
from typing import Any

from alphalens_data.providers.multi_contracts import Instrument

AT = datetime(2026, 10, 10, 10, tzinfo=UTC)
DAY = date(2026, 10, 9)


def instrument(provider: Any = "upstox", **changes: Any) -> Instrument:
    key = {
        "upstox": "NSE_EQ|INE000A00001",
        "indstocks": "NSE_123",
        "angel-one": "123",
        "yahoo": "TEST_ONLY.NS",
        "alpha-vantage": "TEST_ONLY.NSE",
        "tejhq": "TEST_ONLY",
    }[provider]
    return Instrument.model_validate(
        {
            "provider": provider,
            "provider_key": key,
            "exchange": "NSE",
            "segment": "NSE_EQ" if provider == "upstox" else "NSE",
            "symbol": "TEST_ONLY",
            "isin": "INE000A00001",
            "series": "EQ",
            "observed_at": AT,
            "identity_evidence": "TEST_ONLY_NOT_REAL_INSTRUMENT",
            "revision_sha256": "a" * 64,
            "canonical_security_id": "TEST_ONLY:SECURITY_A",
            **changes,
        }
    )


def payload(provider: str) -> bytes:
    row: list[Any] = ["2026-10-09T00:00:00+05:30", "100.123456789", "102", "99", "101", 1000]
    value: dict[str, Any] = (
        {"status": "success", "data": {"candles": [row]}}
        if provider == "upstox"
        else (
            {
                "success": True,
                "data": {
                    "NSE_123": {
                        "candles": [
                            {
                                "ts": 1791484200,
                                "o": row[1],
                                "h": row[2],
                                "l": row[3],
                                "c": row[4],
                                "v": row[5],
                            }
                        ]
                    }
                },
            }
            if provider == "indstocks"
            else {"status": True, "data": [row]}
        )
    )
    # Derive fixture epoch from the declared aware fixture clock, never an actual quote.
    if provider == "indstocks":
        value["data"]["NSE_123"]["candles"][0]["ts"] = int(
            datetime.fromisoformat(row[0]).timestamp()
        )
    return json.dumps(value).encode()


class MissingCredential(Exception):
    winerror = 1168


class CredentialFixture:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    def __init__(self) -> None:
        self.record: dict[str, Any] | None = None
        self.writes = 0

    def CredRead(self, target: str, kind: int) -> dict[str, Any]:
        if self.record is None:
            raise MissingCredential
        return {**self.record, "CredentialBlob": self.record["CredentialBlob"].encode("utf-16-le")}

    def CredWrite(self, record: dict[str, Any], flags: int) -> None:
        self.record = record
        self.writes += 1
