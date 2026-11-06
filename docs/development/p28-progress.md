# Combined P27/P28 provider checkpoint

Worktree D:/al-research/p28-worktree, branch p28-free-nse-provider-evaluation.
Baseline P26 531490987b265bdfae58545f75b7c4fc8c331f00 (pushed); original C checkout
remains on p26-visual-analytics-terminal. Other Codex processes present; do not
modify C source, switch its branch or interrupt them. New .venv/node_modules
junctions point to existing D dependencies. Do not reinstall or move environments.
Set PYTHONPATH to this worktree's package sources for CLI/manual Python commands;
existing editable environment otherwise points to C. Pytest's configured paths
use this worktree automatically. No active owned server; last one stopped safely.

P26:84 distinct targeted Python passes;67 frontend;22 distinct real Chromium cases
across 19/3-selector-failure full run and corrected4-case focused regression.
All five new graph scenarios passed. Ruff/format393/mypy235/Bandit/audits/lock
passed. Full2,485-file and47-alert checksum receipt unchanged. No new NSE data.
P26 CI foundation38208914993 and frontend38208915054 running; check actual outcomes.

Alpha Vantage credential is ALREADY in Windows Credential Manager target
AlphaLens/AlphaVantage, current-user protected; readback verified. Original api file
intact; safe for operator removal. EXACTLY ONE query, SYMBOL_SEARCH RELIANCE,
HTTP200 at2026-10-12T05:13:06.585056Z, returned RELIANCE.BSE India/Bombay. No NSE
match, prices, sessions or model inference. Private request ledger/receipt in
LOCALAPPDATA/AlphaLens/provider-state. Do not repeat the real probe. No secret inGit.
Detailed already-committed decision: docs/data/alpha-vantage-provider-decision.md.

Primary-source findings collected (verification2026-10-12):
* Upstox analytics-token docs: free, one-year, read-only GET, no static IP for market
  quotes/historical, no orders. Account operator-reported UNDER_REVIEW; no token.
  V3 daily candle days/1, per instrument, historyJan2000, max10-year window, aware
  start-of-candle time (not publication); NSE_EQ|ISIN instrument master. Standard
  API rate50/s,500/min,2000/30min. Full Market Quotes V3 supports500 instruments.
  Retention/ML/display permission not verified; do not infer from free access.
* INDstocks official api-docs.indstocks.com verified documentation domain and
  official indstocks.com linked: FAQ free API, completed brokerage KYC required,
  tokens24h, zero balance okay for API. Conventions Data/Quote5/s and100000/day;
  historical /market/historical/1day?scrip-codes=NSE_token,... max5 cash instruments,
  one-year per request (not total history depth), input epoch milliseconds vs candle
  ts seconds/IST session-open convention. Quotes/full up to1000. Missing response
  keys indicate missing instruments, not complete session. No account/token,
  retention/ML permission not established. No paid signup/KYC action.
* Angel One SmartAPI official FAQ free including historical. Docs access currently
  returns not-authorized; no bypass. Indexed official docs contradict 1/s quote
  narrative vs newer table10/s,500/min,5000/h; historical3/s180/min5000/h. Quote
  bulk50. Need exact current primary table/auth/session/permissions before activation.
* Yahoo/yfinance Apache2 software license != data rights. Primary code history.py
  and multi.py reviewed via raw GitHub only, no Yahoo price requests. .NS vs.BO
  separate. 0xramm wrapper current actual code is JS src/index.js,yahoo.js,format.js
  (About claims Flask outdated); repo claims MIT but no LICENSE file at root.
  It strips .NS/.BO during search dedup, defaults bare symbols to.NS, batches quotes,
  formats display separately. It contains cookie/crumb fetching, browser headers
  and NSE autocomplete attempts: DO NOT COPY OR EXECUTE those paths. Original
  exchange-explicit, provenance-first ideas only; no source code imported.
  Raw Git blob ids: yahoo.js2be84de9e5e9c32ec0b93cf8b50b50f218dd3720,
  index.jsa5f326c0cf5767040e3e0e77688194dba741c4c0,
  format.js368f311844d8d558a144a6c69287fb4ce316a50d.
* TejHQ existing pinned historical clearance/report reused. Publisher advertises
  Oct9 status from prior actual bounded check; no price body acquired. Ongoing
  upstream rights/identity/calendar/actions/revisions remain conditional. Do not
  redownload bulk snapshots or repeat all reports.

User now says all permissions; asynchronous question pending for provider-specific
terms/reference and whether Upstox active. This is missing evidence, not another
operator-permission request. Continue offline development while waiting.

NEXT: inspect existing P2/P19 contracts, then implement typed multi-provider
contracts, disabled adapters and request plans/normalization (Upstox/INDstocks/
Angel offline; Yahoo/Alpha/Tej unsupported gates), persistent bounded rate state,
P19 eligibility/fixture integration, authenticated comparison API and Settings/Data
Health UI. Reuse P6/38-feature/model metadata/prospective ledger; investigate XGB
trusted loading separately without predictions/retraining. Tests, docs, push/CI.
Frozen original P19 live/source/inference/ranking and scheduler stay BLOCKED.

Implementation design chosen: provider-specific pure offline parsers + GET/read-only
request plans produce P2 ParsedRow contracts, with explicit exchange/ISIN/series
metadata (never infer EQ series from instrument type). Native bodies and metadata
hashes remain distinct. New P19 vendor dispatch is TEST_ONLY-only while DAILY keeps
its original hard blocker. No competing market store. Source identity bridge must
be explicit and contemporaneous; current BOD master is not historical membership.
Reuse P19 raw landing/normalization/quality/features/receipt/recovery and P20 alerts.
Readiness reports peer scope,38-feature compatibility and original policy blockers,
not invented outputs. Rates/request plans/quotas tested offline.

Latest user confirms operator permission and zero-paid requirement. Optional
source-specific terms/account-status question remains pending; continue engineering.
P26 frontendCI38208915054 SUCCESS. Foundation38208914993 still in progress atlastcheck.

User clarification received: NO provider has verified complete automated-download,
retention, ML or public-derived-display permission. Upstox STILL UNDER REVIEW;
KYC record exists but trading account not confirmed active. Keep all acquisition,
live inference, restricted public display and scheduled downloads DISABLED.
Continue offline/domain/UI/security and isolated clearly labeled TEST_ONLY demo
preparation; do not expose real research publicly or introduce runtime fixture
fallback. No further operator permission question needed for ordinary engineering.

Code checkpoint: typed multi_contracts.py and original disabled multi_adapters.py added; Upstox current-master parser and native daily Upstox/INDstocks/Angel parsers, exact-decimal P2 interoperability guarded by series/raw-basis evidence. No transports or SDK installed. TEST_ONLY vendor-bundle dispatch added to P19 while DAILY hard block unchanged; raw native body captured separately from fixture envelope, existing P2/P3/features/receipts reused. db/providers schema + durable private operational ProviderStore added for disabled selection, quotas, retries/clock guards. Module-level checks passing; targeted tests not yet written/run. Next: write adapter/worker/store tests, provider comparison/API/UI, credentials/worktree launcher, source decision/docs and trusted XGB inspection.

Verified checkpoint 2026-10-12: 47 P28 adapter/store/P19/API/credential/readiness cases passed after correcting two test assertions (sanitized future-error contract and TEST_ONLY ISIN). Separate authorized compatibility/security regression 228 passed in43.57s. Frontend new3 provider component cases passed; full70 run pending. Exact frozen XGB h10 checksum deserialized in bounded trusted subprocess; native XGB3.0.5/config and38 features confirmed, zero predictions/fits, global type allowlist unchanged; current model acceptance still NOT_PASSED. Protected comparison GET API and six-provider Settings/Data Health panels added; disabled selection/quota state initialized in private new D:/al-research/p28-runtime/provider-state; no acquisitions. Actual compiled app running owned loopback8028 using isolated TEST_ONLY operator and copied47alerts. Browser8 provider/P26 cases running. Next: finish browser/static/dependency, isolated demo verification, provider decision/operations docs, preservation review, milestone commit/push, actual CI review.
P26 foundation38208914993 FAILURE: strict full-history TruffleHog0verified/3unverified,1978chunks6689403bytes; Docker/Trivy skipped. Frontend38208915054 SUCCESS. Prior actual container44HIGH/8CVEs/0CRITICAL remains, not a new-head scan. No security exclusions or severity changes.

P28 final checkpoint:51 targeted cases and228 overlapping integration/security cases passed (232distinct); full71frontend passed; eight distinct browser cases verified across7+focused1 after separate-session and bounded cold-capacity retry fixes. Full original artifact/hash/47alert recheck passed36.286s. Static/dependency checks passed. User expanded to a3-4h P29 sprint at2026-10-12T08:23:29UTC; finish/commit/push P28, then branchP29 from that milestone, keeping source acquisition disabled. Next: P29 Evidence Passport, descriptive regime/reliability/drift, isolated static demo, PostgreSQL readiness and final tests/CI.
