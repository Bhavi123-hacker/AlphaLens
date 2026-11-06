"""Actual credential isolation and SELECT-only database reads; sanitized output only."""

import base64
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import httpx
from psycopg import connect, sql

from alphalens_api.credentials import credential_module
from alphalens_api.local.postgres import READER, reader_url


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    module = credential_module()
    needles = set()
    for target in (
        "AlphaLens/UpstoxReadOnlyAnalytics",
        "AlphaLens/AlphaVantage",
        "AlphaLens/PostgreSQL/P30LocalAdmin",
        "AlphaLens/PostgreSQL/ResearchReadOnly",
    ):
        blob = module.CredRead(target, module.CRED_TYPE_GENERIC)["CredentialBlob"]
        value = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        if not value:
            raise ValueError("PROTECTED_CREDENTIAL_REQUIRED")
        needles.update(
            (
                value.encode(),
                value.encode("utf-16-le"),
                base64.b64encode(value.encode()),
                quote(value, safe="").encode(),
            )
        )
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    paths = {repo / p.decode("utf-8") for p in result.stdout.split(b"\0") if p}
    for directory in (repo / ".local-data/p33-web-build", repo / ".local-data/p33-public-demo"):
        paths.update(p for p in directory.rglob("*") if p.is_file())
    scanned = 0
    for path in paths:
        if not path.is_file():
            continue
        if path.stat().st_size > 50_000_000 or any(n in path.read_bytes() for n in needles):
            raise ValueError("CREDENTIAL_ISOLATION_REJECTED")
        scanned += 1
    # Real compiled socket and isolated test identity. No actual operator reset.
    credentials = json.loads(
        (repo / ".local-data/p31-browser-runtime/credentials.json").read_bytes()
    )
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=40) as client:
        reply = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        if reply.status_code != 200:
            raise ValueError("ISOLATED_SECURITY_LOGIN_REQUIRED")
        session = reply.json()
        reply = client.get("/api/v1/providers/upstox-private/instruments?q=BAJFINANCE")
        if reply.status_code != 200 or any(n in reply.content for n in needles):
            raise ValueError("CURRENT_MASTER_SECRET_ISOLATION_REJECTED")
        values = [i for i in reply.json()["data"]["instruments"] if i["symbol"] == "BAJFINANCE"]
        if len(values) != 1:
            raise ValueError("VERIFIED_IDENTITY_REQUIRED")
        reply = client.get("/api/v1/personal/workspace")
        if reply.status_code != 200 or any(n in reply.content for n in needles):
            raise ValueError("PRIVATE_RESPONSE_SECRET_ISOLATION_REJECTED")
        reply = client.get(
            "/api/v1/providers/upstox-private/instruments",
            headers={"Origin": "https://foreign.invalid"},
        )
        if reply.status_code != 403:
            raise ValueError("FOREIGN_ORIGIN_REQUIRED_REJECTED")
        client.post(
            "/api/v1/auth/logout",
            json={},
            headers={"Origin": "http://127.0.0.1:8029", "X-CSRF-Token": session["csrf_token"]},
        )
    with connect(reader_url(), connect_timeout=3) as reader:
        if reader.execute("SHOW transaction_read_only").fetchone() != ("on",):
            raise ValueError("READ_ONLY_DATABASE_REQUIRED")
        counts = {
            name: reader.execute(
                sql.SQL("SELECT COUNT(*) FROM portfolio.{}").format(sql.Identifier(name))
            ).fetchone()[0]
            for name in ("accounts", "transactions", "paper_accounts", "paper_events")
        }
        privileges = [
            reader.execute(
                "SELECT has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE')",
                (READER, "portfolio." + name),
            ).fetchone()[0]
            for name in counts
        ]
        if any(counts.values()) or any(privileges):
            raise ValueError("FINANCIAL_DATABASE_PRESERVATION_REQUIRED")
    receipt = {
        "state": "PASSED",
        "source_and_build_files": scanned,
        "actual_credential_values_and_encodings_found": False,
        "frontend_and_provider_response_secret_isolation": "PASSED",
        "foreign_origin_rejected": True,
        "database": {"financial_counts": counts, "read_only": True, "write_privileges": False},
        "credentials_printed": False,
    }
    (repo / ".local-data/p33-security.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z_]{5,100}", str(exc))
            else "DETAILS_REDACTED"
        )
        print(
            json.dumps(
                {
                    "state": "P33_SECURITY_NOT_VERIFIED",
                    "credential_output": False,
                    "category": type(exc).__name__,
                    "reason": reason,
                }
            )
        )
        raise SystemExit(1) from None
