# Official Upstox cash-equity discovery

Evidence date: 1 November 2026 IST. This release indexes official instrument
metadata for private discovery; it does not authorize new candle acquisition,
extend the NSE model to BSE, or establish current suspension status.

The [official Upstox instrument documentation](https://upstox.com/developer/api-documentation/instruments/)
recommends JSON and `instrument_key`; exchange tokens can be reused. One explicit
unauthenticated HTTPS retrieval of the linked complete BOD JSON gzip was received
at 2026-11-01T08:58:15.523756Z (14:28:15 IST). Its verified display snapshot was
published locally at 2026-11-01T08:58:22.009899Z. The receipt time is not an
independently established provider publication timestamp. The refresh receipt
records one metadata GET, zero quote requests, zero candle requests and zero
history or forecast writes.

Raw metadata SHA-256:
`e58e0d228b7d0449a4c00a2803de7eedfe820c47e635730a84a7eb35b1940fe8`.
Private verified v2 snapshot:
`f032ba8b888b1284fca3347cd2c4ec5954b9a058683729ee92030aa561a931b6`.
The machine-readable source receipt is
`.local-data/private-v1-20261101/display-catalog-refresh.json` in the original
worktree; it remains private and outside Git.

| Denominator | Count | Meaning |
|---|---:|---|
| All complete BOD records | 120,700 | Includes derivatives, indices and other categories |
| NSE_EQ cash records | 9,866 | Includes nonordinary securities |
| BSE_EQ cash records | 13,117 | Includes nonordinary securities |
| Verified ordinary NSE listings | 3,214 | Existing strict NSE series/status/ISIN rules |
| Verified ordinary BSE listings | 4,955 | Separate BSE groups and ordinary ISIN class |
| Searchable unique ordinary instrument keys | 8,169 | Exchange-specific listings, not 8,169 companies |
| Unique ordinary company ISINs | 5,664 | Cross-exchange lookup does not merge histories |
| Independently accepted predictions | 0 | Discovery does not qualify a prediction |


## System Universe & Pipeline Counting Invariants

AlphaLens maintains four distinct, non-overlapping universe count totals across data ingestion and ML:

| Pipeline Dimension | Total Count | Granular Breakdown & Invariant Status |
|---|---:|---|
| **1. Searchable Ordinary Equities** | **8,169** | **3,214 NSE_EQ + 4,955 BSE_EQ** listings across 5,664 unique company ISINs. Indexed via official BOD metadata (latest-all-equities.json). Fully searchable locally with zero provider calls. |
| **2. Stocks with Valid Retained Daily History** | **500** | Retained cohort in local store (450,970 total daily candles). **497** active stocks received validated candles for the 30 Oct session; **3** stocks pending vendor publication (NSE_EQ|INE023A01030, NSE_EQ|INE029L01018, NSE_EQ|INE077P01034). |
| **3. Stocks with Model-Compatible Features** | **307** | **307** NSE stocks evaluated with complete 16-feature vectors on 30 Oct session. 190 stocks excluded due to missing history, insufficient lookback, or data anomalies. |
| **4. Genuinely Produced Experimental Forecasts** | **307** / **1,561** | **307** active pre-entry experimental forecasts generated for the 30 Oct session. **1,561** cumulative immutable forecast records stored in verified local ledger. |

### Quota Clarification: Internal Research Reservation vs. Upstox Platform Limits

> [!NOTE]
> **Operational Quota Definition (D95 / D97 / D100)**:
> The threshold of **1,800 requests/day** (3 scheduled runs × 600 reserved requests) is **NOT** an Upstox API technical rate limit. Upstox's platform enforces rate limits on sub-minute burst windows (e.g., 10-25 requests/second depending on endpoint and application tier) and does not impose a 1,800-call daily ceiling.
> Instead, **1,800 GETs/day is AlphaLens's internal, operator-approved research budget constraint** established to guarantee zero financial cost, bounded local resource consumption, and safe non-intrusive operations. Daily collection runs are strictly bounded by this internal quota to protect provider account standing.

Saved histories, recent histories, complete vectors and model scores have separate
source and observation dates. Their fresh release counts are recorded in
`ALPHALENS_DAILY_DATA_AND_ML_VERIFICATION.md` and the final release attestation;
none is inferred from the 8,169 searchable identities. Refreshing display metadata
does not produce a new saved price, feature vector or prediction.

The master also contains 34,511 NSE_FO, 23,055 NSE_COM, 16,296 MCX_FO, 10,066
BCD_FO, 8,640 NCD_FO, 4,918 BSE_FO, 139 NSE_INDEX, 79 BSE_INDEX, 10 GLOBAL_INDEX
and three GLOBAL_INDICATOR records. These are counted by segment and never
published as ordinary-equity model candidates.

Cash-class exclusions total 14,814: 6,290 unsupported NSE series, 7,538
unverified ordinary ISIN classes, 971 fund/ETF identities, 14 differential equity
rights, and one invalid ISIN. Unknown categories fail closed. In the initial
30 October master, BSE did not supply `security_type`; absent status remains null
and provider status availability remains false. The 1 November metadata refresh
does not independently establish suspension status. BOD presence is not proof of
independently checked active/suspended status. No suspended list was silently
assumed complete.

NSE's existing ordinary series EQ/BE/BZ/SM/ST/SZ are unchanged. BSE groups are
classified separately (A/B/X/XT/T/M/MT/Z/ZP/P/TS/MS) and additionally require a
valid ordinary-equity INE ISIN class. Funds, debt, rights and unknown groups are
excluded. The official instrument documentation links the
[BSE trading classification reference](https://www.bseindia.com/markets/equity/EQReports/tra_trading.aspx);
its web response returned HTTP403 during this review. BSE group classifications
are therefore exposed as current provider metadata, not as verified historical
membership, exchange-calendar evidence, or rights to retain market prices.

## API and detail behavior

Authenticated `GET /api/v1/nse-market/universe` supports case-insensitive symbol,
company name, ISIN and exact instrument key, substring queries, `exchange=ALL`,
`NSE` or `BSE`, and pages of at most 100. An ISIN search returns separate exchange
listings. `include_unsupported=true` exposes classified excluded cash identities
for diagnostics. The public synthetic demo is separate.

Authenticated `saved-history` and `identity-history` accept exact NSE_EQ or BSE_EQ
ISIN keys. Known equities without prices return a valid empty detail, null
OHLCV and `HISTORY_NOT_COLLECTED`. Duplicate keys return
`INSTRUMENT_IDENTITY_AMBIGUOUS`; unsupported identities retain their exclusion.
No missing price becomes zero, and no missing history becomes a chart. BSE detail
shows `MODEL_NOT_VALIDATED_FOR_THIS_SEGMENT` / `MODEL_INCOMPATIBLE`. Its UI offers
neither the NSE inference workflow nor a broader acquisition action.

### Current master aliases and saved observation aliases

The full-catalog browser check exposed a real display defect: for provider key
`NSE_EQ|INE08PH01015`, the dated master supplies symbol `ABCIND`, while saved
observations retain the captured alias `ABCOTS`. A saved-history page displayed
only the captured alias, so a user arriving from current discovery could not see
the master listing they selected. The failed browser receipt is retained.

Commit `8c0ba778ba99173c58d9a26c5af2dea0e6f48dac` adds separate optional
`security.current_identity` metadata for both saved-history and master-only
details: symbol, company name, exchange, nullable source date and verified master
snapshot ID. The page displays the current master listing separately from the
saved observation headline. Existing `security.symbol`/`name`, candle values,
source/observation clocks, forecasts and historical aliases are not rewritten.
This is a display of dated aliases for the same exact provider key, not proof of
a historical rename-effective interval or permission to merge exchange histories.

The existing cached catalog verification supplies this metadata with zero
provider GETs. Missing, unavailable, incomplete or ambiguous current identities
return null with an explicit status; they do not fabricate a current alias or
hide otherwise valid saved history. A focused backend run passed **25 cases in
15.75s**, including current-alias separation, unchanged saved history and
fail-closed duplicate/unavailable cases. Ruff and targeted mypy passed. **Seven
saved-market frontend cases** passed, including a renamed listing with its old
saved alias and chart date preserved and no additional fetches. These are
software checks; the complete actual browser rerun remains a separate gate.

The main market page includes an exchange filter and exchange-specific result
labels. Global autocomplete reads the saved all-equity catalog without provider
requests. Existing NSE-only provider action/watchlist selectors retain their
separate bounded transport policy.

## Preservation and repeatability

All v1 snapshot derivation rules remain unchanged. `universe.load()` and ordinary
collector refresh still use original `latest.json`; the v2 display catalog uses
`latest-all-equities.json` in the same protected directory. The 1 November refresh
receipt confirms the current collector pointer remained byte-for-byte unchanged
during display publication, SHA-256
`95538a876f02665a84ea27d5ba317112c3877398ef7381df915861d5ddca78ce`.
BSE is absent from the collector's `eligible` identity tuple. The 500-stock policy
and protected price/forecast stores are not expanded by this catalog.

The 31 October master remains historical evidence: **119,939 BOD records**,
9,866 NSE_EQ / 13,117 BSE_EQ records, and the same **8,169 ordinary listings /
5,664 company ISINs**. Its raw master SHA-256 was
`9a30828d821e4f3ce9d9fd3c7b0c50db7d53332d5a4ea25950353c273f02e892`,
and its display snapshot was
`d5830fb7a2abb5370731ffc47bb0344da504af282750d2fe80391f1ff3dfb3ba`,
received at 2026-10-31T04:21:17.847622Z and published locally at
2026-10-31T04:21:22.090977Z. The 1 November total increased through MCX_FO records;
ordinary cash-equity discovery counts did not change. No additional equity
history or inference is implied by either metadata refresh.

The earlier 30 October baseline remains historical evidence: 118,937 BOD records,
8,026 ordinary listings (3,197 NSE / 4,829 BSE), and 5,537 company ISINs. Its raw
master SHA-256 was
`7660e9ed08b4eb4434e71403219d989d0f65d4be837b5c2590662b0d15ae7661`
(3,341,248 compressed bytes), and its v2 snapshot was
`0fb446b089269b08511abd786557440ea29a09fb1df2727527d433f03c1f2593`.
At that earlier publication, the v1 collector pointer referenced
`snapshot-2a9f2fb139c6a1806f13f720a3f97b1c3a0aab1a76c18cf05e3e7bb1de5835da.json`,
with pointer SHA-256
`fbb6946dad7a0a6257c35bcb7713e7a47841b4a483812ac24334ed773492e653`.
These older values are not presented as the latest catalog or current collector
pointer, and the display refresh does not authorize changing the collector.

The display catalog caches one checksum-verified snapshot for at most 30 seconds;
pointer changes invalidate it immediately. Collection and current identity-action
paths do not use that cache. Per-security history reads copy only the selected
security from the existing verified 60-second market projection cache, preserving
the existing verification interval without copying every stock's full history.

Focused backend verification passed 54 cases in 45.29 seconds, including
scientific-label clocks, corrupt next-session evidence and truncated-master
rejections for both snapshot versions. The new constructed-data ASGI test
paginates and opens all 110 distinct
NSE/BSE fixture identities, checks dual-listing lookup, lowercase keys/ISINs,
exchange filters, authentication and bounds, with zero provider requests.
Fixtures are TEST_ONLY and are not evidence of genuine new market observations.

The 30 October campaign continuation additionally repaired malformed-master
handling: reserved/corrupt DEFLATE blocks become the same explicit contract
rejection as truncated gzip files, and array/object BSE category values cannot
raise an unhandled membership error or become eligible equities. The combined
universe, all-equity API, saved-history API and scientific-label regression
passed 39 tests in 21.88 seconds. Ruff passed and strict mypy found no issues in
the four universe/API source files. Read-only re-derivation of the actual installed
master retained snapshot `0fb446b089269b08511abd786557440ea29a09fb1df2727527d433f03c1f2593`
and its original 8,026 ordinary listings; these repairs do not rewrite source
records or change valid snapshot derivations.

Historical 30 October pinned Node22.23.3 typecheck, lint and production build
passed. All 136 frontend
tests in 27 files passed on the unchanged-assertion full rerun (78.26 seconds).
The initial cold full run retained one Settings lazy-route timeout; no assertion,
timeout or test was weakened. The actual production build is in a separate
private release directory; the original frontend was not overwritten.

Final-source CI at `8c0ba77` subsequently passed all three discovered workflows:
[foundation](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41170371856),
[research dashboard](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41170371880)
and [container readiness](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/41170371933).
It records **2,059 Linux/PostgreSQL passes / 33 skips**, **137 frontend unit passes
in 27 files**, passing builds/typecheck/lint, zero reported npm vulnerabilities,
and **zero HIGH / zero CRITICAL** findings for each scanned container image.
Full reachable-history review covered 182 commits, three exact reviewed fixture
findings, zero unexpected findings and zero verified secrets. The raw scan was
not clean (exit 183); its exact reviewed disposition passed. The six synthetic
demo browser passes are separate from real private coverage. Private CI receipts
are under `.local-data/private-v1-20261101/ci-final/` in the original worktree.

The first actual 8042 preflight exposed a deployment defect: running from the
original checkout while setting candidate `PYTHONPATH` imported the new API but
old `workers` modules. Universe endpoints returned HTTP500 although the focused
ASGI tests passed. A direct module-file probe confirmed the mismatch. The launcher
now pins the application working directory to the selected source checkout and
the database working directory to its own original source. The failed preflight
is retained as evidence; success requires the subsequent actual browser run.

`apps/web/tests/browser/all-equity-private.spec.ts` provides the actual release
acceptance: enumerate every dated official ordinary listing through authenticated
API search, open every detail API, navigate at least 100 distinct genuine saved
stock pages across NSE/BSE/dual listings/special series/missing histories/excluded
funds, and inspect widths 1600/1366/768/390/320. It forbids provider acquisition and
records server failures and browser exceptions. Its actual execution outcome is
recorded in the final acceptance report; the existence of this test is not a
claim that its release gate has passed.

Final browser acceptance against the 1 November 8,169-listing catalog **PASSED** on 1 November: all 8,169 authenticated detail APIs and 110 distinct browser stock identities opened successfully, with zero provider requests, server errors or browser exceptions. The exhaustive test body took 860.459 seconds. The private receipt is `.local-data/private-v1-20261101/browser-all-report.json` in the original worktree. This verifies discoverability and truthful detail states; it does not imply price history or model eligibility for all listings.
The earlier 30 October actual run opened all 8,026 detail APIs and 110 distinct
stock pages before failing the first responsive search check after the exhaustive
stress phase. A separate clean run exposed a 320-pixel overflow from the unbroken
`EXPERIMENTAL_UNVALIDATED_RESEARCH` evidence label. That defect was repaired by
wrapping the existing disclosure content. Failure receipts and screenshots remain
private; prior partial success does not establish a pass for the refreshed master
or for the complete final browser workflow.

A later full-catalog attempt completed all **8,169 detail API requests**, then
failed its stock-page check at the `ABCIND`/`ABCOTS` alias difference described
above. That partial result is also retained as **FAILED**, not a final coverage
pass. The corrected `8c0ba77` runtime source, the test-only authentication synchronization revision `2f01eb3`, and the dated 1 November master subsequently passed the exhaustive API/stock-page run. Separate quick tests passed responsive discovery/detail at all five widths and the saved-chart/model/forecast-history workflows. The broad route check passed 23 routes at five widths and four accessibility audits. Earlier failures remain retained and are not relabeled as successful.

Private raw masters, snapshots, exact identity lists and receipt files stay outside
Git. Private campaign evidence is under `.local-data/campaign/equity/` in the
isolated campaign worktree, with the installed catalog under the original
`.local-data/nse-universe/`. No market-price records are committed by this work.
