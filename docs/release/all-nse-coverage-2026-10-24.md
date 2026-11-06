# Saved NSE equity coverage — 24 October 2026

| Capability | Status | Evidence and limit |
| --- | --- | --- |
| Entire verified saved ordinary-equity master is searchable | VERIFIED_COMPLETE | 3,188 identities, independent of the configured 500-security collector. Pagination bounds response size and does not restrict the search universe. |
| Known security detail without a model or saved prices | VERIFIED_COMPLETE | Authenticated detail returns the exact saved identity, explicit unavailable prices/history/features and zero provider requests. Unsupported instruments have an explicit rejection classification. |
| Compatible saved inference and Top 5/10/20 scope | VERIFIED_COMPLETE | All eligible saved model outputs are considered before pagination. A 725-candidate offline test selects the highest candidate beyond position 500 for each requested list size. |
| Complete current NSE market-data coverage | BLOCKED_EXTERNAL_DATA | The master and market observations are dated; no new provider calls were authorized or made. Discovery is not proof of current listing, source access or data availability. |
| Expanded recurring acquisition | BLOCKED_APPROVAL | Existing 500-security task, 250/run and 600/run/1,800/day reservations remain unchanged. |
| Fresh latest-session predictions | BLOCKED_EXTERNAL_DATA | Latest retained observations are 21 October; saved predictions refer to 19 October. No new or backdated forecast was created. |
| Independently accepted investment recommendations | BLOCKED_MODEL_EVIDENCE | All rankings remain experimental research; no calibrated probability, investment edge or accepted production model follows from compatible numerical inference. |
| Sector / market-cap stratified acceptance | BLOCKED_EXTERNAL_DATA | The verified saved identity master does not supply authoritative sector or market-cap observations. These attributes were not guessed. |

## Measured denominators

Read-only verification at `2026-10-24T12:06:15.514819+00:00` used the checksum-verified
22 October Upstox master and the existing immutable saved-market publication.
The private numeric receipt is
`.local-data/completion-blockers-20261024/all-nse-coverage.private.json`.

| Measurement | Actual evidence |
| --- | --- |
| Master observed | `2026-10-22T05:15:49.589808+00:00` |
| Master snapshot | `dc8bc785edf2a084f83574144695125f6dac4ef5761c21fe8fd18de4c4148495` |
| Supported ordinary common equities | **3,188** |
| Searchable supported equities | **3,188** |
| Supported series | EQ 2,354; BE 223; BZ 29; SM 481; ST 100; SZ 1 |
| Other discoverable cash-master identities | 6,640 excluded records; these are not additional supported ordinary equities |
| Equities with genuine saved price history | **500** |
| Latest retained session | **21 October 2026** |
| Equities represented on that retained session | **248 / 500**, or **49.6%**; this is retained coverage, not daily job success |
| Sufficient compatible features on that session | **156**, measured independently of dated saved scores |
| Compatible preserved model outputs | **302**, observation session **19 October**, generated `2026-10-20T17:03:12.327501+00:00` |
| Model outputs for the latest retained session | **0** |
| Eligible dated experimental ranking candidates | **302**, under the existing seven-calendar-day display-age and valid-risk policy |
| Top 5 / 10 / 20 returnable dated candidates | **5 / 10 / 20**, selected across all eligible saved outputs |
| Independently accepted predictions | **0** |
| Daily update success rate | **Unavailable** from this coverage projection; the separate collection-status command reports actual run/session evidence |

Do not add feature and prediction counts: they have different dates. The application
now displays both dates and the zero latest-session prediction count explicitly.
The existing Top-N view remains a **dated experimental** research comparison.
It does not publish new current recommendations.

The master is beyond its existing 24-hour action expiry. This no longer erases
saved identity search. It still blocks current provider identity actions through
the unchanged fresh-master checks. Future-dated discovery snapshots are rejected.

## Exclusions

Within the 3,188 supported saved identities:

- **2,688** have no saved market price observations.
- **252** priced equities lack the latest retained 21 October observation.
- **2,886** have no compatible saved prediction.
- Latest feature exclusions are **76** known corporate-action lookback exclusions,
  **16** missing lookback slots and **252** missing latest observations.

These categories overlap. They are not an additive partition of the universe.
Unsupported master records remain classified separately: 6,281 unsupported
non-common series, 355 fund/ETF ISINs, two different-rights equities, one invalid
ISIN and one unverified ordinary-equity class. None is promoted into a supported
ordinary equity by this implementation.

## Representative genuine saved routes

The new route functions were exercised directly against actual verified private
saved evidence, without response fixtures, model fitting, data writes or provider
transport. The receipt is
`.local-data/completion-blockers-20261024/all-nse-detail-replay.private.json`.
This verifies saved route behavior; the final release report separately records
compiled browser/deployment checks.

| Identity | Saved result | Status |
| --- | --- | --- |
| RELIANCE, `INE002A01018` | 21 October price/chart; preserved 19 October prediction | VERIFIED_COMPLETE |
| HDFCBANK, `INE040A01034` | 21 October price/chart; preserved 19 October prediction | VERIFIED_COMPLETE |
| TCS, `INE467B01029` | Dated 19 October price/chart; missing latest session and no compatible saved prediction | VERIFIED_COMPLETE |
| AEGISVOPAK, `INE0INX01018` | Dated 19 October price/chart/score; latest-session exclusion remains explicit | VERIFIED_COMPLETE |
| AGOL, `INE05FR01029` | Seven genuine retained observations; `MISSING_LOOKBACK_SLOT`; no model output | VERIFIED_COMPLETE |
| AAKAAR, `INE1GYP01013`, SM series | Supported master-only identity opens with empty history and null price/forecast | VERIFIED_COMPLETE |
| 0ABCL31, `INE674K07150` | Unsupported non-common series; opens an explicit unsupported state with no substituted price or model output | VERIFIED_COMPLETE |

These examples cover distinct real companies, EQ/SM series and data-eligibility
states. They do not establish an authoritative sector or capitalization sample.
All seven saved-detail replays returned `provider_requests = 0`.

Identity history presents **five verified** saved master observations and reports
**one unverified** historical snapshot instead of trusting it. Snapshot
`5d3bb6c55b1e58f1e0a6e729a00901ca6e833d0ea8f217fa463970ea13889075`
fails the existing derivation check: its older classification produced different
ambiguity/exclusion counts from the current parser. Its original file/raw source
is preserved unchanged. This is visible as `complete_snapshot_history = false`;
it is not silently repaired or converted into listing/delisting evidence.
Missing master observations never establish a delisting.

## Implementation and verification

`workers/nse_market/discovery.py` separates saved discovery from current identity
permission, supplies independently dated coverage and null-data detail states,
and verifies historical snapshots before showing identity observations.
The authenticated API adds `/nse-market/universe-coverage` and
`/nse-market/identity-history`; `/universe` permits positively verified dated
discovery; `/saved-history` opens master-only and unsupported identities honestly.
Current quote/collection identity qualification is unchanged.

The dashboard displays the full measured universe, date-specific feature/score
counts, exclusions and unavailable daily success rate. Stock detail displays exact
identity, data support, feature exclusions and optional observed identity history.
Existing engine inference and forecast persistence already process all qualified
dataset members; no arbitrary 302/500 ranking restriction was found or added.
The saved-data corpus remains the existing authorized corpus, with no expansion.

Verification commands use the isolated release interpreter/dependencies:

```powershell
.local-data/completion-runtime/venv/Scripts/python.exe -m pytest tests/unit/test_nse_discovery.py tests/unit/test_saved_nse_market.py tests/integration/test_nse_market_api.py tests/integration/test_saved_nse_market_api.py -q --basetemp=D:/al-tests/nse-discovery-final-20261024
.local-data/completion-runtime/venv/Scripts/python.exe -m mypy apps/api/src/alphalens_api/nse_saved.py apps/api/src/alphalens_api/nse_market.py workers/nse_market/discovery.py tests/unit/test_nse_discovery.py tests/integration/test_nse_market_api.py tests/integration/test_saved_nse_market_api.py
```

Scoped Python tests passed **41 tests in 63.54 seconds**, including existing saved
financial display contracts, new discovery/coverage/security boundaries and
Top-N selection beyond 500 saved predictions. Scoped Ruff and mypy passed.
Candidate frontend tests passed **7 tests / 3 files**
(`nse-market`, `saved-market`, `universe-coverage`); TypeScript and scoped ESLint
passed. The final release report records the complete final-source regression,
container/security checks, compiled browser verification and deployment revision.

Public market-data display, wider provider calls, scheduler modification and full
fresh NSE coverage remain outside this software-only saved-data verification.

## Later automatic-run evidence, 24 October 16:09 UTC

The unchanged approved collector completed after this report's initial cutoff.
Its immutable receipt `5aa0183f6b514ff0a4e5aa15b57a00a9` accepted **249 / 500**
securities for **23 October**, used **504 actual GETs / 600 reserved**, published
its saved view and appended **150 compatible experimental forecasts**. One
queried stock remained publication-pending; 250 had not yet been queried for the
session. No manual provider request, scheduler change, expansion or fit was made
by this campaign. Process exit zero is not full-cohort coverage.

The same authorized master GET refreshed the supported/searchable denominator to
**3,207** (observed 24 October 15:57:55 UTC). Latest prices **249**, sufficient
features **150**, latest model outputs **150**, independently accepted outputs
**0**. Saved prices exist for **500**; **2,707** supported identities have no saved
price and **3,057** have no latest compatible prediction. Latest feature exclusions
are **80** known-action, **19** lookback-gap and **251** missing-latest observations.
These counts supersede the earlier dated current-state totals, while preserving
the original audit evidence. Top5/10/20 uses all150 current eligible outputs;
49.8% retained coverage is not an aggregate daily-success rate.

Read-only saved-data replay regenerated all150 new sixteen-feature vectors over
61 slots and matched model scores with zero maximum feature/score error. It
verified original forecast/Top-N lineage and created no prediction, outcome or fit.
The existing model hash is unchanged. Current evaluation is **783 raw records /
752 unique decisions / zero matured outcomes**:602 await qualified outcomes and150
future entries start on26October. Five original declarations are saved; none has
a complete qualified outcome cohort. Every model remains BLOCKED_MODEL_EVIDENCE.

Private post-run receipts:
`.local-data/blocker-resolution-20261024/post-scheduled-run.private.json` and
`.local-data/completion/saved-after-scheduled-run-20261024.json`.
See the final blocker report for current browser, CI and preservation scope.
