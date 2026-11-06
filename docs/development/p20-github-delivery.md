# P20 GitHub delivery evidence

Implementation commit: `62b3f14433b52b3a18fa14d8ffb56d0c72e47e70`.
Branch: `p20-alerts-p19-activation`, pushed normally to origin; no merge/force push.
This report records completed head-specific runs, not a prediction of later CI.

[Dashboard run 38140383586](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38140383586)
PASSED: frozen OpenAPI client/license checks, TypeScript, ESLint, 50 frontend tests,
production build and npm audit.

[Foundation run 38140383600](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38140383600)
FAILED at strict TruffleHog. Before that failure, Linux lock/sync, Ruff/format,
mypy, Python/PostgreSQL **689 passed / eight skipped, 221.12 seconds**, Bandit and
Python dependency audit PASSED. Docker build/import/Trivy were SKIPPED; this run
therefore supplies no new container vulnerability result.

TruffleHog reported zero verified / three unverified findings (two URI, one
Postgres). GitHub annotations locate them in:

- `docs/development/command-log.md`, line 218.
- `tests/unit/test_configuration.py`, line 31.
- `tests/integration/test_p17_api.py`, line 248.

These are the same retained historical TEST_ONLY example/negative-test findings
investigated in the P19 verification report. All three current file blobs match
the approved P19 baseline byte-for-byte. The initial push of a new branch scans
retained earlier history; current safe example construction does not remove old
commits. No P20 credential was introduced. Finding values are deliberately omitted.
No live credential was established; unverified is not declared cleared.

Scanner `--results=verified,unknown`, strict failure behavior and severity policies
remain unchanged. No ignore rule, history rewrite, finding suppression or scanner
waiver was used. A later push is evaluated under the action's normal event commit
range; a passing incremental scan does not erase this recorded history failure.

The last actual baseline container receipt remains 44 HIGH OS / zero CRITICAL,
with no stable supported remediation for the whole set established. Later CI runs
may produce a separate fresh result; production security remains blocked until
independent findings are resolved. See the combined verification and Debian tracker
links. Operational software acceptance is separate from these security gates.

Local session-owned API/Vite verification processes were stopped. Original unrelated
Git/Docker processes were preserved. No enabled acquisition, scheduled task, native
notification or email sender was created. Main and frozen artifacts are unchanged.
