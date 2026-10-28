"""TEST_ONLY deployment policy checks; these never provision hosting resources."""

import json
from importlib import import_module
from pathlib import Path

yaml = import_module("yaml")


def test_render_requires_reviewed_persistence_and_manual_deployment() -> None:
    source = Path("infra/deploy/render-private.review-only.yaml")
    blueprint = yaml.safe_load(source.read_text(encoding="utf-8"))
    assert not Path("render.yaml").exists()
    assert len(blueprint["services"]) == 1
    service = blueprint["services"][0]
    assert service["type"] == "web"
    assert service["runtime"] == "docker"
    assert service["autoDeployTrigger"] == "off"
    assert service["numInstances"] == 1
    assert service["disk"]["mountPath"] == "/var/lib/alphalens"
    assert service["disk"]["sizeGB"] >= 10
    assert service["healthCheckPath"] == "/api/v1/health/live"
    variables = {item["key"]: item for item in service["envVars"]}
    for key in (
        "ALPHALENS_DATABASE_URL",
        "ALPHALENS_PUBLIC_ORIGIN",
        "ALPHALENS_ALLOWED_HOSTS",
        "ALPHALENS_CORS_ORIGINS",
    ):
        assert variables[key] == {"key": key, "sync": False}
    assert variables["ALPHALENS_UPSTOX_PRIVATE_VIEW"]["value"] == "false"
    assert "databases" not in blueprint  # No implicit expiring or chargeable DB creation.
    assert "cronJobs" not in blueprint


def test_cloud_image_cannot_include_local_private_state_or_autostart_collector() -> None:
    text = Path("infra/docker/hosted-private.Dockerfile").read_text(encoding="utf-8")
    copies = [line for line in text.splitlines() if line.startswith("COPY ")]
    assert not any(".local-data" in line or "COPY . " in line for line in copies)
    assert 'CMD ["/app/.venv/bin/python", "-m", "alphalens_api", "serve"]' in text
    assert "USER alphalens" in text
    assert "ALPHALENS_UPSTOX_PRIVATE_VIEW=false" in text
    assert "ALPHALENS_ACCESS_MODE=hosted_private" in text
    assert "FROM node:" in text and "COPY --from=web" in text
    assert "workers.nse_market.cli" not in text


def test_vercel_demo_is_explicitly_synthetic_without_any_private_api_proxy() -> None:
    value = json.loads(Path("infra/deploy/vercel-synthetic.review-only.json").read_bytes())
    assert value["buildCommand"] == "npm run build:demo"
    assert value["outputDirectory"] == "demo-dist"
    assert "rewrites" not in value
    assert "env" not in value
    headers = {v["key"]: v["value"] for v in value["headers"][0]["headers"]}
    assert "connect-src 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"


def test_cloud_container_gate_does_not_publish_or_waive_security() -> None:
    text = Path(".github/workflows/hosted-private-container.yml").read_text(encoding="utf-8")
    value = yaml.safe_load(text)
    assert value["permissions"] == {"contents": "read"}
    steps = value["jobs"]["hosted-container"]["steps"]
    scan = next(step for step in steps if step.get("uses", "").startswith("aquasecurity/trivy"))
    assert scan["with"]["severity"] == "HIGH,CRITICAL"
    assert scan["with"]["exit-code"] == "1"
    assert "ignore-unfixed" not in scan["with"]
    assert not any("deploy" in step.get("uses", "").lower() for step in steps)
    assert "--network none" in text
