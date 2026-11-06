"""Explicit TEST_ONLY demo stays isolated, private, unapproved for market acquisition."""

import json
import secrets
from pathlib import Path

import pytest
from scripts.prepare_provider_demo import prepare

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured


def test_demo_does_not_reuse_normal_root_or_create_default_credentials(tmp_path: Path) -> None:
    frontend = tmp_path / "web"
    frontend.mkdir()
    (frontend / "index.html").write_text("TEST_ONLY")
    with pytest.raises(ValueError, match="ISOLATED"):
        prepare(tmp_path / "normal_data", frontend, "test_operator", secrets.token_urlsafe(40))
    root = tmp_path / "TEST_ONLY_demo"
    config = prepare(root, frontend, "test_operator", secrets.token_urlsafe(40))
    settings = configured(config)
    assert settings.environment == "test" and settings.test_only_evidence
    assert AuthStore(root / "auth").diagnostics()["account"]["username"] == "test_operator"
    assert "database_url" not in json.loads(config.read_bytes())
    assert settings.cors_origins == ("http://127.0.0.1:8029",)
    with pytest.raises(ValueError, match="ISOLATED"):
        prepare(root, frontend, "test_operator", secrets.token_urlsafe(40))
