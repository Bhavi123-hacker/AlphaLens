# P1 Mendeley research-fixture source decision

Decision date: 2026-10-05. User-approved policy D36-D39; no purchase or account.

SOURCE: Mendeley Data, five version-1 datasets by Jagadish Tawade and Nitiraj Kulkarni.
ACCESS METHOD: individually identified public download links exposed by the
repository's anonymous dataset page; bounded one-time capture, then offline replay.
COST: zero; no subscription, trial, API key or paid software.
RIGHTS STATUS: explicit CC BY 4.0 and repository uploader-clearance representations
VERIFIED; upstream entitlement is not independently established. Residual risk accepted.
HISTORICAL DEPTH: not documented in dataset descriptions; measure original-file
coverage after capture. Only a bounded common interval will be normalized.
AUTOMATION STATUS: use the site's public file-download route for these five files;
no site crawl, protected API access, rate-limit bypass or production polling.
SAMPLE USE STATUS: RESEARCH_FIXTURE_USE = ACCEPTED_WITH_RESIDUAL_RISK.
KNOWN LIMITATIONS: upstream supplier/collection method unspecified, adjustment and
availability timing unverified, selected company cohort, no historical-universe claim.
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED. PRODUCTION_DATA_CLEARANCE = OPEN.

## Verified before acquisition

All five records explicitly identify CC BY 4.0, version 1, the same two contributors,
and stock-performance research/analysis/forecasting as their purpose. The metadata
review found no specific contrary evidence of unlawful upload. This is a scoped
review, not a warranty or an independent verification of every upstream right.
Publication dates below concern the research datasets, not the market rows.

| Dataset title / security | DOI | Publication date | Original filename |
| --- | --- | --- | --- |
| Dataset: 3M India Limited (3MINDIA.NS) Stock Performance | [10.17632/htsn46xjjg.1](https://data.mendeley.com/datasets/htsn46xjjg/1) | 2024-05-16 | 3MINDIA.NS_stock_data.csv |
| Dataset: ABB India Limited (ABB.NS) Stock Performance | [10.17632/259bpc8672.1](https://data.mendeley.com/datasets/259bpc8672/1) | 2024-05-20 | ABB.NS_stock_data.csv |
| Dataset: Archean Chemical Industries Limited (ACI.NS) Stock Performance | [10.17632/8cyyf8w274.1](https://data.mendeley.com/datasets/8cyyf8w274/1) | 2024-05-22 | ACI.NS_stock_data.csv |
| Dataset: 360 One Wam Limited (360ONE.NS) Stock Performance | [10.17632/5gs6gnfw59.1](https://data.mendeley.com/datasets/5gs6gnfw59/1) | 2024-05-17 | 360ONE.NS_stock_data.csv |
| Dataset: Aditya Birla Sun Life AMC Limited (ABSLAMC.NS) Stock Performance | [10.17632/h44srzgd5c.1](https://data.mendeley.com/datasets/h44srzgd5c/1) | 2024-05-22 | ABSLAMC.NS_stock_data.csv |

Repository: Mendeley Data. Contributor ORCIDs in repository metadata:
Jagadish Tawade 0000-0003-2070-1763; Nitiraj Kulkarni 0009-0009-5423-6119.
Apparent source: author-deposited stock-history CSVs with NSE-style `.NS` labels;
original upstream vendor, collection method and historical revisions are UNKNOWN.
Date range is not stated in the descriptions; it must be measured, not inferred.

## Permission evidence and limits

[Mendeley terms](https://www-prod.elsevier.com/legal/elsevier-mendeley-terms-and-conditions)
sections 3.2-3.3 apply the selected research-data licence and require uploaders to
represent original or licensed/cleared content. Sections 3.4-3.6 restrict scraping
and inappropriate access; this work uses only specifically selected public files.
The [CC BY 4.0 licence](https://creativecommons.org/licenses/by/4.0/) permits copying
and adaptation subject to attribution, licence linkage and indication of changes.
Mendeley's dataset-page footer explicitly distinguishes open-access CC content
from its general reservation of rights.

| Intended local educational/research use | Evidence | Project decision |
| --- | --- | --- |
| Local research | VERIFIED open-licence grant plus uploader representation | ACCEPTED_WITH_RESIDUAL_RISK |
| Local retention | VERIFIED same grant | ACCEPTED_WITH_RESIDUAL_RISK |
| Normalization | VERIFIED adaptation grant | ACCEPTED_WITH_RESIDUAL_RISK |
| Feature experimentation | VERIFIED adaptation/research grant; no feature engine now | ACCEPTED_WITH_RESIDUAL_RISK |
| Backtesting/replay | VERIFIED research/adaptation grant; no backtester now | ACCEPTED_WITH_RESIDUAL_RISK |
| ML research | VERIFIED broad reuse/adaptation grant applied under D36 | ACCEPTED_WITH_RESIDUAL_RISK |
| Derived internal output | VERIFIED same grant | ACCEPTED_WITH_RESIDUAL_RISK |
| Independently verified underlying supplier entitlement | UNKNOWN | Residual risk retained |
| Production/live market-data use | UNKNOWN | NOT_CLEARED |

These VERIFIED labels describe the published grant/representations, not a guarantee
of upstream ownership. No endorsement, legal-risk-zero or production approval claim.
AlphaLens policy for this milestone does not publish raw or normalized third-party
records, despite the licence's redistribution permission; attribution and metadata
are retained in Git. The records remain local research fixtures.

## Access findings

The authenticated gateway documented at [API Docs](https://data.mendeley.com/api/docs/)
returned 401 to a metadata GET; no credentials were sought and that route was stopped.
The public dataset page separately exposes `publicApiBaseUrl=/public-api`; its
published client explicitly uses anonymous file listing and public download URLs.
Five specific file listings returned 200 with filenames, byte sizes and SHA256.
No protected gateway endpoint or `/api/` scraping route is used for acquisition.
[robots.txt](https://data.mendeley.com/robots.txt) restricts `/api/` and administrative
paths, not the public download paths used here. This is not approval for bulk crawling.

Acquisition encountered transient 502 responses and one HTTP 200 JSON error body
instead of CSV. The size/hash checks rejected it. The version-pinned public link
(`file_downloaded?version=1`) delivered the exact metadata-pinned bytes for all five
artifacts. No bad response was preserved as market data or accepted by normalization.

## Measured capture and mapping

Capture: 2026-10-05, five CSVs, 1,322,193 bytes, all five SHA256 values matching the
repository metadata. The original files contain 12,984 source rows; only 300 source
rows in 2024-01-01 through 2024-03-31 were selected. Observed dates end on 2024-03-28.
The data's 60 observed dates are not an independently verified exchange calendar.
See [capture manifest](research-sample-manifest.json) and
[validation evidence](research-sample-validation.json) for exact coverage and hashes.

The CSV header is an unnamed ISO session-date column, open, high, low, close,
adjclose, volume and ticker. OHLC is parsed as Decimal without rounding; integral
volume is preserved. INR is a reference mapping from the explicitly identified
NSE cash-equity instruments and D01, not a currency column invented in the CSV.
The [ABB quote reference](https://finance.yahoo.com/quote/ABB.NS/) explicitly labels
NSE/INR. This supports the market-currency interpretation, not independent validation
of every price or the files' upstream provenance. Direct quote-page checks for the
other four names returned 429; no retry or access-control workaround was attempted.
No Yahoo time series was acquired or used to replace these Mendeley artifacts.

The manifest's currency_basis describes this mapping. There is no FX conversion.
Dataset IDs plus version and source ticker form snapshot-scoped security IDs;
ISIN, identifier history and permanent NSE IDs remain unestablished.
Source adjclose is retained in source_fields but is not mapped to canonical
adjusted_close because its methodology/version is not documented. All historical
publication/availability/session-close instants remain null. Dataset publication
dates and actual acquisition instants remain separately recorded.

One 3M India source row on 2024-03-15 has missing OHLCV; it remains an explicit
UNAVAILABLE observation at raw row 5403. No canonical bar is emitted for it.
ACI, 360ONE and ABSLAMC each report zero volume on 2024-01-15; those three observed
values are preserved. They are not independently certified as exchange-correct.
No corporate-action, index, sector, fundamental or historical-universe sample is claimed.

## Offline replay and obtaining a local replica

Raw artifacts are read-only in ignored `.local-data/p1/mendeley/<dataset_id>/`.
The committed manifest is metadata only. Required tools are already in uv.lock;
no additional package, account or paid API is required.

Run from the repository root, choosing a new output directory for each saved run:

```powershell
.tools/bin/uv.exe run --offline --frozen python -m alphalens_data.research_sample --manifest docs/data/research-sample-manifest.json --raw-dir .local-data/p1/mendeley --output-dir .local-data/p1/mendeley/replay-2
```

The command re-reads/checksums each raw file twice, normalizes twice, compares bytes,
and saves canonical.json, validation.json and attribution in ignored storage.
It refuses an existing output directory or a target outside `.local-data`.
The real-data tests are offline and skip honestly if these artifacts are absent.

On a fresh checkout, the following bounded development snippet retrieves only the
five version-pinned public links in the manifest. It rejects changed bytes, does
not retry restrictions/errors, does not overwrite existing files, and records the
new replica retrieval time separately from the original capture metadata. A normal
browser download of those same links into the recorded relative paths also works;
run the offline verifier afterward. This is a fixed fixture retrieval recipe, not
a provider framework, crawler or P2 ingestion pipeline.

```python
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import stat
import httpx  # existing locked development dependency

catalog = json.loads(Path("docs/data/research-sample-manifest.json").read_text())
root = Path(".local-data/p1/mendeley").resolve()
root.mkdir(parents=True, exist_ok=True)
with httpx.Client(timeout=60, follow_redirects=True) as client:
    for artifact in catalog["artifacts"]:
        target = (root / artifact["raw_relative_path"]).resolve()
        if not target.is_relative_to(root):
            raise RuntimeError("Invalid local path")
        if target.exists():
            payload = target.read_bytes()
            if hashlib.sha256(payload).hexdigest() != artifact["sha256"]:
                raise RuntimeError("Existing artifact mismatch; never overwrite")
            continue
        try:
            response = client.get(artifact["download_url"])
        except httpx.HTTPError:
            raise SystemExit("Download failed; request details redacted") from None
        if response.status_code != 200:
            raise RuntimeError(f"Download stopped: HTTP {response.status_code}")
        payload = response.content
        if (
            len(payload) != artifact["byte_size"]
            or hashlib.sha256(payload).hexdigest() != artifact["sha256"]
        ):
            raise RuntimeError("Size/hash mismatch; no sample accepted")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(payload)
        target.chmod(stat.S_IREAD)
        receipt = {
            "replica_acquired_at": datetime.now(UTC).isoformat(),
            "doi": artifact["doi"],
            "sha256": artifact["sha256"],
            "source_url": artifact["download_url"],
        }
        with (target.parent / "replica-receipt.json").open("x") as output:
            json.dump(receipt, output, indent=2)
```

Replaying the committed catalog reproduces the original recorded acquisition, not
the date of a new download. Never reuse that historical ingestion timestamp as a
new live capture time. Preserve the replica receipt and the attribution below.

## Attribution and future use

For each dataset cite: Tawade, Jagadish; Kulkarni, Nitiraj (2024), the exact title
above, Mendeley Data, V1, the corresponding DOI, CC BY 4.0. Original artifacts are
unchanged; canonical output is a bounded, schema-normalized derivative. Dataset
authors do not endorse AlphaLens. Preserve this notice alongside local outputs.

Research-fixture success establishes parser/replay/provenance behaviour only.
Publication/availability, price basis, action adjustment, identifier continuity,
calendar completeness and departed securities remain unverified. No claim of
unbiased market-wide performance, solved survivorship bias or PIT-safe predictions.
