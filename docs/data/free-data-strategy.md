# Current strategy: research fixtures and production sources are separate

2026-10-05, user-approved D36-D39 supersede the former upstream-rights requirement
for local educational research fixtures. Explicit open licences plus repository
uploader-clearance representations, with no specific contrary evidence, may be
accepted with residual risk. No independent proof of every upstream right is
required for this narrow scope; production/live clearance remains a separate gate.

RESEARCH_FIXTURE_USE = ACCEPTED_WITH_RESIDUAL_RISK.
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED. PRODUCTION_DATA_CLEARANCE = OPEN.

Five CC BY 4.0 Mendeley datasets by Jagadish Tawade and Nitiraj Kulkarni were captured
with matching repository SHA256 values. A 60-observed-date window yields 300 source
rows, 299 canonical OHLCV records and one explicitly unavailable observation.
Two normalizations are byte-equivalent; raw artifacts are unchanged and kept in
ignored local storage. Metadata, attribution, hashes and quality findings are tracked.
See [source decision and replay](research-fixture-source.md),
[capture manifest](research-sample-manifest.json), and [gate result](p1-validation-report.md).

The research cohort is not a historical market universe. No survivorship-bias,
NIFTY membership, corporate-action completeness, PIT availability or unbiased
performance claim follows from this fixture. Unknown timing/price-basis fields
remain unavailable. Later P2/P4 work must explicitly distinguish research fixtures
from a reconstructible historical market universe. P2 has not started.

The prior official-source research and dynamic-universe proposal below remain
historical evidence and unresolved production research. Their previous zero-capture
and no-adapter statements describe the baseline, not the current development fixture.
Neither the zero-paid policy nor source correctness has been weakened.

## Historical free-data-strategy record retained unchanged

---

# Proposed free-data strategy and P1 sample protocol

2026-10-05. Policy D26–D35 is user-approved. The method and exit checklist below
are proposals to validate; no source, adapter or P2 work is approved by this file.
Evidence and source-specific states: [free-data-evaluation.md](free-data-evaluation.md).

## Recommended path and current feasibility

**Primary conditional path:** official dated NSE CM files, joined to evidenced
historical reference/identity records and corporate disclosures, plus official
session notices. Start with the maximum *verified and legally usable* common
interval; disclose separate bounds for every family. Preserve source boundaries
even when all publishers belong to the NSE group. No paid archive is a fallback.

**Rights clarification path:** investigate a no-fee project-specific permission or
eligible research-data route. Do not assume institutional eligibility or that an
academic permission covers a distributed product. No request has been sent.

**Supplement only:** optional lawfully usable index context, historical sector
assignments and current reference for current use. Historical NIFTY 500 is optional.
MCP's documented query convenience does not establish permission for model training
or a complete daily historic roster. It is not the primary training-data path.

**Current answer:** a reconstructible dynamic universe is technically plausible,
but an end-to-end reproducible, PIT-safe free dataset is **BLOCKED**, not verified.
Historical master coverage, vintage/publication evidence, actions and compatible
rights remain unresolved. Zero market records have been ingested. A single query
service is not demonstrated sufficient; several source families are required.

## Historical universe method to validate

The proposed universe is an **observed, classified NSE cash-equity universe** for
each historical date. It is neither a claim of all listed/tradable securities nor
historical NIFTY 500. The exact cohort and any main-board/SME restriction must be
stated and approved before evaluation; do not silently drop classes to ease parsing.

1. **Clear source and purpose rights.** Identify source/product/version and permitted
   capture, storage, snapshots, normalization, ML/backtesting and outputs. Reject
   paid or trial-dependent routes. Do not evade access controls, infer an automation
   grant from a download button, or replace unavailable records.
2. **Establish a coverage window.** Reconcile actual exchange sessions and exceptions
   against a manifest of complete dated files. Record missing sessions, schema eras,
   partial files and retained revisions. A missing download is not a market holiday.
   Legacy/UDiFF mappings must be separate and checked around their boundary. An
   advertised five years is not a coverage manifest.
3. **Enumerate each day's actual records.** Use the whole dated CM file as the
   starting inventory, not a loop over today's tickers or constituents. Keep a
   permitted immutable artifact and accepted/excluded/quarantined row accounting.
   Distinguish normal sessions, auction data and T+0/T+1 variants; do not double
   count one economic security as multiple ranking candidates.
4. **Classify with contemporaneous evidence.** Resolve instrument type, exchange,
   series, valid-dated security identifiers and status as known then. EQ includes
   ETFs in NSE's legend, so EQ alone is not an ordinary-equity filter. Exclude ETFs,
   debt, funds, warrants, REITs/InvITs and other out-of-scope instruments using
   evidenced classification, not modern names or a present-day master. Series and
   classification changes require valid-dated rules. Unknown classification cannot
   enter a claimed cash-equity universe. A partial classified subset needs explicit
   missing-count/bias disclosure and scope review; material unexplained gaps block it.
5. **Apply historical eligibility at the decision time.** For completed session
   `t`, let `D_t` be the actual eligible prediction time after required information
   became available. Select record versions only with evidenced `available_at <= D_t`;
   live use also requires `ingested_at <= D_t`. Event date, file date, fiscal-period
   end, HTTP modification time and today's capture time cannot substitute for
   historical eligibility. Effective membership/classification intervals are a
   separate test. Unknown availability is ineligible for a strict PIT claim.
6. **Define the observation rule explicitly.** The proposed traded subset requires
   a valid same-session equity record with actual positive traded volume, eligible
   classification and quality evidence. Zero-trade rows are retained in accounting
   but do not establish a trade opportunity. Additional liquidity/lookback rules,
   if later justified, use only already available history and versioned parameters.
   This is a proposal to test, not a liquidity threshold or model implementation.
7. **Preserve entry and exit evidence.** Include later-departed securities whenever
   their historical records qualify. A missing row is not by itself a delisting,
   suspension, zero return, or executable exit. Do not require future survival,
   complete forward prices or today's listing to qualify a past candidate.
8. **Audit the ledger.** For each session/security retain source-artifact hash,
   source/version, identity/classification evidence, relevant timestamps, rule
   version and inclusion/exclusion reason. Reconcile totals to source rows and
   reproduce the same candidate set from the same permitted artifacts. This describes
   a bounded P1 demonstration, not implementation of the P4 universe engine.

Formally, a proposed candidate belongs to `U(t, D_t)` only when its same-session
observation, instrument classification, identity, rights and quality evidence pass
the declared historical-eligibility rules. Availability of **every** dependent
input matters. A date-based record seen today may support a retrospective observed
universe while failing strict as-known-then reconstruction; disclose that distinction
and do not call the latter passed without evidence.

Prediction timing remains D08: completed session information, then prediction when
eligible, then no earlier than the next session's open. If a final file arrives
after that open, that fill is unavailable. Presence in session `t` does not prove
tradability or a fill in `t+1`; later execution research must handle restrictions,
suspensions, opening liquidity and costs without invented prices.

## Survivorship, corrections and corporate actions

Daily enumeration avoids the specific error of seeding history from current
survivors, but does not by itself eliminate survivorship/selection bias. Unresolved
risks include missing old files, omitted no-trade securities, incomplete identities,
unrecorded exits, unavailable terminal consideration and retrospectively corrected
data. Compare historical inventories with evidenced listing/status records; show
unexplained gaps, not a fabricated full-market coverage percentage.

Retain candidates with missing future labels in coverage/censoring denominators.
Do not quietly remove failures or departed securities from performance. Terminal
cash/share outcomes need real evidence; no last-price liquidation or zero-loss
assumption. Later evaluation must report missingness sensitivity or withhold claims
if unresolved outcomes could materially bias the results.

Corporate actions remain a price-data dependency even when fundamentals are omitted.
Keep raw prices/volume and evidenced action terms separate. Any adjustment must be
versioned and consistent with what was known then, including announcement versus
ex/effective dates. Do not mix raw OHLC with silently adjusted volume or use today's
fully revised adjustment history as historical features. Unresolved splits, bonuses,
dividends, mergers/demergers or successor mappings block affected calculations.
Keep an exclusion audit; an action discovered in the future cannot become an
undisclosed retrospective selection rule that removes inconvenient outcomes.

A hash captured now proves reproducibility of captured bytes, not absence of earlier
corrections. No free route reviewed proved a complete historical revision ledger.
If historical availability cannot be established, a separately permitted prospective
capture could accumulate future evidence; it cannot manufacture past timestamps or
claim an instant multi-year PIT dataset. Prospective collection still needs source
permission and a later authorized implementation task.

## Fundamental and context policy

`FUNDAMENTAL_PIT_DATA = UNAVAILABLE` now. A real historical filing and some
dissemination fields exist, but no free, complete original/revised numeric panel
with compatible project rights was established. Activation later requires fiscal
period/start/end/type, standalone/consolidated basis, original publication,
available_at, revision linkage/time and actual ingestion to remain distinct.
Fiscal-period end never becomes availability. Restated comparisons do not rewrite
the original feature inputs. Do not claim the existing minimal schema already
represents every necessary field.

Historical sector context is also unavailable until company assignments and taxonomy
versions are reconstructible. Today's sector is not a historical feature. Official
index levels may eventually supply market context/benchmarks if rights, coverage and
availability pass; they do not imply historical component membership. Neither
family is forced into a model to make a screen look complete.

## Is a useful technical ML stock-ranking system defensible?

**Scientifically plausible, not demonstrated by the data currently held.** A later
baseline could learn from lawful, valid prices, returns, volume, volatility,
momentum, moving averages, RSI, MACD and ATR; licensed/compatible market or sector
context is conditional. These transformations add no evidence beyond their inputs.
All windows end at the eligible decision time; unsupported adjustments, missing
bars or unknown timestamps cannot be patched with artificial observations.

For a later authorized model to be credible it must:

- Declare required/optional/used feature families and actual dataset/universe,
  temporal boundaries, coverage and revision versions. Do not advertise fundamentals
  or sentiment when they are absent.
- Split by dates across the whole cross-section, use chronological/walk-forward
  train/validation/test periods and an untouched final evaluation. Fit preprocessing,
  selection and calibration only on training data. Check label maturity, overlapping
  horizons, purge/embargo where needed, cross-sectional leakage and late revisions.
- Define executable targets and version justified fees/slippage/liquidity assumptions
  in P7; no values are invented here. Evaluate sensitivity, turnover, drawdown,
  risk-adjusted outcomes, uncertainty and actual out-of-sample ranking/prediction
  metrics. Many stock rows do not create many independent market regimes.
- Compare with predeclared simple baselines and a lawful, temporally matched benchmark.
  If an index is unavailable, propose a reproducible benchmark from the same permitted
  universe later; never fabricate an index or compare incompatible cohorts/costs.
- Report failures and missing outcomes. Risk assessment and evidence-based explanation
  remain prerequisites for every actionable signal. No accuracy or profitability
  target is guaranteed, and no performance result is produced in this milestone.

Five verified years might support a limited experiment, but cannot guarantee broad
regime coverage or generalization. At present **no training-ready, permission-cleared
free dataset is verified**, so usefulness remains a hypothesis to test, not a claim.

## Source abstraction, local runtime and availability

Keep `MarketDataProvider` in `provider.py` unchanged for now. Future file ingestion
or API delivery must stay behind an approved, accurately named source adapter;
there is no `selected_provider.py`. Do not equate research VERIFIED with runtime
support. Multiple official source families need source-specific permissions,
provenance, errors and conflict rules; no silent swapping or averaging.

Before any real normalization, review the NIFTY_500-only universe literals, reference
history representation, revision time and adjustment/volume basis in a versioned
P1 contract change with meaningful tests. Fundamental period/basis gaps matter only
before that optional family is activated. They do not justify building a feature
engine now. No code or schema changes are made in this decision task.

Canonical product states and propagation are defined in
[product-contract.md](../product/product-contract.md): AVAILABLE, DEGRADED, STALE,
UNAVAILABLE. No source/rights/PIT evidence means unavailable for that purpose;
optional absence never becomes a zero/neutral model input. A price-only model must
be trained and validated as such, not run by amputating inputs from another model.

Local PostgreSQL and upstream Docker Engine/Compose on a compatible local host are
the sufficient no-fee deployment direction. Docker Desktop's conditional free
licence prevents making it universally required. Cloud is optional, with no paid
or trial service on the mandatory path. See runtime references R01–R03 in the
[evidence review](free-data-evaluation.md). This is a design choice, not a claim
that the local Docker/PostgreSQL runtime has passed verification. The final resume
rechecked Docker: the Linux-engine pipe remains absent; no services were started.

## Questions requiring no-fee source-owner confirmation

Prepared questions only; no messages sent. A written answer must identify source,
version, effective terms, eligible user/purpose, coverage and any conditions.

1. Can this local AlphaLens project qualify for a continuing **zero-fee** right to
   capture, retain exact raw files and snapshots, normalize, train conventional ML,
   retain model weights and run chronological backtests? Clarify the simulation
   restriction and MCP's withholding of a training licence explicitly.
2. Is local personal research different from distribution of this software, public
   dashboards or display of prices, rankings, model outputs and aggregate performance?
   Which of these can be allowed free, and what attribution/user/export limits apply?
3. Is the research scheme available to this project/user, and do its permitted
   purposes include this stock-ranking research? How are aggregate volume, NDA,
   reports, retention, expiration and deletion obligations measured? No cap avoidance.
4. Which download/API/MCP automation is explicitly permitted, with what rate,
   range, pagination, retry and bulk limits? What delivery route supersedes the
   general website prohibition? No access-control workaround is acceptable.
5. What complete historical CM date ranges remain free, including legacy/UDiFF,
   all former securities, no-trade rows, T+0/T+1/auction variants and missing files?
   Are dates partitioned by session or release, and are final files ever replaced?
6. Are original/corrected price and reference vintages retrievable free, with
   actual publication/availability evidence? Explain `0000` and final/revised files;
   do not substitute the latest filesystem modification time.
7. Can dated instrument classification, identifier/name/series changes, listing,
   suspension/delisting and successor chains be obtained free for that interval?
   How can an ordinary equity be distinguished from an ETF historically?
8. Which free action records include original/corrected announcements, ex/effective/
   record/payment dates, amounts/ratios and merger/demerger allocation or terminal
   consideration? How can raw prices and volume be reconciled as known then?
9. Is a free original/revised fundamental archive with per-version public
   dissemination evidence available? If not, fundamentals stay unavailable.
10. What free historical session amendments, sector assignments and index-context
    permissions exist? Optional NIFTY 500 history is not a reason to buy membership.

## Bounded real-sample protocol after the blocking gates

The canonical proposed acceptance checklist is
[P1_V1_FREE_v1](../product/roadmap-and-acceptance.md). No real sample was normalized
in this task, and the current user instruction expressly forbids an adapter.

1. Record compatible no-fee terms for the exact **sample use**, including retained
   raw evidence and normalization. Broader ML/output use has separate gates; a
   research-only sample cannot certify a distributed product. Obtain user approval
   for the next bounded sample/contract task; P2 remains separate.
2. Select real dated files from a declared window and bound retrieval in advance.
   Include complete daily inventories for the chosen sessions, reference evidence,
   normal and genuinely missing/corrected cases, a historical departure/identity
   change and actual actions relevant to the supported scope. Legacy/UDiFF cross-era
   claims require cases on both sides. Do not invent events to fill a checklist.
3. Capture exact permitted bytes in ignored local storage with SHA256, source URL
   without secrets, source/schema/version, capture time, rights reference and
   evidenced release/revision metadata. Missing metadata remains missing. Record
   expected/actual coverage and all retrieval failures; never commit restricted data.
4. After approved contract review and named mapping, normalize through the neutral
   abstraction. Reconcile OHLCV, INR/share units, sessions, identity and action basis;
   account for all input rows and duplicate/correction choices. Replay offline from
   those artifacts; compare normalized hashes and candidate ledgers deterministically.
5. Demonstrate historical eligibility for the declared decision times, or mark the
   affected sample unsuitable for strict PIT. Validate departed cases without
   today's roster and without silently discarding missing future outcomes. If key
   cases cannot be obtained, declare the corresponding scope unsupported/blocked.
6. Publish actual interval, per-security/family coverage, unknowns, unavailable
   optional capabilities and discrepancies. P1 cannot pass until the mandatory
   sample, rights, temporal and universe evidence is real and reproducible.

**Can sampling proceed now?** Not yet as a retained, automated ML-ready sample:
compatible rights and historical eligibility remain unresolved, and adapter work
is not authorized in this task. A no-fee rights clarification is the next evidence
step. If it succeeds, a separately approved bounded sample is P1 work; failure
means keep the gate blocked, not buy access or weaken correctness.
