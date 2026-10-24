# Top 5 / Top 10 / Top 20 research recommendations — 24 October 2026

Status: **PARTIAL** for experimental research shortlists; **BLOCKED_EVIDENCE** for validated AI recommendations. `accepted_current_rankings` remains zero and `NO_DEMONSTRATED_EDGE` remains explicit.

The existing five-session model scorer sorts actual eligible saved scores descending with exact instrument key as the deterministic tie breaker. The authenticated research endpoint supports bounded list sizes, including 5, 10 and 20, and optional saved user-preference filtering. It returns fewer rows when fewer qualify. Evidence includes company/symbol, dated observed price, model score, observation/inference dates, volatility/drawdown, exact features, applicability, explanations and missing evidence. Daily-price-change evidence belongs to the saved market/stock-detail observation views; an unsupported expected-return or calibrated probability field must remain absent.

An explicit `rank_policy=risk_adjusted` option orders by classifier score minus saved daily-return standard deviation, weight one, then exact security key. Original `score` is unchanged; `ranking_value` is the ordering value, never a probability or expected return. Missing/nonfinite/negative/boolean daily standard deviations are excluded and counted. The default `model_score` ordering preserves the original interpretation. This [pre-registered policy](risk-ranking-policy-v1.md) is an unvalidated engineering assumption; no claim of better investment results follows. Response `ranking_policy` identifies the formula, penalty weight, excluded-risk count and evidence classification. Descriptive 10/20 views remain descriptive irrespective of this parameter.

A verified defect was corrected: `_candidate()` already marked observations older than seven calendar days `STALE`, but the route continued showing those rows in the current five-session shortlist. The route now removes those rows **before preference filtering and pagination**. It preserves immutable scores, ledgers, stock history and descriptive 10/20-session views.

The response exposes `recommendation_eligibility`:

| Field | Meaning |
| --- | --- |
| `policy` | `EXCLUDE_STALE_SAVED_FIVE_SESSION_CANDIDATES_V1` |
| `maximum_observation_age_calendar_days` | Existing inclusive threshold: 7 |
| `saved_candidates` | All validated saved candidates before freshness filtering |
| `eligible_candidates` | Candidates within that threshold, before preferences |
| `stale_excluded` | Stale rows removed from this response; zero in descriptive views |
| `applied` | True only for the supported five-session ML view |
| `accepted_ml` | Always false |

Seven calendar days is a conservative inherited research-display rule, **not evidence that the observation is the latest official completed session**. The separately reported observation date, collection coverage and source/session gates remain necessary. The current 302-score snapshot is dated 19 October; no new provider request or current forecast was triggered by this campaign audit.

`workers/nse_market/forward_cohort.py` and the pre-registered `docs/development/nse-expanded-forward-protocol-v1.md` already freeze genuine global Top 5/10/20 selections and baselines before future entry. Snapshot IDs and per-security forecast hashes bind the declaration. Evaluation requires every declared member to mature; it never reranks survivors or averages shard Top-N statistics. User preferences do not retrospectively change that evaluation cohort.

The targeted API regression passed **15 tests in 85.34 s**, including three parametrized Top-N cases verifying that a stale highest-score row is excluded, a seven-day row remains eligible, fewer than N rows are returned, all-stale lists are empty, saved input remains unchanged, descriptive history persists and provider/accepted-ranking counts stay zero. A further test covers risk ordering, deterministic ties, unchanged original scores, invalid-risk exclusions and strict policy validation. These TEST_ONLY passes do not establish independent model acceptance.
