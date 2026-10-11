# P19 incremental research integration design (D74)

Design recorded before implementation, 2026-10-09. Approved baseline:
`5e02e5cd1b120e200def460b3ab037fb27df9ec7`; branch `p19-daily-research`.
The original DOCX and completed research are immutable. P20–P25 are outside scope.

## Data and execution boundaries

The worker lives separately from FastAPI. It captures original bytes through P2
RawLanding, uses the existing TejHQ Parquet adapter and P2 normalizer, P3 quality
validation, research P4 assessment/P5 identity rules, and P6 registry/numerical
execution. It publishes independent P19 receipts and bounded per-session products,
never changes the frozen canonical/supervised dataset or historical reports.

Three modes must remain separate: blocked current-source attempts; explicit
TEST_ONLY local replay; and approved pinned historical TejHQ replay. Historical
replay is not evidence of a new session or live activation. Unverified future
calendar dates remain unknown rather than inferred weekday sessions.

Run identity pins source policy, source revision/content, session, calendar,
feature registry, baseline identity and mode. An OS-backed exclusive lock releases
on worker death. Exclusive immutable checkpoints make interrupted runs resumable;
the complete receipt is the atomic visibility boundary. Readers verify referenced
hashes before exposing products. Corrections retain separate revision identities.

The incremental feature stage reads projected trailing calendar windows only,
preserves missing/rejected slots and compares with the existing batch formulas.
No alternative indicator formula or whole-archive daily recomputation is allowed.
Cross-sectional/reference features without adequate scope remain unavailable.

Inference is separately gated by the fixed candidate metadata, checksummed local
artifact, exact fitted preprocessing/feature order, baseline compatibility and
decision chronology. A replay inside the already evaluated holdout cannot rerun
its inference. No model fitting exists in this worker. Experimental inference on
genuine later observations requires independent source/calendar/compatibility
acceptance; candidate evidence status remains insufficient. Ranking/signals remain
withheld when existing P11–P14 gates are unsatisfied; no policy recalibration.

## Integration and operational exposure

P17 gains additive bounded GET-only daily status/run/quality/product reads with
source/session/receipt/classification lineage. Requests never execute a worker.
Existing historical endpoints keep their original semantics. Incremental price
and feature reads are separately named, so the dashboard can deliberately display
new evidence without replacing historical or OOS records.

P18 receives an operational status panel/timeline and a separately labeled daily
research forecast view. Current opportunities continue to honor evidence failures.
Default listeners remain loopback; resource roots are private configuration.

CLI commands provide source check, dry-run, run-once, replay, verify, resume and
status. Scheduler XML is disabled by default and is not registered or enabled
without a separately verified source and explicit scheduling authorization.
Bounded retries, finite read budgets and safe structured events replace infinite
polling. Large data, models, caches and logs stay in ignored D-drive storage.

## Initial provider finding

Official NSE website terms currently restrict systematic automation. Public
Hugging Face metadata shows a newer TejHQ revision, but earlier authorization
pins the historical archive and does not establish unrestricted ongoing exchange
rights. No daily provider is approved merely because its URL works. The source
audit will record exact evidence, hashes and unresolved permissions separately.
Software acceptance and real daily activation are separate gates. Production
readiness remains false, P1 OPEN, market-data use NOT_CLEARED, P21 absent and the
44 HIGH container findings unresolved.
