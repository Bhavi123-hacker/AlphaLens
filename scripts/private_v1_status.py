"""Read-only local release status and opt-in authenticated saved-data smoke test."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import stat
import subprocess
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from psycopg import connect
from workers.experimental_nse_v2 import forward
from workers.nse_market import engine, reliability
from workers.providers import credentials, universe

from alphalens_api.local.cli import configured

REPO = Path(__file__).resolve().parents[1]


def safe_path(path: Path) -> None:
    """Do not follow junction ancestors when validating release or saved-state paths."""
    for ancestor in (path.absolute(), *path.absolute().parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("LOCAL_RELEASE_REPARSE_PATH_REJECTED")


def fingerprint(source: Path) -> dict[str, Any]:
    """Fingerprint tracked and new nonignored source bytes, without private state."""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "apps",
            "workers",
            "scripts",
            "ml",
            "portfolio",
            "decision",
            "backtesting",
            "db",
            "pyproject.toml",
            "uv.lock",
        ],
        cwd=source,
        capture_output=True,
        check=True,
        timeout=15,
    )
    files = {}
    for relative in result.stdout.decode().split("\0"):
        if not relative:
            continue
        target = source / relative
        safe_path(target)
        if target.is_symlink() or target.is_junction() or not target.is_file():
            raise ValueError("RELEASE_SOURCE_FILE_REQUIRED")
        files[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    body = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source,
            capture_output=True,
            check=True,
            timeout=15,
        )
        .stdout.decode()
        .strip()
    )
    return {
        "commit": commit,
        "tracked_source_files": len(files),
        "actual_source_sha256": hashlib.sha256(body).hexdigest(),
    }


def _ledgers(roots: list[Path]) -> dict[str, Any]:
    records = outcomes = 0
    decisions: set[tuple[Any, ...]] = set()
    latest: str | None = None
    seen: set[Path] = set()
    for root in roots:
        paths = [root / "experimental-v2-prospective.sqlite3"]
        paths.append(root / "price-only/experimental-v2-prospective.sqlite3")
        paths.extend((root / "expanded-forecasts").glob("*/experimental-v2-prospective.sqlite3"))
        for path in paths:
            if not path.is_file():
                continue
            safe_path(path)
            if path.resolve() in seen:
                continue
            seen.add(path.resolve())
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                db.execute("PRAGMA query_only=ON")
                bodies = db.execute("SELECT body FROM experimental_forecasts").fetchall()
                outcomes += db.execute("SELECT COUNT(*) FROM experimental_outcomes").fetchone()[0]
            for (body,) in bodies:
                row = json.loads(body)
                decisions.add(
                    (
                        row["model_id"],
                        row["key"],
                        row["session"],
                        row["target_version"],
                        row.get("horizon", row.get("horizon_observed_sessions")),
                    )
                )
                latest = max(latest or row["session"], row["session"])
            records += len(bodies)
    return {
        "forecast_records": records,
        "unique_decisions": len(decisions),
        "outcome_revisions": outcomes,
        "latest_forecast_observation_session": latest,
        "forward_accuracy": "UNAVAILABLE_UNTIL_QUALIFIED_OUTCOME_RECONCILIATION",
    }


def report(config: Path, *, workspace: Path) -> dict[str, Any]:
    safe_path(config)
    settings = configured(config)
    at = datetime.now(UTC)
    result: dict[str, Any] = {
        "schema": "alphalens.private_v1.status.v1",
        "observed_at": at.isoformat(),
        "url": f"http://127.0.0.1:{settings.port}/nse-market",
        "source": fingerprint(REPO),
        "provider_requests": 0,
        "mutations": 0,
        "disk": {},
        "errors": [],
    }
    for volume in sorted({workspace.anchor, config.absolute().anchor, REPO.anchor, "C:\\"}):
        usage = shutil.disk_usage(volume)
        result["disk"][volume] = {"total_bytes": usage.total, "free_bytes": usage.free}
    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            reply = client.get(f"http://127.0.0.1:{settings.port}/api/v1/health/live")
        result["api"] = {"responding": reply.status_code == 200, "http_status": reply.status_code}
    except httpx.HTTPError:
        result["api"] = {"responding": False}
    if settings.operations_root is not None:
        instance = settings.operations_root / "local/instance.json"
        try:
            safe_path(instance)
            if instance.is_file() and instance.stat().st_size <= 8192:
                state = json.loads(instance.read_bytes())
                result["api"]["recorded_instance"] = {
                    key: state.get(key) for key in ("pid", "port", "state", "started_at")
                }
                result["api"]["recorded_instance_scope"] = (
                    "SAVED_OWNERSHIP_RECORD_NOT_OS_PID_VERIFICATION"
                )
        except (ValueError, OSError):
            result["api"]["recorded_instance"] = "UNAVAILABLE"
    if settings.frontend_root:
        index = settings.frontend_root / "index.html"
        result["frontend"] = {
            "exists": index.is_file(),
            "index_sha256": hashlib.sha256(index.read_bytes()).hexdigest()
            if index.is_file()
            else None,
        }
    try:
        if settings.database_url is None:
            result["database"] = {"state": "UNCONFIGURED"}
        else:
            with connect(settings.database_url.get_secret_value(), connect_timeout=5) as db:
                db.execute("SET TRANSACTION READ ONLY")
                version = db.info.server_version
                tables = db.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
                ).fetchone()
            result["database"] = {
                "state": "READ_ONLY_QUERY_PASSED",
                "server_version": version,
                "public_tables": tables[0] if tables else None,
            }
    except Exception as exc:
        result["database"] = {"state": "UNAVAILABLE", "error_type": type(exc).__name__}
    try:
        token = credentials.load_token()
        result["provider_token"] = {
            "locally_available": bool(token),
            "server_validity": "NOT_PROBED",
        }
        del token
    except Exception:
        result["provider_token"] = {"locally_available": False, "server_validity": "NOT_PROBED"}
    v2 = settings.experimental_nse_v2_root
    if v2 is not None:
        root, master_root = v2.parent / "nse-market-expansion", v2.parent / "nse-universe"
        sections: dict[str, Callable[[], dict[str, Any]]] = {
            "saved_market": lambda: _market(root),
            "equities": lambda: _equities(master_root),
            "forecasts": lambda: _ledgers([v2, root]),
            "quota": lambda: reliability._request_counts(settings.providers_root),
            "scheduler": lambda: _scheduler(root, at),
            "collection": lambda: _collection(root),
        }
        for name, function in sections.items():
            try:
                result[name] = function()
            except Exception as exc:
                result[name] = {"state": "UNAVAILABLE", "error_type": type(exc).__name__}
                result["errors"].append(name)
    return result


def _market(root: Path) -> dict[str, Any]:
    view = engine._pointed(root, "market-view-latest.json")
    scores = engine._pointed(root, "scores-latest.json")
    return {
        **{
            key: view.get(key)
            for key in (
                "dataset_id",
                "latest_observed_session",
                "generated_at",
                "configured_securities",
                "latest_session_securities",
            )
        },
        "securities_with_history": len(view.get("histories", {})),
        "experimental_scores": scores.get("scored_securities", len(scores.get("candidates", []))),
        "score_observation_session": scores.get("observation_session"),
        "inference_at": scores.get("generated_at"),
        "current_eligible_prediction_count": _current_predictions(
            root, view, scores, datetime.now(UTC)
        ),
        "model_id": scores.get("model_id"),
        "model_compatible_segments": ["NSE_EQ"],
        "independently_accepted_predictions": 0,
        "validation_status": "EXPERIMENTAL_RESEARCH_INDEPENDENT_ACCEPTANCE_PENDING",
        "score_snapshot_matches_view": scores.get("dataset_id") == view.get("dataset_id"),
    }


def _current_predictions(
    root: Path, view: dict[str, Any], scores: dict[str, Any], at: datetime
) -> int:
    """Count exact immutable forecast matches with a genuinely future entry window."""
    if scores.get("dataset_id") != view.get("dataset_id") or scores.get(
        "observation_session"
    ) != view.get("latest_observed_session"):
        return 0
    keys: set[str] = set()
    for score in scores.get("candidates", []):
        if any(
            score.get(key) != scores.get(snapshot_key)
            for key, snapshot_key in (
                ("dataset_id", "dataset_id"),
                ("model_id", "model_id"),
                ("session", "observation_session"),
            )
        ):
            continue
        if not score.get("next_session_timing", {}).get("open_at"):
            continue
        if datetime.fromisoformat(score["next_session_timing"]["open_at"]) <= at:
            continue
        shard = hashlib.sha256(score["key"].encode()).hexdigest()[:2]
        path = root / "expanded-forecasts" / shard / "experimental-v2-prospective.sqlite3"
        safe_path(path)
        if not path.is_file():
            continue
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            saved = [
                forward._verified(row) for row in db.execute("SELECT * FROM experimental_forecasts")
            ]
        for forecast in saved:
            fields = (
                "key",
                "session",
                "model_id",
                "dataset_id",
                "feature_hash",
                "source_sha256",
                "score",
            )
            if not all(forecast.get(key) == score.get(key) for key in fields):
                continue
            if not score.get("feature_hash") or not score.get("source_sha256"):
                continue
            if forecast.get("prospective_eligible") is not True:
                continue
            eligible, _ = forward._eligible_timing(
                forecast["session"],
                forecast.get("session_timing"),
                forecast.get("next_session_timing"),
                datetime.fromisoformat(forecast["source_observed_at"]),
                at,
            )
            recorded = datetime.fromisoformat(forecast["recorded_at"])
            opening = datetime.fromisoformat(forecast["next_session_timing"]["open_at"])
            if (
                eligible
                and datetime.fromisoformat(forecast["source_observed_at"]) <= recorded
                and datetime.fromisoformat(forecast["inference_at"]) <= recorded < opening
                and recorded <= at
            ):
                keys.add(score["key"])
    return len(keys)


def _equities(root: Path) -> dict[str, Any]:
    # The all-equity catalog is optional; collector v1 remains separately pinned.
    selected = (
        universe.load(root, expanded=True)
        if (root / "latest-all-equities.json").exists()
        else universe.load(root)
    )
    return {
        "master_id": selected.snapshot_id,
        "master_observed_at": selected.observed_at.isoformat(),
        "summary": selected.summary,
    }


def _scheduler(root: Path, at: datetime) -> dict[str, Any]:
    from alphalens_api.nse_monitoring import windows_observation

    return windows_observation(engine._pointed(root, "task-observation-latest.json"), at=at)


def _collection(root: Path) -> dict[str, Any]:
    receipts = sorted(
        (root / "operational/runs").glob("*.done.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if len(receipts) > 10_000:
        raise ValueError("STATUS_TERMINAL_RECEIPT_INDEX_LIMIT")
    latest = []
    for path in receipts:
        safe_path(path)
        row = engine._read(path)
        outcome = row.get("outcome") or {}
        latest.append(
            {
                **{
                    key: row.get(key)
                    for key in (
                        "run_id",
                        "state",
                        "reason",
                        "started_at",
                        "completed_at",
                        "finished_at",
                        "session",
                        "api_calls",
                        "error_code",
                    )
                },
                "session": outcome.get("session", row.get("session")),
                "api_calls": row.get("source_requests_last_run", outcome.get("api_calls")),
                "new_daily_observations": outcome.get("new_daily_observations", 0),
                "market_view_state": (outcome.get("market_view") or {}).get("state"),
                "has_source_failures": bool(outcome.get("failures")),
            }
        )

    def receipt_time(row: dict[str, Any]) -> datetime:
        value = row.get("completed_at") or row.get("finished_at") or row.get("started_at")
        if value is None:
            return datetime.min.replace(tzinfo=UTC)
        observed = datetime.fromisoformat(value)
        if observed.utcoffset() is None:
            raise ValueError("STATUS_AWARE_TERMINAL_RECEIPT_TIME_REQUIRED")
        return observed.astimezone(UTC)

    latest.sort(key=receipt_time, reverse=True)
    failures = [
        row
        for row in latest
        if row["state"] in {"FAILED", "INTERRUPTED"} or row["has_source_failures"]
    ]
    publications = [
        row for row in latest if row["market_view_state"] == "SAVED_MARKET_VIEW_PUBLISHED"
    ]
    new_publications = [row for row in publications if row["new_daily_observations"] > 0]
    return {
        "latest_terminal_receipt": latest[0] if latest else None,
        "latest_failure": failures[0] if failures else None,
        "last_successful_saved_view_publication": publications[0] if publications else None,
        "last_new_observation_publication": new_publications[0] if new_publications else None,
        "terminal_receipts_examined": len(latest),
    }


def smoke(base: str, credential_file: Path) -> dict[str, Any]:
    """Use one owned auth session; GET saved evidence only, then revoke that session."""
    if base != "http://127.0.0.1:8041":
        raise ValueError("PRIVATE_V1_LOOPBACK_8041_REQUIRED")
    safe_path(credential_file)
    result: dict[str, Any] = {"provider_requests": 0, "financial_writes": 0, "routes": []}
    headers = {"Origin": base, "X-AlphaLens-Local": "p21"}
    with httpx.Client(base_url=base, timeout=180, trust_env=False) as client:
        if client.get("/api/v1/nse-market/research").status_code != 401:
            raise ValueError("SMOKE_UNAUTHENTICATED_BOUNDARY_FAILED")
        login = client.post(
            "/api/v1/auth/login", json=json.loads(credential_file.read_bytes()), headers=headers
        )
        if login.status_code != 200:
            raise ValueError("SMOKE_LOGIN_FAILED")
        csrf = login.json()["csrf_token"]
        try:
            ranks = []
            for count in (5, 10, 20):
                reply = client.get(
                    "/api/v1/nse-market/research",
                    params={"page_size": count, "rank_policy": "risk_adjusted"},
                )
                if reply.status_code != 200:
                    raise ValueError("SMOKE_RESEARCH_FAILED")
                ranks.append([row["key"] for row in reply.json()["data"]["candidates"]])
                if len(ranks[-1]) != count:
                    raise ValueError("SMOKE_INSUFFICIENT_TOP_N_CANDIDATES")
            if ranks[0] != ranks[1][:5] or ranks[1] != ranks[2][:10]:
                raise ValueError("SMOKE_TOP_N_PREFIX_MISMATCH")
            for path in (
                "/api/v1/health/ready",
                "/api/v1/nse-market/universe-coverage",
                "/api/v1/nse-market/saved-market",
                "/api/v1/nse-market/prospective-evaluation",
            ):
                reply = client.get(path)
                result["routes"].append({"path": path, "status": reply.status_code})
                if reply.status_code != 200:
                    raise ValueError("SMOKE_SAVED_ROUTE_FAILED")
            result.update(state="PASS", top_n_consistent=True, authenticated=True)
        finally:
            logout = client.post(
                "/api/v1/auth/logout", json={}, headers={**headers, "X-CSRF-Token": csrf}
            )
            if logout.status_code != 200:
                raise ValueError("SMOKE_LOGOUT_FAILED")
        result["post_logout_status"] = client.get("/api/v1/nse-market/research").status_code
        if result["post_logout_status"] != 401:
            raise ValueError("SMOKE_REVOCATION_FAILED")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--credential-file", type=Path, help="Opt-in authenticated smoke; never printed"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report(args.config, workspace=args.workspace)
    if args.credential_file:
        result["smoke"] = smoke(result["url"].removesuffix("/nse-market"), args.credential_file)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
