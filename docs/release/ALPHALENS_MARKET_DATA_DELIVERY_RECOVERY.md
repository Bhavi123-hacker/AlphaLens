# Market-data delivery investigation and isolated correction

Investigation date:26 October2026. Starting commit:
`6a5b73af588624cadc1e464d8ca90b5944421893`.
Delivery target: `alphalens-master-completion`; no main merge.
Private application: **http://127.0.0.1:8041/nse-market**.

**A current-day request-routing defect is confirmed and corrected in an isolated,
offline-tested checkout. It is not activated in the live collector.** The active
checkout, patched Python installation, launcher, clock protections and both task
definitions remain unchanged. There are still no genuine26 October candles or
fresh predictions. Endpoint correction does not establish provider availability.

## 1. Expected equity session

26 October2026 was an expected regular NSE equity trading session, based on
the [official2026 Capital Market holiday circular](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf),
the [current NSE holiday list](https://www.nseindia.com/resources/exchange-communication-holidays?apiversion=v2)
and the saved official provider timing fact for that date. The October exchange
holidays listed are2 and20 October;26 October is not listed. This conclusion
does not rely on the weekday alone. No26 October special-session amendment was
located in targeted official-source searches; those searches are not a complete
inventory of every possible unscheduled exchange event.

The [official equity timing table](https://www.nseindia.com/static/market-data/market-timings)
gives normal trading09:15–15:30 IST, closing15:40–16:00 and trade modification
until16:15. The retained26 October fact is03:45–10:00 UTC, matching normal equity
hours. At the20:30 collection trigger, the expected latest completed session was
therefore26 October, while the latest retained price session was23 October.
Exchange completion does not establish a provider's publication deadline or
per-security tradability. No calendar or cutoff change is justified by this audit.

Five original public official documents and their hashes are privately archived
under `.local-data/market-data-delivery-20261026/calendar-docs/`; the source manifest
records retrieval times separately from market-ingestion clock evidence.

## 2. Exact requests and retained responses

Pinned source at the starting commit constructed:

```text
GET /v3/historical-candle/{percent-encoded instrument_key}/days/1/2026-10-26/{from_date}
```

All keys were configured `NSE_EQ|ISIN` identities. The pipe is encoded once as
`%7C`; the date ordering is ending date followed by starting date. Daily unit and
interval, bounded ranges and key construction match the documented historical
route. The defect is the same-day route choice, not reversed dates or double encoding.

| Cohort | Genuine last saved candle | Reconstructed inclusive range |
| --- | --- | --- |
| SHERVANI, `NSE_EQ\|INE011D01013` |19 October |20–26 October |
| Other249 securities in the20:30 batch |23 October |24–26 October |
|250 different securities in the21:30 batch |23 October |24–26 October |

These are reconstructed from pinned request code and genuine pre-run observations;
original wire URLs were not retained. Null chart placeholders for21–23 October
are not SHERVANI candles and were explicitly excluded from reconstruction. An
initial private draft using those placeholders is preserved with its correction,
not silently represented as exact evidence.

All250 original20:30 bodies, and subsequently all500 bodies across both batches,
were individually checksum verified. Every body is:

```json
{"status":"success","data":{"candles":[]}}
```

Exact body SHA-256:
`83d511d64ffda7e4c950b5f2c8f95130e5fa0c872af9b85a70e1a6bf3616428f`.
There are zero nonempty arrays lost to parsing and zero retained malformed/error
bodies in this publication-pending set. The normalized result is genuinely empty.

The old publication-attempt format did not retain an explicit HTTP status or
request context. Its code path requires ACCEPTED/200 before writing this receipt,
and the shared ledger records succeeded attempts; that is corroborating derived
evidence, not a recovered wire capture. No401/403/429 failure explains these
retained bodies. Success on the historical route does not prove operator
entitlement or actual availability on another endpoint. No credentials, headers
or authenticated provider URL were printed or committed.

Current master identity eligibility does not prove historical trading status,
corporate-action completeness or that SHERVANI should have a candle. Such issues
cannot be inferred away because all500 return the same empty envelope.

## 3. Confirmed defect and remaining causal uncertainty

[Upstox Historical V3](https://upstox.com/developer/api-documentation/v3/get-historical-candle-data/)
defines an inclusive ending date but directs current-day retrieval to Intraday V3.
[Intraday V3](https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data/)
supports the current trading day with `days/1`, without arbitrary date parameters.
The existing qualified V2 collector already makes this distinction; the expanded
500-stock daily path always selected historical candles.

**Confirmed software issue:** the expanded collector omitted that current-day
selection rule. All499 ordinary reconstructed24–26 October ranges contain a
weekend followed by the current day, making the mismatch a strong explanation
for the systematic empty responses. **Not established:** that every current-day
historical request must always be empty, an exact historical-publication time,
or that the intraday alternative would have returned an acceptable candle for
each security. The reviewed documents promise no exact post-close publication
SLA or exchange-final adjustment status. No live comparison request was made.

No substitution from quotes, fabricated OHLCV, minute-bar aggregation, date
rewriting, relaxed timestamp acceptance or invented corporate-action evidence
is part of the correction.

## 4. Minimal isolated implementation

To honor the instruction to preserve the active patched collector, implementation
and tests use this separate checkout:

```text
D:\al-research\p28-worktree\.local-data\market-data-delivery-20261026\candidate-worktree
```

The original `D:\al-research\p28-worktree` stays at the reviewed starting commit.
New commits are delivered to the requested remote branch from the isolated
checkout. Updating that remote branch does not deploy source into the active
checkout. There is no environment installation, scheduler cutover or application
restart. The old third-cutover approval is not reused to activate new source.

The correction in `workers/nse_market/daily.py`:

- Selects one `intraday_candles` GET for a target matching the independent guard's
  IST date; past-session requests keep their existing historical date ranges.
- Makes no historical fallback request, automatic retry or all500-stock replay.
  Stock-count limits, shared request accounting and reservation ceilings remain intact.
- Requires the same official completed-session fact and existing receipt-time,
  OHLCV, identity, uniqueness and corporate-action checks. Current-day data must
  contain exactly one target-session daily candle received after official close;
  pre-close, wrong-date or duplicate data is not accepted. This does not certify
  the provider's finality or rule out a subsequent revision.
- Describes a current-day response as that day only, preserving older missing
  history. Missing lookback slots still block model features; no older bar is invented.
- Retains operation, unit, interval, target and actual date parameters in new
  accepted-response metadata, and explicit status/request context in new empty
  receipts. Original receipts remain untouched. `engine._response` adds only an
  optional request-context field; existing historical callers retain their format.

The dashboard correction separates model inference time, original forecast
recording and original entry session/opening. Missing original times stay
unavailable. Viewing a saved ranking never recreates or backdates a forecast;
an elapsed entry is explicitly historical. Numerical scores, ranking policy and
forecast bodies are unchanged. Existing Collection Health already separates the
expected completed session from the latest retained historical coverage.

Older gaps, including26 October if it later becomes historical, may still need
separately approved bounded catch-up. The isolated correction does not add a
second request per stock or silently expand recurring acquisition to fill gaps.

## 5. Offline verification

The committed empty-response fixture contains the exact retained empty body and
its lineage hash, with no market prices, identity-sensitive headers or secrets.
Nonempty candles used for tests are constructed **TEST_ONLY** values; they are
not evidence of actual intraday availability or model performance.

| Check | Result |
| --- | --- |
| New routing/publication regressions |17 passed; final focused rerun12.99 seconds |
| Relevant Windows backend/provider/clock/scheduler regressions |457 passed in78.10 seconds |
| Python lint/format/type checks |PASS; mypy438 source files |
| Targeted Bandit checks |PASS |
| Frontend unit/component suite |132 passed across26 files |
| Frontend type checking, lint, private and synthetic builds |PASS |
| Frontend dependency audit |Zero reported vulnerabilities |
| Active patched-runtime dependency audit |Zero advisories; installation unchanged |
| Fresh protected-artifact scan |2485 files/8505278241 bytes and47 original alerts checksum verified |

Coverage includes the exact empty replay, current versus historical routes,
single-GET behavior, strict empty/wrong-date/multiday/duplicate rejection,
official-close and receipt-time checks, UTC/IST rollover, missing lookback,
bounded requests/stocks, per-security failure isolation and zero-GET immutable
replay. These tests perform no provider, NTP, scheduler or real-model request.
Initial literal-typing/test-import errors were corrected; no check was weakened.

Exact final-commit Linux/PostgreSQL regression, container, dependency and full
historical secret-scan results are retained separately in the private final
attestation after CI completes. Do not treat a pending CI run as passed.

## 6. Observed live runs and unchanged current data

This investigation passively inspected existing authorized triggers; it did not
start a collector or make an extra market-data/time-source request.

| Existing trigger | Actual evidence |
| --- | --- |
|20:30 IST | Run `eafeaaa1f6f44b83a82ac63fb1bf36fd`; all exits0;600 reserved/251 actual;250 empty replies; zero accepted candles |
|21:30 IST | Run `bd3661ba454c416a9b6034ac56a6b61a`;600 reserved/251 actual; other250 empty replies; supervisor ancestor-exit interruption125 at16:10:12.161069 UTC; Scheduler `0x8007042B`; terminal missing |
|22:30 IST | Run `42825678795f45049755ab6d6ecfdcd7`; initial `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`; all exits1; zero GETs and no reservation |

The21:30 clock refresh has genuinely new observations and retained continuity
acceptance before collection. Its later interruption is separate. AC loss at
16:10:11.0572018 and restoration at16:10:13.0831103 UTC bracket the interruption,
but the specific termination initiator is unproven. That missing terminal is
preserved; no successful completion or recovery receipt is manufactured.
The22:30 calibration's specific rejection detail was not retained, so neither a
clock jump nor stale-evidence reuse is established. Clock validation stays strict.

After22:30, the task is enabled, Ready, zero matching collectors, Scheduler
result1. Both task definitions and the installed patched runtime remain unchanged;
no rollback was performed under this preserve-runtime investigation scope.

| Current measurement | Genuine value |
| --- | --- |
| Expected latest completed / latest retained session |26 October /23 October |
|26 October coverage |0/500;500 queried with empty arrays |
| Latest retained-session coverage |499/500 for23 October; SHERVANI's latest genuine candle19 October |
| Searchable identities / saved price histories |3207 /500 |
| Saved experimental scores |312; observation23 October, inference25 October15:09:11 UTC |
| Fresh26 October observations / predictions |0 /0 |
| Forecast records / unique decisions / qualified outcomes |945 /914 /0 |
| Current forward accuracy |NOT_YET_MEASURABLE |
| Actual26 October GETs / reserved capacity consumed |502 /1200 |
| Remaining reservation capacity |600; not authorization for a manual run |

Saved candidate entry sessions are26 October. Their original entry opening has
passed. New inference needs fresh compatible features, a still-future eligible
entry and unchanged model/source gates; those conditions are not established.
The saved312 scores are not reissued as fresh predictions. No accepted model or
investment edge is claimed.

## 7. Next opportunity and unresolved gates

The next unchanged authorized trigger is **27 October2026 at20:30 IST /15:00 UTC**.
Its execution still depends on the existing power, operator, clock and quota
checks. Neither remaining capacity nor a prepared fix authorizes a manual probe.
Provider publication at that time is not guaranteed.

| Gate | Verdict |
| --- | --- |
| Calendar,250-response audit and expanded500-response reconstruction |VERIFIED_COMPLETE |
| Minimal request/timing correction and offline regression |FIXED_AWAITING_LIVE_VERIFICATION |
| Activating new source in the preserved active checkout |BLOCKED_APPROVAL |
| Genuine same-day corrected-endpoint candle availability/finality and entitlement |BLOCKED_EXTERNAL_DATA |
| Complete fresh-data-to-prediction workflow |BLOCKED_EXTERNAL_DATA |
|21:30 ancestor termination/missing terminal and22:30 unavailable clock evidence |BLOCKED_EXTERNAL_DATA; precise initiators remain unresolved |
| Independent model acceptance and measurable forward accuracy |BLOCKED_MODEL_EVIDENCE /BLOCKED_EXTERNAL_DATA |

Before activation, review the exact delivered commit/diff, preserve the installed
runtime and task XML, require idle Ready/zero processes and qualify the new source
identity. Operator approval must explicitly allow updating the active checkout;
no scheduler action, trigger, quota, credential or environment change is proposed.
Any additional live verification request needs separate exact scope approval.
Keep original reservations, forecasts, models,2485 research files and47 original
alerts intact. Public deployment remains unauthorized and is not attempted.

Private primary evidence and final attestations:
`.local-data/market-data-delivery-20261026/`. Active application verification and
preservation evidence are kept separately from isolated-code fixture results.
