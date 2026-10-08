# D70: final-vintage research methodology

The user authorizes this separate methodology solely for the pinned TejHQ
`14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98` research archive. D70 amends the
earlier strict historical gate; it does not assert that missing evidence exists.
Normal P4/P5 PIT contracts and production clearance are unchanged. No P17 or
P11-P14 recalibration is authorized.

`RESEARCH_EOD_FINAL_VINTAGE_V1` requires RESEARCH_ONLY, preserves
REAL_MARKET_OBSERVATIONS and FINAL_VINTAGE_RESEARCH_ASSUMPTION, and declares
NOT PRODUCTION PIT. Production/test/fixture classifications cannot use the
profile. Profile identity, raw hashes and downstream versions enter manifests.
Ordinary PIT provenance never receives synthetic VERIFIED_PUBLICATION clocks.

## Availability and execution ordering

Session t OHLCV is assumed usable at local midnight of the next calendar session,
an engineering pre-open stage named ASSUMED_NEXT_SESSION_AVAILABILITY. This is
not an actual exchange publication or opening timestamp. A decision uses completed
t prices only. Entry is the next session's evidenced open, after the pre-open
decision stage; there is no same-session t close execution or use of the entry
open as a predictive feature. Missing next opens produce no fill. Targets use
the existing t+1 open to t+h close convention on actual calendar slots.

Historical vendor publication/revision clocks remain unknown. The current archive
may include later corrections: FINAL-VINTAGE REVISION RISK persists through
P5-P10. No exact historical vendor-view reconstruction is claimed.

## Research calendar and missing observations

The observed calendar adds official Muhurat dates 2013-11-03, 2016-10-30,
2019-10-27, 2020-11-14 and 2023-11-12, using the primary NSE references in
the ingestion report. These slots say SESSION_EXISTS / PRICE_OBSERVATION_MISSING.
Other slots say OBSERVED_DATASET_SESSION. The calendar is not a complete
authoritative NSE calendar; unobserved dates are not asserted to be holidays.
No OHLCV interpolation/fill is allowed. P6 trailing windows retain missing slots;
P7 requires every outcome slot and never skips a missing session to change h.
Affected-row counts must accompany results.

## Analytical equity candidates and identity

`NSE_RESEARCH_EQUITY_CANDIDATE_UNIVERSE_V1` is an observed analytical universe,
not NIFTY 500 or an authoritative common-equity universe. EQ/BE/BZ price evidence
with an observed INE-like ISIN, or an explicitly provisional identifier, may be
RESEARCH_EQUITY_CANDIDATE. This never sets production SecurityType.COMMON_EQUITY.
Explicit ETF/REIT/INVIT/preference/debt/fund/index name evidence excludes rows;
INF-like identifiers are conservatively excluded as a disclosed research heuristic,
not authoritative classification. Other identifier/series patterns remain unusable.
Known exclusions carry forward within an observed identity, never backward from
future names. No current constituent list enters historical membership.

Observed ISIN identities retain their P2/P4-compatible source IDs and dated row
symbols. Missing-ISIN observations use source-year-scoped provisional IDs; no
cross-year merger or future ISIN backfill is attempted. This deliberately sacrifices
some continuity and warm-up rather than merging ambiguous ticker reuse.

## Quality, actions and computational execution

P3 VALID/DEGRADED/REJECTED states and reasons are retained unchanged. Existing
ALLOW_DEGRADED feature/training settings are explicitly enabled for this research
run; rejected/missing/type-excluded observations never become usable. Known raw
economic actions degrade trailing context and exclude affected P7 training outcomes.
Corporate actions become research-known only after their effective session using
the same assumed boundary; future actions never influence earlier model inputs.
Raw prices stay RAW_UNADJUSTED; no factors or dividends are manufactured.

Partitioned P5 research contracts and P6 array execution are a scale extension for
7.2 million rows. P6 formulas reuse the closed registry and are checked against
the scalar implementation. P7 stores exact Decimal numerator/denominator/targets;
float conversion occurs only at the estimator boundary. P9 uses the existing fixed
model arena, chronological fold rules, train-only preprocessing and metric helpers.
The normal verified-PIT code paths retain their behavior.

2010-2014 early history, 2015-2021 development training, 2022-2024 sequential
OOS, 2025 confirmation and 2026 final holdout remain fixed. Final candidate choice
must precede 2026 performance evaluation; no tuning after final results. Metrics
remain research diagnostics with assumptions, not production validation.

P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
Fundamental PIT and genuine benchmark data remain UNAVAILABLE.

## Runtime scale safeguards

The free MIT pytz==2026.5 dependency is explicitly pinned/audited for Arrow
UTC timezone interoperability; it removes repeated absent-module lookups and
changes no assumed time boundary. P6 reads pruned columns and computes only
necessary trailing history; P7's indexed execution keeps original global calendar
indices. Full/trimmed feature and exact label parity are tested. Training uses
owned finite row matrices; imputer copy=False avoids a redundant copy without
changing medians/values, and scaler defaults stay unchanged. All twelve native
model-family tests prove the frozen source feature matrix remains unchanged.
No sample cap, random temporal split, feature/label change or performance-based
optimization follows from these allocation improvements.
