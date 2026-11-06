# Operator-downloaded NSE final EOD recovery

Implemented 30 October 2026. This adapter makes **no network requests**. The
operator must legitimately obtain the file and establish source-specific private
retention/research rights. Public availability alone is insufficient. No actual
operator file or permission grant was found in the campaign's checked locations;
the importer has only been exercised in disposable TEST_ONLY stores.

A fresh filename-only search on 30 October checked the three named AlphaLens
roots (`D:\AlphaLensStorage`, `D:\al-research`, `C:\Users\Dell\AlphaLens`), without
following reparse entries. No `alphalens_manual_eod_recovery.zip` or official-named
final NSE CSV/ZIP was found. One old test directory in the C-drive checkout denied
access; that limitation is retained in the private search log. No permissions were
changed and this result does not assert absence outside the checked scope.

`scripts.nse_udiff_review` previews and imports the exact
`BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv[.zip]` file. The ZIP contains one
same-name CSV, without paths, links or encryption. Limits are 8 MB compressed,
64 MB expanded and 100,000 rows. The exact 34-column schema and STK/CM/NSE values
come from the [official NSE format publication](https://www.nseindia.com/static/resources/forms-formats-members),
updated 30 June 2026. The reviewed workbook SHA256 is
`b9f2fa369af20381374cdb40c3ebc96c43029401e057225599cfe63b288ba3e8`.
The [official report page](https://www.nseindia.com/all-reports) identifies the
CM-UDiFF Common Bhavcopy Final product. Neither page is scraped by this adapter.

Preview requires an existing checksum-verified official session receipt from the
existing AlphaLens calendar store. Filename, trade date and business date agree;
the official close precedes documented publication, retrieval and review.
Provenance records contain `source_url` (the exact official archive URL),
`raw_sha256`, aware `published_at`/`retrieved_at` and `publication_reference`.
The operator's provenance statements remain explicit statements rather than
cryptographic proof of the download origin. The import gate additionally binds
rights and publication evidence documents by their file SHA256.

ISIN checksum/class, symbol, NSE exchange, series and instrument key must map
unambiguously to the dated official master. This is current identity mapping,
not historical-universe evidence. Unsupported rows have counted exclusion reasons.
Malformed schemas, mixed sessions and duplicate identity/series rows reject the
file. Decimal prices, OHLC inequalities, integer nonnegative volume, derivative
fields and ambiguous sessions are checked. Zero/missing prices are excluded,
never filled. Duplicate source slots and conflicting revisions are explicit.

Run with the existing private interpreter and the release's pinned PYTHONPATH:

```powershell
python -m scripts.nse_udiff_review preview --source <official-file> --provenance <provenance.json> --master-root <nse-universe> --calendar <checked-session.json> --output <new-private-candidate.json>
```

The preview does not import, publish observations or run ML. It produces the
candidate SHA256 to review. Before a live import the operator must explicitly
approve that checksum and the exact source/destination/session/instrument list.
The approval JSON contains:

```json
{
  "candidate_id": "<reviewed candidate SHA256>",
  "raw_sha256": "<reviewed file SHA256>",
  "source": "NSE_CM_UDIFF_FINAL_OPERATOR_DOWNLOAD",
  "destination": "<absolute approved private source directory>",
  "session": "YYYY-MM-DD",
  "instrument_keys": ["<exact sorted NSE instrument keys from candidate>"],
  "mutation_scope": "APPEND_NSE_MANUAL_EOD_SOURCE_ONLY_NO_MODEL_OR_PROVIDER_MUTATION",
  "rights_scope": "PRIVATE_RETENTION_AND_RESEARCH_OF_THIS_EXACT_NSE_SOURCE",
  "operator_approval_reference": "<actual approval reference>",
  "approved_at": "<aware timestamp>",
  "expires_at": "<aware expiry timestamp>",
  "rights_evidence": {"path": "<private document>", "sha256": "<document hash>"},
  "publication_evidence": {"path": "<private document>", "sha256": "<document hash>"}
}
```

Only after that approval:

```powershell
python -m scripts.nse_udiff_review import --source <same-file> --candidate <candidate.json> --approval <approved-scope.json> --approve-candidate <exact-SHA256> --root <approved-private-source-directory>
```

Imports use the existing kernel writer lock and immutable, checksum-bound receipt
publisher. All records for a candidate become visible through one atomic receipt;
an orphan raw checkpoint is reusable after interruption. Repeating the approved
candidate adds zero observations. Reads verify the retained raw checksum and
candidate hash. Source files and previously accepted records are never overwritten.

The normalized fields match the existing OHLCV vocabulary, but source and basis
remain `NSE_CM_UDIFF_FINAL_OPERATOR_DOWNLOAD` and
`NSE_EXCHANGE_REPORTED_UNADJUSTED_EOD`. `manual_eod.load` exposes that qualified
source namespace to explicit consumers. It does **not** merge with the model's
split/bonus-adjusted Upstox series. Corporate-action, adjustment and model-domain
qualification are required before an explicit downstream migration. Importing
these files therefore cannot by itself pass the fresh-ML gate. NSE recovery does
not provide BSE observations. No live protected-store import was performed.
