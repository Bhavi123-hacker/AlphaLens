# 21 October: scheduled collection, local acceleration and expansion verification

Branch: `alphalens-gpu-operational-verification`, from `aa021ddbc1e73bb7b9fb2b82c087151db7c2e530`. Production repair remains `56e4245`. This is an **interim evening verification**, not acceptance of the later 21:30/22:30 attempts. No production deployment, manual acquisition, model training, forecast publication, scheduler change or quota change was performed by this work.

## Actual collection result

**SOURCE_PUBLICATION_PENDING as of the completed 20:30 attempt.** The scheduler and worker ran, but no qualified 21 October candle was accepted. The next two authorized attempts must be assessed from their own eventual evidence.

| Item | Observed result |
| --- | --- |
| 20:30 task | Started 20:30:01 IST; worker started 20:30:08.979395 and completed **20:32:05.020682 IST**. Windows result 0; terminal state **PARTIAL_OR_PUBLICATION_PENDING**, not successful fresh collection. |
| Target/coverage | Target 21 October: **0/500 qualified**, **500 pending**. **250 distinct securities queried**, all returned status success with **empty candle arrays**. Other 250 were not queried in this batch. No new quality rejection, authentication failure or rate-limit failure was reported. |
| New qualified candles | **0**. Retained coverage stays **447,982 qualified historical observations**, latest qualified session **19 October, 499/500**; RRECL remains missing. These older observations do not prove today's update. |
| Actual provider usage | **251 shared GET attempts, 251 completed HTTP 200, 0 unresolved**. 250 candle attempts plus one official 22 October timing response; no action GET was justified by an empty response. Master refresh GETs: 0; all configured 500 identities remained eligible in the dated cached master. |
| Reservations | **600 reserved**, one collecting attempt, **1,200 daily reservation capacity remains**. Capacity is not authorization for another manual run. Existing crash reservations remain intact. |
| Shared rolling request peaks | **8/second, 251/minute, 251/30 minutes**, below the configured 50/500/2,000 limits. No concurrent collecting worker or new cooldown violation was observed. |
| Research | No new eligible 21 October model inputs, scores or forecasts. Saved scoring remains **302 V2 scores dated 19 October**, **43 sequence scores dated 16 October**. Last worker scoring state `NO_FUTURE_ENTRY`: the old frame's next opening had already passed. No backdated forecast was created. |
| Forecasts/outcomes | **633 raw V2 forecast records, 602 unique model/security/session decisions, 0 outcome records, 0 matured outcomes**. All 633 pre-window bodies preserved. No accuracy/profitability claim follows. |
| Later slots | **21:30 and 22:30 PENDING** at this verification. No collecting process was left waiting for those slots. |

Primary evidence: `.local-data/nse-market-expansion/operational/runs/e71cb300c51841b5a1fde1df098ae04e.{attempt,started,done}.json`, associated checked diagnostics, `.local-data/gpu-verification-20261021/collection-audit.private.json`. The audit verifies raw-response checksums and source identity against the frozen plan; all 250 queried responses contained zero candles. Its own provider request count is **0**. Official saved 21 October timing is 09:15–15:30 IST; official 22 October timing was received at **20:30:53.590356 IST**. Empty responses establish unavailable observations at receipt time; they do not establish whether the cause is publication delay or another provider coverage issue. No additional probe was authorized or issued.

RRECL is `NSE_EQ|INE0AK901016`. Existing 19 October empty evidence and today's empty catch-up response remain preserved. Unknown missing observations were neither filled nor discarded. A later valid observation is not evidence that the earlier gap traded.

## Scheduler and Windows reliability

Both task definitions remain byte-equivalent to the protected baseline:

| Task | Configuration / XML SHA-256 |
| --- | --- |
| `AlphaLens-Private-NSE-Market-Research` | Interactive operator, limited privilege; IgnoreNew; unchanged 20:30/21:30/22:30 IST; 250 stocks/run, 600 reserved/run, 1,800/day, three attempts/day, 60-minute cooldown and 31-day catch-up. XML `a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820`. |
| `AlphaLens-Private-EOD-Watchlist` | Separate original 08:30 task. Last observed start **21 October 20:16:45**, result **1**; saved receipt `DAILY_INDEPENDENT_CLOCK_UNAVAILABLE`. No provider GET was made by that failed clock preflight. XML `d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`. |

Read-only System log inspection found a Modern Standby exit event (507, record 332921) before the collection window. The 20:30 expanded worker has a normal terminal receipt; no interruption was observed in that run. This does **not** identify the initiator of the earlier `0xC000013A` interruptions. Task Scheduler Operational history remains disabled; no power/audit/task settings were changed. Prior standby association remains distinct from proven causation.

Evidence: `hardware.private.json`, `tasks-before.private.json`, the worker receipts above and `.local-data/p34-runtime/daily-last-run.json`. Task state and next trigger were queried directly from Windows, not inferred from historical registration.

## Hardware and actual acceleration eligibility

| Fact | Measured result |
| --- | --- |
| GPU | **Intel Iris Xe Graphics**, driver **32.0.101.7085**. No NVIDIA adapter or `nvidia-smi` detected. |
| Graphics memory | DirectX diagnostic: **128 MB dedicated, 8,034 MB shared**, 8,162 MB displayed total. The shared amount is system memory, not dedicated VRAM. WMI's 2,147,479,552-byte AdapterRAM value is not used as authoritative dedicated VRAM. |
| Usage snapshot | At 20:29, adapter counters reported 0 dedicated bytes and approximately 948 MB aggregate shared usage across two adapter instances. This is a dated sample, not a permanent allocation or available compute-memory guarantee. |
| CPU/RAM | **i5-1235U, 10 cores / 12 logical processors**; 16,849,293,312 physical RAM bytes. Approximately 3.44 GiB OS-reported free memory at the initial sample. |
| Main application environment | PyTorch not installed; the reviewed NumPy CPU predictor works without it. |
| Existing isolated sequence environment | **PyTorch 2.14.1+cpu**, CUDA unavailable, Intel XPU unavailable, DirectML not installed. No package, graphics driver or system setting was changed. |

Evidence: private WMI/performance-counter snapshot `hardware.private.json`, DirectX `dxdiag.private.xml`, explicit framework probe and saved benchmark capability. The [PyTorch 2.14 validated Intel client hardware list](https://docs.pytorch.org/docs/2.14/notes/get_start_xpu.html#intel-client-gpu) lists Arc and Core Ultra/Arc families; this 12th-generation Iris Xe is not listed. Therefore **no supported working GPU training/inference path or GPU speedup was demonstrated on this installation**. Installing a CUDA wheel cannot accelerate this non-NVIDIA adapter. No speculative driver/framework migration was attempted.

## Implemented isolated runtime and measured replay

`workers/nse_market/sequence_runtime.py` adds **opt-in** bounded-batch inference over the existing numeric JSON LSTM. Production `sequence.predict`, registered training code and all model artifacts remain unchanged. The optional CUDA/XPU path uses the same fixed float64 gate equations, no pickle/executable artifact loading, full-batch parity within 1e-10 and identical classification boundaries. Invalid feature order/scaling/nonfinite input fails before device probing. Memory headroom, batch/input limits and explicit fallback cover unavailable devices, driver errors, insufficient/unknown device memory, unsupported kernels and execution failures. Mixed execution is disclosed. Real GPU behavior is **not hardware-verified** here; failure paths use clearly TEST_ONLY simulated backends. CPU remains the default, and no training acceleration was activated.

`scripts/benchmark_sequence_runtime.py` reconstructs **43 genuine saved 16 October sequences** from qualified source history and the exact 20×8 contract. It reproduces saved scores with **0 maximum error** and verifies the pinned model SHA `062caac5753ec836208e82514e27c0b270f339c2709c1f4ea3b4a63a73626733`. It makes no provider calls, trains nothing and publishes no forecasts. The 500/1,000 rows below repeat those same 43 eligible inputs for a throughput stress test; they are **not** 500/1,000 newly eligible securities.

Final quiet benchmark: five measured trials after one warmup, two BLAS threads, observed 20:48:13–20:48:29 IST; times exclude source reconstruction, feature generation, model loading and forecast persistence.

| Sequence inputs | Existing CPU reference median | Bounded CPU batch-128 median | Auto selection median / completed backend |
| --- | --- | --- | --- |
| 43 genuine unique sequences | **0.002577 s** | **0.003813 s** | **0.003913 s / CPU fallback** |
| 500 repeated saved sequences | **0.017583 s** | **0.023934 s** | **0.022520 s / CPU fallback** |
| 1,000 repeated saved sequences | **0.040021 s** | **0.046716 s** | **0.055622 s / CPU fallback** |

All outputs matched the original predictor exactly in these trials. **No GPU speedup is available; bounded batching was slower on this small workload.** Its benefit is memory bounds/fallback infrastructure, not a measured acceleration claim. Two earlier measurements during concurrent checks were materially slower and remain retained (`benchmark-main.private.log`, `benchmark-torch.private.log`); they are not discarded favorable/unfavorable model results. This is execution benchmarking, not training or model selection. The native CPU predictor is consequently retained.

Latest checked benchmark pointer: `.local-data/sequence-runtime/benchmark-latest.json`; private audit/benchmark files under `.local-data/gpu-verification-20261021/`. Numeric 1,000×20×8 float64 inputs require **1,280,000 bytes** before working tensors; default working budget 32 MiB, input ceiling 128 MiB, batch ceiling 4,096. GPU allocation additionally requires independently reported free-memory headroom; unknown capacity falls back. This does not remove source/feature eligibility requirements.

## 1,000-stock feasibility: FAIL under current daily capacity

The existing deterministic proposal was independently revalidated against the checked master and frozen 500-stock plan: **1,000 unique keys and ISINs**, original 500 preserved, no unsupported common-equity classifications or duplicate ISINs. Candidate SHA `8f7fd1745454547d149a3fdafc755a2286dc8dceb0b9d5c9c244395e90597405`. Dated master **20 October 22:30:16.832160 IST**, **3,185** eligible identities. Earlier 3,198 belongs to another dated snapshot. Additional 500 histories, listing-time evidence, actions, liquidity and model vectors remain **unqueried/unverified**. Current-master presence is not historical eligibility or provider-accessibility proof.

| Capacity | Result |
| --- | --- |
| Current three slots ×250 stocks | At most **750 stock attempts/day**, insufficient for a fresh 1,000-stock session. |
| All-valid daily stock requests | **1,000 candle +1,000 action GETs =2,000**, before metadata/retries. Already exceeds 1,800. |
| Minimum full batches | **Four ×600 =2,400 reserved/day**, an additional 600/day and one attempt/slot. Declared stock+metadata envelope 2,284 GETs within those reservations, excluding unforeseen retry needs. |
| Recovery | Four-slot simulation with one persistent oldest empty security updates **996**, leaves **4 pending**; five-slot/3,000 reservation scenario updates **999**, leaves the unavailable one pending. TEST_ONLY queue arithmetic, not acquired data. |
| Bootstrap added 500 | Successful path **500 historical candle +up to 500 action GETs**, metadata/retries separately bounded within two 600-reserved batches; separate source/workload approval required. Not executed. |
| Duration/storage planning | Prior measured 250-stock completed runs took 191–391 s: four-batch planning range 12.8–26.1 active minutes plus hourly spacing, not a guarantee. Earlier measured raw/normalization/action evidence extrapolates approximately **3.02 MB/session for 1,000**, additional **1.51 MB/session /33.3 MB per 22 sessions**, excluding models, versioned workspaces, ledgers, master snapshots and backups. Added comparable historical retention roughly 42.3 MB, unverified until a bounded pilot. |

GPU inference speed cannot solve this acquisition capacity deficit or unavailable publication. Existing source permission is narrow private noncommercial research/retention/derived ML, not unrestricted bulk redistribution. Current code intentionally rejects >1,800/day or >3 attempts. **No caps, task definitions, cohort config or activation receipt were changed.**

Full prerequisite/rollback details remain in [1,000-stock readiness](alphalens-1000-stock-expansion-readiness.md). Minimum conditional all-valid proposal: exact frozen 1,000 identities; 250/run; 600/run; **2,400/day and four attempts**; illustrative day-contained **19:30/20:30/21:30/22:30**; unchanged 60-minute cooldown/31-day catch-up. An earlier slot does not guarantee source publication. Recovery alternative five slots/3,000 requires broader approval. Keeping 1,800 supports only separately approved rotating partial freshness, not daily complete coverage. None is activated.

## Monitoring changes and verification

The isolated dashboard now distinguishes **last retained session coverage** from **latest collection target coverage**, and displays actual/reserved requests, saved forecast publication and matured-only evaluation using the previously completed read-only repairs. New saved processing details show capability, dated model/input lineage and measured throughput, explicitly identifying repeated-input stress tests and CPU fallback. Page reads never import PyTorch, run inference or fetch provider data. Missing/corrupt/future-dated benchmark evidence is unavailable, never a fabricated throughput value.

Authenticated compiled browser test on the isolated **8033** server passed, comparing target/retained coverage and saved throughput against actual backend responses, opening point-in-time evaluation, checking no fake accuracy with zero outcomes and checking WCAG A/AA/2.1AA for the operations section. Upstox acquisition was blocked server-side. The isolated server was stopped cooperatively afterward. Native **8017 was not replaced or restarted**.

| Check | Result / evidence |
| --- | --- |
| Targeted backend/data/scheduler/read-only API regression | **82 passed, 1 skipped**, 51.25 s. Optional PyTorch absent in the main environment is the skip, not a GPU pass. `final-targeted-corrected.private.log`. |
| Optional framework runtime tests | **19 passed**, 7.86 s, including actual Torch CPU equation parity and TEST_ONLY GPU failure paths. No actual GPU tested. `optional-torch-tests.private.log`. |
| Frontend | First concurrent run **113 passed, 3 timeouts** in unchanged shell/search tests; focused same-deadline run **15 passed**, quiet full run **116 passed /23 files**, 27.05 s. Initial failures retained; no timeout increase or suppression. |
| Browser/accessibility | **1 passed**, 18.4 s; no operations-section axe violations. `browser-report.private.json` / `browser.private.log`. |
| Static/build | Isolated frontend build passed; Ruff, format, strict mypy and targeted Bandit passed. Final CI/security evidence recorded below when available. |
| Preservation | All **633 baseline forecast bodies** and pinned sequence/V2 artifacts/config hashes match. Original **2,485 frozen files /8,505,278,241 bytes**, **47 alerts**, V1 artifacts/evaluation byte-exact. Account/password, personal records, four credential fingerprints and protected configuration match. Verification writes only separate local receipts. |
| Native processes | App **PID 28760**, PostgreSQL **PID 19512** unchanged; native compiled HTML SHA `d3ba347265100ab748a3ebb9ae7524b9649f821ab99f2fd7b593c9c8b2580f41`. Public demo untouched. |

Final saved-evidence conservation check additionally verified **4,544 protected baseline files**, all **499 previously accepted daily source records and raw-response hashes**, and the **2,503 pre-21-October quota rows**. Their original ordered-row digest remains `8767702190458003c39052eeeb92d69b81a7480348f00de7efd7c53222db7f70`; today's legitimate 251 scheduled attempts are additional rows, not a reset. Evidence: `final-preservation.private.json`, read at 21:02:56 IST. Actual shared usage remained 251 with zero audit-issued provider requests.

### New dependency findings

The audit of the unchanged active environment **failed: nine advisories in two packages**: certifi 2026.7.22 (`PYSEC-2026-4320`) and Pillow 12.3.0 (eight reported CVEs). The failure is retained in `dependency-audit.private.log`. The candidate `uv.lock` updates **only** [certifi to 2026.10.19](https://pypi.org/project/certifi/2026.10.19/) and [Pillow to 13.0.0](https://pypi.org/project/pillow/13.0.0/); lock validation passed. A private isolated overlay of these two patched packages passed pip-audit with **no known vulnerabilities**, loaded the TLS CA bundle and rendered/reopened a real Matplotlib PNG. Production site-packages and the optional CPU research environment are **not updated** and retain the reported findings until a separately approved candidate deployment. A preliminary unsupported audit flag combination produced a usage error; the valid `--path` audit above passed without exclusions.

The prior zero-HIGH/CRITICAL container report is historical evidence, not proof against newly disclosed advisories. Fresh candidate CI/container results are recorded separately below. No advisory is ignored/suppressed and no scanner threshold changes.

### Exact final code CI evidence

Tested implementation commit: **`79c64a6f4a05d7ded0451b9a5bbb17f70d1800c2`**. Later evidence-only documentation commits do not replace this full-history result.

- [Foundation run 39626089270](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39626089270): **FAILED overall**, solely at full-history TruffleHog scanning. Backend/PostgreSQL 17 regression **1,545 passed, 13 skipped**, 284.13 seconds; frozen lock validation, Ruff, formatting, strict mypy, Bandit and installed candidate dependency audit passed. The optional PyTorch test is skipped in the standard environment; it passed separately on actual Torch CPU.
- The same run's rebuilt strict-container job **PASSED** with **0 HIGH /0 CRITICAL**, including runtime imports/auth smoke and unchanged severity/failure policy. Downloaded artifact `.local-data/gpu-verification-20261021/ci-trivy/trivy-results.json` confirms those counts.
- [Frontend run 39626089120](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39626089120): **PASSED**, **116 tests /23 files**, typecheck/lint/build, four isolated synthetic-demo browser checks and npm audit **0 vulnerabilities**.
- Full-history scanner: **0 verified /3 unverified findings, exit 183**. Current check-run annotations match the previously audited historical locations `docs/development/command-log.md:218`, `tests/unit/test_configuration.py:31`, `tests/integration/test_p17_api.py:248`. Their documented context remains test/configuration placeholders; this does not convert the scanner failure into a pass. See [the existing sanitized history audit](../security/final-secret-history-audit.md). No historical rewriting, suppression, detector exclusion, threshold change or fixture alteration was made. A later changed-range success would not erase this full-history failure.

Private exact outputs: `ci-full.private.log`, `ci-frontend.private.log`, `annotations.private.json`, `candidate-full-audit.private.log`. The complete locked candidate dependency set was also independently audited from the frozen transitive export with no known vulnerabilities; production dependencies remain unchanged and still carry the initial findings.

### Host storage blocker

At **21:06–21:08 IST**, `Get-PSDrive C,D` reported **C: 0 bytes free**, D: approximately **115.4 GB free**. GitHub CLI could not write its log cache on C:. This audit redirected only its own CLI cache to `D:\al-research\p28-runtime\gh-cache-root` and retrieved the logs successfully. No system cleanup, private-data movement, power change or production configuration change occurred. Native app/PostgreSQL remain running. System-disk exhaustion is an actual operational blocker requiring operator space recovery before deployment; it is **not proven to have caused** earlier browser latency, control interruptions or today's empty provider responses. The failed C: cache entry was zero bytes; deleting it would not solve the capacity problem.

At **21:10**, the final evidence commit also failed because this worktree's Git metadata is on C:. To recover safely, the audit positively identified **only its three just-downloaded installer wheel caches** (uv 0.11.25, certifi 2026.10.19 and Pillow 13.0.0) by archive metadata and creation window, copied them into `.local-data/gpu-verification-20261021/quarantine-own-install-cache`, verified SHA-256 equality and removed those three redundant cache bodies from C:. **34,270,835 logical bytes relocated**, recoverably; no Git data, credentials, runtime package, market data or personal file was removed. Inventory and reversible source/destination map: `own-cache-inventory.private.json` and `cache-relocation.private.json`. Git commit/push then succeeded. Concurrent host writes mean this is not the net volume-free-space increase: C: still had only **12,447,744 free bytes** at the post-action sample and remains critically constrained. The operator must recover substantial system-drive headroom; this narrow cache relocation is not a declaration of a healthy Windows host.

A private preliminary audit helper used the wrong normalized master field name, then was corrected to `symbol`; no provider call or production write occurred. One targeted pytest command named a nonexistent file and collected **no tests**; the corrected 82-pass run is the evidence above. These command errors are not represented as passed checks.

## Exact approval boundary and next action

1. **Tonight: allow existing 21:30/22:30 tasks to run unchanged.** No manual collection or reservation reset. Read their terminal receipts and revalidate per-security raw/normalized evidence afterward; a zero exit alone remains insufficient. The read-only `collection_audit.py` in the private audit directory records the current target, actual/reserved requests and preserved forecasts without acquisition.
2. **Monitoring/dependency deployment requires approval and host-space recovery.** The full-history secret gate remains failed and must be explicitly accounted for, not waived by calling the frontend/container green. After operator recovery of C: space, an independently reviewed deployment decision and a fresh idle-worker check, create a recoverable config/build/environment backup, promote the tested isolated monitoring frontend/API and staged dependency fixes in an idle window, restart only the owned API as required and run authenticated saved-only smoke checks. A separate collection-environment update must be explicitly included in authorization before touching the existing collector's packages. Roll back to the protected prior environment/config/build on any failure. Do not include a new inference device, model, acquisition, quota or scheduler change. This has **not been deployed**.
3. **1,000-stock acquisition/activation requires separate exact approval and tested capacity changes.** First approve the bounded added-500 bootstrap, verify real history/actions/storage, then choose either the larger daily capacity above or honestly partial rotating freshness. Today's 1,800 limit remains enforced.
4. **No supported GPU acceleration is presently established.** CPU inference is already milliseconds for the measured LSTM math; source availability, validation and acquisition dominate this operational problem. No framework/driver installation or model retraining is needed to finish today's checks.

Final scientific state remains **NO_DEMONSTRATED_EDGE**, zero matured outcomes and zero independently accepted models/rankings. Today’s missing provider observations and future independent evaluation cannot be replaced by faster numerical computation.
