# Existing 500-stock collection and 1,000-stock readiness

Audit: 24 October 2026 IST. **Existing 500: PARTIAL. Expanded recurring 1,000: BLOCKED_APPROVAL and BLOCKED_EXTERNAL_EVIDENCE.** No extra provider requests, production configuration changes, task changes or universe activation were performed.

## Current 500-stock evidence

The latest saved accepted session is **21 October: 248/500, 252 pending**. The prior 499/500 coverage applies to 19 October, captured on 20 October. RRECL has no accepted daily record for either session. The saved 21 October evening attempts were empty; next-morning catch-up recovered only one bounded batch. Later task interruption observations and the 22 October clock-preflight failure prevent a consistent-completion claim. See `08-live-collection-reliability.md` and `.local-data/completion-collection-audit/audit.private.json`.

The original exact 500-stock plan, active protected configuration, existing model hashes and all 633 forecast bodies remain preserved. A frozen historical 43-score LSTM snapshot is not current inference over 500 or 1,000 securities. Adding metadata identities does not add price observations, features, action compatibility or accepted models.

## Deterministic proposed universe

The existing private candidate file remains present and byte-identical:

`.local-data/nse-1000-readiness/8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405.candidate.json`

Its independently recomputed SHA-256 on 24 October is **`8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405`**. The preparation implementation is `scripts/prepare_nse_1000_readiness.py`; original methodology and per-security limitations are documented in `docs/development/alphalens-1000-stock-expansion-readiness.md`.

The selection retains every approved 500-stock identity, then adds 500 eligible common equities in ascending ISIN/key order without returns or scores. The pinned master was observed **20 October 22:30:16.832160 IST**, with **3,185 eligible common equities** at that snapshot. The 1,000 candidate series mix is **EQ 574, BE 49, ST 63, SM 310, BZ 4**. Exact keys and ISINs are unique. This is a reproducible dated proposal; its master is now older than the 24-hour current-identity gate. This audit preserved the original manifest rather than silently replacing its membership. Revalidate a fresh dated master before any approved acquisition.

The 500 added names remain **unqueried by this preparation**. Current-master presence establishes dated identity/type/series, not historical listing, suspension/delisting status, liquidity, provider candle accessibility, full feature lookback, complete corporate actions or model applicability. The large SME/trade-to-trade component needs explicit consideration in the scope and economic acceptance criteria.

## Capacity under the unchanged policy

| Requirement | 500 all-valid missing stocks | 1,000 all-valid missing stocks |
| --- | ---: | ---: |
| Minimum 250-stock batches | 2 | 4 |
| Candle GETs | 500 | 1,000 |
| Action GETs if all candles validate | 500 | 1,000 |
| Fixed 600-GET reservations | 1,200 | 2,400 |
| Fits three slots / 1,800 daily reservation | Yes, one recovery slot | **No** |

Metadata/timing requests must remain within each run's reservation. Existing conservative full-batch headroom is **70 timing requests plus one master request**, so the complete valid-stock path is at most **571/run** before any separately unbudgeted retry. Four batches require a conservative **2,284 logical GET envelope** and **2,400 reserved**, without a guaranteed retry slot. Current configuration intentionally rejects more than three attempts or 1,800 reserved/day. Faster CPU/GPU inference cannot remove this acquisition deficit.

TEST_ONLY queue simulation in the existing readiness module yields **1,000 successes** for four all-valid slots; if one oldest stock remains empty, four slots produce **996**, leave **4 pending**, and never attempt three of those names. Five slots produce **999**, correctly retaining one unavailable stock. These are deterministic capacity examples, not acquired data or guaranteed provider publication.

Compliant preparation options, none activated:

1. Keep the 500 cohort and qualify its current publication/clock/interruption behavior first. Replay completed raw/action evidence with zero GETs; reuse a still-valid checksummed master without relaxing its TTL. These behaviors already exist.
2. Propose a rotating 1,000-name cohort under 1,800/day, with at most **750 selections/day** and explicit per-security lag. It cannot promise every name's latest session daily and still needs exact scope/cadence approval.
3. Propose four 600-reserved slots / **2,400/day** for minimum all-valid capacity, or five / **3,000/day** for the demonstrated limited recovery case. This requires explicit approval of exact cohort, trigger times, quota/storage bounds and reviewed software hard-cap changes. No account-level provider entitlement follows from a workflow reservation budget.
4. Provider-supported bulk endpoints or a lower reservation policy require source documentation, bounded independent qualification and conservative concurrency/retry accounting. None is assumed available merely to make the arithmetic fit.

The original proposal estimated **about 3.0 MB of raw/normalized/action/receipt artifacts per 1,000-stock session**, excluding scoring workspaces, ledgers, master snapshots and backups. This is historical linear planning evidence, not a newly measured retention envelope. A source-qualified bounded pilot must measure actual incremental storage before a recurring capacity approval. No protected history or forecasts may be deleted to meet that envelope.

## Approval-ready remaining work

| Gate | Current status | Next action / owner |
| --- | --- | --- |
| Original cohort preservation | COMPLETE_VERIFIED for 633 forecast bodies and baseline model/configuration hashes in the isolated audit | Preserve while performing campaign-wide final baseline comparison. |
| Stable 500 daily publication and process recovery | PARTIAL | Operator/environment evidence; approved bounded source qualification if required. |
| Dated deterministic 1,000 identities | COMPLETE_VERIFIED as a preserved 20 October proposal | Fresh-master revalidation before any use; do not relabel it current. |
| Added 500 history/action/feature availability | BLOCKED_APPROVAL / BLOCKED_EXTERNAL_EVIDENCE | Exact bounded bootstrap approval, source scope/quota checks and genuine pilot receipts. |
| Full same-session 1,000 under current policy | BLOCKED_APPROVAL | Choose rotating lagged coverage or explicitly approve a new exact reservation/cadence/storage envelope. |
| New model eligibility and useful prospective performance | BLOCKED_EXTERNAL_EVIDENCE | Complete unchanged compatible vectors, genuine outcomes and independent registered acceptance. |
| Activation/deployment | BLOCKED_APPROVAL | Review concrete tested configuration/task changes and rollback before deployment; preserve original RELIANCE task. |

No runnable 1,000-stock production task or configuration was installed. Any future rollback preserves newly collected sources, forecasts and consumed request reservations; it never rewinds ledgers or removes unfavorable evidence. Existing TEST_ONLY capacity/selection/recovery contracts reside in `tests/unit/test_nse_dashboard_readiness.py`. Final campaign verification results are recorded in `14-end-to-end-verification.md`.
