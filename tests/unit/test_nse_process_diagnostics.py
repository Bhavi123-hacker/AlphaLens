"""TEST_ONLY process facts; simulated exits, no collecting process or provider."""

import json
import os
import runpy
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from test_nse_scheduled_preflight import prior, run, setup
from workers.experimental_nse.acquire import initialize
from workers.nse_market import diagnostics, engine, launcher, operational

from alphalens_api.auth.permissions import restrict


@pytest.mark.parametrize("ending", ["normal", "failed", "interrupt", "exception"])
def test_in_process_launcher_records_only_safe_facts_and_preserves_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ending: str
) -> None:
    root = tmp_path / "TEST_ONLY_private"
    initialize(root)
    cfg = tmp_path / "TEST_ONLY_config.json"
    cfg.write_text(json.dumps({"root": str(root)}))
    restrict(cfg)
    monkeypatch.setattr(sys, "argv", ["TEST_ONLY_launcher", "--config", str(cfg)])
    before = sys.argv
    monkeypatch.delenv("ALPHALENS_NSE_LAUNCH_ID", raising=False)

    def fake_worker(module: str, **kwargs: Any) -> None:
        assert module == "workers.nse_market"
        assert "--scheduled" in sys.argv and "--collect" not in sys.argv
        assert os.environ["ALPHALENS_NSE_LAUNCH_ID"]
        if ending == "failed":
            raise SystemExit(1)
        if ending == "interrupt":
            raise KeyboardInterrupt
        if ending == "exception":
            raise RuntimeError("TEST_ONLY_SECRET_MUST_NOT_BE_RECORDED")

    monkeypatch.setattr(runpy, "run_module", fake_worker)
    if ending == "normal":
        launcher.main()
    else:
        expected = {
            "failed": SystemExit,
            "interrupt": KeyboardInterrupt,
            "exception": RuntimeError,
        }[ending]
        with pytest.raises(expected):
            launcher.main()
    facts = [engine._read(p) for p in (root / "operational/diagnostics").glob("*.json")]
    assert len(facts) == 2
    assert "LAUNCHER_STARTED" in {f["event"] for f in facts}
    assert len({f["launch_id"] for f in facts}) == 1
    assert all(f["termination_initiator"] is None for f in facts)
    assert all("TEST_ONLY_SECRET" not in json.dumps(f) for f in facts)
    assert sys.argv is before and "ALPHALENS_NSE_LAUNCH_ID" not in os.environ
    if ending == "failed":
        assert next(f for f in facts if f["event"] == "LAUNCHER_EXIT")["exit_code"] == 1


def test_keyboard_interrupt_preserves_crash_reservation_and_records_incomplete_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, clock, meters = setup(tmp_path, monkeypatch)
    prior(cfg, clock.now - timedelta(hours=2))

    def interrupted(*args: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(operational, "_refresh_identities", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(cfg, scheduled=True)
    starts = list((cfg.root / "operational/runs").glob("*.started.json"))
    assert len(starts) == 2 and len(meters) == 1
    assert len(list((cfg.root / "operational/runs").glob("*.interrupted.json"))) == 1
    assert not list((cfg.root / "operational/runs").glob("*.done.json"))
    assert engine._pointed(cfg.root, "operational-latest.json")["state"] == "INTERRUPTED"


def test_diagnostic_rejects_sensitive_free_form(
    tmp_path: Path,
) -> None:
    root = tmp_path / "TEST_ONLY_private"
    initialize(root)
    with pytest.raises(ValueError, match="METADATA_REJECTED"):
        diagnostics.emit(root, "a" * 32, "STAGE", code="https://TEST_ONLY/token=secret")
    assert not (root / "operational").exists()


def test_missing_exit_is_not_fabricated_as_completed(tmp_path: Path) -> None:
    root = tmp_path / "TEST_ONLY_private"
    initialize(root)
    diagnostics.emit(root, "a" * 32, "LAUNCHER_STARTED")
    facts = [engine._read(p) for p in (root / "operational/diagnostics").glob("*.json")]
    assert len(facts) == 1 and facts[0]["exit_code"] is None
