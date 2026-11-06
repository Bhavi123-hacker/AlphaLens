"""Additive authorized personal workspace; original operator and databases unchanged."""

import json
from pathlib import Path

from workers.personal.store import PersonalStore

from alphalens_api.auth.permissions import restrict
from alphalens_api.auth.store import AuthStore


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    for label, original in (("runtime", "runtime"), ("browser-runtime", "browser-runtime")):
        root = repo / f".local-data/p32-{label}"
        root.mkdir(exist_ok=False)
        restrict(root)
        config = json.loads(
            (repo / f".local-data/p31-{original}/operator-config.json").read_bytes()
        )
        if "database_url" in config:
            raise ValueError("SECRET_CONFIG_REJECTED")
        config.update(
            frontend_root=str(repo / ".local-data/p32-web-build"),
            personal_root=str(root / "personal"),
            personal_mutations=True,
        )
        account = AuthStore(Path(config["auth_root"])).diagnostics()["account"]
        if not account or account["role"] != "ADMIN" or account["status"] != "ACTIVE":
            raise ValueError("EXISTING_AUTHORIZED_SINGLE_OPERATOR_REQUIRED")
        PersonalStore(Path(config["personal_root"]), account["account_id"]).initialize()
        (root / "operator-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("P32_OWNED_ADDITIVE_WORKSPACES_READY_NO_ORIGINAL_DATABASE_OR_CREDENTIAL_MUTATION")


if __name__ == "__main__":
    main()
