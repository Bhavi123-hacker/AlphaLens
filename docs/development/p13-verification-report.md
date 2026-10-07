# P13 development verification

Status: P13 DEVELOPMENT PASSED. P14 implementation has not begun.

Continuation audit (2026-10-07): the observed starting tree already contained
staged P13 work on the requested branch, with HEAD at approved P12. It was not
clean and P13 had started; no P14 files existed. The clean baseline described
below is the earlier recorded baseline, not this continuation's observed state.
Reviewed and preserved those changes. Made the positive-momentum reason threshold
serialized and completed probability/freshness/history/eligibility invalidation.
Refreshed 100-signal deterministic replay into data/p13-signal-final.

The first sandboxed regression could not access Docker. After escalation, a
pre-existing disposable database volume retained an old test password, causing
two integration failures and one fixture error; stopped that run early. PostgreSQL
logs confirmed authentication failures. Removed only the dedicated verification
container/network/volume, then started a fresh complete regression. No domain
logic or tests were changed to hide these environment failures.
Branch p13-p14-signals-explainability from approved P12
28070df3981170a4a1f1725b5bb9b4373b490568. Baseline clean; approved P11 b50314b and
P12 commits and DEVELOPMENT PASSED reports present. Main 9fa8228 and original
DOCX SHA256 196e1803a2ebc52fda57a54d86e7eefcb1842c61e8f3f67eb9bafd163891b34a
unchanged. No P13/P14 source was present at baseline. Earlier reports preserved.

P13 consumes target-free approved risk/ranking evidence with exact PIT lineage.
Canonical states, explicit synthetic-position contexts, independent horizons,
serialized development thresholds, confirmation/retention hysteresis, ordered
reasons, invalidation, freshness, immutable history and checksum IDs implemented.
Normal insufficient model selection and unknown action coverage block entry.
Full lifecycle tests use explicit TEST_ONLY demonstration evidence; they never
upgrade model confidence or represent actual user positions/performance.

100 approved-artifact TEST_ONLY signals replayed twice and round-tripped with
identical IDs. All 100 WATCH; 64 EOD_COMPLETE and 36 UNAVAILABLE. No ownership,
entry or exit inferred. TEST_ONLY — NOT A PERFORMANCE CLAIM. This distribution
shows conservative evidence handling, not model accuracy or market performance.

Initial authored fixture test failures exposed typed Pydantic construction and
the ignored-output workspace boundary; corrected the fixture types and temporary
working directory rather than suppressing warnings or weakening storage rules.
Focused 17 state/lifecycle cases passed. The actual P2-P12 future-evidence replay
has been extended to P13 and is included in the complete gate.

Focused P13 plus actual source replay: 18 passed in 68.05s. Two additional cases
verify LIMITED historical evidence and STALE feature evidence cannot become entry
confidence; final focused P13 run: 19 passed in 8.76s. Immutable signal artifacts
and standalone UTF-8 CLI match exactly, including past-only state history.
Lock/frozen sync PASS (96 resolved/95 checked), Ruff check/format PASS (204 files),
mypy PASS (129 source files), Bandit eight roots PASS (12098 lines, zero findings/
suppressions), dependency audit no known vulnerabilities. No new external package.
Current incremental Linux signal image build/import under -W error passed.
Prior cold-build disk-capacity caveat remains historical; no new cold build or
hosted CI result claimed. Docker resources belonging to other work were untouched.

Leakage evidence is in test_p13_signals.py (future risk/history/position visibility,
unknown future member rejection, policy identity, duplicate/incompatible history,
missing/mismatched risk, freshness/sufficiency and no production promotion) and
test_p9_future_knowledge.py (actual later price revision, listing/membership and
corporate-action evidence through P2-P12). Signal states, conditions, reasons and
historical symbols remain unchanged under future source evidence. Full source
dataset identities can change while earlier decision evidence stays numerically
invariant; this is audit versioning, not an information upgrade. P13 histories
contain only validated prior compatible observations. All seven lifecycle states
are exercised on explicitly constructed TEST_ONLY evidence, not real holdings.

Production clearance OPEN; production market-data use NOT_CLEARED. No paid/new
external dependency, market acquisition, P15 portfolio or API/frontend/live work.

Final reviewed-source full Windows-safe run: 394 passed, one production/live skip
in 1388.13s (data/p13-full-clean.log). All 19 P13 cases and actual source-level
future knowledge replay passed. PostgreSQL 17 ingestion/canonical CLI replay
twice and dedicated teardown completed. PowerShell's combined-output redirection
reported Docker progress on stderr as NativeCommandError and returned wrapper
status 1, despite the passing suite/replay and no Python traceback. A focused
three-case PostgreSQL/replay/teardown invocation with explicit native exit capture
passed (392 deselected); verification runner exit 0. The full-suite result is one
coherent 394-test run; the focused check resolves runner status only.
Final replay: 100 WATCH, 64 EOD_COMPLETE/36 UNAVAILABLE; UTF-8 CLI exact equality.
Final Ruff check/format204, mypy129, Bandit12107 zero findings, frozen lock/sync and
dependency audit passed. Incremental Linux image rebuilt/import passed using its
installed /app/.venv/bin/python (the initial system-Python import failed and was
corrected). Original DOCX/main unchanged. No P14 code before the P13 commit.
