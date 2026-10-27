# AlphaLens private market workspace and routing activation — 27 October 2026

Private application: http://127.0.0.1:8041/nse-market.

This continuation preserves the existing application and makes its saved-data
workflow easier to use. It does not certify fresh provider delivery, predictive
edge, complete daily NSE coverage or public-data rights.

## Authorization and collector source scope

The operator's latest instruction explicitly removed waiting for AC stability.
Decision D97 records that amendment separately from the original sealed plan;
no AC-stability pass or Windows power-policy change is claimed.

Original protected plan:
`.local-data/intraday-v3-activation-20261026/candidate-review-final/sealed-plan/plan.json`.
SHA-256: `aecdd593308164063ad800c5408875d6b700d613e85386be30011c58585c242a`.
Preparation commit: `0c6588185f37314a33c201c0a7b6a71b3344b671`.
Active collector checkout: `6a5b73af588624cadc1e464d8ca90b5944421893` plus
only the reviewed `engine.py` / `daily.py` modifications. The active checkout is
intentionally not fast-forwarded to the development checkout.

The source replacement uses the reviewed primitive, engine first then daily,
with fresh exact task XML, zero-process, policy, accounting, source-set and hash
checks before and after each replacement. Conditional rollback restores daily
first then engine and retains the same patched interpreter. No task, interpreter,
provider request, quota, credential, clock, model or protected-data change follows.

Observed runtime fingerprint after the two exact replacements:
`98d635dc30737ac7c034fbcd6bd463ac4a4553878e4efac906ee4f4701c05eac`.
Fresh runtime verification checks 15,387 package RECORD files and the installation,
Python and package-version identities. The activation execution report and all
before/after evidence are retained privately under
`.local-data/intraday-v3-activation-amended-20261027-1635`.

Activation completed its postconditions at 16:51:48 IST, before the 20:15 IST
deadline. Both deployed hashes match the sealed artifacts, all 19,503 immutable
market-store files and original forecast bodies remained unchanged, task XMLs
and accounting matched, and offline imports resolved the active files. No source
rollback occurred. This proves source installation, not live provider delivery.

The existing 500-stock task keeps 20:30/21:30/22:30 IST triggers, 250 securities
and 600 reserved GETs per run, 1,800 per day, the 60-minute cooldown and its retry
policy. The watchlist task is unchanged. Original interrupted reservations remain
retained. Before activation, the shared attempt ledger contained 5,019 attempts,
including two already-authorized watchlist attempts on 27 October; this work
makes zero provider or NTP calls. Today's collector reservations remain zero
until an existing trigger actually reserves capacity.

## Private market workspace

The compact watchlist and adjacent chart workspace use
[Upstox Pro Web](https://upstox.com/upstox-pro-web-online-trading/) as a workflow
reference. AlphaLens retains its own interface and private research restrictions.
Search, gainers, losers and volume leaders read genuine saved observations.
Selecting a row opens its candlestick/line and volume preview without a provider
request. The preview shows source, saved session, freshness and OHLCV; a full
stock-research link preserves identity, feature exclusions and forecast history.
The responsive layout, keyboard-scrollable list, movement arrows and signed colors
make the evidence easier to inspect. No order or trading action is added.

The new compiled build and configuration are additive:
`.local-data/completion-release/web-build-market-workspace-20261027-v3` and
`.local-data/completion-release/qa-config-market-workspace-20261027-v3.json`.
Only `frontend_root` differs from the prior private app configuration. Port 8041,
authentication, database targets, operations and provider-acquisition restrictions
are preserved. The old compiled build and configuration remain available for a
cooperative rollback. The final private attestation records deployment and browser
verification. The running shell serves `index-CyuHA4qJ.js`; the compact chart
uses a shorter INR axis label and 420-pixel height while preserving source basis.

Browser verification found an existing mobile overflow caused by a 64-character
model ID in the shortlist paragraph. Targeted wrapping preserves the full ID.
The final actual desktop/mobile page widths are 1600/1600 and 390/390; workspace
accessibility scans report zero violations on both. No global clipping or relaxed
assertion is used. A genuine RELIANCE preview loads 120 saved candles, not fixtures.

An intermediate cooperative-stop CLI returned exit 2 while its matching owned
instance actually reached STOPPED. The procedure retained the failed result,
verified the original PID absent and port 8041 unbound, then started the next
configuration. It killed no processes and did not claim that command passed.
The final cooperative restart returned `OWNED_INSTANCE_STOPPED`, verified nonce
continuity and the vacant port, and started the final configuration. The earlier
rejection's precise exception was not retained; no root cause is invented.
Original and intermediate builds/configurations remain preserved.

## Measured saved-data and ML coverage

| Measure | Verified retained evidence |
| --- | ---: |
| Searchable dated common-equity identities | 3,207 |
| Configured recurring collection universe | 500 |
| Equities with saved price history | 500 |
| Latest retained session | 23 October 2026 |
| Latest retained session observations | 499 / 500 |
| Compatible genuine saved experimental predictions | 312 |
| Original forecast records / unique decisions | 945 / 914 |
| Qualified forward outcomes | 0 |
| Independently accepted models | 0 |

These are dated counts, not today's freshness or daily update success rate.
All 312 saved candidates match their original immutable forecast's model, source,
feature hash, feature vector, target and score. Existing numerical replay has
zero maximum feature or score error. Predictions use 23 October observations;
the inference timestamp is 25 October 15:09:11.372907 UTC. They are not relabeled
as newly created forecasts. Top 5/10/20 ranks every eligible saved prediction
before pagination, with no arbitrary 302-security cap.

Five sessions is the trained target. Ten/twenty-session controls remain descriptive
research views. The risk penalty is an unvalidated engineering assumption, and
model scores are uncalibrated. `EXPERIMENTAL_RESEARCH` remains mandatory.

Of the 188 configured securities without compatible latest saved scores, 152
have known corporate-action lookback exclusions, 35 lack required lookback slots
and one lacks the latest observation. Another 2,707 searchable identities have
no saved price history. The UI must display unavailable evidence for these cases.
SHERVANI remains a genuine unresolved missing observation; a usable 23 October
candle is not invented and eligible-universe coverage is not redefined as 100%.

Forward accuracy is `NOT_YET_MEASURABLE`. All 914 decisions lack required qualified
target-price slots; the newest 312 also lack five proven future official session
dates. Six decisions have known target-action exclusions. These diagnostic
categories overlap. Missing 26 October observations are not recovered by routing
27 October requests to the current-day endpoint. Genuine saved evidence and the
existing deterministic maturation job must supply any future outcome.

## Verification and release boundaries

Fresh local checks passed: 134 frontend tests across 26 files, TypeScript, ESLint,
production build, zero npm advisories, 122 ML/forecast/outcome tests and 57 routing/
activation tests. No financial/model assertion or test timeout was weakened.
The first parallel frontend run had two timeouts; the unchanged suite passed
with one worker. Both results are retained rather than claiming the first run passed.

Fresh collector dependency audit reports zero known advisories. Preservation
verified 2,485 frozen research files, 47 original alerts, all 945 original forecast
bodies, and 19,503 immutable market-store files before activation. PostgreSQL
17.11 passed a read-only transaction probe. Thirteen authenticated saved-data
HTTP checks returned 200, and unauthenticated access returned 401.

The excluded watchlist task still calls `p30-daily-update.cmd`, then
`project-python.cmd`, invoking the original shared `.venv`. A fresh separate
audit found **43 advisories across three packages**, rather than the historical
41. Therefore dependency clearance is not claimed for every scheduled task.
Evidence and a separate preparation proposal are under
`.local-data/watchlist-runtime-readiness-20261027`. No watchlist task or launcher
is modified; an exact separate approval remains necessary for its cutover.

The unchanged preparation commit previously passed 1,879 backend tests / 30 skips,
132 frontend tests, full historical secret disposition with zero verified secrets
and three exact reviewed fixtures, and a strict container scan with zero
HIGH/CRITICAL findings. Those are prior results, not fresh results for new UI code.
The final delivery attestation records the exact new commit and its CI results.

The next existing collection opportunity is 27 October 20:30 IST. A finite local
read-only observer may record task/process transitions, request accounting,
terminal receipts and data publication; it never starts a worker or calls a
provider. Live routing, clock acceptance, worker exit and genuine candle delivery
remain `FIXED_AWAITING_LIVE_VERIFICATION` until actual receipts establish them.
Source installation and offline fixtures alone do not establish a fresh candle.

Task battery restrictions remain unchanged. A future AC interruption may still
terminate a scheduled worker. The previous ancestor interruption and independent
clock-unavailable failure remain separate risks; routing does not resolve them.
Public market-data display, expanded acquisition and paid deployment remain
`BLOCKED_APPROVAL` / `BLOCKED_EXTERNAL_DATA`; model acceptance remains
`BLOCKED_MODEL_EVIDENCE`. No public service or full production clearance is claimed.
