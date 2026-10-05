# TEST-ONLY fixtures

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
