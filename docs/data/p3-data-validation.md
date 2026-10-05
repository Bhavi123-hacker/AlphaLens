# P3 deterministic data-quality validation

Authority: user-approved D43-D44, amending the DOCX development gate.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. No production or investment claims.

## Architecture

`alphalens_data.quality` preserves P1 `validation.py` and working P2 ingestion.
Immutable contracts: ValidationRule, ValidationIssue, ValidationSeverity,
ValidationInput, DatasetQualitySummary, SessionQuality, ValidationReport.
The engine operates on P2 canonical records without acquisition, vendor parsing,
network, FastAPI or database imports. It consumes P2 quarantine and reuses P2
`normalize` for canonical-boundary invariants; there is no competing OHLC policy.

A separate file loader checks raw checksum/size, replays the selected P2 parser
and normalizer, then checks canonical/quarantine values, normalized lineage and P2
run accounting. CLI selects the fixture interchange parser. Other parsers must be
passed explicitly to load_run with the captured version. Direct service inputs
declare observed raw/normalized evidence; file loading verifies it independently.

## Severity and gate

| Severity | Meaning | Effect |
| --- | --- | --- |
| INFO | Valid observation or declared limitation | Does not degrade alone |
| WARNING | Usable within stated scope with disclosure | DEGRADED |
| ERROR | Affected record/session or dataset unsafe | REJECTED |
| FATAL | Dataset/run cannot be accepted | REJECTED |

VALID has no warnings or blocking issues. DEGRADED has warnings without errors.
REJECTED has any ERROR/FATAL. Severities belong to validator v1; anomaly thresholds
cannot downgrade hard rules. No filtering/adjustment. `dataset_blocked` distinguishes
global failures from scoped failures. Unlocated P2 quarantine blocks analysis
because identity/session is unknown. P4 can preserve existence independently.

## Rules

| Scope | Checks |
| --- | --- |
| P2 | Identifier/date/numeric/positive-price/exact decimal checks, all five OHLC inequalities, nonnegative integral int64 volume, malformed rows/headers/encoding quarantine |
| Dataset | Empty output, partial quarantine, duplicate security/session, conflicting revisions with no winner, duplicate artifact content, one source/dataset/version scope, homogeneous allowed classification, known currency consistency, requested date bounds |
| Provenance | Raw size/SHA256, normalized SHA256, ID derivation, row ordinal, manifest/source/version/filename/acquisition consistency, P2 counts and canonical/quarantine hashes; file input replays original raw parsing |
| Identity | Same source/ISIN/session or source/symbol/session with unexplained multiple security IDs; symbols are attributes, not permanent IDs |
| Time | Per-security chronology, future session relative to acquisition, publication/availability/close/acquisition inversions, invalid effective intervals, use before availability, repeated availability across distinct sessions |
| References | Duplicate/contradictory reference keys and temporal evidence for absent records fail |
| Continuity | Observation-gap candidates; missing sessions require scoped TRADING evidence; NON_TRADING evidence explains dates or rejects contradictory observations |
| Readiness | Source-scoped symbols/missing availability cannot establish historical eligibility |

P2 supports INR or unknown currency only. Canonical publication/availability stay
null; separately referenced TemporalEvidence does not fill canonical fields.
Repeated acquisition times are legitimate. Repeated availability is a warning
because batch publication may explain it. Fundamentals, live freshness SLAs and
complete corporate-action reconciliation remain unavailable. No freshness UI.

## Calendar and anomaly policy

No weekends, holidays, suspensions or exchange closes are inferred. Calendar status
is UNAVAILABLE without references and PARTIALLY_VERIFIED with scoped references.
OBSERVATION_GAP counts adjacent observations with intervening calendar dates;
unverified dates have UNKNOWN_SESSION_STATUS. It is not a missed trading-day count.
CONFIRMED_MISSING_SESSION requires security/date-specific TRADING evidence.
NON_TRADING_SESSION requires its own evidence. Leading/trailing missing sessions
are confirmed only with scoped references within declared bounds.

Default `p3.policy.v1` thresholds (strictly greater than): absolute consecutive-
observation close return 0.5; high/low ratio 1.5; volume/prior-positive-volume
multiple 10. Identical OHLC warns once when a run reaches 5 observations; zero
volume warns. These configurable inspection thresholds are not market judgements.
Returns across gaps are observation returns, not claimed single-session returns.
Decimal computations use precision 38 and ROUND_HALF_EVEN independent of caller
context. Nonpositive prices and hard OHLC failures remain errors.

Discontinuities retain KNOWN_CORPORATE_ACTION, POSSIBLE_CORPORATE_ACTION,
NO_ACTION_EVIDENCE or ACTION_DATA_UNAVAILABLE with referenced evidence. No invented
split/dividend adjustment or synthetic value. Original prices/IDs stay traceable.

## Metrics, report and replay

Counts: canonical/valid/quarantined records, errors/fatals/warnings, securities,
first/last session, duplicate excess observations, gap candidates, confirmed missing
sessions, zero volume, price anomalies, provenance complete/missing observations.
Quarantine counts unique artifact/row pairs; errors count issues. Valid ratio is
valid canonical / canonical count, null for empty input, not a composite score.
Price anomalies count extreme returns/ranges/repeated OHLC; volume rules are distinct.

Every issue includes rule/severity, nullable security/date/artifact/source, original
row numbers, canonical/normalized IDs where available, reason and validator version.
Global issues leave unsupported identifiers null. Reports retain classification,
input SHA256, policy/version, scope limits and session reasons. Input hash includes
order and references. Stable sorted JSON contains no runtime timestamp. Same
complete input reproduces identical bytes/hash; new evidence/policy requires a new
report. Immutable publication never overwrites different bytes.

```powershell
uv run --frozen alphalens-ingest tests/fixtures/p3/TEST_ONLY.csv --spec tests/fixtures/p3/TEST_ONLY.spec.json --data-root data/p3-test-only
uv run --frozen alphalens-validate data/p3-test-only/canonical/<run_id>/canonical.json
```

CLI prints status/counts/hash/version; exit 0 for VALID/DEGRADED, 2 for REJECTED or
integrity failure. Default output: validation-report.json beside canonical input.
Outputs must stay under ignored data/ or .local-data/. Invalid schema/files/replay
produce a deterministic FATAL integrity envelope, classification UNAVAILABLE,
without disclosing input/exception details. Differing existing reports survive.

File output suffices; no P3 migration or P5 schema. db/ remains migration owner.
P2 real PostgreSQL integration is rerun. Constructed fixtures are TEST_ONLY;
accepted research remains RESEARCH_FIXTURE; production input is disabled.
See [verification](../development/p3-verification-report.md).
