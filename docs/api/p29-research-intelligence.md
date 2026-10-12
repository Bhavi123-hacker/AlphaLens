# P29 authenticated research intelligence API

The P21 single-operator authorization, loopback host/origin restrictions, response
bounds and original research envelopes apply to every new endpoint. No new write,
public webhook or provider collection endpoint is introduced.

| GET /api/v1/intelligence route | Parameters | Evidence |
| --- | --- | --- |
| /regime | session optional observed date; sessions1-10, default5 | archival timeline, strict PIT and VALID-only sensitivity |
| /drift | session optional; sessions2-10, default5 | earlier-reference empirical features/cohort diagnostic |
| /reliability | horizon1/5/10/20 optional; phase development/2025/2026 optional | preserved evaluation reports only |
| /passport/{security_id} | start/end optional valid interval | actual selected identity, features, hashes and blockers |

401 unauthenticated;403 foreign origin/unauthorized;422 invalid/unobserved scope;
429 bounded read occupied;503 unavailable underlying evidence. Original research
503 is never transformed into a successful prediction. Read-capacity retries
remain bounded and only apply to explicit local READ_CAPACITY responses.

Two-window LRU cache keys include selected dates, dataset IDs and every immutable
source path,size,mtime,expected SHA. Sources are checksum-verified through the
existing reader. One bounded projection per partition covers the selected window.
Limits:20,000 identities,220,000 source rows,50,000 rows/partition,1-10sessions,
existing query timeout/reader permits. No private account data is cached here.
Source revisions change fingerprints; cache cannot authorize inference.

New frozen OpenAPI snapshot: p29-openapi.json; old snapshots are preserved.
Typed frontend schemas require unavailable current forecast/shortlist,
false inference authorization and null confidence percentage.
