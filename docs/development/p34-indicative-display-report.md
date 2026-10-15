# P34 private indicative quote display — verified results

15 October 2026; continued `p34-operational-readiness` from `1261977`.
This is the user's narrowly authorized display-policy follow-up. Strict current
quote acceptance has **not passed**. No portfolio, Decision Desk, historical
leaderboard, public demo or frozen research was rebuilt.

## Display policy and isolation

The original `quote()` VERIFIED validator is byte-for-byte unchanged, pinned by
SHA-256 `cec00eb40aa4c9c6f01ecbad2c3a55c4af6bc42b7bb5ae196ce505ea8326d5b1`.
Its `quote` field, rejection state, acceptance counters and financial consumers
remain separate from the new optional `indicative_quote` sibling.

`INDICATIVE_PROVIDER_QUOTE_TIME_UNCERTAIN` requires an authenticated provider
response, exact current NSE_EQ/type-EQ key/ISIN/symbol match, valid positive finite
prices, aware timestamps, last trade <= generation, and **receipt lower bound <
generation <= receipt upper bound**. All existing calibration checks still apply:
two independent sources, three valid samples each, agreement, bounded latency,
uncertainty, freshness and clock-discontinuity checks. Future beyond the upper
bound, stale, malformed, mismatched or missing/contradictory clock evidence fails
closed. There is no unconditional tolerance, timestamp rewriting, artificial
receipt delay or OS time-policy change.

The primary private stock chart labels the value **“Provider quote — timing not
independently verified”**, with original generation and last-trade values, receipt
interval, freshness, raw local receipt and uncertainty. It is neither VERIFIED nor
an official close. Change uses the documented V3 `prev_close_price` with Decimal
arithmetic. Unauthenticated public NTP remains a disclosed private research
assumption, not cryptographic time attestation or production security.

Internal financial cache copies omit the sibling entirely. Indicative prices
cannot feed portfolio marks/reviews, alerts, signals, rankings, ML, retained EOD
ingestion or execution. Same short proof lease; passive backend and React cache
removal; read-time expiry; explicit refresh only. The separately dated provider
EOD chart remains after expiry. Original ten-minute chart retention and source
separation remain. No private market-price payloads enter committed evidence.

One intermittent UDP timeout initially prevented all browser quote requests.
The transport now permits **one timeout retry per source**, at most eight UDP
probes per 30 seconds per process. Three valid samples per source and every
original acceptance threshold remain mandatory. Invalid packets, disagreement or
failed bounds are never discarded/retried into acceptance. No provider retry or
unattended probing was added. [Full policy](../operations/p34-quote-clock-policy.md).

## Genuine observations and browser acceptance

| Capability | Result | Genuine verification / remaining requirement |
| --- | --- | --- |
| Current identities | PASS | 2,697 verified current NSE_EQ/type-EQ identities; six exact identities tested |
| Strict VERIFIED quotes | **FAIL, 0/6** | Unchanged lower-bound chronology rejects uncertainty overlap; tighter independent evidence or a later genuinely eligible response is required |
| Separate indicative display | **PASS, 6/6** | RELIANCE, BAJFINANCE, TCS, INFY, HDFCBANK, ICICIBANK; one six-key quote batch, no provider retries |
| Indicative previous-close arithmetic | PASS, 6/6 | Actual LTP minus `prev_close_price`, exact Decimal comparisons; no strict accepted arithmetic claim |
| Provider EOD charts and indicators | PASS | All six latest returned daily candles **14 October 2026**; indicator dates checked against actual returned series |
| Authenticated compiled dashboard | PASS for classified viewing | All six actual stock routes checked against provider API values, warning, original timestamps, clock evidence and chart identity |
| Passive expiry | PASS | Dated EOD headline/chart restored, no automatic snapshot request |
| Daily scheduling | **NOT ACTIVATED** | Independent prerequisites below; not blocked by indicative intraday classification or model acceptance |
| Current ML/Top 5/10/20 | UNAVAILABLE, unchanged | Compatible basis/actions/calendar/dated peers/risk inputs and independent acceptance still required |
| Public synthetic demo | UNCHANGED | No private backend, prices or records published |
| Production security | **FAIL retained** | Strict container result remains independent; latest CI recorded below |

The direct batch generation was **17:04:44.082 IST**; raw local receipt
**17:04:43.897881 IST**, preserved. Independently calibrated receipt interval was
**17:04:44.072377–17:04:44.125710 IST**, width **53.333 ms**. Generation lies
inside, not before, that interval. All six trades preceded generation and were
same-date trades; generation after market close is not a new trade or final close.
The direct batch requested no candles. Browser chart checks were separate bounded
requests; the initial browser observation reported 11 provider GETs, including two
three-key quote batches/session OHLC and six candle requests. No full-NSE polling
or market-breadth claim follows.

Browser history is explicit:

* First run: **0 passed / 3 failed**, 39.61 s. NTP calibration unavailable; quote
  requests correctly skipped. A bounded timeout diagnostic identified transport
  loss. No fixture was substituted for genuine acceptance.
* Final compiled run: **2 passed / 1 failed**, 44.17 s, no retries/flaky passes.
  Strict six-stock acceptance failed **0/6** (15.65 s); six-route classified display
  passed (8.88 s); passive expiry/no-polling passed (15.52 s).

Screenshots, traces and videos were disabled to avoid market-payload retention.
Price-bearing failure DOM artifacts were removed; failure statistics and sanitized
timestamps remain. [Counts, original timestamps and preservation receipt](p34-indicative-display-verification.json).

## Independent daily EOD assessment

[Existing private source-use decision](../data/p34-private-upstox-use-decision.md)
and original RELIANCE **14 October** retained capture/idempotent replay remain
valid within their narrow private scope. Readiness/catch-up verified the accepted
revision with **zero network calls**. No new retained session was claimed here.

A separate fresh two-source clock measurement passed **date and elapsed-session**
checks. One official timing GET identified 15 October NSE trading from
03:45 to 10:00 UTC; receipt interval 11:41:57.409730–11:41:57.461666 UTC was clearly
after close and on the same local date. This does not establish exchange
publication/finality. That day's candle was still absent in the independently
tested dashboard, and today is not an eligible *past* session under the existing
D-1 worker. Intraday strict VERIFIED quote acceptance is **not a prerequisite**.

Scheduling stays disabled because the unattended worker lacks a wired and verified
**independent per-run clock guard**, and the **next eligible past-session release
has not been retained and replay-verified**. These are specific worker/readiness
requirements, distinct from permissions, ML acceptance and millisecond intraday
uncertainty. No scheduler/task/time-service policy was changed.

One actual software bug was fixed: an empty successful EOD response could become
an immutable capture and prevent later catch-up. It now returns
`EOD_CANDLE_PENDING` without saving a capture. A labelled TEST_ONLY test proves
empty → real fixture row → idempotent zero-GET replay, zero predictions. Wrong
session/multirow releases still reject before capture. Existing publication,
rights, calendar and canonical/model gates remain intact.

## Software, security and preservation verification

* Targeted P30/P31/P34 Python suite: **138 passed**, final run 4.24 s; original
  validator hash, interval boundaries, definitely future/stale/malformed/wrong
  source/instrument responses, clock replay, financial-consumer exclusion, passive
  purge, bounded timeout retries, pending EOD recovery and prior provider tests.
  Earlier overlapping runs are not additional distinct passes.
* Frontend full Windows run: **87 passed / 3 timed out**, 90 tests, 142.43 s.
  The three existing component cases hit the unchanged five-second limit.
  Focused diagnostic retry of components and terminal: **22 passed**, 10.33 s;
  overlaps the full run. No timeout increase or test weakening. Separate production
  build passed (14.14 s); typecheck and lint passed.
* Ruff, Linux/Windows mypy on changed provider scripts/tests, Bandit and diff checks
  passed. Full Linux/PostgreSQL/frontend CI results follow GitHub delivery below.
* Actual protected-credential source/build/response scan: **PASS**, 890 files,
  no credential values/encodings found. Foreign Origin rejected; PostgreSQL reader
  read-only, no write privilege, zero financial rows written.
* Frozen **2,485 artifacts** and **47 original alerts** byte-exact: PASS. Three
  historical metadata CRLF hash representations were verified against Git baseline;
  no financial artifact normalization or mutation. No research fits, holdout runs,
  backtests, model promotion or public-data release.
* Normal **8017** application stop/restart passed. New compiled index SHA-256
  `993c1cdb97884b3af84490df44109d6e70a04d39f0e6b6e5295a1751d16b5cb9`.
  Eight routes serve that build; five private API routes reject anonymous requests.
  Original account/password/personal records identical; only configured frontend
  root changed. Separate authenticated browser operator used port 8029 and isolated
  stores, never an original-password reset.

## Delivery

Branch **`p34-operational-readiness`**; no merge into main. GitHub run/commit results
will be recorded after push; no aggregate all-green claim is made.

Running local app: **http://127.0.0.1:8017/login**. Native CMD commands:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\start-p33-alphalens.cmd
```

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\stop-p33-alphalens.cmd
```

Remaining requirements are narrowly identified: stronger genuine time evidence
for VERIFIED quotes; per-run daily clock readiness and next-session capture/replay
before scheduling; independently compatible inputs and prospective acceptance for
ML; upstream patched dependencies for strict container security. None is presented
as a missing UI feature or a fabricated investment recommendation.
