# D71 frozen baseline review verification

Baseline `8507f7fd5457fe5e53e016c2cd7b8f14e6b6e430`; branch
`real-data-10y-training`. This review adds an independent read-only auditor,
small evidence reports and foundation-container packaging/CI changes.
It changes no frozen research source, dataset/feature/label hash, model
configuration, fold, threshold, candidate lock or 2026 result.

| Verification | Result |
|---|---|
| Stored economic evidence | All 504 runs checked; all 474 unresolved runs classified; zero checked lifecycle/NAV/status inconsistencies |
| Completed run preservation | SHA256 inventory of 2,485 files / 8,505,278,241 bytes; sizes/paths/mtimes unchanged after read-only audit |
| Canonical/source evidence | Canonical bucket hashes; 17 action and 17 price originals verified against frozen receipts |
| Statistical protocol | All four frozen source SHA256 values and uv.lock match the pre-results locked plan |
| Focused TEST_ONLY tests | 14 distinct auditor tests passed: initial 13, then the newly added archive case only |
| Ruff / format | Passed for new auditor and tests |
| Strict mypy | Passed for new auditor and tests, with explicit package bases |
| Bandit | Passed for new auditor |
| Container build | Passed using unchanged frozen Python dependencies |
| Runtime smoke | Non-root UID 999, nine workspace packages and four model-library imports; build installer absent; network disabled |
| Actual Trivy 0.70.0 | FAILED, exit 1: 44 HIGH OS findings, zero CRITICAL; no Rust/Python/npm findings at HIGH/CRITICAL |
| Existing Windows/PostgreSQL gate | Reused completed 548 passed / one live skip, replay/teardown exit 0; no schema/domain dependency changed |
| Existing Python dependency audit | Reused under byte-identical uv.lock; no dependency added |
| Git whitespace / protected files | Checked before commit; main and original DOCX unchanged |

Only necessary targeted tests/checks were run locally. Push triggers the existing
Actions workflow automatically; no manual full-suite/research rerun is requested.
Its strict scan is expected to remain red until supported fixes or a reviewed,
evidence-based packaging remedy resolves the eight remaining OS CVEs.
No suppressed finding or full CI pass is claimed.

See [economic remediation](../backtesting/real-research-economic-remediation.md)
and [container security remediation](container-security-remediation.md).
P17 remains NOT_STARTED and security readiness is BLOCKED. Research-only,
final-vintage assumptions and production OPEN/NOT_CLEARED remain unchanged.
No production champion or P11–P14 calibration is selected.
