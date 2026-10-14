"""Additive P30 private operator configuration; existing account/stores/config preserved."""

import json
from pathlib import Path

from alphalens_api.auth.permissions import restrict


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    root = repo / ".local-data/p30-runtime"
    root.mkdir(parents=True, exist_ok=False)
    restrict(root)
    source = Path("D:/al-research/p29-runtime/operator-config.json")
    config = json.loads(source.read_bytes())
    if "database_url" in config:
        raise ValueError("SECRET_CONFIG_REJECTED")
    config.update(
        {
            "frontend_root": str(repo / ".local-data/p30-web-build"),
            "upstox_validation_root": str(repo / ".local-data/p30-upstox-validation"),
            "upstox_private_view": True,
        }
    )
    (root / "operator-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("P30_ADDITIVE_OPERATOR_CONFIG_CREATED_EXISTING_ACCOUNT_PRESERVED")


if __name__ == "__main__":
    main()
