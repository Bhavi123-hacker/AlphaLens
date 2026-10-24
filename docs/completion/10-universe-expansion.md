# Existing 500 and proposed 1,000-stock universe — 24 October 2026

Audit branch: `alphalens-master-completion`; starting HEAD `da4382242371c17ebdf2cecc620541931b91e313`. This preserves the earlier proposal instead of treating a dated manifest as a newly acquired universe.

**Existing daily 500: PARTIAL. Proposed 1,000 activation: BLOCKED_APPROVAL and BLOCKED_EVIDENCE.** This audit made no market-data requests and changed no approved cohort, tasks or quota. The original RELIANCE task remains separate.

## Preserved deterministic candidate

The existing immutable candidate file is `.local-data/nse-1000-readiness/8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405.candidate.json`, with SHA-256 `8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405`. The 24 October saved-evidence audit independently rechecked its bytes. Methodology: preserve every approved 500 identity, then add 500 eligible common equities sorted by ISIN/key, without prices, returns, model scores or hindsight selection. Keys and ISINs are unique.

This proposal is tied to the **20 October 22:30:16.832160 IST** master with 3,185 eligible common equities. Its series mix is EQ 574, BE 49, ST 63, SM 310, BZ 4. It includes SME and trade-to-trade instruments; it is not a liquid large-cap cohort. A newer saved master pointer exists from 22 October, but it does not silently revise this frozen proposal or establish a fresh current master on 24 October. The 24-hour identity freshness gate remains in force.

The added 500 have no history/action/model-compatibility qualification from this preparation. Current presence does not establish historical membership, listing date, delisting/suspension status, candle accessibility, liquidity or feature eligibility. The preserved manifest is an offline proposal, not authorization or 1,000-stock data coverage. See [the original readiness investigation](../development/alphalens-1000-stock-expansion-readiness.md).

## Capacity and recovery

| Case | 250-stock batches | All-valid stock GETs | Reservations | Within three attempts/1,800 daily? |
| --- | ---: | ---: | ---: | --- |
| 500 missing securities | 2 | 1,000 | 1,200 | Yes; one possible recovery slot |
| 1,000 missing securities | 4 | 2,000 | 2,400 | **No** |

The all-valid path uses one historical candle GET and one action GET per security, plus metadata/timing overhead. Existing policy reserves 70 timing GETs and one master refresh/run, so a full valid batch has a declared 571-request envelope inside 600. Four batches have a 2,284-request declared envelope inside 2,400 reservations, without guaranteed retry capacity. The shared per-second/minute/30-minute ledger remains independent of workflow daily reservations; neither establishes an unrestricted account-level allowance.

Three current slots select at most **750 securities/day**. Existing `operational.Config` hard-limits attempts to three and daily reserved capacity to 1,800; changing only a JSON file cannot bypass it. Quote V3's 500-key snapshot support does not replace genuine historical/action/adjustment/session requirements for model features or authorize quote retention as daily candles.

Existing TEST_ONLY oldest-missing queue simulation yields:

| Simulation | Updated | Pending | Meaning |
| --- | ---: | ---: | --- |
| Four slots, all 1,000 available | 1,000 | 0 | Minimum all-valid capacity only |
| Four slots, oldest one persistently empty | 996 | 4 | Three other stocks never attempted |
| Five slots, oldest one persistently empty | 999 | 1 | Correctly leaves unavailable security pending |

The source can remain unavailable despite spare capacity. These deterministic arithmetic examples were revalidated in the campaign's 56-case offline guard/capacity suite; they are not acquired observations or forecasts.

## Compliant next choices

First stabilize the approved 500: latest saved 21 October coverage is **248/500**, not complete daily updates. Existing replay skips completed evidence without GETs; retries preserve pending empty bodies and action lineage. Publication/endpoint availability, independent time and interrupted process evidence need resolution before making a larger commitment.

If expansion is later desired, choose a concrete policy for review:

- A rotating 1,000-stock cohort under the existing daily reservation budget, with no more than 750 selections/day and honest per-security lag. It cannot promise all 1,000 fresh each day and still requires exact cohort/cadence approval.
- Four 600-reserved slots, **2,400/day**, for minimum all-valid daily capacity; a fifth slot/**3,000/day** adds the demonstrated limited recovery opportunity. Both require reviewed hard-cap changes, exact day-contained triggers, provider entitlement checks, storage scope and explicit approval.
- Independently qualify a provider-supported more efficient acquisition path. Bulk quote snapshots, caches, hypothetical batching or faster GPU math are not evidence of a suitable replacement for historical/action collection.

A separate bounded bootstrap for the added 500 would require, on the all-valid stock path, 500 historical candle GETs plus up to 500 action GETs, with metadata/retries bounded separately within two approved 600-reserved batches. This has not been executed or approved by this report. Retain historical rights/point-in-time limitations and measure actual growth rather than assuming all new identities become usable inputs.

Prior linear planning estimated about **3.02 MB/session** of raw/normalized/action/receipt evidence for 1,000, excluding models, score workspaces, ledgers, master snapshots and backups. It is not a new measured storage commitment. No protected source/model/forecast may be removed to meet an estimate.

Future activation must preserve current configuration, task XML, model/source/workspace pointers and consistent database backups, promote only in an idle window, and provide a tested rollback to the original 500. Rollback must retain new observations, saved forecasts and consumed reservations; never rewind request history or erase unfavorable outcomes. Nothing in this campaign activated the proposed universe.
