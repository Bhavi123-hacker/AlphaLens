"""New owned portable PostgreSQL17 only; no service or unrelated cluster changes."""

import hashlib
import hmac
import json
import secrets
import subprocess
from pathlib import Path

from alphalens_api.auth.permissions import restrict
from alphalens_api.credentials import credential_module
from alphalens_api.local.postgres import bootstrap

ROOT = Path(__file__).resolve().parents[1] / ".local-data/p30-postgres"
URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260616"
ADMIN_TARGET = "AlphaLens/PostgreSQL/P30LocalAdmin"


def run(args: list[str]) -> None:
    # Windows grandchildren may retain inherited pipe handles after pg_ctl exits.
    # A private file avoids hanging capture_output without printing command output.
    with (ROOT / "command-status.private").open("wb") as output:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=90,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    if result.returncode:
        raise ValueError("OWNED_POSTGRES_COMMAND_REJECTED")


def main() -> None:
    if ROOT.exists() and (ROOT / "cluster").exists():
        raise ValueError("EXISTING_CLUSTER_PRESERVED")
    ROOT.mkdir(parents=True, exist_ok=True)
    restrict(ROOT)
    manifest_path = ROOT / "binary-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("VERIFIED_OFFICIAL_SELECTED_BINARIES_REQUIRED")
    manifest = json.loads(manifest_path.read_bytes())
    for item in manifest["files"]:
        path = (ROOT / item["file"]).resolve()
        if (
            not path.is_relative_to(ROOT.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("VENDOR_BINARY_CHANGED")
    sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    binaries = ROOT / "pgsql/bin"
    version = subprocess.run(
        [str(binaries / "postgres.exe"), "--version"], capture_output=True, check=True
    ).stdout.decode()
    if not version.startswith("postgres (PostgreSQL) 17."):
        raise ValueError("POSTGRES17_REQUIRED")
    module = credential_module()
    try:
        module.CredRead(ADMIN_TARGET, module.CRED_TYPE_GENERIC)
    except Exception as exc:
        if getattr(exc, "winerror", None) != 1168:
            raise ValueError("ADMIN_CREDENTIAL_STORE_UNAVAILABLE") from None
    else:
        raise ValueError("EXISTING_ADMIN_CREDENTIAL_PRESERVED")
    password = secrets.token_urlsafe(48)
    pwfile = ROOT / "init-password.private"
    pwfile.write_text(password, encoding="utf-8")
    cluster = ROOT / "cluster"
    try:
        run(
            [
                str(binaries / "initdb.exe"),
                "-D",
                str(cluster),
                "-U",
                "alphalens_p30_admin",
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
                "--pwfile=" + str(pwfile),
            ]
        )
    finally:
        pwfile.unlink(missing_ok=True)
    with (cluster / "postgresql.conf").open("a", encoding="utf-8") as output:
        output.write(
            "\nlisten_addresses='127.0.0.1'\nport=15430\nmax_connections=20\n"
            "shared_buffers='32MB'\nlog_statement='none'\n"
            "log_min_error_statement='panic'\npassword_encryption='scram-sha-256'\n"
        )
    module.CredWrite(
        {
            "Type": module.CRED_TYPE_GENERIC,
            "TargetName": ADMIN_TARGET,
            "CredentialBlob": password,
            "Persist": module.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": "AlphaLens owned P30 loopback PostgreSQL17 cluster administrator",
        },
        0,
    )
    blob = module.CredRead(ADMIN_TARGET, module.CRED_TYPE_GENERIC)["CredentialBlob"]
    readback = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
    if not hmac.compare_digest(password, readback):
        raise ValueError("ADMIN_READBACK_FAILED")
    run(
        [
            str(binaries / "pg_ctl.exe"),
            "start",
            "-w",
            "-D",
            str(cluster),
            "-l",
            str(ROOT / "postgres.log"),
        ]
    )
    result = bootstrap(15430, "alphalens_p30_admin", password)
    receipt = {
        **result,
        "binary_source": URL,
        "binary_manifest_sha256": sha,
        "binary_integrity": manifest["integrity"],
        "complete_vendor_archive_sha256": None,
        "server_version": version.strip(),
        "cluster_scope": "NEW_OWNED_P30_ONLY",
        "listen_address": "127.0.0.1",
        "port": 15430,
        "windows_service_installed": False,
    }
    (ROOT / "setup-receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "state": "PORTABLE_POSTGRES_SETUP_BLOCKED",
                    "error_category": type(exc).__name__,
                    "sensitive_output": False,
                }
            )
        )
        raise SystemExit(1) from None
