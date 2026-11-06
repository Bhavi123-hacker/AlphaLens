# P29 measured performance and resource limitations

Windows Python3.12.4/Node22.23.3,16GiB host, real preserved8.5GB archive.
Measurement on2026-10-12; original source/report paths and checksums unchanged.
Read-only diagnostic process; no estimator loading, fit, prediction or evaluation.

| Actual workload | Seconds |
| --- | ---: |
| Two-session intelligence window, first process read |12.212|
| Same two-session regime with bounded immutable cache |0.147|
| Drift reusing the same projected window |1.223|
| Canonical stock Evidence Passport |0.340|
| Stored h1 development Reliability Matrix |0.019|

Warm response is98.8% less elapsed than first read in this sample. This is a
cold-process/warm-cache measurement, not a controlled old-vs-new code benchmark
or full-universe ingestion throughput. OS filesystem cache state was not cleared.
Private complete results stay D:/al-research/p29-runtime/archival-diagnostics-private.json.

Window projector reads each existing partition once for the whole selected date
window, rather than independently requesting every date. Bounded2window cache,
checksums/source fingerprints and query deadlines remain enforced. Heavy model
serialization/discovery imports now occur only after the original authorized
load gate. CLI stop no longer needs ML/research-reader imports, preserving safe
shutdown under memory pressure. No original inference loading/type policy changes.

Private compiled new Intelligence page13.11kB/4.22gzip, Passport8.33kB/3.35gzip;
separate lazy chart engine681.15kB/228.27gzip warning retained. Public synthetic
package initially1,236.41kB/425.88gzip main plus681.14kB/228.26gzip charts; larger
main includes all generated examples. No false claim of reduced ECharts chunk.
No validation/auth/provenance was disabled for performance.

Machine commit pressure repeatedly fell below1GiB because unrelated Dell/WSL/
Oracle services used substantial memory. Concurrent Node launch failed with
paging-file allocation error; initial authentication/API tests encountered memory
allocation failures. Only owned test servers were cooperatively stopped; no
unrelated service, pagefile, security Argon parameters or dependency environment
was modified. Sequential verification and bounded source reads are required.

## Rejected prefetch experiment and operational settings

Bounded read of the same canonical+feature partitions for one canonical security
(242rows each): default scanner0.07507s vs disabled batch/fragment readahead
0.08169s; both Arrow peak15,149,824bytes and identical SHA986a9c933f3b64d872ebd9ba5f473fdc8a4332c27a46c88bf121c143b59399c8.
No memory benefit and slightly slower in this sample; not adopted. Private
reproduction script/receipts remain in D runtime; no source scanner change.
[Arrow scanner documentation](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html)
explains the readahead/memory tradeoff; measurement does not establish a general
result for every archive/workload.

Windows startup now defaults native BLAS/OpenMP/NumExpr threads to1 for the read
server only, preserving explicit operator overrides and frozen training scripts.
Actual API after bounded reads was369,426,432privatebytes/16threads in the sampled
process; no controlled before/after process-memory ratio is claimed. Optional
Chromium renderer count2/JSheap256MiB caps are test settings only; no sandbox/
auth weakening. A temporary1-reader test configuration caused contention during
legacy chart fan-out; restored original2reader setting and focused RELIANCE
scenario passed7.5s. Default backend security/read-response bounds unchanged.
