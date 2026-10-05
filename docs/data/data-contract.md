# P1 data contract, p1.v1 with p1.v2 research extension

Provider-neutral Python contracts in ml/data/src/alphalens_data. These are bounded
foundation schemas, not proof of provider coverage or a P5 production database.
Supported market: NSE/INR/EOD only. Vendor payload fields cannot escape adapters.

## Identity and provenance

Stable security_id; dated ticker and exchange mappings are future P4/P5 work.
Every record carries source_id, source_record_id, revision_id, ingested_at, origin
(REAL_PROVIDER, REAL_RESEARCH_FIXTURE or TEST_ONLY), schema_version, and availability metadata.
Provider metadata must never include credentials, token-bearing URLs, auth headers,
or full connection strings. Real credential-bearing payloads must be rejected by
the selected adapter, not written to raw storage.

## Time semantics

- All instants require timezone offsets and are canonicalized to UTC.
- session_date is exchange local; session_close_at must match that date in
  Asia/Kolkata. Actual close/calendar comes from verified data, not invented hours.
  The p1.v2 extension permits an explicit null session_close_at only when
  available_at is also null. The stricter p1.v1 behaviour remains unchanged.
- published_at is original publication; period_end is not a publication timestamp.
- available_at is historical eligibility, backed by VERIFIED_PUBLICATION or a
  documented CONSERVATIVE_BOUND and evidence reference. Unknown remains null.
- ingested_at is actual receipt. Historical eligibility can precede later ingestion
  of a verified historical capture; live knowledge also requires receipt by time T.
- effective intervals are half-open [effective_from, effective_to), independent of
  announcement availability. Announced future events may be known before effect.
- revision_id preserves original versus corrected facts. Never overwrite revisions.

Known availability cannot precede publication or exceed recorded receipt. A completed
EOD bar cannot be available/ingested before its close. Unknown availability is never
PIT eligible. Historical membership additionally requires an effective interval
containing the query instant. Joining/querying a full PIT universe remains P4.

## Records

PriceBar: positive finite Decimal OHLC; low/high bound open and close; volume is a
nonnegative strict integer; nullable turnover is nonnegative Decimal; optional
adjusted_close requires adjustment_method_version and vice versa. No adjustment
engine is implemented. Do not assume source OHLC is unadjusted: the research wrapper
explicitly carries price_basis=UNKNOWN. Units (shares,
INR turnover) must be verified at adapter mapping time, not guessed.

FundamentalRecord: fiscal period_end plus separately dated provenance and named
finite Decimal/nullable metrics with explicit units. Null is missing, not zero.
Negative EPS/cash flow may be valid; no invented fundamental positivity rule.
Current metrics are a minimal P1 schema, not all future production fields.

CorporateAction: action ID/type, event time, effective interval, optional ratio/cash
amount. Source event handling/mapping must be documented before adjustment use.
UniverseMembership: conditional NIFTY_500, effective intervals, source/revisions.
No historical membership has been acquired.

## Provider requests and capabilities

provider.py defines get_capabilities/get_prices/get_fundamentals/
get_corporate_actions/get_universe. A request includes stable IDs, date range and
aware as_of. Unsupported operations must raise explicit errors, never fabricate
empty success. Only a vendor-specific adapter after selection may implement them.

Evidence status: UNKNOWN, VERIFIED_SUPPORTED, VERIFIED_UNSUPPORTED. Verified
statuses require scope, reference and verification time. A string scope records
evidence; it does not automatically prove coverage for every security/date range.
Adapter evaluation must check the requested scope, original/revised fundamentals,
pagination, units, delisted coverage and membership history. No flags are verified
for any real vendor currently.

CapturedBatch wraps original data payload bytes and canonical records, provider ID
and completeness. Adapter must consume full bounded pagination before setting
complete=True. Missing sessions are not fabricated; missing-session detection needs
the actual exchange calendar in later quality work.

## Bounded sample and deterministic replay

evaluate_price_sample requires verified EOD and licensed sample-use evidence, a
complete nonempty batch, consistent provider/source, requested securities/session
range, known PIT eligibility, and explicit record origin. TEST_ONLY records cannot
pass default REAL_PROVIDER mode. No provider -> PROVIDER_NOT_SELECTED.

Canonical serialization preserves revisions, orders records deterministically,
deduplicates exact repeats and rejects conflicting duplicate source/revision
identities. Hashes use SHA256; raw and normalized hashes differ in purpose. Same
capture with the same ingestion/provenance produces the same output. A new live
fetch or source revision is a new capture, not a reason to overwrite history.

The in-memory SampleManifest records actual counts/checksums and explicitly says
BOUNDED_PRICE_SAMPLE_NOT_FULL_P1_ACCEPTANCE. It is not a claim of complete history,
survivorship-free universe, freshness, production quality or ML validity.
No files/network calls are made by the provider-status CLI. These are P1 helper
boundaries. The subsequently authorized P2 path is documented separately below.

## Bounded Mendeley research fixture under D36-D39

`providers/mendeley.py` is an offline CSV-to-PriceBar adapter. The neutral
MarketDataProvider abstraction and historical evaluator are unchanged. This file
adapter does not impersonate a production provider or set its capabilities VERIFIED.
`research_sample.py` has a separate, explicitly scoped development replay path.
It cannot make unavailable history PIT eligible or promote REAL_RESEARCH_FIXTURE
records into REAL_PROVIDER history. Its file-specific IDs are snapshot-scoped;
they are not exchange security-master IDs or historical identifier continuity.

Every canonical ResearchRow includes its canonical PriceBar, exact parsed source
fields (including unpromoted adjclose), source-row SHA256, physical CSV row number,
raw-relative path/hash, DOI/version, licence, contributors and scope. Join that
explicit raw reference to research-sample-manifest.json for title, repository,
download URL, acquisition time, original filename, bytes and repository SHA256.
The recorded initial acquisition time is stable across offline replays. A later
download of identical bytes is a replica, with its retrieval time recorded separately.

OHLC uses Decimal directly from source text; integral nonnegative volume is required.
Duplicates fail rather than silently disappearing. A source row missing required
OHLCV fields produces an explicit UNAVAILABLE observation and no PriceBar; no zeros,
forward-fills or fabricated bars. Input order is audited, output sorted by security
and session. No independent exchange calendar or all-market completeness claim.
Dataset publication dates remain catalog metadata; they never populate historical
bar available_at or published_at. No fabricated close time or adjustment methodology.

The default provider-status CLI describes only PRODUCTION_PROVIDER status; its
zero count is production_provider_records_ingested, not the research capture count.

## Later quality gates (still deferred)

P2 now adds bounded artifact ingestion and basic row quarantine under D40-D42.
P3 and later work must add broader retries, licensing-aware retention, calendars,
corporate-action reconciliation, missingness/outlier review and freshness policies.
P4 adds reconstructible universe/identifiers; P5 adds financial entity migrations.
Feature generation, labels, training and signals remain unauthorized.

## P2 EOD contract extension

`ingestion/contracts.py` defines p2.v1 with explicit source-scoped symbol identity
when stable security IDs are unavailable. It does not silently promote that identity
to a security master or force NSE/INR defaults on unknown evidence. Currency is NULL
unless explicitly evidenced. Exact OHLC decimals and integral volume are typed in
Parquet; unknown publication, availability, session close and adjustment basis stay
NULL. Existing P1 PriceBar/eligibility contracts are unchanged, and P2 artifacts
cannot supply historical PIT eligibility. See [P2 architecture](p2-raw-ingestion.md).
