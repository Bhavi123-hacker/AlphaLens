# C: recovery and D: storage delivery

**RECOVERY VERIFIED.** Operator-approved A and B are complete. Final check: 2026-10-22T11:19:05.5789964+05:30.
C: has **27,693,944,832 bytes (25.79 GiB) free**, exceeding the 5-10 GB objective.
D: has **61,259,087,872 bytes (57.05 GiB) free**, including the working Docker disk and independent backup.
Source baseline: `da4382242371c17ebdf2cecc620541931b91e313`, branch `alphalens-gpu-operational-verification`.

## Disk measurements

| Point | C: free bytes | D: free bytes |
| --- | ---: | ---: |
| Initial audit, 21 October 21:19:10 IST | 20,635,648 | 115,380,547,584 |
| Immediately before first cache pass | 56,975,360 | 115,333,660,672 |
| Before offline Docker backup, 22 October 10:52:40 IST | 1,589,121,024 | 115,078,139,904 |
| Docker migration verified | 27,693,133,824 | 61,259,091,968 |
| Final | 27,693,944,832 | 61,259,087,872 |

Net C: free-space increase from the initial audit: **27,673,309,184 bytes**. Background host activity also changed free space, including a substantial increase before Docker moved; the entire net difference is not attributed to cache cleanup. Independently accounted actions are the exact cache bytes below and Docker's supported release of its old C: disk. D: intentionally retains both a working disk and its backup.

## Inventory and actions

Metadata-only audit evidence: `.local-data/disk-recovery-20261021/inventory.private.json` and `details.private.json`. This was a targeted scan, not a reconciliation of all Windows storage. Inaccessible entries and reparse targets are not declared empty. Logical sizes below do not imply exclusive physical allocation.

| Original location | Observed bytes | Decision |
| --- | ---: | --- |
| `%LOCALAPPDATA%\pip\Cache` | 74,546,308 | Approved inactive cache files relocated with hashes. |
| `%LOCALAPPDATA%\uv\cache` | 1,050,406,533 logical | **Already a junction to `D:\alphalens-uv-cache`; left unchanged.** Initial root traversal overstated C: recovery by following this D: target. |
| `%LOCALAPPDATA%\npm-cache` | 392,885,988 | Approved inactive packages/cache relocated; no Node runtime moved. |
| `%LOCALAPPDATA%\node-gyp` | 53,577,449 | Approved rebuildable headers relocated. |
| `%LOCALAPPDATA%\GitHub CLI` | 4,640,278 | Only downloaded run logs relocated; its 36-byte device identity stays on C:. Authentication/configuration untouched. |
| User Temp | 691,405,767 | Mixed installers/diagnostics; no blanket purge. |
| Windows Temp | 21,036,188 | Left unchanged. |
| Chrome profile tree | 2,832,448,904 | Active browser; all profiles/cache left unchanged. |
| Edge profile tree | 1,380,142,548 | Left unchanged. |
| JetBrains analysis cache/index | 322,426,233 | Left unchanged, including all local history/settings. |
| User `.cache` | 135,789,692 | Mixed ownership; left unchanged. |
| Active `.codex` state | 4,260,071,446 | Protected; left unchanged. |
| Downloads | 3,989,963,225 | Personal files; left unchanged. |
| Windows Update downloads | 509,156,410 | System-owned; left unchanged. |
| Old C: AlphaLens checkout | 374,140,670 observed | Protected, including shared Git metadata. |
| Docker VHDX | 26,653,753,344 allocated and logical initially | Approved supported migration; full pre-start backup retained. |
| Ubuntu WSL VHDX | 2,036,334,592 allocated and logical | Left in place. |

### A: verified cache relocation

**41,943 files / 525,649,987 logical bytes** relocated. Every source removal is within the four approved C: cache roots; every retained body was rehashed afterward. No incomplete prepared-removal record remains. Existing empty source directories are retained. The already-D: uv cache contributes **zero** C: recovery.

| D: cache category | Files | Verified bytes |
| --- | ---: | ---: |
| `pip` | 287 | 74,546,308 |
| `npm` | 39,213 | 392,885,988 |
| `node-gyp` | 2,368 | 53,577,449 |
| `GitHubCLI` | 75 | 4,640,242 |

Destinations are under `D:\AlphaLensStorage\Caches`; GitHub CLI logs are under `Caches\GitHubCLI\GitHub CLI`. The private `cache-relocation.private.jsonl` records original path, destination, size, SHA-256 and durable pre-removal evidence. Files were opened exclusively; locked files, reparse paths, conflicts and active collectors fail closed. Hash-verified matching copies support interruption replay. Directory validation precedes parallel file work. Temporary pauses/refusals are retained in the journal rather than removed from the audit trail. D-only destination ACLs were enforced before copying. GitHub device-identity conflict was resolved by preserving/excluding that non-cache file, never overwriting it.

Rollback: with consumers stopped, use the journal to verify each D: hash and copy to its original location only if no newer file exists there. Keep the D: copy; never overwrite a newly populated cache blindly. Caches can also be regenerated. No junction or global environment change was created.

### B: Docker supported migration

Offline exclusive-read backup: `D:\AlphaLensStorage\Backups\Docker-20261021\docker_data.vhdx`, **26,653,753,344 bytes**, full source-stream/copy SHA-256 match. Manifest and pre-move Docker settings are retained privately. Backup start/end: `2026-10-22T05:22:40.230448+00:00` / `2026-10-22T05:23:47.296292+00:00` (UTC).

Used **Docker Desktop Settings -> Resources -> Advanced -> Disk image location -> Apply & restart -> Yes, move it**. Docker selected its managed layout:

```text
D:\AlphaLensStorage\Docker\DockerDesktopWSL\disk\docker_data.vhdx
```

`CustomWslDistroDir` is the **only changed Docker settings key**. Stable before/after inventory comparison passed: **15 images, 3 volumes, 5 containers**, including image tags and all container mount references. Mount serialization order changed for one container; the same references were verified without requiring their incidental list order. Original C: VHDX is absent after Docker's completed move. No manual WSL/registry edit, volume prune, VHD unlink or Ubuntu move occurred. Docker Desktop was returned to its original stopped state using its supported CLI.

A version query during restart returned transient HTTP 500; the later engine query succeeded (`29.6.2`) and inventories matched. No application update was installed. Backup verification is a full byte/checksum check, **not a claim that a separate destructive restore was performed**.

Rollback: retain the independent backup and settings record. With Docker stopped and no collector active, use the supported storage-location controls/recovery procedure. Do not automatically restore 26.65 GB to C: and recreate the original disk shortage. Keep the verified D: copies while reviewing any restore; do not overwrite newer Docker data.

[Docker's WSL storage controls](https://docs.docker.com/desktop/features/wsl/) and [offline backup requirements](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/) support this method. [Microsoft warns against manually moving/editing AppData WSL files](https://learn.microsoft.com/en-us/windows/wsl/disk-space).

## D: development defaults

Prepared private operator/SYSTEM storage: `Temp\Development`, `Caches`, `pyc`, `Tests`, `Builds\WebDevelopment`, `Logs`, `Backups`, `MLArtifacts`, `Quarantine`, `Docker`. No AlphaLens production database, model checkpoint, credential or evidence root was moved.

New opt-in helper: `scripts/windows/with-d-dev-storage.ps1`. Child-process-only TEMP/TMP, pip/npm/node-gyp, Ruff/mypy/Matplotlib/Torch caches, bytecode, test scratch and development build/cache output point to D:. uv reuses its existing D: cache. LOCALAPPDATA, APPDATA, USERPROFILE, HOME and authentication/configuration stores retain their original locations for every command, including `gh`. The proposed GH LOCALAPPDATA override was removed after identifying its non-cache device identity; future GitHub CLI cache defaults remain on C:. Original process values are restored on success and failure. User/machine environment and production launchers are unchanged.

```powershell
& .\scripts\windows\with-d-dev-storage.ps1 `
  -FilePath '.\scripts\windows\project-python.cmd' `
  -CommandArguments @('-c', 'import tempfile; print(tempfile.gettempdir())')
```

Expected: `D:\AlphaLensStorage\Temp\Development`. Use this for new development commands; commands launched outside it keep their previous defaults. Production task/start commands were not rerouted. Existing production logs/data already on D: stay at their original paths. The node-gyp setting follows its [documented process configuration](https://github.com/nodejs/node-gyp#environment-variables).

## Collection safety, tests and preservation

An overnight elapsed-time gap caused the cache guard to time out and pause. On 22 October, Task Scheduler showed Ready while surviving collector processes were still active; those processes were not interrupted. Backup began only after their exit and the terminal receipt `operational/runs/69d81cf9042348269f5d838fee01b4a2.done.json` at 10:51:33 IST. The initiator/cause of the elapsed gap and scheduler interruption was not established by this disk operation.

- PASS: exclusive read/delete-on-close on owned D: canary; 32 concurrent TEST-ONLY relocations; locked-file exclusion; matching-copy replay; conflicting destination rejection.
- PASS: PowerShell parsing, nonzero Python child exit propagation, success/failure environment restoration, unchanged user/machine environment, Python imports and D: temporary/bytecode paths.
- PASS: original GitHub CLI device identity unchanged after an actual wrapper `gh --version` invocation.
- PASS: every actual relocated body rehashed; approved-root removal check; no unresolved prepared-removal entry.
- PASS: all **633 baseline forecast bodies** unchanged; pinned model/report/config hashes match; private production roots accessible; CPU configuration unchanged.
- PASS: actual PostgreSQL read-only `SELECT 1`; native login HTTP 200. Application PID 28760 and PostgreSQL PID 19512 retain their original start times. No native restart.
- PASS: both scheduled-task XML hashes equal the pre-recovery baseline; action paths exist. Approved 500-stock quotas, cooldown, reservations and RELIANCE definition were not edited. No provider GET or collection was initiated by recovery.
- PASS: Docker's stable images/volumes/container identities and mounts preserved; only disk-location setting changed; independent backup retained.

Private evidence: `cache-verification.private.json`, `docker-backup.private.json`, `docker-migration-verification.private.json`, `wrapper-tests.private.log`, `parallel-tests.private.log`, `compatibility.private.json`, `final-host.private.json` under `.local-data/disk-recovery-20261021`. These files and market/financial bodies are not published to Git.

No market/model/security logic or dependency changed. A full backend/frontend/container rescan was not rerun for this storage-only operation; prior security findings are not relabelled as resolved. No model training/inference/publication or financial-record change was performed by recovery. Naturally authorized collector appends are separate from preservation of the 633 baseline bodies.

## Remaining operational boundary

The disk-space objective is complete. Both task definitions are preserved, but their previously observed Windows last result was `0x8007042B`; Ready alone is not collection acceptance. This recovery did not reset or repair that result. Next expanded trigger read from Windows: **2026-10-22T20:30:00.0000000+05:30**. Continue source-receipt verification under the existing approved schedule; no extra acquisition is needed to prove disk recovery.
