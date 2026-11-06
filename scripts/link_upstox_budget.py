"""Link idle same-account Upstox request ledgers without moving prices or credentials.

Stop the local web server and confirm no collecting worker is active first.
All historical attempts remain in their original stores; copies only append to
the shared quota ledger. There is no network or scheduling activation here.
"""

import argparse
import json
from contextlib import closing
from pathlib import Path

from workers.providers.store import ProviderStore

from alphalens_api.auth.permissions import verify


def link(source: Path, target: Path) -> dict[str, int | bool | str]:
    source, target = source.resolve(), target.resolve()
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("DISTINCT_EXISTING_PRIVATE_QUOTA_ROOTS_REQUIRED")
    verify(source)
    verify(target)
    pointer = source / "upstox-shared-quota.json"
    if pointer.exists() or (target / pointer.name).exists():
        raise ValueError("EXISTING_SHARED_QUOTA_LINK_REQUIRES_OPERATOR_REVIEW")
    first, shared = ProviderStore(source), ProviderStore(target)
    with closing(first.connection()) as src, closing(shared.connection()) as dst, src, dst:
        src.execute("BEGIN IMMEDIATE")
        dst.execute("BEGIN IMMEDIATE")
        if any(
            conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE provider='upstox' AND outcome='PENDING'"
            ).fetchone()[0]
            for conn in (src, dst)
        ):
            raise ValueError("UPSTOX_ATTEMPTS_MUST_BE_IDLE_BEFORE_LINKING")
        rows = src.execute("SELECT * FROM attempts WHERE provider='upstox'").fetchall()
        inserted = 0
        for row in rows:
            previous = dst.execute(
                "SELECT * FROM attempts WHERE provider=? AND request_id=? AND attempt=?", row[:3]
            ).fetchone()
            if previous is not None and tuple(previous) != tuple(row):
                raise ValueError("QUOTA_HISTORY_CONFLICT_NOT_OVERWRITTEN")
            if previous is None:
                dst.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?)", row)
                inserted += 1
        # Commit the copied history before publishing the protected single-hop link.
        dst.commit()
        with pointer.open("x", encoding="utf-8") as stream:
            json.dump({"version": "provider.shared_quota.v1", "root": str(target)}, stream)
        if __import__("os").name != "nt":
            pointer.chmod(0o600)
        verify(pointer, directory=False)
    return {
        "state": "SHARED_UPSTOX_QUOTA_LINKED",
        "original_attempts_preserved": len(rows),
        "copied_attempts": inserted,
        "provider_GETs": 0,
        "prices_or_credentials_moved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--confirm-idle", action="store_true", required=True)
    args = parser.parse_args()
    print(json.dumps(link(args.source, args.target)))


if __name__ == "__main__":
    main()
