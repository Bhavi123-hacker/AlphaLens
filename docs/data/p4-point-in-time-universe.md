# P4 point-in-time historical universe

Authority: user-approved D43-D45. P3 passed and was committed as
304ab3ddc22619c3248da446c785dbf48b2f567b before P4 started. This is a minimal
development identity/universe service, not the P5 financial/entity schema.
P1_PRODUCTION_DATA_CLEARANCE = OPEN. Production data remains NOT_CLEARED.

## Evidence and identity

`alphalens_data.universe` is source-neutral and does not import FastAPI, vendors,
acquisition, feature/model/signal or backtest logic. IdentityFact preserves internal
security_id, source_security_id, symbol, series, optional ISIN/aliases, effective
interval and independently versioned provenance. MembershipFact preserves explicit
listing status and security type. Each fact has fact_id, revision_id and optional
supersedes_revision_id. Identity and membership versions are independently recorded.
Ticker alone is never permanent identity. Aliases retain former names without
silently mapping a future symbol backward.

Fact provenance keeps source, artifact reference/SHA256, evidence reference,
classification, published_at, available_at, availability_basis and ingested_at.
Known availability requires a supported basis and reference; publication cannot
follow availability, availability cannot follow recorded receipt. Unknown stays
null and is not eligible. RESEARCH_FIXTURE additionally requires accepted rights/
attribution evidence; labels alone do not clear data. Production facts are disabled.
Only non-secret references are accepted; request URLs are not provenance IDs.

Effective intervals are always `[effective_from, effective_to)`: start included,
end excluded, null end open-ended as asserted by that revision. A future termination
cannot appear in the earlier revision until evidence of the closure is available.
Equal/reversed intervals fail. Exclusive identity and membership intervals cannot
overlap in a queried knowledge state; overlaps fail, with no arbitrary winner.
Simultaneous conflicting source security ID, symbol or ISIN mappings also fail.

## Point-in-time query and revisions

```python
snapshot = HistoricalUniverse(evidence).as_of(session_date, decision_time)
```

Decision time must be aware; instants normalize to UTC. Session dates are NSE-local
dates. A future session relative to the declared decision date is rejected; no
exchange-session calendar is invented. In historical mode only revisions with
`available_at <= decision_time` are considered. Live mode additionally requires
`ingested_at <= decision_time`. Verified evidence acquired later can be used in
historical mode without treating acquisition as historical availability.

For each fact, a single explicit revision chain preserves the original, then selects
the last known revision via a bisect index. Branching, missing parents, cycles,
duplicate revisions, changing internal security identity and time inversions fail.
Unknown-availability corrections never supersede a known historical revision.
Selected intervals are sorted and queried with half-open bounds. There is no
all-securities pairwise scan; quality lookups are indexed by session/source ID.
No benchmark or performance claim is made.

An explicitly later decision_time can restate an old session with newer knowledge.
Keeping the old decision_time preserves old known membership/classification/symbols.
Snapshots pin both the complete input hash and known-evidence hash. Adding later
corrections creates a different complete input hash/new snapshot, while old-cutoff
known-evidence hash and entries stay unchanged. Existing snapshots are never
overwritten, and replay against different pinned input fails. This is an explicit
new knowledge-state query, not silent rewriting of an earlier snapshot.

The candidate inventory may contain internal IDs of unrecognized future/unknown
securities for diagnostic exclusions. Such candidates are not historical existence
or membership: their unavailable identity/membership facts, symbols, intervals and
provenance are not exposed as known facts. Only known facts enter the known-evidence
hash and artifact-reference list.

## Membership policy

TEST_DYNAMIC_CASH_UNIVERSE is implemented with constructed TEST_ONLY evidence.
RESEARCH_DYNAMIC_NSE_CASH has an extensible typed definition requiring research
classification/rights, but no real historical NSE universe has been acquired or
verified. Historical NIFTY 500/INDEX_MEMBERSHIP remains UNAVAILABLE/unsupported;
there is no index-membership fallback. CURRENT_SNAPSHOT_ONLY fails loudly at the
service/CLI boundary and cannot automatically become historical truth.

Only explicitly LISTED COMMON_EQUITY with an effective, known identity is included.
ETF, REIT, INVIT, PREFERENCE and DEBT are ineligible; UNKNOWN stays unknown. EQ-like
series is not evidence of common-equity classification. A known future listing
supports EXCLUDED_NOT_YET_LISTED, not early inclusion. A known DELISTED interval
supports EXCLUDED_DELISTED; a closed interval without departure evidence becomes
EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE, never an inferred delisting.

Inclusion/exclusion reasons are explicit: INCLUDED_LISTED_CASH_EQUITY,
EXCLUDED_NOT_YET_LISTED, EXCLUDED_DELISTED, EXCLUDED_SECURITY_TYPE,
EXCLUDED_UNKNOWN_CLASSIFICATION, EXCLUDED_INFORMATION_NOT_AVAILABLE and
EXCLUDED_MEMBERSHIP_EVIDENCE_UNAVAILABLE. Past departed companies remain in earlier
snapshots and the historical audit. Missing prices do not erase listing history.
Unknown/incomplete evidence degrades historical_universe_status; unavailable
coverage is UNAVAILABLE. VERIFIED fixture coverage refers only to constructed facts.

## P3 interaction

QualityEvidence contains a one-session P3 report, its checksum/source/evidence
reference and separately declared availability/receipt. Reports are checked for
consistent severity/gating and unique sessions. Report availability is never
inferred from the fixture session or real catalog publication. Quality must be
available by the decision time, and source/security mappings must agree.

Universe membership and analysis eligibility are separate fields. A listed common
equity with rejected session quality remains a member, with analysis_eligible=false
and DATA_QUALITY_REJECTED. Missing/unavailable session quality produces
DATA_QUALITY_UNAVAILABLE. VALID/DEGRADED scoped quality can allow analysis within
fixture scope. Global P3 failures block analysis, not historical existence. Multiple
ambiguous reports for one session or mixed validator versions are rejected rather
than choosing a report silently.

The P4 integration adds `p3.quality.v2` optional QuarantineScope: when the selected
P2 parser preserves an explicit valid stable source ID/date on a rejected financial
row, the file loader associates errors with that session. Symbol-only or malformed
identity/date rows remain unlocated and fail closed. Scope references must join
actual quarantine rows. P2 financial/parsing behavior is unchanged. v1 reports
remain readable/preserved; v2 output uses versioned filenames and hashes. Metrics
count valid observations only in nonrejected sessions. This extension is required
to show a bad G session without rejecting unrelated A sessions or erasing G.

## Snapshots, CLI and audit

Snapshots retain session/decision time/mode, definition/version/classification,
identity/membership/validator versions, eligible/excluded entries with evidence,
quality/reasons, input hashes and known artifact references. Source facts are
canonically ordered before input hashing; reordering identical evidence reproduces
the same snapshot. Snapshot ID is SHA256 of canonical contract JSON excluding only
snapshot_id. UTC instants are serialized before hashing. Replay compares complete
bytes; publication uses P2 immutable writes. No runtime timestamp or random ID.

```powershell
uv run --frozen python scripts/build_p4_test_fixture.py --data-root data/p4-test-only-v2
uv run --frozen alphalens-universe --input data/p4-test-only-v2/universe-input.json --date 2024-01-10 --decision-time 2024-01-10T12:00:00+00:00
```

Explicit decision time is required; no exchange-close time is invented. CLI reports
session/eligible IDs and symbols/analysis eligibility/exclusion reasons/hash/version;
exit 2 on invalid evidence/replay, otherwise 0. Outputs stay in ignored data/ or
.local-data/. `--audit-snapshots <chronologically ordered prior files>` adds the
current snapshot and writes a deterministic audit after replaying every input.

Audit counts describe sampled requested sessions: unique included securities,
membership entries (including initial members), exits, observed symbol changes,
security/snapshot exclusions by reason, unknown/unavailable evidence and analytical
exclusions. It preserves historically-present IDs absent from the final snapshot.
These are observed membership transitions, not inferred legal listing dates or
statistics about unsampled sessions. Inputs/definition/mode must match.

Fixture A survives; B enters Jan 5; C departs Jan 12; D changes symbol Jan 10 with
Jan 9 availability; E is ETF despite EQ; F stays UNKNOWN; G has no Jan 5 price and
invalid Jan 10 OHLC but remains listed; H's Jan 10 symbol change is only available
Jan 12. TEST_ONLY.evidence.txt is a checksum-pinned constructed attribution marker,
not official market evidence. Per-session quality availability is explicitly
constructed at 11:00 UTC, never claimed as actual NSE timing.

Across Jan 1/5/10/12/20 fixtures, six common equities are represented historically,
C is retained in history but absent at the end, and G's two analytical exclusions
do not remove membership. Real NSE survivorship-bias control, departed coverage,
classification history, calendar, licensing and PIT membership remain unverified.

File storage suffices: no new PostgreSQL migration, SQLite or P5 entity tables.
Existing real P2 PostgreSQL integration is rerun. No paid dependency, real-market
recommendation, feature/label/model/backtest/frontend or trade execution.
See [P4 verification](../development/p4-verification-report.md). Stop before P5.
