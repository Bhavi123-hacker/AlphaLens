## D78 prospective and source-status extension

Fixed-host metadata checks cannot be used as SSRF/arbitrary downloader endpoints:
network access is explicit CLI only, bounded, no redirects, token URL or price fetch.
Provider statements are not authorization. No source or current prediction is promoted
by an accessible status response, checksum-compatible artifact or historical IC.

Prospective paths are private, transactional and schema checked. Immutable evidence
and content hashes defend crash/collision/corruption; OS-operator compromise can still
alter local files and is outside cryptographic authentication guarantees. Normal
research cannot accept TEST_ONLY records or arbitrary future prices; no public upload
or mutation API exists. Real clocks cannot be overridden. Forecasts recorded too late,
unknown calendar/actions/availability and unsupported ranking fields fail closed.

P20 events are fixed text from hash-verified persisted outcomes. A durable cursor
acknowledges after idempotent publication, retaining failures for replay. TEST_ONLY
producers require isolated alert namespaces. No credential/body/model serialization,
new stock signal channel, external sender or account ownership claim is introduced.
Backups remain operator-private, integrity checked and never overwrite live accounts.
Strict container and secret scans remain unchanged; supported-distribution CVEs and
production/local HTTP/multi-owner limitations remain independent blockers.

## P22-P25 local operational additions and residual risks

D77 authorizes the final local platform sprint; historical stops below are superseded
only for these phases. Private health/metrics/history require P21 sessions. Fixed
log fields/metric families omit secrets and unbounded labels; operational event
outbox verifies lineage before using P20. Online backups have private roots,
schema/checksum manifests and non-destructive new-location restore with revocation.

Compiled-shell XSS consequences remain constrained by same-origin CSP, HttpOnly
cookies, no frontend token storage and verified Origin/CSRF mutations. Static paths
are allowlisted and cannot overlap private stores; unknown APIs never serve HTML.
The native supervisor never adopts/kills a foreign PID or exposes a shutdown API.
OS-operator compromise remains outside web authentication's protection; private
config/backup/control directories must remain operator-controlled. SameSite on
loopback HTTP does not establish TLS or secure multi-owner isolation.

Disappearing SQLite sidecars are distinguished from existing-file ACL failures;
negative permission tests preserve the gate. Dependency/secret/container checks
remain strict. Supported trixie CVEs, public networking/TLS, data rights, live source,
economic validation and current signals remain independent blocked gates. See
[P25 review](../development/p25-security-review.md) and
[executed verification](../development/p25-verification-report.md).

## P21 implemented local controls and residual gates

D76 authorizes P21 from approved P20 eaeb01d, stopping before P22. Genuine local
single-operator authentication, server-side authorization, Argon2id/opaque sessions,
Origin/CSRF controls and React login preserve all research and P20 event evidence.
This milestone amends the original managed-identity/multi-role proposal to a local
singleton ADMIN workspace. It does not establish multi-owner financial isolation,
production HTTPS or market-data clearance. No public signup, brokerage, automatic
acquisition/scheduling or outbound notification is introduced.

See [implemented security design/threat model](../security/p21-authentication.md),
[Windows setup](../security/p21-windows-commands.md) and
[verification](../development/p21-verification-report.md). Strict supported-image
CVEs remain a separately reported security gate. Earlier sections below retain
their historical foundation/phase context.

# Foundation threat model and future release gates

Assets: source/provenance, licensed raw data, model artifacts, user portfolios,
identity/session tokens, provider credentials and audit records. Model artifacts,
user portfolios and auth are not implemented yet.

Trust boundaries: untrusted providers/files -> adapter -> canonical validation;
untrusted web input -> API validation/authorization -> owned resources; workers ->
storage under scoped identities; future explanatory text never becomes instructions.

| Threat | Foundation control / future gate |
| --- | --- |
| Fabricated/poisoned/revised provider data | Explicit origins, source/revisions, evidence, PIT checks; broader reconciliation/quarantine later. |
| Historical leakage/survivor-only selection | Known availability, effective intervals, unknown capabilities; actual universe/evaluation gates later. |
| Credentials in Git/logs/errors | Ignore env/keys, placeholders only, allowlisted JSON events, safe API errors, SecretStr config; scans required when tooling available. |
| Unsafe user cross-portfolio access (BOLA/IDOR) | No product endpoints now; managed OIDC, RBAC and resource ownership required before P17. |
| Privileged operator misuse | USER/ADMIN/DATA_OPERATOR/ML_OPERATOR design; append-oriented audits and promotion approvals later. |
| Network/database exposure | Local loopback Compose ports and internal network; nonroot read-only API container; private production networks/TLS later. |
| Provider auth abuse/SSRF | No network adapter now; later fixed provider destinations, bounded timeouts/quotas and payload limits. |
| Prompt injection/news poisoning | News and LLM excluded; future LLM has no DB writes, arbitrary SQL, secrets or trade tools. |
| Model tampering | No artifacts now; checksums, approved registry, restricted artifacts and integrity checks before inference. |
| Misleading readiness | /live is process-only; /ready requires real DB response; neither claims market/provider/ML availability. |
| Real-trade execution | Permanent prohibition; no broker execution surface or credentials. |

CI skeleton fails closed on missing lockfile and includes intended lint/type/tests,
static/dependency/secret/container scans. Auth, rate limiting, request body limits,
MFA, session revocation, encryption/backup restoration, DAST, operational alerts and
production IAM are not implemented or claimed complete. Runtime health surface is
local/test only. Do not publicly deploy this skeleton as the product.

Retention is dataset-specific and constrained by license/user privacy. Concrete
retention/RPO/RTO values need approval/evidence, not invented compliance periods.
Test-only CI database values are clearly nonproduction ephemeral test configuration.

## P17 local read exposure (D72)

P17 exposes private P15/P16 records only within a loopback development boundary.
There is no fake authentication or public authorization claim. Actual peer IP,
trusted hosts and configured local browser origins are checked; the launcher
disables proxy-header trust. Do not place it behind a public proxy/tunnel. GET-only
routes never call writes, paper session processing or model execution. Database
transactions are read-only with timeouts and ledger bounds. Artifact references
come from pinned metadata, resolve beneath configured roots and require SHA256
plus OOS role/model/dataset validation. Model binaries are never deserialized.
Errors/logs omit input values, credentials and personal paths. Response size and
read concurrency are bounded. Trusted local cache receipts are not signatures or
a defense against a malicious local filesystem. P21 and strict Trivy remain
release blockers; no container finding is ignored. See the P17 contract.
