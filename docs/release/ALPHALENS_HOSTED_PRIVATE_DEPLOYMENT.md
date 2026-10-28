# Hosted private AlphaLens deployment preparation — 28 October 2026

The functioning application remains at **http://127.0.0.1:8041/nse-market**.
The prepared cloud target is the **actual authenticated research application on
one Render web service**, serving both the compiled dashboard and its API on one
HTTPS origin. It is separate from the existing synthetic demonstration at
https://bhavi123-hacker.github.io/AlphaLens/.

No cloud resource, domain, database, credential, scheduler or paid service was
created. No local collector or application was restarted by this preparation.
The existing Windows collector remains responsible for its approved schedule;
the web image does not contain or launch a cloud collection job.

## Exact artifacts and limits

| Artifact | Purpose |
| --- | --- |
| `infra/docker/hosted-private.Dockerfile` | Builds the real React application and the locked Python API; runs non-root, with private state supplied separately. |
| `infra/deploy/render-private.review-only.yaml` | Inactive, manual-deployment Render proposal with one service and a persistent disk. It is deliberately not a root `render.yaml`. |
| `.github/workflows/hosted-private-container.yml` | Builds the hosted image, tests original offline authentication/recovery, rejects unprovisioned startup and applies the strict HIGH/CRITICAL container scan. It never deploys. |
| `infra/deploy/vercel-synthetic.review-only.json` | Optional Vercel configuration for the existing separate synthetic demo only; project root must be `apps/web`. It cannot publish the real research API. |
| `infra/release/alphalens-private-2026-10-28.json` | Dated record of the current private Windows deployment; preserves the previous historical manifest. |
| `scripts/verify_dated_private_deployment.py` | Offline current-config/build wiring check; makes zero provider requests and does not certify live collection or cloud deployment. |

The former loopback-only application cannot be moved to Render by changing a
hostname alone. Hosted mode is explicit: exact HTTPS origin and host allowlist,
Secure/HttpOnly/SameSite cookies, original CSRF checks, protected persistent
operator state, and no trust in caller-supplied forwarded-client headers. The
default local mode retains its existing loopback restrictions.

Vercel and Render as separate browser origins would require a different cookie
and proxy architecture. That arrangement is not the deployment supplied here.
The single Render origin avoids changing the application's same-origin API
contract. Vercel remains optional for independently synthetic static content.

## Preconditions before creating resources

1. Select the operator's actual Render account, region, service hostname and
   allowed audience. Confirm that applicable provider/exchange agreements cover
   storing and processing this private dataset at that host for that audience.
   Ownership of AlphaLens code does not establish market-data redistribution
   rights. Do not enable public raw data, export or third-party recommendations.
2. Approve the exact hosting cost or supply an existing persistent server.
   Render's free web service sleeps after inactivity, has ephemeral local
   storage and does not support a persistent disk. Free Render PostgreSQL also
   has an expiry; it is not the persistent production database used here.
   The inactive proposal's `0.5c-512mb` service and 20-GB disk are chargeable and
   **have not been approved or created**. That smallest service's memory capacity
   is unverified; measure it with the actual imported workload before acceptance.
3. Require passing CI for the exact final hosted image. Previous zero-HIGH/
   zero-CRITICAL results for the local API foundation image do not certify this
   new hosted image. Record its digest, scan artifact and final source commit.
4. Prepare a verified portable snapshot into a new private destination. Include
   genuine source/master observations, unchanged model artifacts, all forecast
   bodies and outcome revisions, required registered protocols, and the intended
   operator's state. Do not copy Windows drive paths as cloud configuration.
   Preserve the original PC data and use snapshot hashes/counts to verify import.
   Revoke sessions only in the imported account copy; never overwrite the
   existing operator or publish its credential material.
5. Supply persistent PostgreSQL through a secret environment value if those
   financial/historical features are required. Use a separate least-privilege
   cloud database target, encrypted transport and verified backup/restore. The
   blueprint does not automatically create, migrate or replace a database.
6. Document whether the hosted saved-data snapshot is a dated copy or receives
   a separately authorized private synchronization process. A snapshot is not
   an automatic cloud daily feed. Moving collection or copying new observations
   off the PC requires a qualified exact policy; existing task approval is not
   transferred to a new cloud worker.

The applicable hosting capabilities and blueprint keys were checked against
[Render's blueprint specification](https://render.com/docs/blueprint-spec) and
[free-service limitations](https://render.com/docs/free). These are configuration
references, not an authorization to create paid resources.

## Environment and persistent layout

Use the Render service's real HTTPS origin consistently. Values below illustrate
the contract; replace the example host with the explicitly selected service.
Enter secrets through the host's environment controls, never into Git, URLs,
build arguments, frontend variables or command history.

```text
ALPHALENS_ACCESS_MODE=hosted_private
ALPHALENS_HOSTED_BIND_HOST=0.0.0.0
ALPHALENS_PUBLIC_ORIGIN=https://alphalens-private.example
ALPHALENS_ALLOWED_HOSTS=["alphalens-private.example"]
ALPHALENS_CORS_ORIGINS=["https://alphalens-private.example"]
ALPHALENS_HOSTED_DATA_ROOT=/var/lib/alphalens
ALPHALENS_AUTH_ROOT=/var/lib/alphalens/auth
ALPHALENS_OPERATIONS_ROOT=/var/lib/alphalens/operations
ALPHALENS_FRONTEND_ROOT=/app/web-build
ALPHALENS_EXPERIMENTAL_NSE_V2_ROOT=/var/lib/alphalens/experimental-nse-v2
ALPHALENS_UPSTOX_PRIVATE_VIEW=false
ALPHALENS_DATABASE_URL=<host-secret-only, when required>
PORT=<host-assigned-port>
```

The V2 root's siblings must preserve the saved workspace layout:
`nse-market-expansion/` and `nse-universe/`. Configure any additional research,
personal, daily, alert and provider-store paths to their imported protected
locations under the same data root. Unimported optional components remain
unavailable; do not fabricate an empty successful database or market history.
Do not enable the provider button or import an acquisition token to make the web
server fetch data. Persistent account directories/files must have the API user's
ownership and original owner-only security policy.

The existing `scripts.backup_research` bundle uses `v1/`, `v2/`,
`nse-market-expansion/` and `nse-universe/` siblings, with a checksum-bound manifest.
If that bundle is imported under `/var/lib/alphalens/imported/snapshot/`, override
`ALPHALENS_EXPERIMENTAL_NSE_V2_ROOT` to
`/var/lib/alphalens/imported/snapshot/v2`; do not keep the image's illustrative
`/var/lib/alphalens/experimental-nse-v2` default. Use the bundle's verified sibling
layout rather than renaming directories or editing original manifest bytes.
The research backup excludes credentials, the operator account and PostgreSQL.
Those require separate protected provisioning and acceptance procedures.
The hosted image includes the existing backup verifier. Linux accepts validated
retained Windows manifest separators without rewriting the original evidence;
new manifests use portable relative separators. Verify a provisioned bundle:

```bash
/app/.venv/bin/python -m scripts.backup_research verify --source /var/lib/alphalens/imported/snapshot
```

Hosted startup fails closed when its required origin, persistent state, protected
active operator or compiled frontend is absent. It does not bootstrap an account,
initialize replacement databases or create sample prices. The image includes no
private state; starting a freshly built image without provisioning is expected
to fail.

Initial Render deployment therefore requires seeding the disk, protecting the
operator account and validating the snapshot before a usable app can start.
The exact first-boot transfer/provisioning method has not yet passed acceptance
on a selected Render account. The blueprint is a preparation artifact, not a
one-click complete deployment. Do not bypass startup checks, embed private data
in an image or temporarily publish a data-transfer endpoint to solve this gap.

## Build and release sequence

Run the build in an isolated development checkout. This downloads ordinary build
dependencies, not market data, and does not touch the working Windows process.

```bash
docker build -f infra/docker/hosted-private.Dockerfile -t alphalens-hosted-private:review .
```

After the prerequisites above pass, manually review the inactive Render blueprint,
fill only approved target values and provision/import the persistent state using
the release's qualified snapshot procedure. Record the state inventory before
starting the service. Its command is:

```bash
/app/.venv/bin/python -m alphalens_api serve
```

In explicit hosted mode the server binds the host-provided `PORT` on the container
interface. Default loopback mode remains bound to `127.0.0.1`; no existing local
listener, Windows task, quota or operating-system network setting is changed.
Render must terminate HTTPS at its ingress; do not expose the database publicly.

The platform health check uses `/api/v1/health/live`. This checks process health;
it is not proof of fresh market coverage, qualified forecasts or complete data
import. The protected `/api/v1/health/ready` and collection-health pages require
the original authenticated acceptance workflow.

## Hosted acceptance and rollback

Verify the selected HTTPS URL, wrong-host/origin rejection, secure session cookie,
login/logout, CSRF rejection, unauthenticated market API denial and no credential
leakage. Then verify genuine saved stock search, price/volume charts, original
forecasts, Top5/10/20, model version/freshness, history, pending outcomes and health
receipts. Include a master-only stock with truthful unavailable data. Compare
imported forecast bodies/counts and dataset/model hashes with the snapshot.

Restart only the newly deployed owned cloud instance. Verify that account state,
saved forecasts and observations survive. Check process memory/latency on the
chosen service, back up the cloud store and restore into a separate destination.
Do not mark the hosted application accepted until these actual target checks pass.

If acceptance fails, remove access to the new hosted service and restore the
previous approved image/configuration against its compatible preserved state.
For an initial deployment, keep the working PC application as the service of
record. Do not downgrade databases, erase reservations, reset accounts, replace
frozen models, clear forecast history or modify either Windows task to recover
a cloud release. Keep failed image/log/snapshot evidence for diagnosis.

Cloud availability and current market delivery are separate results. Experimental
predictions remain experimental after deployment; zero qualified forward outcomes
still means no measured forward accuracy.
