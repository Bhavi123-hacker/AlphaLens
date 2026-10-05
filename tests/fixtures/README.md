# TEST-ONLY fixtures

P3 `p3/TEST_ONLY.csv` exercises transparent quality/anomaly/gap checks.
P4 `p4/TEST_ONLY.universe.json`, prices and checksum-pinned attribution marker
exercise A-H listing/departure/symbol/type/availability/quality cases. All invented
IDs, dates and facts are TEST_ONLY, not NSE records. The fixture builder writes
raw/canonical/report/snapshot outputs to ignored storage, never market data to Git.

Every constructed price, security, publication, revision, membership, credential-like
string and capability in tests is TEST-ONLY. They are boundary/edge cases, not
historical market data, provider evidence, predictions or performance results.

Records carry `provenance.origin=TEST_ONLY`. Replay manifests retain this origin.
Production sample evaluation rejects TEST_ONLY records unless explicitly invoked
in TEST_ONLY mode. Tests do not populate product endpoints or persist datasets.

Real CC BY Mendeley research captures exist only in ignored
`.local-data/p1/mendeley/`. They carry REAL_RESEARCH_FIXTURE, never TEST_ONLY or
REAL_PROVIDER. The tracked manifest contains attribution, metadata and hashes,
not market rows. `test_research_sample.py` validates these actual local artifacts
and explicitly skips when absent on another checkout; it never downloads or
substitutes synthetic data. See docs/data/research-fixture-source.md for retrieval.
A passing synthetic test does not establish real data, PIT suitability or production clearance.

## P2 constructed fixtures

`p2/TEST_ONLY.csv` and its explicit spec are deterministic constructed examples.
Their prices, dates, symbols and currency definition are TEST_ONLY, never historical
market evidence or investment-performance results. P2 outputs preserve this
classification and always set production_claims_permitted=false.
