"""TEST_ONLY constructed UDiFF fixtures, not real NSE prices or permissions."""

from __future__ import annotations

import csv
import gzip
import io
import json
import subprocess
import sys
import zipfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import digest, encoded, initialize, write_new
from workers.nse_market import engine
from workers.nse_market import manual_eod as eod
from workers.providers import universe
from workers.providers.upstox import Reply

AT = datetime(2025, 1, 4, 12, tzinfo=UTC)
ISIN = "INE002A01018"  # Identifier only; all prices below are constructed.


def fixture(
    tmp_path: Path, changes: dict[str, str] | None = None, *, zipped: bool = True
) -> tuple[Path, dict[str, Any], universe.Snapshot, Path]:
    row = dict.fromkeys(eod.HEADERS, "")
    row.update(
        TradDt="2025-01-03",
        BizDt="2025-01-03",
        Sgmt="CM",
        Src="NSE",
        FinInstrmTp="STK",
        FinInstrmId="123",
        ISIN=ISIN,
        TckrSymb="TEST-ONLY",
        SctySrs="EQ",
        FinInstrmNm="TEST ONLY",
        OpnPric="10",
        HghPric="12",
        LwPric="9",
        ClsPric="11",
        TtlTradgVol="100",
        SsnId="F1",
    )
    row.update(changes or {})
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=eod.HEADERS)
    writer.writeheader()
    writer.writerow(row)
    csv_body = text.getvalue().encode()
    name = "BhavCopy_NSE_CM_0_0_0_20250103_F_0000.csv"
    source = tmp_path / (name + (".zip" if zipped else ""))
    if zipped:
        with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name, csv_body)
    else:
        source.write_bytes(csv_body)
    provenance = {
        "source_url": "https://nsearchives.nseindia.com/content/cm/" + source.name,
        "raw_sha256": digest(source.read_bytes()),
        "published_at": "2025-01-03T13:00:00+00:00",
        "retrieved_at": "2025-01-03T14:00:00+00:00",
        "publication_reference": "TEST_ONLY operator-obtained official publication evidence",
    }
    native = [
        {
            "segment": "NSE_EQ",
            "exchange": "NSE",
            "isin": ISIN,
            "instrument_key": "NSE_EQ|" + ISIN,
            "trading_symbol": "TEST-ONLY",
            "name": "TEST ONLY",
            "instrument_type": "EQ",
            "security_type": "NORMAL",
        }
    ]
    master = universe.parse(Reply(200, gzip.compress(encoded(native)), AT, "ACCEPTED"))
    timing = encoded(
        {
            "status": "success",
            "data": [
                {
                    "exchange": "NSE",
                    "start_time": int(datetime(2025, 1, 3, 4, tzinfo=UTC).timestamp() * 1000),
                    "end_time": int(datetime(2025, 1, 3, 10, tzinfo=UTC).timestamp() * 1000),
                }
            ],
        }
    )
    calendar = tmp_path / "calendar.json"
    engine._checked(
        calendar,
        {"raw_hex": timing.hex(), "raw_sha256": digest(timing), "received_at": AT.isoformat()},
    )
    return source, provenance, master, calendar


def candidate(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    source, provenance, master, calendar = fixture(tmp_path)
    return source, eod.review(source, provenance, master, calendar, at=AT)


def approval(tmp_path: Path, root: Path, value: dict[str, Any]) -> dict[str, Any]:
    evidence = tmp_path / "TEST_ONLY_evidence.txt"
    evidence.write_text("TEST_ONLY permission and publication fixture, not an actual grant")
    proof = {"path": str(evidence), "sha256": digest(evidence.read_bytes())}
    return {
        "candidate_id": value["candidate_id"],
        "raw_sha256": value["raw_sha256"],
        "source": eod.SOURCE,
        "destination": str(root),
        "session": value["session"],
        "instrument_keys": [r["key"] for r in value["rows"]],
        "mutation_scope": "APPEND_NSE_MANUAL_EOD_SOURCE_ONLY_NO_MODEL_OR_PROVIDER_MUTATION",
        "rights_scope": "PRIVATE_RETENTION_AND_RESEARCH_OF_THIS_EXACT_NSE_SOURCE",
        "operator_approval_reference": "TEST_ONLY explicit operator approval",
        "approved_at": (AT - timedelta(minutes=1)).isoformat(),
        "expires_at": (AT + timedelta(minutes=1)).isoformat(),
        "rights_evidence": proof,
        "publication_evidence": proof,
    }


@pytest.mark.parametrize("zipped", [False, True])
def test_preview_preserves_source_and_never_promotes_raw_basis(
    tmp_path: Path, zipped: bool
) -> None:
    source, provenance, master, calendar = fixture(tmp_path, zipped=zipped)
    before = source.read_bytes()
    value = eod.review(source, provenance, master, calendar, at=AT)
    assert value["rows"][0]["close"] == "11"
    assert value["source"] == eod.SOURCE and value["price_basis"] == eod.BASIS
    assert value["model_compatible"] is False and value["rights_verified"] is False
    assert value["provider_requests"] == 0 and source.read_bytes() == before


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"TradDt": "2025-01-02"}, "SESSION_MISMATCH"),
        ({"Src": "BSE"}, "CASH_SOURCE"),
        ({"ClsPric": "NaN"}, "NO_ACCEPTABLE"),
        ({"HghPric": "9"}, "NO_ACCEPTABLE"),
        ({"TtlTradgVol": "10.5"}, "NO_ACCEPTABLE"),
        ({"ISIN": "INE002A01019"}, "NO_ACCEPTABLE"),
        ({"OptnTp": "CE"}, "NO_ACCEPTABLE"),
        ({"SctySrs": "XX"}, "NO_ACCEPTABLE"),
        ({"SsnId": "F2"}, "NO_ACCEPTABLE"),
        ({"TckrSymb": "OTHER"}, "NO_UNAMBIGUOUS"),
    ],
)
def test_corrupt_or_incompatible_record_never_publishes(
    tmp_path: Path, change: dict[str, str], reason: str
) -> None:
    source, provenance, master, calendar = fixture(tmp_path, change)
    with pytest.raises(ValueError, match=reason):
        eod.review(source, provenance, master, calendar, at=AT)
    assert not (tmp_path / "imports").exists()


@pytest.mark.parametrize(
    "entry", ["../escape.csv", "C:\\escape.csv", "other.csv", "folder/data.csv"]
)
def test_zip_traversal_and_wrong_member_rejected(tmp_path: Path, entry: str) -> None:
    source, provenance, master, calendar = fixture(tmp_path)
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(entry, b"TEST_ONLY")
    provenance["raw_sha256"] = digest(source.read_bytes())
    with pytest.raises(ValueError, match="ZIP_MEMBER"):
        eod.review(source, provenance, master, calendar, at=AT)


def test_strict_schema_and_duplicate_conflict(tmp_path: Path) -> None:
    source, provenance, master, calendar = fixture(tmp_path, zipped=False)
    body = source.read_text()
    source.write_text(body.replace("TradDt", "TradeDate"))
    provenance["raw_sha256"] = digest(source.read_bytes())
    with pytest.raises(ValueError, match="EXACT_SCHEMA"):
        eod.review(source, provenance, master, calendar, at=AT)
    source.write_text(body + body.splitlines()[-1] + "\n")
    provenance["raw_sha256"] = digest(source.read_bytes())
    with pytest.raises(ValueError, match="DUPLICATE"):
        eod.review(source, provenance, master, calendar, at=AT)


@pytest.mark.parametrize(
    "field,value",
    [
        ("published_at", "2025-01-03T09:00:00+00:00"),
        ("retrieved_at", "2099-01-01T00:00:00+00:00"),
        ("retrieved_at", "2025-01-03T14:00:00"),
        ("raw_sha256", "f" * 64),
    ],
)
def test_publication_clock_and_raw_identity_required(
    tmp_path: Path, field: str, value: str
) -> None:
    source, provenance, master, calendar = fixture(tmp_path)
    provenance[field] = value
    with pytest.raises(ValueError):
        eod.review(source, provenance, master, calendar, at=AT)


def test_exact_approval_atomic_idempotence_and_read_corruption(tmp_path: Path) -> None:
    source, value = candidate(tmp_path)
    root = tmp_path / "TEST_ONLY_source_store"
    policy = approval(tmp_path, root, value)
    kwargs = {"approved_candidate": value["candidate_id"], "at": AT}
    with pytest.raises(ValueError, match="EXACT_OPERATOR_SCOPE"):
        eod.import_candidate(root, source, value, {}, **kwargs)
    assert not root.exists()
    first = eod.import_candidate(root, source, value, policy, **kwargs)
    assert first["new_observations"] == 1 and first["model_compatible"] is False
    assert eod.import_candidate(root, source, value, policy, **kwargs)["new_observations"] == 0
    assert len(eod.load(root)) == 1
    raw = root / "raw" / (value["raw_sha256"] + ".bin")
    raw.write_bytes(b"CORRUPT_TEST_ONLY")
    with pytest.raises(ValueError, match="SOURCE_CHECKSUM"):
        eod.load(root)


def test_rehashed_false_normalization_and_scope_expansion_rejected(tmp_path: Path) -> None:
    source, value = candidate(tmp_path)
    value["rows"][0]["close"] = "999"
    value["candidate_id"] = digest(encoded({k: v for k, v in value.items() if k != "candidate_id"}))
    root = tmp_path / "TEST_ONLY_source_store"
    policy = approval(tmp_path, root, value)
    with pytest.raises(ValueError, match="NORMALIZED_SOURCE_MISMATCH"):
        eod.import_candidate(
            root, source, value, policy, approved_candidate=value["candidate_id"], at=AT
        )
    assert not root.exists()


def test_different_source_for_same_slot_is_explicit_conflict(tmp_path: Path) -> None:
    source, value = candidate(tmp_path)
    root = tmp_path / "TEST_ONLY_source_store"
    policy = approval(tmp_path, root, value)
    eod.import_candidate(
        root, source, value, policy, approved_candidate=value["candidate_id"], at=AT
    )
    # Same source bytes with a changed receipt is a new version needing review;
    # the existing source slot cannot be silently overwritten by another import.
    revised = json.loads(json.dumps(value))
    revised["rows"][0]["received_at"] = "2025-01-03T15:00:00+00:00"
    revised["candidate_id"] = digest(
        encoded({k: v for k, v in revised.items() if k != "candidate_id"})
    )
    policy["candidate_id"] = revised["candidate_id"]
    with pytest.raises(ValueError, match="SLOT_CONFLICT"):
        eod.import_candidate(
            root, source, revised, policy, approved_candidate=revised["candidate_id"], at=AT
        )
    assert eod.load(root) == value["rows"]


@pytest.mark.parametrize("child", ["raw", "imports", "control"])
def test_store_child_junctions_are_rejected_before_any_write(tmp_path: Path, child: str) -> None:
    source, value = candidate(tmp_path)
    root = tmp_path / "TEST_ONLY_store"
    initialize(root)
    outside = tmp_path / "TEST_ONLY_outside"
    outside.mkdir()
    link = root / child
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="REPARSE_PATH"):
            eod.import_candidate(
                root,
                source,
                value,
                approval(tmp_path, root, value),
                approved_candidate=value["candidate_id"],
                at=AT,
            )
        assert list(outside.iterdir()) == []
    finally:
        if sys.platform == "win32":
            link.rmdir()
        else:
            link.unlink()


def test_interrupted_raw_write_is_not_a_published_source_and_can_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, value = candidate(tmp_path)
    root = tmp_path / "TEST_ONLY_store"
    policy = approval(tmp_path, root, value)
    original = write_new

    def interrupted(path: Path, body: bytes) -> None:
        if path.parent.name == "raw":
            path.write_bytes(body[:2])
            raise OSError("TEST_ONLY interrupted disk write")
        original(path, body)

    with monkeypatch.context() as patch:
        patch.setattr(eod, "write_new", interrupted)
        with pytest.raises(OSError):
            eod.import_candidate(
                root, source, value, policy, approved_candidate=value["candidate_id"], at=AT
            )
    assert not list((root / "raw").glob("*.bin"))
    assert eod.load(root) == []
    assert (
        eod.import_candidate(
            root, source, value, policy, approved_candidate=value["candidate_id"], at=AT
        )["new_observations"]
        == 1
    )


def test_interrupted_receipt_publication_completes_orphan_sidecar_on_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, value = candidate(tmp_path)
    root = tmp_path / "TEST_ONLY_store"
    policy = approval(tmp_path, root, value)
    original = eod._publish

    def interrupted(path: Path, body: bytes) -> None:
        if path.suffix == ".json":
            raise OSError("TEST_ONLY interrupted receipt publication")
        original(path, body)

    with monkeypatch.context() as patch:
        patch.setattr(eod, "_publish", interrupted)
        with pytest.raises(OSError):
            eod.import_candidate(
                root, source, value, policy, approved_candidate=value["candidate_id"], at=AT
            )
    assert eod.load(root) == []
    eod.import_candidate(
        root,
        source,
        value,
        policy,
        approved_candidate=value["candidate_id"],
        at=AT + timedelta(seconds=1),
    )
    assert len(eod.load(root)) == 1


def test_rehashed_source_identity_cannot_escape_raw_namespace(tmp_path: Path) -> None:
    source, value = candidate(tmp_path)
    value["raw_sha256"] = "../../TEST_ONLY_outside"
    value["candidate_id"] = digest(encoded({k: v for k, v in value.items() if k != "candidate_id"}))
    root = tmp_path / "TEST_ONLY_store"
    with pytest.raises(ValueError, match="SOURCE_ID_REJECTED"):
        eod.import_candidate(
            root,
            source,
            value,
            approval(tmp_path, root, value),
            approved_candidate=value["candidate_id"],
            at=AT,
        )
    assert not root.exists()


def test_future_master_evidence_cannot_qualify_an_import(tmp_path: Path) -> None:
    source, provenance, master, calendar = fixture(tmp_path)
    master = replace(master, observed_at=AT + timedelta(seconds=1))
    with pytest.raises(ValueError, match="MASTER_AFTER_REVIEW"):
        eod.review(source, provenance, master, calendar, at=AT)
