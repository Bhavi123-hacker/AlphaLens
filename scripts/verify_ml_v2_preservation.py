"""Read-only V2 preservation receipt; original artifacts and V1 are never rewritten."""

import ast
import io
import json
import subprocess
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.verify_experimental_preservation import check as original_check
from workers.experimental_nse.acquire import digest
from workers.experimental_nse.workspace import read_workspace

BASELINE = "30283d7dd9158d4507aeb7b99c8290b1d7092eda"
V1_RECEIPT_SHA256 = "e925be63c635c28487b3a65654a12a5ac30ca30191f7d99707e78aebc18c5f8f"
V1_MODEL_SHA256 = "6f8451655926e1107f6f691bc5e1908d8248ef56441234867fdb9e85fd9709d8"
V1_EVALUATION_SHA256 = "83ee458f29f0bb90c136ca7fbbe45cdb2f6fd4cd37e5f17df4b3b59b9ae8407e"


class RemoveOnlyCurrentDayAddition(ast.NodeTransformer):
    """Normalize exactly the separately authorized read-only endpoint addition."""

    def visit_If(self, node: ast.If) -> ast.AST | list[ast.stmt]:
        self.generic_visit(node)
        if ast.dump(node.test) == ast.dump(
            ast.parse('operation == "intraday_candles"', mode="eval").body
        ):
            expected = ast.parse(
                'if operation == "intraday_candles":\n'
                "    if start is not None or end is not None or keys is not None:\n"
                '        raise DataContractError("CURRENT_DAY_SINGLE_INSTRUMENT_SCOPE_REQUIRED")\n'
                "    path = f\"/v3/historical-candle/intraday/{quote(key, safe='')}/days/1\"\n"
            ).body[0]
            if not isinstance(expected, ast.If) or ast.dump(
                ast.Module(body=node.body, type_ignores=[])
            ) != ast.dump(ast.Module(body=expected.body, type_ignores=[])):
                raise ValueError("CURRENT_DAY_TRANSPORT_ADDITION_NOT_EXACT")
            return node.orelse
        return node

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        self.generic_visit(node)
        if (
            any(
                isinstance(target, ast.Name) and target.id == "Operation" for target in node.targets
            )
            and isinstance(node.value, ast.Subscript)
            and isinstance(node.value.slice, ast.Tuple)
        ):
            node.value.slice.elts = [
                value
                for value in node.value.slice.elts
                if not isinstance(value, ast.Constant) or value.value != "intraday_candles"
            ]
        return node


def transport_preserved(repo: Path) -> bool:
    name = "workers/providers/upstox.py"
    before = subprocess.check_output(["git", "show", BASELINE + ":" + name], cwd=repo)
    actual = ast.parse((repo / name).read_bytes())
    normalized = RemoveOnlyCurrentDayAddition().visit(actual)
    if ast.dump(normalized) != ast.dump(ast.parse(before)):
        raise ValueError("ORIGINAL_UPSTOX_TRANSPORT_CHANGED_BEYOND_ADDITIVE_ENDPOINT")
    return True


def check() -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    archived = subprocess.check_output(
        [
            "git",
            "archive",
            BASELINE,
            "workers/experimental_nse",
            "db/experimental-nse.sql",
            "docs/development/experimental-nse-v1-predeclared-study.md",
            "docs/development/experimental-nse-numerical-audit.json",
        ],
        cwd=repo,
    )
    original_v1_files = 0
    with tarfile.open(fileobj=io.BytesIO(archived), mode="r:") as files:
        for entry in files:
            if not entry.isfile():
                continue
            stream = files.extractfile(entry)
            if stream is None:
                raise ValueError("ORIGINAL_V1_SOURCE_MISSING")
            with stream:
                expected = stream.read()
            actual = (repo / entry.name).read_bytes()
            if actual != expected and actual.replace(b"\r\n", b"\n") != expected:
                raise ValueError("ORIGINAL_V1_SOURCE_CONTENT_CHANGED")
            original_v1_files += 1
    v1 = repo / ".local-data/experimental-nse-v1"
    pointer = json.loads((v1 / "latest.json").read_bytes())
    run = v1 / "runs" / pointer["run_id"]
    if (
        pointer["receipt_sha256"] != V1_RECEIPT_SHA256
        or digest((run / "receipt.json").read_bytes()) != V1_RECEIPT_SHA256
        or digest((run / "model.json").read_bytes()) != V1_MODEL_SHA256
        or digest((run / "evaluation.json").read_bytes()) != V1_EVALUATION_SHA256
    ):
        raise ValueError("ORIGINAL_V1_MODEL_OR_EVALUATION_BYTES_CHANGED")
    workspace = read_workspace(v1)
    base_copy = repo / ".local-data/experimental-nse-v2/base-v1"
    copied = 0
    for source in (v1 / "snapshot-v1").iterdir():
        if source.is_file():
            if not (base_copy / source.name).is_file() or digest(source.read_bytes()) != digest(
                (base_copy / source.name).read_bytes()
            ):
                raise ValueError("ORIGINAL_V1_SNAPSHOT_COPY_CHANGED")
            copied += 1
    return {
        "state": "PASSED",
        "verified_at": datetime.now(UTC).isoformat(),
        "baseline": BASELINE,
        "original_v1_tracked_files_git_content_unchanged": original_v1_files,
        "v1_model_and_evaluation_byte_exact": True,
        "v1_source_snapshot_copy_files_byte_exact": copied,
        "v1_verified_saved_scores": len(workspace["candidates"]),
        "v1_accepted_rankings": workspace["accepted_current_rankings"],
        "upstox_existing_ast_unchanged_except_exact_additive_current_day_get": transport_preserved(
            repo
        ),
        "original_frozen_account_alert_preservation": original_check(),
        "provider_requests": 0,
        "market_values_or_credentials_in_receipt": False,
    }


def main() -> None:
    result = check()
    folder = Path(__file__).resolve().parents[1] / ".local-data"
    output = folder / ("ml-v2-preservation-" + str(time.time_ns()) + ".json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"V2_PRESERVATION_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
