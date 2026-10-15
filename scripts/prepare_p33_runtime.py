"""Preserve existing personal/authentication roots; select only the new compiled UI."""

import json
from pathlib import Path

from alphalens_api.auth.permissions import restrict


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    for label in ("runtime", "browser-runtime"):
        root = repo / f".local-data/p33-{label}"
        root.mkdir(exist_ok=False)
        restrict(root)
        settings = json.loads((repo / f".local-data/p32-{label}/operator-config.json").read_bytes())
        settings["frontend_root"] = str(repo / ".local-data/p33-web-build")
        (root / "operator-config.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("P33_COMPILED_FRONTEND_CONFIGURED_EXISTING_PERSONAL_AUTH_AND_DATABASE_ROOTS_PRESERVED")


if __name__ == "__main__":
    main()
