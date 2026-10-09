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
