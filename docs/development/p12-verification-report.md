# P12 development verification

Status: P12 DEVELOPMENT PASSED. Stop before P13.
Branch p11-p12-risk-ranking. P11 passed a coherent 355-test/one-live-skip Windows
short-root PostgreSQL 17 run and was committed as
b50314b2dc3eba55581f6e4d5792f0369019d635 before P12 began. P0–P11 reports are preserved.

P12 implements fixed per-task/horizon model configuration, normalized observed
components, explicit P11 penalties, complete historical candidate/exclusion
accounting, stable Top-N presentation and past-only rank history. Verified P9
fold/ranking and P10 economic reports require historical availability before
comparison. No target inputs, future reports, tuning or automatic market champion.
Insufficient selection evidence permits TEST_ONLY development only.

## Current evidence

Focused P12 run: 19 passed in 347.37s. The subsequent independent-horizon change
case and extension of the actual P9 future-knowledge replay are included in the
final complete regression. Tests cover deterministic ordering/ties, Top-N,
normalized return/missing components, material risk/uncertainty penalties,
configured-model mapping, future predictions/diagnostics/risk/economics, historical
universe, source rejection, missing risk, past-only compatible rank history,
identity/classification/research gates, immutable artifacts, weak naive results
and verified P9/P10 model lineage. No trivial test-count target was used.

20 TEST_ONLY rankings replayed twice with identical complete IDs/results, 64
ranked records and 36 retained exclusions. 144 P10 MODEL artifacts were verified;
zero economic reports were visible at these earlier ranking cutoffs. This is
intentional availability enforcement. Standalone UTF-8 Top-1 CLI matched the
complete saved snapshot and preserved all exclusions/history. No real-market
winner, production promotion or performance assertion exists.

Static gates: lock/frozen sync PASS (96 resolved/95 checked), Ruff check/format
PASS (196 files), mypy PASS (124 source files), Bandit eight package roots PASS
(11500 lines, zero findings/suppressions), dependency audit no known vulnerabilities.
An initial Bandit check identified one assert in the new ranking branch. Replaced
it with an explicit runtime DataContractError guard, retaining validation under
optimized Python. The early complete invocation was stopped at 15%, its owned
PostgreSQL resources were torn down, and a fresh coherent full run was started
from corrected source. That invocation completed with 374 passed, one live skip
and one new adversarial failure (1501.01s): a future-only P4 catalog placeholder
appeared in an earlier P12 exclusion list. It never became rank-eligible, but its
presence was still a knowledge leak. Narrowly corrected P12 candidate enumeration
to require contemporaneous facts, P4 known-membership reasons or evidenced prices;
unknown future catalog membership is not proof of known existence. Retained
known/announced/departed and price-evidenced ineligible candidates. P2–P11 source
behavior was unchanged. The actual future-knowledge retry passed (63.62s), and
the fixture assertion now also requires absent future-only candidates. The final
coherent complete regression passed 375 tests/one production-live skip (1411.25s),
including all 20 P12 cases and the actual future-knowledge integration. PostgreSQL
17 ingestion, canonical CLI replay twice, dedicated teardown and runner exit 0
passed (p12-full-corrected.log). No source edits during/after that run. This is one
complete passing invocation, not accumulated targeted passes. Prior reports and
main/DOCX remain preserved.

Current incremental Linux ranking image build and CPU/CLI imports under -W error
passed. The prior cold-build disk-capacity limitation remains historical; no new
cold rebuild or hosted CI scan is claimed. No general Docker prune, unrelated
resource removal, new market download or external paid dependency occurred.

The corrected incremental image build/import and standalone CLI artifact check
also passed. Final staged integrity/secret/DOCX/main checks and whitespace passed.
No P13 signals, P14 explainability product, P15 portfolio or frontend/live work
was started. Software acceptance is ready for separate user review of P13 scope;
actual NSE selection/data/production readiness remains blocked as documented.

TEST_ONLY — NOT A PERFORMANCE CLAIM. P1_PRODUCTION_DATA_CLEARANCE = OPEN;
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED. Stop before P13 after verification/commit.
