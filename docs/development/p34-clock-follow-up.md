# P34 narrow clock follow-up — 15 October 2026

Baseline: `p34-operational-readiness`, `5f8aec7b428d416272be86ce84fcb8071859bf73`.
[Read-only follow-up metadata](p34-clock-follow-up-metadata.json) preserves the
two-source measurements, rate comparison and unchanged compiled-build hash.
No runtime, frontend, financial formula, validation, operator record, frozen
research, alert, portfolio, Decision Desk or public demo change in this follow-up.

## Actual verification

At 15:14 IST, five NTP samples from each independent source measured Microsoft
median +242.9655 ms (maximum reported distance 38.32955 ms) and Google median
+243.2004 ms (20.0738 ms). All sampled intervals remained above zero. Programmed
correction was +64 ppm; precise wall time gained 2.083700 ms over 30.000131 seconds
of monotonic time. This corroborates gradual correction, not convergence.

Windows Time is Running/Automatic. Last successful sync remains 14:27:02; verbose
status reports Hold/stale data. The active peer uses special polling (32,768 s),
with about 29,743 s remaining when queried. The 1 s phase threshold routes this
subsecond discrepancy to gradual correction. These observations explain why a
successful resync did not immediately eliminate the offset; a network defect or
competing hypervisor time provider is not established. No policy was changed.

The [clock runbook](../operations/p34-clock-recovery.md) now supplies the measured
diagnosis, administrator-reviewed maintenance steps and exact policy rollback.
Its PowerShell examples are syntax checked only; no clock-step outcome is claimed.

| Check | Result | Evidence / requirement |
| --- | --- | --- |
| Two-source bounded NTP diagnostics | PASS | 5 samples each; uncertainty and rate recorded |
| Clock convergence | FAIL | Both medians approximately 243 ms behind; all intervals positive |
| New bounded six-stock quote request | NOT RUN | User required convergence first; zero quote GETs this follow-up |
| Accepted current LTP and previous-close change | NOT VERIFIED THIS FOLLOW-UP | Last genuine six-stock attempt accepted 0/6; unchanged timestamp checks still mandatory |
| Authenticated current-quote browser acceptance | NOT RERUN | Prerequisite failed; previous strict case remains failed |
| Primary dated EOD fallback | PREVIOUSLY PASSED; unchanged | Prior real authenticated browser proof; no new browser pass claimed |
| Existing compiled loopback app | PASS, availability only | Login and compiled index checked without requesting quotes; not authenticated quote acceptance |
| Private retention and completed-session readiness | PASS, scoped | Existing official source decision; one RELIANCE 14 Oct session; replay receipt unchanged |
| Scheduling | NOT ACTIVATED | Clock fails; no AlphaLens task registered; XML remains disabled |
| Complete ML vector / independent acceptance / current rankings | UNAVAILABLE | Evidence requirements below; no inference or research rerun |

## Daily collection decision

Reviewed the [private source-use decision](../data/p34-private-upstox-use-decision.md)
and existing genuine capture receipt. Source permission covers the single-operator,
non-commercial private historical-data/ML scope, subject to provider terms and
quotas. It does not authorize public redistribution. No support message was sent.

The read-only readiness CLI again reports READY_FOR_OPERATOR_TASK_ACTIVATION,
0 network calls, scheduler false, and DUPLICATE_ACCEPTED_REVISION_NO_FETCH for
14 October. The original capture used 2 GETs, replay 0; it contains one observation
and zero features/predictions. This follow-up did not repeat acquisition or modify
the private retained session. UNKNOWN basis and absent action/publication evidence
still prevent canonical/ML eligibility.

All activation conditions do **not** pass together: clock convergence fails.
The user conditionally authorizes narrow scheduling once gates pass; that condition
is not met. The explicit calendar presently proves only 14 October. The existing
worker can obtain official timing for the previous local date within its maximum
3-GET run, but must skip unknown/nonreturned dates; it does not infer weekdays or
claim a complete calendar. Its existing schedule is one verified RELIANCE key,
previous-session EOD (not same-day EOD), least privilege, no overlapping runs,
10-minute limit. No whole-universe plan or task registration was introduced.

After clock repair, the next activation check is: verify official elapsed timing
for the next eligible past session, retain one source-qualified EOD release and
replay with zero fetches, inspect warnings, then register/enable only the reviewed
single-key task. Missing publication must remain pending; no synthetic close.
The existing readiness label is source/staging readiness, not a clock-health or
model-acceptance certificate.

## Finite ML evidence-acquisition and independent evaluation plan

This is a bounded evidence plan, not a new implementation phase or approval of
the four frozen models. Reuse the [registered-protocol design](../ml/p33-prospective-acceptance-protocol.md).
No paid source, research refit, locked-2026 evaluation or new inference is run here.

1. **Close one provider-semantics evidence packet.** Obtain written, versioned
   Upstox documentation/support confirmation for historical-candle adjustment
   basis, handling/revision of splits/bonuses/dividends and timestamp/publication
   semantics. Use the existing unsent inquiry; sending still requires explicit
   instruction. OHLCV retention is permitted; complete action accounting and
   original publication/known-at evidence are not supplied merely by that licence.
   Outcome: accepted compatible basis, or an explicit unresolved gap for each field.
2. **Assemble one dated calendar/identity packet.** Obtain official trading,
   holiday and special-session facts covering each intended input/target date,
   plus dated equity-series/type/identity and peer-membership facts. Preserve
   their actual known-at times and permitted-use evidence. Today's 2,697 identities
   cannot reconstruct historical membership. Missing facts block the affected
   date/security; do not substitute today's universe or infer actions from jumps.
3. **Run one bounded six-security compatibility pilot after those gates pass.**
   The fixed diagnostic cohort is RELIANCE, BAJFINANCE, TCS, INFY, HDFCBANK and
   ICICIBANK. Plan a maximum of 6 historical GETs, one per verified key, only if
   the provider range contract supports the required interval; otherwise stop
   and obtain a revised bounded request plan. Target the existing P6 engine's
   201 verified session slots per security (at most 1,206 requested cohort slots),
   preserving missing rows and identity boundaries. Private historical OHLCV can
   be acquired now under the scoped permission once clock/session checks pass.
   Such backfill is retrospective data, not proof it was available at an earlier
   decision. Build a compatibility/missingness report using unchanged P6 formulas,
   with exact basis, source, calendar, revision and cutoff lineage. This is a
   diagnostic pilot, **not** an eligible six-stock cross-sectional replacement.
4. **Resolve one complete peer-universe and P11 risk packet before inference.**
   Specify the genuine dated eligible denominator and obtain compatible return-20
   inputs for every peer at the same cutoff, using a separate explicit batch/quota
   plan before expanding acquisition. Preserve the original tie-aware
   momentum_percentile_20 formula and peer lineage. Six quotes or a current master
   do not fill this field. Required current risk, corporate-action and liquidity
   evidence must also pass existing contracts. If a newly scoped prospective
   universe is needed, independently review it as a separate protocol/version;
   do not silently assert compatibility with the frozen model universe.
5. **Obtain one independent signed evaluation registration.** Pin the exact four
   artifact hashes, ordered 38 features, horizons 1/5/10/20, cohort, decision clocks,
   baseline predictions, missingness, costs and review criteria. An independent
   reviewer must set numeric improvement margins, error budget, power and minimum
   independent sessions/outcomes using a separate permitted pre-period. Apply
   dependence-aware power analysis, calibration, session-block stability, cost
   sensitivity and complete drawdown assessment from the existing protocol.
   No thresholds are invented to approve these candidates. Missing registration
   blocks the prospective evaluation regardless of successful artifact loading.
6. **Observe one locked prospective cohort through its registered boundary.**
   Timestamp eligible predictions before outcomes, then wait for genuine sessions
   and horizon maturity. The 20-session task needs at least 20 subsequent verified
   sessions for its first label; statistical acceptance additionally requires the
   independently calculated sample and multiple chronological blocks. Backfilled
   prices cannot create this future track record. Evaluate once at the locked
   boundary and obtain a written independent pass/fail review of every candidate.
   Failure remains failure. The 474 unresolved historical economic backtests stay
   unresolved. P11–P14 publication, financial-advice and security gates remain
   independent even if a future statistical acceptance passes.

Immediate finite deliverables are the two source/calendar evidence packets, one
six-stock diagnostic report, one dated peer/risk packet, one signed registration,
and one future cohort evaluation. Some documents/data can be acquired under private
scope; actual future outcomes and independent scientific judgment cannot be
compressed into this software session. Current accepted ML predictions: **zero**.

No new full Python/frontend/browser/security pass is claimed for this documentation
follow-up. Previous exact results remain in the P34 operational report; strict
production container security remains failed on its recorded upstream findings.
An initial availability probe used an incorrect default build path and a nonexistent
auth route; it did not verify those checks. The corrected probe used the actual
configured `.local-data/p33-web-build`: login returned 200 and served/compiled
index SHA-256 both matched `da8ddf75c13b15364b877dd1a1170f95e1a0c07a6b5f2876d87200dcbbcc2575`.
