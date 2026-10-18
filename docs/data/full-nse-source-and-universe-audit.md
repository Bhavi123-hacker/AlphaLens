# Full NSE identity and private research source audit

Observed 17 October 2026. This audit and service do not change original models,
evaluation periods, forecasts, quote timestamp gates or scheduled tasks.

## Genuine current identity observation

One bounded, unauthenticated GET used the existing Upstox transport and shared
quota ledger for the official
[NSE beginning-of-day master](https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz).
The original response was received at **2026-10-17T11:30:28.220996+00:00**.
Its 1,982,987 compressed bytes remain in protected, Git-ignored storage:

`D:/al-research/p28-worktree/.local-data/nse-universe/master-d6670c143b6e6e4b0260e9f6fec2decf0e2c979b3c4b9d2df3cc729cf265a38d.json.gz`

SHA-256: `d6670c143b6e6e4b0260e9f6fec2decf0e2c979b3c4b9d2df3cc729cf265a38d`.
Verified derived snapshot:
`2d257a4edbd999e6e7bf86ae7a387139a6458ebfa22e25041d300c914fb8b210`.

| Identity scope | Actual count |
|---|---:|
| All rows in official NSE master, including derivatives/indexes | 79,580 |
| NSE cash-segment (`NSE_EQ`) identities, including debt and funds | 9,832 |
| Discoverable `NSE_EQ` / `instrument_type=EQ` | 2,706 |
| Verified ordinary common equities across supported full-paid series | **3,198** |
| Ordinary equities in EQ series | 2,350 |
| Ordinary BE / BZ equities | 229 / 38 |
| Ordinary SME SM / ST / SZ equities | 482 / 97 / 2 |
| Excluded fund/ETF EQ identities | 355 |
| Excluded equity with different rights (`IN9`) | 2 |
| Invalid-format/checksum identity, already non-common SDL series | 1 |
| Other excluded series, including debt, REITs and InvITs | 6,276 |

The common-equity count can exceed the narrower type-EQ count because verified
fully paid ordinary shares also trade in surveillance and SME series. This is
not a claim that all 3,198 have been queried for candles or are model eligible.
The service leaves source accessibility, historical observations, technical
features and experimental eligibility **unknown** until separately measured.
Independently accepted current ML securities remain zero.

## Positive common-equity classification

[NSE's official series legend](https://www.nseindia.com/static/market-data/legend-of-series)
identifies fully paid ordinary-equity series EQ, BE and BZ, and SME series SM,
ST and SZ. EQ also includes ETFs; therefore EQ alone is insufficient.
REIT/InvIT units, preference shares, warrants, debt, rights entitlements and
partly paid shares have separate or overlapping series and must not be inferred
to be ordinary shares from the cash segment alone.

The [NSDL core-services handbook](https://nsdl.co.in/downloadables/Core%20Services.pdf)
describes Indian ISIN issuer and security codes: company prefix INE, mutual-fund
prefix INF, differentiated equity-rights prefix IN9, and ordinary equity code 01.
The official handbook's indexed primary-source text was inspected; direct PDF
retrieval failed (web reader HTTP 502 and native connection closed), so no new
local PDF receipt is claimed. The classification combines this documented ISIN
structure with the exchange series, rather than treating an issuer prefix as
sufficient by itself. Full ISO-6166 expanded-alphabet Luhn checks are applied.

Every eligible record must have exact NSE exchange and cash segment, a supported
full-paid series, valid INE/01 ISIN, key exactly `NSE_EQ|<ISIN>`, bounded nonempty
symbol and company name, a recognized provider status, unique key and an
unambiguous symbol **among ordinary equities**. A same-company warrant or debt
can share the symbol without making the exact ordinary-equity ISIN ambiguous;
ELECTCAST and MOTHERSON are real examples in this response. Unknown classes
remain explicitly excluded, rather than being upgraded through name heuristics.

Upstox's [security-status appendix](https://upstox.com/developer/api-documentation/appendix/equity-security-type/)
describes NORMAL, SME, PCA, IPO and RELIST statuses. NORMAL is **not** a security
asset-class guarantee: it is also present on government debt in this master.
PCA/surveillance/SME labels remain visible, with their distinct risk and lot
constraints; inclusion in identity search does not establish suitability for a
retail portfolio or applicability of the current 50-stock experimental model.

## Dated identity history and service boundaries

`workers/providers/universe.py` provides explicit `refresh`, `save`, `load`,
bounded `search`, `changes` and `is_ordinary_instrument`. Search is read-only and
performs **zero provider requests**, with at most 100 returned rows per page.
Raw master and derived snapshots are content pinned, owner protected, and
reparsed and checksum verified when loaded. The latest pointer changes atomically;
an earlier observation cannot replace a later current pointer. Raw observations
and actual receipt times are never rewritten.

The private terminal, watchlists and manual portfolio identity validation reuse
this saved universe when a V2 private root is configured. A snapshot must be no
more than 24 hours old, not future dated, positively classified and checksum
verified. A present stale or malformed snapshot fails with an explicit refresh
reason; it does not silently fall back to archived prices or a different identity
set. Installations with no saved universe retain the original bounded current-EQ
master path. These changes leave the strict quote chronology unchanged.

An explicit operator refresh is available; it sends one static identity-master
GET and never acquires quotes or candles:

```powershell
.\scripts\windows\project-python.cmd -m workers.providers.universe refresh --root .local-data\nse-universe --provider-root .local-data\p30-upstox-validation
.\scripts\windows\project-python.cmd -m workers.providers.universe status --root .local-data\nse-universe
```

`status` makes zero provider requests and reports whether the saved dated identity
snapshot is currently usable. A failed refresh does not fabricate a newer receipt.

Non-EQ surveillance/SME shares require the new positive master evidence before
terminal selection. Cached observations cannot silently inherit a changed symbol
or series. Bounded per-stock provider charts and quotes remain separately
requested, transient observations; discovering all identities does not trigger a
historical download for the universe.

Snapshots retain observed identity additions, symbol/name/series changes and
absence from a later master. Absence is explicitly **not verified delisting**;
it may reflect suspension, vendor coverage or a different listing state.
No current master establishes original listing dates, historical membership,
historical series changes, departed-security completeness, point-in-time sectors,
or a survivorship-free historical NSE universe. Existing current-master-only
semantics remain unchanged. The official
[Upstox instrument documentation](https://upstox.com/developer/api-documentation/instruments/)
supports stable instrument keys over reusable exchange tokens and supplies a
separate current suspended-instrument list; that separate list was not fetched
in this one-master audit. Missing active identities therefore remain unknown.

## Private research scope rechecked

One read-only public request to `https://community.upstox.com/t/17302.json`
rechecked **post 3** at **2026-10-17T11:31:04.979093+00:00**. It was written
1 September 2026 by **Anand_Sajankar, Software Engineer, Upstox**. Its exact
staff-post HTML SHA-256 remains
`317b0353c515183175f98a4de5794837816528560377b52cfba1c2d0bda23800`, matching
the existing V2 audit. No question or other message was sent to the provider.

The [specific official reply](https://community.upstox.com/t/can-upstox-historical-api-data-be-retained-locally-for-private-ml-backtesting-research/17302/3)
permits local historical API retention and personally retained derived features,
statistics and models for private noncommercial research, subject to API terms
and limits. It states no stock-count cap. Accordingly, separately bounded manual
100-stock and 250-stock pilots for the same private purpose fit that evidence;
they still require valid identities, request budgeting, quality controls and
disclosed residual rights/action uncertainty. This is not permission for public
market-data redistribution, paid/commercial services, brokerage orders or an
unbounded full-market archive.

The permission is about historical API observations and private derived ML. It
does not explicitly grant permanent raw Fundamentals datasets. The existing
V2 approach remains: transient action inspection, retained minimal event/date
exclusions and response hashes, no stored raw action payload. An empty action
response does not certify a complete action-free history. Do not apply invented
adjustment factors or silently upgrade corporate-action compatibility.

## Actual API capacity versus operating authorization

[Official standard limits](https://upstox.com/developer/api-documentation/rate-limiting/),
rechecked today, are 50 requests/second, 500/minute and 2,000/30 minutes per
API/user for standard historical requests. Shared application quotas can be
stricter and must continue to reserve each attempt before sending it.

For an existing 50-stock baseline, an additional 50-stock historical/action
pilot needs at most 100 instrument GETs; a subsequent additional 150 needs at
most 300. These are ceilings before measured failures, calendar lookups or
explicit correction probes, not evidence that the requests or observations
already succeeded. Exact pilot results belong in the consolidation report.
Preserve original 50-stock snapshots, model contract and forecast ledger.

A full 3,198-stock historical-plus-action pass could require roughly 6,396 GETs,
and a one-session daily candle pass roughly 3,198, before independent calendar
and correction evidence. The old 120/run, 360/day proposal cannot imply complete
daily coverage of that universe. A conservative one-request/second worker alone
would take about 107 or 54 minutes respectively; measured network time, payload
sizes and failures must replace these estimates after pilots. No guaranteed EOD
publication time or guaranteed API-accessible stock count follows.

**Expanded recurring acquisition remains unapproved.** It requires the user's
explicit approval of the exact universe, cadence, per-run/day/rolling limits,
retry/catch-up behavior and storage consequences after real dry-run qualification.
This audit neither registers nor enables a Windows task and preserves the
existing RELIANCE task. Larger one-off acquisition should remain staged and
checkpointed; do not turn a broad permission interpretation into an unmeasured
automatic full-market download.

## Verification

The initial targeted run passed **20 TEST_ONLY unit cases**, covering official
series, fund/differentiated/debt exclusions, ISIN/key mismatch, duplicate identity,
cross-class shared symbols, checksum tampering, dated changes, rollback rejection,
bounded saved search and malformed/naive master rejection. Ruff and mypy passed
for the new module and tests. These engineering fixtures are separate from the
single genuine master observation and do not establish real candle/ML coverage.

Four additional TEST_ONLY identity-integration cases passed for non-EQ selection,
saved-master terminal/watchlist use with zero master GETs, missing-snapshot legacy
fallback, future/stale rejection and raw-checksum tampering. The separate existing
terminal/universe/personal-API regression batch passed 42 cases. All original
strict quote validation remains covered by the terminal cases.
