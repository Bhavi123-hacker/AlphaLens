"""Scan actual protected credential values without printing values or fingerprints."""

import base64
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

from alphalens_api.credentials import credential_module


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
            raise ValueError
        for encoded in (
            value.encode(),
            value.encode("utf-16-le"),
            base64.b64encode(value.encode()),
            quote(value, safe="").encode(),
        ):
            needles.add(encoded)
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    paths = {repo / p.decode("utf-8") for p in result.stdout.split(b"\0") if p}
    for directory in (repo / ".local-data/p30-web-build", repo / ".local-data/p30-public-demo"):
        paths.update(p for p in directory.rglob("*") if p.is_file())
    scanned, found = 0, False
    for path in paths:
        if not path.is_file():
            continue
        if path.stat().st_size > 50_000_000:
            raise ValueError
        data = path.read_bytes()
        found |= any(needle in data for needle in needles)
        scanned += 1
    receipt = {
        "state": "FAILED" if found else "PASSED",
        "files_scanned": scanned,
        "actual_values_or_encodings_found": found,
        "credential_material_printed": False,
        "scope": "CURRENT_SOURCE_AND_BOTH_BUILDS",
    }
    print(json.dumps(receipt))
    (repo / ".local-data/p30-runtime/secret-isolation.json").write_text(json.dumps(receipt))
    if found:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps({"state": "SECRET_SCAN_NOT_VERIFIED", "credential_material_printed": False})
        )
        raise SystemExit(1) from None
