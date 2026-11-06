# Performance and hardware — 24 October 2026

Status: **PARTIAL**. CPU inference is operational; supported GPU acceleration and a complete same-day stage-by-stage production benchmark are not established. This campaign did not repeat training, historical fits or backtests.

## Measured environment

Read-only `Get-CimInstance Win32_Processor`, `Win32_ComputerSystem`, `Win32_VideoController` found:

| Item | Measured value |
| --- | --- |
| Processor | Intel Core i5-1235U, 10 physical cores, 12 logical processors |
| Physical RAM | 16,849,293,312 bytes (15.69 GiB) |
| GPU | Intel Iris Xe Graphics, driver 32.0.101.7085 |
| Shared Python environment | Python 3.12.4; NumPy 2.5.3; scikit-learn 1.7.2; PyTorch absent |
| GPU capability probe in that environment | `torch_version=null`, `cuda_available=false`, `xpu_available=false` |
| Node on PATH | 20.17.0; below frontend's required >=22.23.3 <23 |
| Existing supported local Node | `D:\al-research\p18-runtime\node-v22.23.3-win-x64\node.exe` |

The earlier optional framework environment used CPU-only Torch and demonstrated no CUDA/XPU support. This installation has not acquired a supported Intel GPU backend. No driver/framework install, accelerator selection, paid service or model replacement is needed for release. CPU remains the fallback and active reference implementation. Shared graphics memory is not dedicated VRAM or an accelerator capacity guarantee.

## Fresh bounded inference measurement

Executed `scripts/windows/project-python.cmd .local-data/completion-20261024/cpu_benchmark.py`. The private script loads the existing numeric JSON model, limits BLAS to two threads, runs one warmup and five measured trials per case, and checks every result against `sequence.predict`. Inputs are explicitly **TEST_ONLY zero numeric arrays**, shape `N×20×8`, for throughput and equation compatibility. They are **not genuine market features, additional eligible stocks, forecasts or validation observations**. Model SHA-256: `062caac5753ec836208e82514e27c0b270f339c2709c1f4ea3b4a63a73626733`.

| TEST_ONLY rows | Reference CPU median | Batch-128 CPU median | Maximum absolute difference |
| ---: | ---: | ---: | ---: |
| 43 | 0.056492 s | 0.046536 s | 0 |
| 500 | 0.327624 s | 0.439260 s | 0 |
| 1,000 | 0.445429 s | 1.079331 s | 0 |

These measurements ran while storage inventory and candidate dependency preparation shared the workstation. They exclude model loading, feature construction, database persistence and provider acquisition. They establish bounded CPU execution/parity under that load, **not a general speedup** or production throughput guarantee. No GPU executed; GPU speedup is unavailable. No predictions were persisted and no provider GET was issued. Exact result: `.local-data/completion-20261024/cpu-benchmark.private.json`.

For comparison, the [21 October saved-input benchmark](../development/alphalens-2026-10-21-gpu-expansion-verification.md) reconstructed 43 genuine saved sequences and exactly reproduced their scores. Its quiet CPU reference medians were 0.002577 s for 43 inputs, 0.017583 s for 500 repeated inputs and 0.040021 s for 1,000 repeated inputs. Those are historical measurements with different inputs/load; their difference from today's fixture run is not an attributed regression or improvement. Repeated inputs did not qualify 1,000 actual securities.

## Pipeline performance and safe choices

| Stage | Current evidence / release decision |
| --- | --- |
| Live ingestion | No additional authorized live collection was started. Existing scheduled receipts report actual attempts; HTTP latency cannot be inferred from Task Scheduler success. New ingestion throughput benchmark: **BLOCKED_APPROVAL** for extra requests. |
| Feature generation | Existing source/schema-compatible feature builders retained. No incremental cache that could obscure availability clocks was introduced. Complete fresh stage timing: **IMPLEMENTED_UNVERIFIED**. |
| Model inference | Fresh bounded numeric equation parity above; compatible saved-data checks and model eligibility remain separate. **COMPLETE_VERIFIED** for this measured CPU path. |
| Training | Original trained models preserved. Training timing is historical; no same-day rerun merely for performance. **NOT_STARTED** for new training benchmark by design. |
| Database | No index migration or production mutation. Actual startup/read-only connection/latency evidence belongs to [release tests](../release/2026-10-24-test-results.md). |
| API/UI | Candidate startup, authenticated smoke/browser checks and actual test timings belong to [release tests](../release/2026-10-24-test-results.md). No invented p95/p99. |
| Storage | Inventory uses cached directory-entry metadata and skips reparse traversal; no cleanup or protected-data movement. See [storage audit](02-storage-recovery.md). |

Retain the established bounded CPU predictor, worker/concurrency locks, per-run/day request reservations and incremental acquisition. Optional batching remains opt-in; it is slower on the larger measured cases. Do not increase worker counts on a 16 GB workstation while the full test/inventory workload is active. A memory-bound optional GPU fallback is infrastructure, not evidence of supported acceleration. No performance claim changes model acceptance, data rights, freshness or forecasting gates.
