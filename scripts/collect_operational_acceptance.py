"""Collect counts, classifications and hashes only; exclude provider price payloads."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from workers.personal.store import PersonalStore
from workers.providers.operations_status import status

from alphalens_api.auth.store import AuthStore
from alphalens_api.local.cli import configured


def main() -> None:
    repo = Path(__file__).resolve().parents[1]

    def local(name: str) -> dict:
        return json.loads((repo / ".local-data" / name).read_bytes())

    browser_settings = configured(repo / ".local-data/p33-browser-runtime/operator-config.json")
    if browser_settings.auth_root is None or browser_settings.personal_root is None:
        raise ValueError("ISOLATED_TEST_OWNER_REQUIRED")
    owner = AuthStore(browser_settings.auth_root).diagnostics()["account"]["account_id"]
    store = PersonalStore(browser_settings.personal_root, owner)
    credentials = local("p31-browser-runtime/credentials.json")
    with httpx.Client(base_url="http://127.0.0.1:8029", timeout=40) as client:
        login = client.post(
            "/api/v1/auth/login",
            json=credentials,
            headers={"Origin": "http://127.0.0.1:8029", "X-AlphaLens-Local": "p21"},
        )
        credentials.clear()
        login.raise_for_status()
        response = client.get("/api/v1/personal/workspace")
        response.raise_for_status()
        workspace = response.json()["data"]
        for kind in ("watchlists", "journal", "rules", "recent"):
            if workspace[kind] != store.listing(kind):
                raise ValueError("RESTARTED_SOCKET_PERSONAL_RECORD_MISMATCH")
        expected = [
            {
                "id": p["id"],
                "revision": p["revision"],
                "updated_at": p["updated_at"],
                "name": p["value"]["ledger"]["portfolio"]["portfolio_name"],
                "event_count": len(p["value"]["ledger"]["transactions"]),
            }
            for p in store.listing("portfolios")
        ]
        if workspace["portfolios"] != expected:
            raise ValueError("RESTARTED_SOCKET_FIFO_EVENT_SUMMARIES_MISMATCH")
        # No provider request is made by workspace or operational status reads.
    scans = {}
    for label in (
        "operational-trixie-trivy",
        "operational-ubuntu-trivy",
        "operational-default-ubuntu-trivy",
    ):
        document = local(label + "/trivy-results.json")
        vulnerabilities = [
            v for result in document.get("Results", []) for v in result.get("Vulnerabilities", [])
        ]
        scans[label] = {
            "created_at": document["CreatedAt"],
            "os": document["Metadata"]["OS"],
            "image_id": document["Metadata"]["ImageID"],
            "trivy": document["Trivy"],
            "high": sum(v["Severity"] == "HIGH" for v in vulnerabilities),
            "critical": sum(v["Severity"] == "CRITICAL" for v in vulnerabilities),
        }
    result = {
        "version": "alphalens.operational-acceptance.v1",
        "collected_at": datetime.now(UTC).isoformat(),
        "scope": "SANITIZED_CLOCKS_COUNTS_CLASSIFICATIONS_HASHES_NO_PROVIDER_PRICES_OR_CREDENTIALS",
        "direct_six_quote_batch": local("operational-six-quotes.json"),
        "initial_strict_browser_batch": local("operational-browser/p34-provider-metadata.json"),
        "browser_initial": local("operational-browser-report.json")["stats"],
        "browser_broader_initial": local("operational-journey-browser-report.json")["stats"],
        "browser_verified_regression": local("operational-browser-final-report.json")["stats"],
        "browser_final_changed_cases": local("operational-browser-delivery-report.json")["stats"],
        "published_synthetic_demo": local("operational-demo-report.json")["stats"],
        "private_daily": status(repo / ".local-data/p34-runtime/daily-config.json"),
        "daily_last_run": local("p34-runtime/daily-last-run.json"),
        "scheduled_task": local("operational-task-verification.json"),
        "native_original_operator": local("operational-native-verification.json"),
        "isolated_test_owner_recovery": local("operational-test-owner-restart.json"),
        "restarted_socket_matches_personal_records_and_fifo_event_summaries": True,
        "frozen_and_original_alerts": local("operational-frozen-preservation.json"),
        "credential_and_postgres_isolation": local("operational-security.json"),
        "real_model_audit": local("operational-model-audit.json"),
        "container_scans": scans,
        "current_model_predictions_generated": 0,
    }
    (repo / "docs/development/alphalens-operational-evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "state": "SANITIZED_OPERATIONAL_RECEIPT_WRITTEN",
                "restarted_socket_records_equal": True,
                "provider_prices_exported": False,
                "credentials_exported": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"state":"OPERATIONAL_RECEIPT_NOT_VERIFIED","sensitive_output":false}')
        raise SystemExit(1) from None
