# TEST-ONLY fixtures

Every constructed price, security, publication, revision, membership, credential-like
string and capability in tests is TEST-ONLY. They are boundary/edge cases, not
historical market data, provider evidence, predictions or performance results.

Records carry `provenance.origin=TEST_ONLY`. Replay manifests retain this origin.
Production sample evaluation rejects TEST_ONLY records unless explicitly invoked
in TEST_ONLY mode. Tests do not populate product endpoints or persist datasets.

Licensed real captures are not committed by default. No real sample currently
exists. A passing synthetic replay test does not pass P1's real-ingestion gate.
