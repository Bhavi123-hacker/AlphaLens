# AlphaLens Private V1 storage and recovery evidence

Read-only preservation and recovery evidence refreshed **2 November 2026,
04:43–04:46 UTC / 10:13–10:16 IST**. Cache cleanup remains dated **31 October**;
the separately dated full inventory was collected on **30 October 2026**.
Scope is twelve explicitly configured AlphaLens roots, not unrelated projects or personal files.
Private receipts are in the original worktree under
`.local-data/private-v1-20261029/storage/`; no private databases, observations,
credentials, forecast payloads or full inventories are published by this report.

## Measured footprint

The completed supplemental scan on 30 October adds eight independently identified
AlphaLens test/cache/archive roots to the four primary roots below. The combined
rolling inventory contains **1,664,659 regular file entries**, **101,249,232,605
logical bytes** and **102,749,932,968 unique allocated file bytes** (101.2492 / 
102.7499 decimal GB). Cross-root file-identity comparison found no allocation
shared between these eight supplemental roots and the primary four. The combined
hard-link alias count is 30,680. One pre-existing ACL-denied C: test subtree remains
excluded; these are measured lower bounds, not exact whole-volume totals.

| Supplemental verified AlphaLens root | Files | Logical bytes | Allocated bytes |
|---|---:|---:|---:|
| `D:\al-tests` | 1,177,852 | 4,303,504,802 | 6,903,441,976 |
| `D:\alphalens-npm-cache` | 1,264 | 526,315,036 | 529,757,368 |
| `D:\AlphaLens-verification-archive` | 59,201 | 280,307,828 | 426,763,128 |
| `D:\al-temp` | 8,660 | 23,312,349 | 39,180,816 |
| `D:\alpt10r` | 2,837 | 16,026,358 | 23,163,320 |
| `D:\p19fix` | 12 | 34,461 | 57,424 |
| `D:\p19real` | 12 | 34,461 | 57,424 |
| `D:\al-path-audit` | 2 | 48 | 24 |

These supplemental contents are retained. Generated test names alone do not prove
that every payload is disposable; the archive and historical test receipts may
support recovery or reproducibility. The fresh scan records 2,911 immediate
historical test directories under `D:\al-tests`; no blanket test-output purge was
performed. Raw inventories and the cross-root comparison are privately retained
as `additional-roots-20261030-refresh.json` and
`additional-cross-root-hardlinks-20261030.json`. Subsequent test/build growth is
outside that explicitly dated inventory and is not silently folded into it.

The refreshed inventory contains **414,819 regular file entries**,
**96,099,697,262 logical bytes** and **94,827,511,488 unique allocated file bytes**.
Decimal GB is used below. This supersedes the 29 October three-root measurement
of 388,738 entries / 94,421,817,104 allocated bytes. It is a rolling read-only
inventory during development, not an atomic filesystem snapshot. The earlier preliminary inventory is superseded:
Windows `DirEntry.stat()` returned zero file identity fields; the reviewed
implementation uses `Path.stat()` to obtain actual volume/file identity.

| Explicit root | Regular files | Logical GB | Unique allocated GB |
|---|---:|---:|---:|
| `D:\al-research` | 322,313 | 40.6352 | 40.1315 |
| `D:\AlphaLensStorage` | 46,045 | 54.0251 | 54.1013 |
| `C:\Users\Dell\AlphaLens` | 30,166 | 0.3726 | 0.4387 |
| `D:\alphalens-uv-cache` (additional allocation after cross-root deduplication) | 16,295 | 1.0667 | 0.1560 |
| Total | 414,819 | 96.0997 | 94.8275 |

The scans deduplicate **30,677 hard-link aliases** by actual volume/file identity.
The existing development wrapper explicitly configures `D:\alphalens-uv-cache`;
the C: uv cache junction points there. Of its 16,295 files, **15,032 actual file
identities / 938,800,544 allocated bytes** already occur in the other three roots.
Counting its 1,094,801,024 allocated bytes in full would double-count those
shared dependencies. This cache and all dependency environments remain retained.
Allocation uses the existing cleanup tool's Windows `FileStandardInfo` method,
including sparse/compressed file allocation rather than virtual disk capacity.
Directory/MFT metadata is excluded. Per-folder physical allocation is attributed
to the first encountered hard-link identity; logical directory entries remain
counted separately. These measurements are not sums of advertised VHDX capacity.

Ten reparse points were recorded and not followed in the refreshed primary scan, including the shared Python
environment, Node dependencies, legacy incoming data and tool/cache junctions.
Their owned targets under the three explicit roots are enumerated separately.
One historical test subtree, `C:\Users\Dell\AlphaLens\data\t\r31536-6a6b6e`,
denied enumeration. Its ACL and contents were preserved. Totals are consequently
lower bounds rather than an invented exact whole-volume measurement.

| Largest category | Logical GB | Allocated GB | Class and decision |
|---|---:|---:|---|
| Owned Docker disks | 26.7240 | 26.7240 | A/E: retain persistent disks |
| Docker pre-migration backup | 26.6538 | 26.6538 | C: retain verified rollback |
| Final-vintage canonical/features/matrix | 12.0882 | 12.0885 | B: frozen research inputs, retain |
| Protected research evaluation | 8.5053 | 8.5111 | B: 2,485 protected files, retain |
| P2/P3 v3 evidence | 3.9274 | 3.9420 | B: source/normalization evidence, retain |
| Shared Python runtime at `p17-api` | 2.7999 | 2.8620 | A: shared environment, retain |
| Security review tools | 2.0335 | 2.0335 | A/E: verification/rebuild dependencies, retain |
| Shared Node runtime at `p18-runtime` | 1.5496 | 1.6178 | A: shared dependency environment, retain |
| Completion campaign private data/environment | 1.0336 | 1.0485 | A/B/E: retain |
| Production collector runtime | 0.9672 | 0.9971 | A: scheduled runtime, retain |
| LSTM CPU environment | 0.6423 | 0.6852 | A/E: model reproduction environment, retain |
| PostgreSQL binaries and cluster | 0.6831 | 0.6853 | A: live database, retain |
| Relocated general caches | 0.5986 | 0.6673 | D/E: individually review before removal |

Classes follow the campaign: A active essential; B historical evidence; C verified
rollback; D reproducible caches; E requires individual dependency/duplicate review.
Names containing backup, old, temp or a date do not establish disposability.

The approximately 100 GB footprint is real, but most of it has an identified
preservation or recovery purpose. The live Docker data disk is
26,623,344,640 bytes and the pre-migration rollback disk is
26,653,753,344 bytes. Different lengths disprove exact duplication. The latter
has an existing full SHA-256 verification and a successful migration receipt.
Deleting it would remove the recorded pre-migration recovery copy.

Docker's engine was unavailable during inspection; both Docker Desktop and Ubuntu
WSL distributions were stopped. No Docker container/image/volume inventory is
represented as freshly verified. Historical 22 October migration evidence records
15 images, three volumes and five containers, which are historical counts only.
No engine start, image prune, volume deletion, VHDX compaction or WSL reset was
performed. Ubuntu ownership beyond AlphaLens is unproven and was not inspected.
These engine and WSL states were checked again on 30 October at approximately
05:35 UTC / 11:05 IST with the same result.

## Controlled cache cleanup

The existing `scripts/cleanup_inventory.py` remains the only deletion engine.
It rejects protected `.local-data`, `.git`, `.venv` and `node_modules` paths,
tracked files, escapes and reparse points. It checks every cache child and opens
Windows files exclusively before removal. Only named `.pytest_cache`,
`.mypy_cache`, `.ruff_cache` and `__pycache__` roots qualify; bytecode roots may
contain only `.pyc`/`.pyo` files. Source files and compiled application assets
remain intact.

Earlier preliminary candidates in the original D worktree and its nested
development worktree totalled 732 files, 42,162,620 logical / 43,447,624 allocated
bytes. Their removal was deferred until concurrent development checks stopped;
the reviewed 31 October cleanup below supersedes that preliminary estimate.
The inactive C checkout was refreshed and cleaned after the parent engineer
verified that no development checks used that exact checkout. At
**2026-10-29 20:03:34 UTC / 30 October 01:33:34 IST**, **591 files from 31 cache
roots** were removed: **4,487,825 logical / 5,140,136 allocated bytes**.
Immediate C volume free space increased **5,238,784 bytes**. D free space changed
by **-1,339,392 bytes** during concurrent campaign work; that is separately
reported, not attributed to deletion. Gross removed allocation and whole-volume
free-space change differ because of metadata and concurrent machine activity.
The exact per-path manifest is `c-original-removed.json`, bound to the fresh
`c-original-reviewed.json` inventory by SHA-256. No larger category is currently
approved for destructive cleanup. Localhost health returned HTTP 200 after this
cleanup. Authenticated saved-data checks also passed at
**20:06:08 UTC / 01:36:08 IST**: login, private coverage/search responses,
saved Top 5/10/20 prefix consistency, logout and session revocation, with zero
provider calls. These verify continued saved-research operation and make no
fresh acquisition or fresh inference claim.

At **31 October 2026 04:19:13–04:19:15 UTC / 09:49:13–09:49:15 IST**, the existing
cleanup tool removed **1,083 files from 72 named cache roots** in the original D:
worktree and its nested development worktree: **79,802,515 logical bytes /
81,717,184 allocated bytes**. The receipt records that the full backend run had
completed, the native API was cooperatively stopped, and no concurrent Python or
frontend test, build, type check or collector was running. Protected stores,
dependency environments, source files and compiled frontend assets were retained.

The immediate **D: free-space gain was 81,514,496 bytes**; C: free space did not
change during this removal. The exact inventory, per-path removal manifest and
summary are retained under `.local-data/private-v1-20261031/` as
`cache-inventory-reviewed.json`, `cache-removed.json` and
`cache-cleanup-summary.json`. The removal manifest binds the reviewed inventory
by SHA-256 `bd28773c1d6b8bcb16ceaae8c96a69cc50b8d7d2385f66416167ca97f438fd96`.

Together, the earlier C: cleanup and this D: cleanup removed **1,674 cache files /
86,857,320 allocated bytes** (86.8573 decimal MB) from 103 cache roots. This is
gross verified cache removal, not a claim that the total project footprint fell
by that amount. The additional isolated web security dependency environment at
`.local-data/private-v1-web-env-20261031/` and subsequent frontend/test outputs
add storage after the 30 October inventory. Only that new owned environment was
measured on **31 October 04:48:18 UTC / 10:18:18 IST** using the reviewed allocated
file method: **18,664 files / 314,445,923 logical bytes / 343,930,464 allocated
bytes**. No reparse points, hard-link aliases within this root or scan errors
were found. This active security/dependency environment is retained; its measured
343.9305 MB allocation is separate from the 86.8573 MB gross cache removal.
Subsequent frontend/test output growth and the whole-project net change remain
unmeasured. The dated 12-root inventory must not be presented as a fresh post-build
net-size measurement. No large archive, database, backup, Docker volume or VHDX
was deleted. This focused measurement wrote no environment file and performed
no deletion or full-inventory rerun.

| Volume | Free bytes immediately before C cleanup | Free bytes immediately after |
|---|---:|---:|
| C: | 12,207,222,784 | 12,212,461,568 |
| D: | 75,343,450,112 | 75,342,110,720 |

| Volume | Free bytes immediately before 31 October D cleanup | Free bytes immediately after |
|---|---:|---:|
| C: | 49,363,865,600 | 49,363,865,600 |
| D: | 73,957,224,448 | 74,038,738,944 |

A separate capacity sample at **31 October 04:48:18 UTC / 10:18:18 IST** recorded
**48,847,314,944 free bytes on C:** and **73,596,358,656 free bytes on D:**.
These later whole-volume values include other activity and are not the cleanup
window's before/after result. The focused environment inventory and timestamped
capacity sample are privately recorded in
`.local-data/private-v1-20261031/web-security-env-storage.json`.

The final read-only capacity sample at **1 November 08:54:36.961084 UTC /
14:24:36.961084 IST** recorded **48,800,260,096 free bytes on C:** and
**73,544,605,696 free bytes on D:**. These are a new point-in-time volume sample,
separate from every cleanup window; no space recovery is attributed to this
check. Its private receipt is `drive-free-after-final-20261101.json` in the
storage receipt directory. No new storage inventory or deletion was performed.

The post-handoff capacity sample at **2 November 04:46:44.754148 UTC /
10:16:44.754148 IST** recorded **29,058,650,112 free bytes on C:** and
**73,438,617,600 free bytes on D:**. It is retained privately as
`drive-free-after-handoff-verification-20261102.json` in the same storage receipt
directory. The earlier 04:36 UTC sample is separately retained as
`drive-free-after-handoff-20261102.json`. These point-in-time whole-volume samples
are independent of the historical cleanup gains; no cleanup or full-inventory
rerun was performed on 2 November.

The refreshed inventory began on 30 October with **50,132,078,592 bytes free on
C:** and **74,742,738,944 bytes free on D:**. Changes since the earlier cleanup
include other machine activity; the additional C: free space is **not** claimed
as AlphaLens cleanup. Newly generated development/test/build data also explains
why a later footprint can increase after a verified small cache removal.

The reviewed original D worktree Git classification was 1,127 tracked files,
216,487 ignored files and 1,368 untracked files. Untracked count includes the
new isolated development worktree and is not a disposal list. External Git
history is retained; the C checkout `.git` has 16,055,956 logical /
22,708,176 allocated bytes. Existing builds, browser artifacts, backups and
research stores remain retained regardless of Git status.

## Preservation and backup/restore

The baseline verified at **2026-10-29 19:57:09 UTC / 30 October 01:27:09 IST**:

- All **2,485 protected research files / 8,505,278,241 bytes** match the registered
  SHA-256 inventory; no estimator operation or research rerun was performed.
- All **47 original alert bodies** and their recorded evidence hashes match.
- The original **945 forecast bodies** remain unchanged; all **1,254 current
  forecast bodies** were newly pinned for append-only campaign verification.
- Six current model artifacts, the original research protocol files, four
  credential records, the original operator account/personal records and
  active localhost account/personal records were pinned privately.

The full check was repeated after the C-cache cleanup at
**20:05:28 UTC / 01:35:28 IST** and passed with the same 2,485 frozen files,
47 alerts, all 1,254 baseline forecast bodies, six models, credentials, original
operator and active localhost account/personal state unchanged. Git connectivity
verification also exited zero. All 31 removed C cache roots remained absent
immediately after cleanup.

The preservation check was repeated again at **30 October 05:36:52 UTC /
11:06:52 IST** and passed: all **2,485 protected files / 8,505,278,241 bytes**,
**47 original alerts**, **1,254 pinned forecast bodies**, six model artifacts,
four credential records and both original/active operator and personal records
still match. The check makes no provider request or model fit.

After the D: cache cleanup, the existing preservation verifier passed again at
**31 October 04:31:03 UTC / 10:01:03 IST**, using the existing completion runtime
and explicit original-worktree package paths. All **2,485 protected research
files / 8,505,278,241 bytes**, **47 original alerts**, **1,254 pinned forecast
bodies**, six model artifacts and 240 registered immutable files match their
baseline. The four credential records, original and active account/personal
records, and protected configuration fields also match. The read-only check
performed **zero provider requests, zero fits and no original-state mutation**.
Its private receipt is `preservation-after-cleanup-20261031.json` under the
29 October storage receipt directory.

The final preservation check passed at **1 November 08:55:39 UTC /
14:25:39 IST**. All **2,485 frozen research files / 8,505,278,241 bytes**,
**47 original alerts**, **1,254 baseline forecast bodies**, six model artifacts
and 240 registered immutable files match. Four credential records, original and
active accounts/personal records, and protected configuration fields also match.
The fixed 1,254-body count is the preserved baseline, not a claim about the
current total: concurrent authorized collection may append forecasts without
altering those bodies. The existing verifier ran in the pinned completion runtime
with explicit original-worktree package paths, made zero provider requests or
fits, and changed no original state. Private receipt:
`preservation-after-final-20261101.json`.

The post-handoff preservation check passed at **2 November 04:44:29 UTC /
10:14:29 IST**, after the parent confirmed derived-view publication had completed
at 04:41:57 UTC and no protected source/forecast writer remained active. Owned
AlphaLens tasks were Ready and the known collector/publication Python processes
were absent before the audit. The pinned completion runtime and explicit original
package paths verified the same **2,485 files / 8,505,278,241 bytes**, **47 alerts**,
**1,254 original baseline forecast bodies**, six models, 240 immutable files,
four credential records, original/active account and personal records, and
protected configuration fields. There were zero provider requests, fits or
original-state mutations. Receipts: `idle-before-handoff-20261102.json` and
`preservation-after-handoff-20261102.json`.

A separate targeted read-only forecast audit at **04:46:17 UTC / 10:16:17 IST**
pins **1,561 current forecast body hashes** across the original price-only ledger
and expanded forecast shards: the unchanged 1,254-body baseline plus **307
appends from 1 November**. All 187 baseline ledgers remain preserved; the audit
also includes three new shard ledgers, bringing its current ledger scope to 190.
The original preservation baseline was retained unchanged. The new hash receipt,
`forecast-preservation-after-handoff-20261102.json`, supports future comparisons
of the complete current forecast bodies without copying their payloads or
changing any ledger. This targeted ledger check did not repeat the storage
inventory or evaluate models.

Capacity was checked before making a small new operational backup. Five active
SQLite databases (`auth`, `alerts`, `operations`, `prospective`, `personal`) were
backed up online and restored to a separate private destination. Total backup
payload is **294,912 bytes**. Logical records match. Restoring authentication
intentionally revokes restored sessions and adds one session-revocation audit
record; original audit rows remain an exact prefix and the live databases are
unchanged. An initial overly strict audit-table equality assertion identified
that intended behavior; verification was corrected to check it explicitly.

The actual PostgreSQL **17.11** source database was **8,337,075 bytes**. Full
custom-format backup is **11,747 bytes**, SHA-256
`73f64b9cf957d4a17bef64dab5ae6d857ffa3e92aa5a2f01d4ec5c920729d9dc`.
The dump was restored into new isolated database
`alphalens_private_v1_restore_81bbb2098cfd` in the verified owned cluster on
port 15430. All five application tables and their logical rows, seven indexes
and four immutable triggers match. The original database remains unchanged.
The dedicated reader still has transaction read-only enabled. Four financial
tables contain zero rows; this does not imply the separate SQLite personal
workspace is empty. No live credential value was printed or replaced.

At **30 October 05:38:14 UTC / 11:08:14 IST**, the dump checksum and full existing
PostgreSQL restore were checked again against the running source database.
All five tables/rows, seven indexes and four immutable triggers still match;
the reader remains read-only. The five existing SQLite backup/restore payloads
also match, including intentional restored-session revocation. This check wrote
no live record and created no new full PostgreSQL copy.

The release configuration now uses its own `operations-8041` state directory.
At **05:40:57 UTC / 11:10:57 IST**, the existing online-backup/isolated-restore
workflow successfully verified all five databases from that current configuration,
using **294,912 bytes** of new backup payload after checking capacity. Every
logical table matches except the documented restored authentication session
revocation and appended revocation audit row. Prior backups remain intact.

Read-only recovery verification passed again on **31 October at 04:30:15 and
04:30:57 UTC / 10:00:15 and 10:00:57 IST**. The running PostgreSQL source still
matches its existing full isolated restore: all five tables/rows, seven indexes
and four immutable triggers; the saved dump checksum is unchanged and the reader
remains read-only. Both previously saved five-database SQLite backup/restore
sets, including the release configuration's set, retain matching logical payloads
with the documented restored-session revocation. This verifies the saved backup
snapshots; it does not assert that mutable live SQLite audit/session rows have
stopped advancing. No new database copy was created and no live record was
modified. Private receipts are `backup-restore-reverified-20261031.json` and
`release-backup-restore-reverified-20261031.json` in the same storage directory.

Final read-only backup/restore comparisons also passed on **1 November at
08:54:14 and 08:54:38 UTC / 14:24:14 and 14:24:38 IST**. The PostgreSQL source,
existing full isolated restore and saved dump remain consistent: all five
tables/rows, seven indexes and four immutable triggers match, the dump SHA-256
is unchanged, and the reader remains read-only. Both existing five-database
SQLite backup/restore sets retain matching saved payloads and revoked restored
sessions. These comparisons created **zero new backup bytes** and modified no
live record. Private receipts: `backup-restore-reverified-20261101.json` and
`release-backup-restore-reverified-20261101.json`.

Both existing operational backup/restore sets passed another read-only comparison
at **2 November 04:43:36 UTC / 10:13:36 IST**. Their five saved SQLite databases
still match their isolated restores with the documented restored-session
revocation. The live PostgreSQL source and its existing full isolated restore
still match all five tables/rows, seven indexes and four immutable triggers;
the saved dump checksum is unchanged and the reader remains read-only. No new
database copy was made and no live record was modified. These comparisons
continue to verify the existing saved snapshots; the forecast hash receipt above
separately pins the newer appends. Private receipts:
`backup-restore-reverified-20261102.json` and
`release-backup-restore-reverified-20261102.json`.

Private receipts: `preservation-before.json`, `protection-baseline.private.json`,
`operational-backup-restore.json`, `postgres-full-backup-restore.json`,
`inventory-reviewed.json`, `cache-inventory-preliminary.json` and
`cache-c-original-preliminary.json`. The enriched
`classified-folder-inventory.private.json` records sizes, allocation, file counts,
latest modification time, known executable owners, conservative Git/operation/
recovery/reproducibility classifications, duplication uncertainty and removal
decisions for 382 groups. An empty process-owner list is not proof that files
are unused. Protected raw data is not copied into Git.

## Verification and follow-up

Seven targeted Windows tests passed: three new inventory tests and four existing
cleanup tests. They exercise actual hard links, actual Windows junctions,
overlapping-root refusal, protected paths, tracked files, unexpected bytecode
contents and exact cache accounting. Ruff and focused mypy pass. Tests use
disposable `TEST_ONLY` stores and do not mutate protected research.
The same seven tests passed again on 30 October (**7 passed in 0.47s**).

Re-inventory with the existing environment and an explicit source import path:

```powershell
$env:PYTHONPATH='D:\al-research\p28-worktree\.campaign-worktree'
& 'D:\al-research\p28-worktree\.venv\Scripts\python.exe' -m scripts.private_storage_inventory --root D:\al-research --root D:\AlphaLensStorage --root C:\Users\Dell\AlphaLens --root D:\alphalens-uv-cache --output D:\al-research\p28-worktree\.local-data\private-v1-20261029\storage\inventory-next.json
```

Use a new receipt filename. The command is read-only and never follows reparse
points. The inventory helper provides no deletion capability.

Fresh private receipts are `inventory-20261030-refresh.json`,
`uv-cache-20261030-refresh.json`, `uv-cross-root-hardlinks-20261030.json`,
`combined-storage-review-20261030.json`, `preservation-20261030-refresh.json`,
`backup-restore-reverified-20261030.json` and
`release-operational-backup-restore-20261030.json`. The combined receipt records
source SHA-256 values and subtracts independently checked cross-root hard-link
allocation; it does not count Docker virtual capacity or unrelated storage.

Further large savings require an exact additional proposal: identify the Docker
objects and dependencies with the engine available; validate a current recovery
alternative before discussing the pre-migration disk; prove full duplicate
identity and ownership for other environments or backups. No large deletion is
justified by a similar name or a target size. Retention should prefer incremental
or hash-addressed copies, but frozen formats and existing backups are unchanged.
