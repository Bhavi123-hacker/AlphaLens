# Offline readiness for 1,000 current NSE common equities

Audit date: 20 October 2026 IST. Branch: `alphalens-monitoring-evidence-repair`, from production repair `56e42455909bd1eda2b3d3daa25565c44ac4966b`.

**Conclusion: technically feasible as a staged engineering expansion, but FAIL under the currently approved daily capacity. Not activated.** The candidate universe has been expanded offline to exactly 1,000 identities. Genuine retained history remains 500 securities; scoring remains 302 current V2 securities. No new market observations, requests, scores or forecasts were created by this preparation.

## Revalidated production baseline

Independent saved-source audit reproduced 499 accepted 19 October candles, 447,982 qualified retained observations, RRECL pending, 1,004 actual shared GETs, 1,200 expanded reservations, 302 new forecasts, 633 V2 forecast records and zero matured outcomes. Of those 633 records, **602 are unique model/security/observation decisions**; 31 original records overlap expanded decisions. These are not 633 independent samples. 20 October has no open NSE session in the retained dated timing evidence.

Evidence: `docs/development/alphalens-2026-10-20-live-collection-verification.md`; independently regenerated `.local-data/monitoring-repair-20261020/initial-audit.json`, `ledger-preservation.private.json`, `forecast-audit.private.json`, `api-final.private.json`. Every accepted candle's identity, source-body hash, session, normalized/raw parity and saved-frame membership was checked. No live source probes were performed.

## Reproducible proposed universe

Command (offline; creates private proposal files only):

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\project-python.cmd -m scripts.prepare_nse_1000_readiness
```

Frozen manifest: `.local-data/nse-1000-readiness/8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405.candidate.json`.
SHA-256: `8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405`.
It is private provider metadata, not a public redistributed data file. Replaying against the same master and plan produces identical candidate bytes. Computed readiness/simulation results have a separate `.readiness.json` file.

Selection preserves **every existing approved 500-stock identity**, then adds 500 eligible identities in ascending ISIN/key order. No historical return, forecast score or hindsight winner selection is used. Exact provider keys and ISINs are unique. Eligibility reuses the checksum-verified current-master/common-equity classifier, not a competing ETF/type filter.

| Identity/data fact | Observed result |
| --- | --- |
| Dated master | Retrieved **20 October 22:30:16.832160 IST**; current-master snapshot `40a0e0548ec84f3864e0cfb3f5d02709c9391a7a84d290dc87c0e760e6648040`. |
| Current eligible common equities | **3,185**; earlier 3,198 belongs to a different master date. |
| Candidate cohort | **1,000**, existing 500 preserved plus 500 additional. |
| Series | **EQ 574; BE 49; ST 63; SM 310; BZ 4**. These include supported ordinary SME/trade-to-trade series; they are not all liquid large-cap EQ shares. |
| Verified historical securities within proposal | **500**. Additional 500 have not been queried by this preparation. |
| Currently scored within proposal | **302 V2**, all existing saved eligible observations. Additional 500 scored: **0**. |
| Latest compatible saved LSTM scores | **43**, dated 16 October; no expanded/current LSTM inference was run. |
| Listing/status evidence | Present in the dated current master with valid identity/type/series classification. Historical listing dates, suspensions, delistings and point-in-time membership are **not established** by that fact. |
| Price-basis/action readiness | Existing observations retain the documented split/bonus-adjusted price-component limitations; complete dividends and exhaustive actions remain unavailable. Additional 500 compatibility is **unverified**. |

The private manifest records these distinctions for each security. Discovery never upgrades to provider candle accessibility, complete lookback, action compatibility or model eligibility. The large SME component makes liquidity/capacity validation especially important; its membership was not adjusted after examining model outcomes.

## Request arithmetic and limits

Current implementation: **250 securities/run, 600 reserved GETs/run, 1,800/day, at most three attempts/day, 60-minute cooldown**, 20:30/21:30/22:30 IST. RELIANCE is separate and unchanged. `workers/nse_market/operational.py` also hard-limits its configuration to three attempts and 1,800/day; a proposal cannot bypass that by editing JSON. Existing exact-cohort approval hashes bind the original 500.

The current successful path uses **one candle GET per missing security and one action GET per nonempty accepted candle response**. Additional dated timing and master requests are charged to the same per-run reservation. Existing policy reserves headroom for **70 timing GETs and one master GET/run**; a full 250-stock valid batch therefore needs at most **571** requests on that declared path, within 600. Actual retries, interruptions and publication failures are not guaranteed away by this envelope.

| Coverage case | Minimum batches | Valid-stock GETs, excluding metadata | Fixed reserved capacity | Fits current three slots / 1,800? |
| --- | --- | --- | --- | --- |
| 500 missing securities, all valid | 2 | 1,000 | 1,200 | **PASS**, one recovery slot remains. |
| 1,000 missing securities, all valid | 4 | 2,000 | 2,400 | **FAIL**, needs one more slot and 600 more daily reservation capacity. |
| One-time history bootstrap of additional 500, all nonempty/action requests valid | 2 | 1,000 | 1,200 if using 600-reserved batches | Separate acquisition approval required; must not silently consume the current 500 task's scope. |

Thus the existing three slots can select at most **750 securities/day**, even if network and CPU were infinitely fast. For four full valid batches, the conservative declared stock-plus-metadata envelope is **2,000 + 4 × 71 = 2,284 GETs**, within 2,400 reserved. The actual number cannot be known before provider publication; 2,000 is the complete valid-stock path, not a fabricated measured future request count. An empty response consumes a candle request but does not justify an action request or accepted candle. Already complete evidence should replay with zero acquisition.

Keeping 1,800/day could support a separately approved **rotating partial-freshness** 1,000-stock cohort, with at most 750 selected per day and honest per-security lag/catch-up. It cannot provide all 1,000 on the latest session every day and does not authorize a scope change by itself. That alternative was not activated either.

Shared configured rate limits are **50/second, 500/minute, 2,000/30 minutes**. The independently read 20 October rolling peaks were **8, 326 and 502** respectively. Serial hourly batches do not require higher rate limits. The shared ledger must continue enforcing all clients' aggregate consumption, including RELIANCE/quotes/master clients. No universal account-level daily allowance was independently established by the saved configuration; workflow reservation approval is distinct from provider entitlement.

### Recovery simulation using saved implementation rules

`simulate_pending` is explicitly **TEST_ONLY queue arithmetic**, not market data or a successful 1,000-stock acquisition. It uses the existing oldest-missing-first policy, skips completed stocks and keeps an unavailable oldest security pending on subsequent batches.

| Simulation | Qualified hypothetical successes | Pending | Distinct attempted | Stock GETs excluding metadata |
| --- | --- | --- | --- | --- |
| Four slots, all 1,000 publish | 1,000 | 0 | 1,000 | 2,000 |
| Four slots, one oldest security stays empty | **996** | **4** | **997** | 1,996 |
| Five slots, one oldest security stays empty | **999** | **1** | **1,000** | 2,003 |

Four slots/2,400 is therefore a **minimum all-valid capacity**, not robust recovery. Five slots/3,000 provides another bounded attempt in the demonstrated one-persistent-missing case, while correctly leaving that security unavailable. More missing/suspended stocks, unpublished sessions, failed clocks or Windows interruptions can still prevent completion. No schedule can manufacture an unavailable candle. The current 500-stock task's retry resilience should not be silently traded away.

## Duration, storage and inference costs

Measured completed 250-security worker durations on 20 October were **391.273536 seconds** and **191.328691 seconds**, including their actual capture/research stages. A linear four-batch planning range is roughly **12.8–26.1 minutes of active work**, separated by at least three hours between first and fourth triggers. This is an estimate, not an execution guarantee. Current Windows task limit remains 30 minutes/run; standby/AC interruptions and source latency must be resolved operationally rather than hidden by a longer timeout.

Pinned-model replay measured **302 existing compatible vectors in 2.4777075 seconds**, model reload **0.0187600 seconds**, exact saved-score parity. Pure prediction linear extrapolation for 1,000 complete vectors is **8.2043295 seconds**, excluding feature generation, calendar/action validation, ledger publication and outcome reconciliation. Source: `.local-data/monitoring-repair-20261020/prediction-cost.private.json`. The added 500 currently have **zero proven complete vectors**. This benchmark does not create their scores or establish new-model applicability. Feature processing must consider at least 61 compatible slots/security, up to 61,000 slots for 1,000 fully eligible inputs, and preserve all exclusions.

Measured existing `instruments/` source/checkpoint storage: **38,076,229 bytes**, excluding reused seed history and other research stores. Measured 499-security latest-day raw/normalized/action/receipt evidence: **1,509,270 bytes**. Linear EOD-artifact estimate: **3,024,589 bytes/session for 1,000**, additional **1,512,295 bytes/session** for 500 (about 33.3 MB additional per 22 sessions). These figures **exclude** versioned scores/workspaces, SQLite forecast/outcome stores, master snapshots and backups. A rough new-history estimate from 450 non-seed history stores is approximately **42.3 MB for another 500 at comparable depth**, with substantial coverage/volume uncertainty. No retention deletion is proposed. Actual growth must be measured at a bounded pilot before approving a disk envelope.

Existing documented source scope supports narrow private noncommercial retention/derived research. It is not a grant for public redistribution, commercial use or unlimited polling. No new source/contract was acquired. Exact 1,000-stock acquisition and recurring workload authorization remains separate from the earlier approved 500-stock policy.

## Acceptance criteria and exact approval boundary

| Gate | Result | Required before live expansion |
| --- | --- | --- |
| Revalidated original 500/data/forecast/quota evidence | **PASS** | Remain preserved. |
| Reproducible 1,000 unique current common-equity identities | **PASS** | Revalidate dated master before acquisition. |
| Additional 500 provider history, actions, listing/candle availability | **PENDING** | Explicit bounded source-qualified pilot/bootstrap; no live GET performed here. |
| All 1,000 same-session updates under three slots / 1,800 | **FAIL** | Mathematical capacity deficit; do not activate. |
| Four-slot / 2,400 all-valid capacity simulation | **PASS, conditional** | New exact policy, reviewed hard-cap change, approval receipt and idle-window task change. No recovery slot is guaranteed. |
| Five-slot recovery with one persistent missing security | **PASS, TEST_ONLY** | 3,000 daily reservation ceiling and five-attempt limit would require broader explicit approval and testing. |
| Additional 500 technical/model readiness | **PENDING** | Actual history/lookback/action compatibility and unchanged model-input validation. No imputation or model retraining. |
| Independent performance / accepted rankings | **PENDING** | Genuine future outcomes and unchanged independent acceptance protocol. |

No runnable 1,000-stock production config or scheduled task was installed. The minimum all-valid proposal is the frozen manifest above, **250 stocks/run, 600 reserved/run, four attempts/day, 2,400 reserved/day, 60-minute cooldown, 31-day catch-up**, with illustrative triggers **20:30/21:30/22:30/23:30 IST**. It requires explicit approval and software policy changes because current guards intentionally reject it. For recovery, an alternative proposal is **19:30/20:30/21:30/22:30/23:30**, five attempts and **3,000/day**; 19:30 publication is not guaranteed and an empty early run still consumes a reservation. Neither proposal is approved or enabled by this report.

Before selecting either recurring policy, approve a separate bounded bootstrap of the exact added 500 identities: successful-path **500 historical candle GETs + up to 500 action GETs**, metadata/retries separately bounded within two 600-reserved batches, with measured quality/storage and safe resume. It must not run as an extra manual collection under today's 500-stock approval. Multiple publication failures or a need for different history windows require review, not unlimited retries. The original RELIANCE task remains untouched.

### Rollback

There is nothing to roll back in production today: it still uses the unchanged 500-stock plan/config/tasks. Candidate/readiness files are separate private evidence and may be retained without operational effect. Any future activation must first back up current configuration, exact task XML, plan/score/workspace pointers and consistent personal/forecast database snapshots. Promote only while no collector runs. Preserve the old 500 plan and source stores; if rollback is needed, restore the approved 500 configuration/task definition and coherent previous pointers under the same idle-window controls. **Never delete new source records/forecasts, rewind consumed reservations or rewrite ledger history.** Recheck source coverage, account preservation, replay and task paths before re-enabling a prior policy.

Offline simulations and regression evidence are recorded in [the companion dashboard repair report](alphalens-dashboard-evidence-repair.md). No profitable strategy, 1,000-stock data coverage or accepted model is claimed.
