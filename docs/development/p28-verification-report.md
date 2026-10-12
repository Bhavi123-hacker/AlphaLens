# P27/P28 engineering verification

Baseline P26 `531490987b265bdfae58545f75b7c4fc8c331f00`; isolated worktree
D:/al-research/p28-worktree, branch p28-free-nse-provider-evaluation. Original
C/P26 checkout remained clean. New user-authorized P29 sprint will branch after
this verified provider checkpoint; independent development does not await Upstox.

Delivered typed exchange-aware provider/quote contracts, three original native
offline daily adapters, current-only Upstox master parser, disabled interfaces
for all six sources, request/capacity planning, private durable quotas/selection,
P19 TEST_ONLY dispatch, catch-up/revision planning, peer/38-feature diagnostics,
future hidden Analytics Token import, protected six-provider API/Settings/Data Health,
worktree-correct Windows launchers and isolated synthetic demo preparation.
See provider comparison, architecture and CMD operations documents.

## Executed checks

* Targeted P28:51 passed (22.01s):29 adapter/store,7 worker,7 readiness/credential,
  4 API,3 release-planning and1 demo case. Authorized P17/P19/P20/P21/P26/P28
  integration/security regression228 passed (43.57s), overlapping47 P28 cases:
  232 distinct cases across these runs. Not a new whole-repository clean run.
* Initial P28 failures: wrong receipt key in2 worker assertions;2 later tests
  expected the pre-redaction exception type/wrong TEST_ONLY ISIN;3 session tests
  omitted the fixture calendar argument. Corrected; failure history retained.
* Frontend complete71 unit/component tests passed (12.71s); TypeScript/build,
  ESLint and npm audit passed; zero known npm vulnerabilities. First70-case run
  predates the extra bounded read-policy test and demo-label changes.
* Actual compiled browser first8-case run:3 provider cases passed/5 chart cases
  failed because a logout test revoked the shared setup session. Separate logout
  session fixed. Next8-case run7 passed/1 failed on genuine cold READ_CAPACITY.
  Bounded local retry policy added without changing backend limits. Focused
  RELIANCE regression then1 passed (10.2s). Eight distinct browser scenarios
  verified across runs, not one clean8-case result. Keyboard/mobile/Axe checks passed.
* Ruff/format417 files, strict mypy253 sources, Bandit, pip-audit, frozen103-package
  lock and whitespace checks passed; no dependency versions changed. Bandit status
  constants were represented as an enum rather than password-like string comparisons;
  no scanner exclusions or severity changes. Dependency audits found zero known
  vulnerabilities; editable workspace packages skipped by pip-audit as documented.
* Compiled build passed; chart engine retains681.15kB/228.27gzip warning and lazy
  loading. No unsupported live chart or synthetic runtime fallback was introduced.
* Native CMD owned startup/shutdown/restart passed on127.0.0.1:8028 with genuine
  archive and isolated TEST_ONLY operator/copied alerts. No unrelated process killed.
* Verified CLI comparison/status/disabled-selection/capabilities/planning/catch-up,
  fixture verification and P19 replay. Initial standalone fixture used an invalid
  uppercase P2 dataset identifier and produced an immutable FAILED receipt;
  corrected generator/new v2 test root produced COMPLETED_WITH_WARNINGS. Neither
  failure nor original receipt was overwritten. Unknown actions/peers/model gates
  remain explicit, and no live inference or ranking was produced.
* Trusted checksum-pinned XGB load inspection confirmed38 features/native3.0.5;
  zero fits/predictions/evaluation, artifact and global reviewed types unchanged.
  Initial subprocess implementation was replaced by an owned bounded multiprocessing
  child; no broad Bandit suppressions were introduced.

## Credentials, actual data and preservation

Reuse the earlier single Alpha SYMBOL_SEARCH test: valid credential, RELIANCE.BSE,
no NSE proof, zero price/new-session acquisitions. No further quota used. Key
remains Windows-current-user protected; original plaintext unchanged and removable
by operator after successful migration. Future Upstox import tested only with
generated TEST_ONLY secret material, never a real token.

Full read-only SHA verification:2,485 frozen files/8,505,278,241 bytes,152 fits,
504 backtests and46,072,188 OOS rows preserved.47 original alerts/evidence hashes
unchanged. Original report bytes were checked in C (actual API source); isolated
worktree checkout CRLF representation was separately verified against Git text.
See p28-artifact-preservation.json. No research execution occurred.

P19 live acquisition BLOCKED; source rights NOT_CLEARED; Upstox UNDER_REVIEW;
current inference/ranking/signals and scheduler DISABLED/UNAVAILABLE.474 economic
outcomes unresolved. Optional demo is synthetic and local, not public deployment.

## CI baseline and follow-up

Actual P26 frontend38208915054 SUCCESS. Foundation38208914993 FAILED at strict
Git-history TruffleHog:0 verified/3 unverified;1,978 chunks/6,689,403 bytes.
Docker/Trivy were skipped. Historical examples/negative fixtures remain reviewed
in existing secret reports, not automatically declared revoked or harmless.
No candidate secret values are reproduced. Previous actual container gate still
44 HIGH instances across8 CVEs,0 CRITICAL; no new-head scan is claimed.
P28/P29 pushes will record their own actual workflow outcomes; scans remain strict.

**Implementation/offline verification passed; authorized live activation has not.**
