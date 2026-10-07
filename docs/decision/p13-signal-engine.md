# P13 decision-state engine

Authorized by D62-D64 after approved P12 28070df. The canonical states describe
the configured decision policy, not a guarantee, order or live recommendation.
TEST_ONLY — NOT A PERFORMANCE CLAIM. Production data clearance remains OPEN and
market-data use NOT_CLEARED. All thresholds are DEVELOPMENT_ASSUMPTION; P11/P12
engineering weights remain uncalibrated against genuine NSE history.

## Evidence and lifecycle

The pure offline engine consumes immutable, validated P12 ranking and P11 risk
snapshots. Exact security/session/horizon, cutoff, classification, policy and
P5/P6/P4 identities must match, as must risk/quality/prediction references.
P12 determines historically known candidates; an unknown future catalog name is
rejected rather than added to the decision output. There is no price/label join,
model fitting, current-constituent query or P7 target input. The trusted-local
artifact boundary is the same as P11/P12: hashes prove integrity, not authenticity.

| State | Meaning and required context |
| --- | --- |
| WATCH | Known candidate lacks a completed setup; availability separately exposes exclusion/unavailable evidence. |
| SETUP_FORMING | Eligible candidate passes basic risk/freshness and favorable score/prediction checks, but entry checks or confirmation remain incomplete. |
| ENTRY_SIGNAL | All configured entry checks and confirmation observations pass, or previously confirmed entry meets the separate retention checks. No position is inferred. |
| HOLD | An explicit active synthetic TEST_ONLY position is evidenced and every continuation check passes. |
| TAKE_PROFIT_REVIEW | Same continuation checks pass and the supplied synthetic position includes a contemporaneously available review request. No realized-profit estimate or automatic exit is invented. |
| EXIT_SIGNAL | An evidenced active synthetic position fails continuation requirements. It does not prove an exit happened. |
| EXITED | The supplied synthetic position includes an exit event whose time and availability precede the decision. |

MARKET_OPPORTUNITY_STATE and POSITION_DECISION_STATE are distinct. P15 owns
actual user holdings. P13 accepts only explicitly labeled synthetic TEST_ONLY
lifecycle records, with event and availability chronology; it stores no quantity,
cash, entry execution, user holding or broker integration. Later position records
are invisible. Latest unambiguous known context is used; conflicting timestamps
are rejected. ENTRY to HOLD requires entry evidence; EXIT_SIGNAL to EXITED requires
exit evidence. Direct lifecycle reconstruction also works when earlier signal
history is absent but the explicit position event is evidenced.

## Versioned policy and transitions

Signals are independent for 1/5/10/20 sessions. No preferred horizon is inferred.
An optional configured review horizon must be one of those horizons and no longer
than the model horizon. All serialized thresholds carry DEVELOPMENT_ASSUMPTION.
They were not optimized against TEST_ONLY results.

Initial entry requires rank <=5, adjusted score >=0.30, probability >=0.60,
estimated return >=0.005, risk <=MEDIUM, model uncertainty <=0.50, VALID source
quality, SUFFICIENT price history, EOD_COMPLETE evidence, rank eligibility and no
corporate-action uncertainty. Both predictive tasks must be present. Normal v1
model-selection evidence is insufficient, so the model-evidence entry check
fails: neither TEST_ONLY nor research results create an apparently validated entry.

The positive relative-momentum reason uses the serialized
positive_momentum_percentile threshold (initially 0.75). It does not independently
qualify entry. All continuation checks, including probability, freshness, history
and historical eligibility, have explicit invalidation conditions.

The explicit test_only_state_demonstration policy can exercise entry/holding
mechanics on constructed TEST_ONLY evidence. It does not change P11/P12 model
confidence, clear research/production gates, or claim validation. Signal confidence
is categorical TEST_ONLY_DEVELOPMENT_EVIDENCE only when all shared checks pass;
otherwise INSUFFICIENT_EVIDENCE. Model probability, confidence, risk and opportunity
score remain separate. Non-TEST_ONLY inputs cannot enable demonstration mode.
Default approved-artifact replay deliberately produces WATCH rather than weakening
risk, corporate coverage or confidence to obtain favorable signals.

Two consecutive available qualifying observations confirm entry by default.
They are observations, not invented exchange sessions; gaps over seven calendar
days reset confirmation. Compatible history means strictly earlier date/cutoff,
same policy/horizon/classification and historical universe definition. Latest past
state is recorded; future/current, incompatible and duplicate history cannot supply
confirmation. The retention thresholds are rank <=10, score >=0.20, probability
>=0.55 and return >=0, with all essential shared checks unchanged. Confirmed
ENTRY may persist within this band, preventing tiny score changes from flapping.
Below retention it may deteriorate to SETUP_FORMING/WATCH without a position.
Setup can deteriorate to WATCH. HOLD/REVIEW can deteriorate to EXIT_SIGNAL; a
later evidenced closed position becomes EXITED. Every transition stores a trigger.

## Output, freshness and invalidation

SignalSnapshot pins full policy/version, ranking/risk/prediction/model/evaluation
IDs, feature/canonical/universe versions, cutoff, symbol known at decision time,
state/previous state, confirmation count, all entry and retention checks, scores,
quality, risk, ordered positive/negative/transition reasons and position context.
SHA256 covers the complete versioned snapshot excluding its own ID. Changed
policy/evidence creates a new ID. Invisible future evidence cannot alter it.
Immutable signal JSON and checksum manifests provide deterministic history;
loading validates the whole schema/identity/classification/checksum.

Risk limit, uncertainty, rank, score, expected return, source quality, corporate
actions and missing model evidence are explicit machine-readable invalidation
conditions, retaining threshold values. Price-level invalidation is UNAVAILABLE:
no approved technical stop/target policy exists. No price target is fabricated.
Expected return is MODEL ESTIMATE — NOT GUARANTEED, never promised profit or an
order. Signal confidence is not a percentage or probability of loss.

Freshness distinguishes evidenced historical EOD_COMPLETE, STALE and UNAVAILABLE.
Excluded/missing risk retains WATCH with UNAVAILABLE analysis; it never assumes
LOW risk or implies a fresh/live opportunity. Source timestamps remain visible.
No current/live market data, charts, portfolio, paper trading or frontend is added.

`alphalens-signals evaluate --ranking RANK_DIRECTORY --risk RISK_DIRECTORY
--security TEST:ALPHA --output data/signals` emits UTF-8 JSON with the prominent
fixture disclaimer. Optional policy/history/position arguments accept trusted
local files. `python -m scripts.verify_p13_test_only` replays approved P12/P11
artifacts twice and checks persisted identities/history. No predictions or data
are fabricated by replay. Authored unit evidence is separately marked TEST_ONLY.
