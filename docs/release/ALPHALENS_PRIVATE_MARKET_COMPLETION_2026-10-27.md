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
makes zero manual provider or NTP calls. The later existing 20:30 trigger reserved
600 requests; that interrupted reservation remains retained, with 1,200 requests
remaining under the daily reservation limit. It is not reset or released.

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

The full Windows backend regression finished with **1,889 passed / 20 skipped**
in 1,571.56 seconds, exit zero. Linux/PostgreSQL verification is separately
reported below; Windows skips are not represented as Linux or live-provider tests.

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

### Verified code checkpoint

Released UI/code commit: **`0344f29d83edb9139333f74b43647eecca0d1594`**, pushed to
`alphalens-master-completion`. The deployment uses this compiled frontend with
the separately pinned collector source described above. Later documentation
commits do not replace the active collector checkout.

Fresh exact-commit CI is green:

- [Foundation and PostgreSQL](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40498685692):
  1,879 passed / 30 skipped in 278.83 seconds; Ruff, formatting, mypy, Bandit and
  the frozen dependency audit passed. The strict rebuilt container has zero
  HIGH/CRITICAL findings; image ID
  `sha256:8149d96d62c72ececfb6ec8a6f17654efe08614f77756554093378f1a3493460`.
- [Frontend](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40498685817):
  all 134 tests / 26 files, type checking, lint, production/demo builds, four
  isolated synthetic-demo browser cases and zero-advisory npm audit passed.
- The complete 168-commit reachable-history secret scan passed the unchanged
  exact fixture gate: zero verified secrets, three reviewed fixtures, zero
  unexpected findings. Raw scanner exit was 183, not a clean-scan claim. The
  sanitized receipt is preserved in private `ci-secrets-0344/receipt.json`.
- Six final-build private browser cases passed: four genuine saved-data flows
  (market/Top-N/history, full-master missing/insufficient cases, processing health,
  stock-specific saved LSTM/scenario evidence), plus two explicitly TEST_ONLY
  unavailable/error cases. Separate login/logout/session-privacy and authentication
  accessibility/invalid-login cases also passed in recorded runs.

The dashboard's current audit qualification now records fingerprint `98d635...`,
current container/secret evidence and `FIXED_AWAITING_LIVE_VERIFICATION` for the
routing change. It explicitly shows `BLOCKED_SECURITY` for the legacy watchlist's
43 advisories. Publication appends immutable audit/health records and advances
only the two dedicated health pointers; their earlier bytes are archived and
all earlier immutable reports are retained. No raw price, score, forecast,
reservation, model or original alert is replaced by this metadata refresh.

The separate reviewable watchlist proposal is
`.local-data/watchlist-runtime-readiness-20261027/plan-INACTIVE.json`, SHA-256
`1e0882e7b6e7abccda2bb80c22d6cf16c8902f6c3dc80db044fcf3bb460127d8`.
It changes only the watchlist task's command to its inactive private patched
wrapper; config arguments, directory, single RELIANCE identity, 08:30 IST trigger,
three-GET maximum, credentials, clock/power policies and shared ledger remain
fixed. Its 157 offline provider/calendar/quota/clock/replay tests passed. The
patched worker's import/help and wrapper's missing-argument fail-closed checks
passed. No collector run was manually launched and no task uses this proposal.
Its exact before/after XML, rollback commands and source/runtime hashes are in
the accompanying private `WATCHLIST_RUNTIME_READINESS.md`.

## Existing 20:30 scheduled run: actual evidence

The existing trigger launched run `c27f54ffcb5546e6892c2368e4c92278`; no manual
collector was started. The worker began at 20:30:33.439709 IST. Its initial
independent clock gate passed with genuinely new bounded observations, and it
entered session selection and EOD capture. This verifies the initial gate only;
it does not prove every later clock check would have passed.

| Observed event | 27 October IST |
| --- | --- |
| Fresh independent clock bounds | 20:30:35.897534–20:30:35.957206 |
| Kernel-Power 105 reports DC | 20:31:46.5958307 |
| Supervisor reports ancestor exited, worker interrupted, exit 125 | 20:31:47.653912 |
| Kernel-Power 105 reports AC | 20:31:48.6065449 |

Scheduler subsequently returned `0x8007042B`; the task returned to enabled Ready
with zero collector processes. There is no durable DONE receipt. Task Scheduler
Operational logging was already disabled; no logging policy was changed.
The exact termination initiator is not recorded. The two-second DC interval,
unchanged `StopIfGoingOnBatteries=true` setting and ancestor interruption are
consistent with a battery-policy stop, but that causal explanation remains an
inference. It is not evidence of a routing/parser failure.

The shared ledger remained at 5,019 attempts, including only the two earlier
watchlist requests on 27 October. Thus this scheduled run has **zero recorded
provider attempts and zero validated candles**. Intraday V3 routing was not
reached. Expected-session coverage remains 0/500 for 27 October; retained-session
coverage remains 499/500 for 23 October. No new forecast was generated.

Both deployed source hashes and task XMLs remain unchanged. No source rollback
occurred: the source-installation checks passed, and the observed interruption
does not establish a critical source/contract failure. The original plan treats
ancestor interruptions and independent clock unavailability as separate risks.
The new run evidence, original reservation and failure diagnostics are retained.
Derived local monitoring alerts and the unified health report were refreshed
without outbound delivery, provider requests or changes to original alert bodies.

The next existing opportunities are 21:30 and 22:30 IST. A finite read-only local
observer records task/process transitions, accounting and receipts without
starting a worker. Routing and fresh delivery remain
`FIXED_AWAITING_LIVE_VERIFICATION`; offline tests do not establish fresh candles.

### Separate inactive battery-settings proposal

The reviewable proposal is
`.local-data/nse-battery-policy-proposal-20261027/plan-INACTIVE.json`, SHA-256
`24698ecdfc693c333c904bc9a823e7865f7fdc6569eb2fdd8d3d1496cd19636b`.
It expires **27 October 2026, 21:15 IST**. It proposes only setting
`StopIfGoingOnBatteries=false` and `DisallowStartIfOnBatteries=false` on the NSE
task. All other task nodes and action remain identical; three offline negative
controls reject unrelated action, timeout and trigger changes. Exact original and
proposed XML, preconditions and conditional rollback are retained alongside it
in `BATTERY_SETTINGS_REVIEW.md`. It does not change Windows power policy or
authorize manual collection, new requests or reservation resets.

This proposal is **BLOCKED_APPROVAL**. The operator's AC-wait waiver applied to
source activation; earlier instructions explicitly preserved task settings.
Neither this proposal nor the separate watchlist proposal has been activated.
Stable AC throughout an existing scheduled run is an alternative that requires
no task modification. Neither alternative guarantees provider candle availability.

Public market-data display, expanded acquisition and paid deployment remain
`BLOCKED_APPROVAL` / `BLOCKED_EXTERNAL_DATA`; model acceptance remains
`BLOCKED_MODEL_EVIDENCE`. No public service or full production clearance is claimed.

The later [battery-policy execution and 21:30 follow-up](ALPHALENS_BATTERY_POLICY_FOLLOWUP_2026-10-27.md)
records the expired settings execution (no mutation) and the separate actual
21:30 clock-refresh failure. It supersedes the pending-run statements above for
that trigger; the next existing opportunity is 22:30 IST.
