"""TEST_ONLY files exercise deployment guards; no tasks, providers or listeners."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.verify_dated_private_deployment import relative, validate, verify


def manifest() -> dict[str, Any]:
    return json.loads(Path("infra/release/alphalens-private-2026-10-28.json").read_bytes())  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    "key,changed",
    [
        ("backend_host", "0.0.0.0"),
        ("database_host", "TEST_ONLY_REMOTE"),
        ("public_ingress_enabled", True),
        ("public_market_data_authorized", True),
        ("trading_enabled", True),
        ("backend_port", True),
        ("reserved_gets_per_day", 2400),
        ("configured_securities", 3194),
        ("model_status", "ACCEPTED"),
        ("collector_task", "AlphaLens-Private-EOD-Watchlist"),
    ],
)
def test_unapproved_deployment_policy_rejected(key: str, changed: Any) -> None:
    value = manifest()
    value[key] = changed
    with pytest.raises(ValueError, match="POLICY_MISMATCH"):
        validate(value)


@pytest.mark.parametrize(
    "path", ["", "../outside", "a/../../outside", "C:/private", "a\\b", "/outside"]
)
def test_unsafe_relative_paths_rejected(path: str) -> None:
    with pytest.raises(ValueError, match="RELATIVE_PATH_REQUIRED"):
        relative(path)


def configured(tmp_path: Path) -> dict[str, Any]:
    value = manifest()
    for key in (
        "backend_python",
        "collector_python",
        "collector_config",
        "rollback_backend_config",
    ):
        path = tmp_path / value[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("TEST_ONLY", encoding="utf-8")
    frontend = tmp_path / value["frontend_root"]
    entry = frontend / value["frontend_entry"]
    entry.parent.mkdir(parents=True)
    entry.write_text("// TEST_ONLY", encoding="utf-8")
    index = '<script src="/' + value["frontend_entry"] + '"></script>'
    (frontend / "index.html").write_text(index, encoding="utf-8")
    value["frontend_index_sha256"] = hashlib.sha256(index.encode()).hexdigest()
    config = {
        "port": 8041,
        "upstox_private_view": False,
        "cors_origins": ["http://127.0.0.1:8041"],
        "frontend_root": str(frontend),
    }
    raw = json.dumps(config).encode()
    (tmp_path / value["backend_config"]).write_bytes(raw)
    value["backend_config_sha256"] = hashlib.sha256(raw).hexdigest()
    return value


def test_offline_valid_wiring_never_claims_live_deployment(tmp_path: Path) -> None:
    result = verify(tmp_path, configured(tmp_path))
    assert result["scope"] == "OFFLINE_DEPLOYMENT_WIRING_ONLY"
    assert result["tasks_modified"] is False
    assert result["provider_requests"] == 0
    assert result["live_candle_delivery_verified"] is False


@pytest.mark.parametrize(
    "file_key,error",
    [("backend_config", "CONFIG_HASH_MISMATCH"), ("frontend_root", "FRONTEND_INDEX_HASH_MISMATCH")],
)
def test_changed_deployed_files_rejected(tmp_path: Path, file_key: str, error: str) -> None:
    value = configured(tmp_path)
    path = tmp_path / value[file_key]
    if path.is_dir():
        path /= "index.html"
    path.write_text("TEST_ONLY_TAMPERED", encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        verify(tmp_path, value)


@pytest.mark.parametrize(
    "key,changed",
    [
        ("upstox_private_view", True),
        ("cors_origins", ["https://TEST_ONLY_PUBLIC"]),
        ("database_url", "TEST_ONLY_NOT_A_SECRET"),
    ],
)
def test_config_boundary_rejected_even_with_matching_hash(
    tmp_path: Path, key: str, changed: Any
) -> None:
    value = configured(tmp_path)
    path = tmp_path / value["backend_config"]
    config = json.loads(path.read_bytes())
    config[key] = changed
    path.write_bytes(json.dumps(config).encode())
    value["backend_config_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="PRIVATE_CONFIG_BOUNDARY_MISMATCH"):
        verify(tmp_path, value)


def test_disabled_or_numeric_battery_flags_not_misreported() -> None:
    value = manifest()
    value["collector_battery_policy"]["StopIfGoingOnBatteries"] = 0
    with pytest.raises(ValueError, match="REVIEWED_BATTERY_FLAGS_REQUIRED"):
        validate(value)
