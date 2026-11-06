"""Resumable official PostgreSQL17 binary ranges; extract only required owned files.

Partial archive reconstruction verifies selected ZIP member CRCs, not a checksum
of the full vendor archive. No server/credential actions occur in this downloader.
"""

import concurrent.futures
import hashlib
import json
import struct
import subprocess
import zipfile
from pathlib import Path

from alphalens_api.auth.permissions import restrict, verify

ROOT = Path(__file__).resolve().parents[1] / ".local-data/p30-postgres"
URL = "https://get.enterprisedb.com/postgresql/postgresql-17.11-5-windows-x64-binaries.zip"
SIZE = 381531864
CENTRAL = 378926842


def fetch(start: int, end: int, output: Path) -> None:
    expected = end - start + 1
    present = output.stat().st_size if output.exists() else 0
    if present == expected:
        return
    if present > expected:
        raise ValueError("VENDOR_RANGE_SIZE_REJECTED")
    begin = start + present
    piece = output.with_suffix(".part")
    headers = output.with_suffix(".headers")
    result = subprocess.run(
        [
            "curl.exe",
            "--silent",
            "--show-error",
            "--fail",
            "--range",
            f"{begin}-{end}",
            "--max-time",
            "240",
            "--dump-header",
            str(headers),
            "--output",
            str(piece),
            URL,
        ],
        capture_output=True,
        timeout=250,
        check=False,
    )
    header = headers.read_text().lower()
    marker = f"content-range: bytes {begin}-{end}/{SIZE}"
    if marker not in header or not piece.exists() or piece.stat().st_size > end - begin + 1:
        raise ValueError("OFFICIAL_VENDOR_RANGE_REJECTED")
    with output.open("ab") as stream:
        stream.write(piece.read_bytes())
    piece.unlink()
    if result.returncode or output.stat().st_size != expected:
        raise ValueError("BOUNDED_VENDOR_DOWNLOAD_INCOMPLETE_RESUME_SUPPORTED")


def main() -> None:
    if not ROOT.exists():
        ROOT.mkdir(parents=True)
        restrict(ROOT)
    verify(ROOT)
    if (ROOT / "cluster").exists():
        raise ValueError("EXISTING_CLUSTER_PRESERVED")
    directory = ROOT / "zip-directory.bin"
    fetch(CENTRAL, SIZE - 1, directory)
    data = directory.read_bytes()
    position = 0
    intervals: list[list[int]] = []
    while data[position : position + 4] == b"PK\x01\x02":
        values = struct.unpack_from("<4s6H3L5H2L", data, position)
        name = data[position + 46 : position + 46 + values[10]].decode()
        if name.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
            start = values[16]
            end = start + 30 + len(name.encode()) + 65535 + values[8]
            if intervals and start - intervals[-1][1] < 131072 and end - intervals[-1][0] < 5000000:
                intervals[-1][1] = max(end, intervals[-1][1])
            else:
                intervals.append([start, end])
        position += 46 + values[10] + values[11] + values[12]
    jobs = [(a, b, ROOT / f"vendor-range-{n}.bin") for n, (a, b) in enumerate(intervals)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda args: fetch(*args), jobs))
    package = ROOT / "postgresql17-selected.zip"
    with package.open("wb") as output:
        output.truncate(SIZE)
        output.seek(CENTRAL)
        output.write(data)
        for start, _, path in jobs:
            output.seek(start)
            output.write(path.read_bytes())
    manifest = []
    with zipfile.ZipFile(package) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                continue
            destination = (ROOT / entry.filename).resolve()
            if not destination.is_relative_to(ROOT.resolve()):
                raise ValueError("VENDOR_ARCHIVE_PATH_REJECTED")
            archive.extract(entry, ROOT)  # ZIP reader checks CRC for each selected member.
            if destination.is_file():
                manifest.append(
                    {
                        "file": entry.filename,
                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    }
                )
    receipt = {
        "source": URL,
        "version": "17.11-5",
        "files": manifest,
        "integrity": "OFFICIAL_TLS_DOWNLOAD_SELECTED_MEMBER_ZIP_CRC_AND_LOCAL_SHA256",
        "complete_vendor_archive_sha256": None,
    }
    (ROOT / "binary-manifest.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps({"state": "OFFICIAL_SELECTED_BINARIES_VERIFIED", "files": len(manifest)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"state": "BINARY_DOWNLOAD_BLOCKED", "category": type(exc).__name__}))
        raise SystemExit(1) from None
