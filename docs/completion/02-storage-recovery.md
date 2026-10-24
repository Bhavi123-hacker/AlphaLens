# Storage recovery audit — 24 October 2026

Status: **PARTIAL** for the full storage inventory; the requested C: headroom is **COMPLETE_VERIFIED**. **0 bytes recovered by this campaign**: no file was deleted, relocated or compressed. At first measurement C: already had **19.70 GiB free** and D: **67.34 GiB free**. A later sample was C: **23,484,014,592 bytes (21.87 GiB)** and D: **81,498,132,480 bytes (75.90 GiB)**. Background activity changes free space; those differences are not attributed to this read-only audit.

The [22 October recovery report](../development/alphalens-c-drive-recovery-and-d-storage-plan.md) records a previously approved, hash-verified cache relocation and supported Docker storage migration. That historical action already exceeded the 5–10 GiB target. Its net free-space increase is not new recovery credited here, and its independent Docker backup remains protected.

## Method and active references

Read-only Python `os.scandir` inventory sums logical file sizes, uses cached entry metadata, and skips every reparse directory/file rather than following junctions. Logical GiB is bytes/2^30; it is not exclusive physical allocation or recoverable space. Root directory listings, `git worktree list --porcelain`, process paths, current task actions and repository references were checked. Mixed roots are never treated as caches merely because of their names. One inaccessible C: checkout entry is recorded; inaccessible paths are not declared empty.

Registered Git worktrees are **C:\Users\Dell\AlphaLens** at `5314909` (P26) and **D:\al-research\p28-worktree** at `da43822` when audited. The D: worktree's common Git metadata lives in the C: checkout. Both are active/protected, not disposable old checkouts. The `.venv` in both checkouts targets `D:\al-research\p17-api\workspace-venv-original`; frontend `node_modules` targets `D:\al-research\p18-runtime\node_modules`. `%LOCALAPPDATA%\uv\cache` targets `D:\alphalens-uv-cache` and contributes **zero C: reclaimable bytes**.

Both actual scheduled task action paths exist and reference the D: worktree. The original watchlist launcher is `scripts\windows\p30-daily-update.cmd`; expanded collection uses `scripts\windows\run-nse-market.cmd` and `.local-data\full-nse-runtime\market-workflow-500.json`. Both observed states were Ready, both last result values were **3221225786 (0xC000013A)**. That state is not successful data collection or proof that referenced storage is unused. Definitions were not changed.

## Requested D: roots

Sizes are the completed19-root no-reparse-traversal logical inventory. One inaccessible C: checkout entry remains explicitly unresolved; all mixed test/evidence roots remain protected.

| Full path | GiB | Classification / purpose | Active reference / reproducible | Recoverable now | Risk / proposed action / rollback |
| --- | ---: | --- | --- | ---: | --- |
| `D:\alphalens-npm-cache` | 0.4886 | REBUILDABLE_CACHE; npm `_cacache` and logs | Existing development cache; package downloads reproducible subject to network and registry retention | 0 without approval | Low–medium; optional selected cache purge only after idle check and approval. Regenerate from exact locks; retain logs needed as evidence. |
| `D:\alphalens-uv-cache` | 0.9935 | REBUILDABLE_CACHE; uv wheel/build/archive/index structures | Actively referenced C: junction and D: wrapper; exact future artifact availability is not guaranteed | 0 without approval | Medium; retain for same-day release. Approved future eviction must preserve running consumers; re-download hash-pinned artifacts. |
| `D:\al-temp` | 0.0167 | ACTIVE_REQUIRED; current completion test/API scratch and older temporary output | Current completion directories present; full mixed root not proven reproducible | 0 | Retain; selected inactive child review only. |
| `D:\al-tests` | 2.8030 | ACTIVE_REQUIRED / UNKNOWN_DO_NOT_DELETE; 1,686 historical/current test directories | Referenced in regression commands and Windows test fixture defaults; evidence/data copies may exist | 0 | Retain. Names alone do not establish disposability; no blanket removal. |
| `D:\al-path-audit` | <0.0001 (48 bytes) | UNKNOWN_DO_NOT_DELETE; two path-audit files | No current production action reference found; evidence ownership unresolved | 0 | Negligible recovery; preserve. |
| `D:\AlphaLens-verification-archive` | 0.2611 | PROTECTED_RESEARCH_DATA; historical accepted verification artifacts | Referenced by historical P10 verification commands; reproducibility does not replace original evidence | 0 | Preserve original archive and hashes. |
| `D:\alpt10r` | 0.0149 | UNKNOWN_DO_NOT_DELETE; historical short-path P10 regression output | Named in accepted report and command log | 0 | Preserve evidence; per-child provenance required before cleanup. |
| `D:\p19fix` | <0.0001 (34,461 bytes) | UNKNOWN_DO_NOT_DELETE; 12 historical TEST_ONLY outputs | Not a registered Git worktree; root-wide reproducibility not established | 0 | Preserve; hash comparison with p19real **fails** despite equal byte counts. |
| `D:\p19real` | <0.0001 (34,461 bytes) | UNKNOWN_DO_NOT_DELETE; 12 historical TEST_ONLY outputs | Not a registered Git worktree | 0 | Preserve; not DUPLICATE_VERIFIED. |
| `D:\al-research` | 34.6440 at scan | ACTIVE_REQUIRED + PROTECTED_RESEARCH_DATA; code, shared runtimes, histories, models, private databases and audit evidence | Task paths, active worktree, dependencies and frozen research all reference this root | 0 | No root cleanup or move. The candidate release adds separate reproducible artifacts; this logical scan is a point-in-time lower-level inventory, not a snapshot. |
| `D:\AlphaLensStorage` | 50.2362 at scan | ACTIVE_REQUIRED + PROTECTED_RESEARCH_DATA; working Docker disk, independent backup, approved caches and development storage | Current wrapper and candidate npm downloads reference this root | 0 | Preserve working disk, backup, logs/evidence; optional individual cache policy later. Full root never disposable. |

No requested root qualifies as a removable OLD_WORKTREE or DUPLICATE_VERIFIED directory from the checked evidence. Equal names/sizes are not sufficient. Full per-file hashes were checked for p19fix versus p19real and differ; bulk protected-data rehashing is handled by the preservation campaign, not inferred from this size inventory.

## AlphaLens-related C: roots

| Full path | Fresh logical GiB | Classification / proposed action |
| --- | ---: | --- |
| `C:\Users\Dell\AlphaLens` | 0.3487, plus one inaccessible entry | ACTIVE_REQUIRED; shared Git metadata and preserved P26 checkout. Reparse targets excluded. Keep. |
| `C:\Users\Dell\AppData\Local\pip\Cache` | 0 | REBUILDABLE_CACHE; already emptied by prior approved relocation. No recovery available. |
| `C:\Users\Dell\AppData\Local\uv\cache` | Reparse root skipped | ACTIVE_REQUIRED junction to D: cache; **not C: disk data**. Keep junction. |
| `C:\Users\Dell\AppData\Local\npm-cache` | 0.0063 | REBUILDABLE_CACHE; newly repopulated cache/logs. No meaningful emergency recovery; preserve current logs. |
| `C:\Users\Dell\AppData\Local\node-gyp` | 0 | REBUILDABLE_CACHE; no recovery available. |
| `C:\Users\Dell\AppData\Local\Docker` | 0.0298 | ACTIVE_REQUIRED; control/log metadata, not the relocated VHDX. Do not delete Docker state. |
| `C:\Users\Dell\AppData\Local\Programs\Python` | 0.0015 | UNKNOWN_DO_NOT_DELETE; three installer/control bodies, not proof of duplicate runtime. Preserve. |
| `C:\Users\Dell\.cache` | 0.1265 | UNKNOWN_DO_NOT_DELETE; mixed ownership; not automatically AlphaLens-owned. Preserve. |

System Python under `C:\Program Files\Python312` and Node/GitHub CLI executables remain active installations. No Windows, Oracle, unrelated project, browser profile, user document, Codex state, account, credential, PostgreSQL data, financial record, model, saved forecast or backup is proposed for deletion. C: is above the target; additional risky movement is unnecessary for this release.

## Approval-only cache commands

No cleanup is requested or executed automatically. If optional D: npm cache eviction is approved later, use the exact named cache subroot below only after confirming all npm consumers are idle. It recovers D: capacity, **not C:**. Retain the independent manifest/logs outside the selected cache and verify full canonical paths and all reparse components before deletion. A cache can be rebuilt from the lockfiles; rollback is regeneration or an independently hash-verified backup, not restoration of protected data from guessed copies.

```powershell
# PROPOSAL ONLY. Requires explicit user approval and a fresh idle/reference check.
$cacheTarget = [IO.Path]::GetFullPath('D:\alphalens-npm-cache\_cacache')
if ($cacheTarget -cne 'D:\alphalens-npm-cache\_cacache') { throw 'Unexpected cache path' }
foreach ($ancestor in @('D:\alphalens-npm-cache', $cacheTarget)) {
    $item = Get-Item -LiteralPath $ancestor -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Missing, non-directory, or reparse target'
    }
}
$reparseEntries = Get-ChildItem -LiteralPath $cacheTarget -Recurse -Force -ErrorAction Stop |
    Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
if ($reparseEntries) { throw 'Reparse child; review required' }
# After approval, verified idle consumers, and retained inventory:
# Remove-Item -LiteralPath $cacheTarget -Recurse -Force -ErrorAction Stop
```

The exact C: cache candidate is only `C:\Users\Dell\AppData\Local\npm-cache\_cacache`, at most part of 6.8 MB; it is not worth deleting release diagnostics to meet an already-satisfied disk target. Any approval for D: cache eviction does not authorize this different path.

## Development storage and evidence

Reuse the existing opt-in [D: development wrapper](../../scripts/windows/with-d-dev-storage.ps1). It sets only child-process TEMP/TMP, compiler/test/build/cache paths. It preserves HOME/USERPROFILE/LOCALAPPDATA, authentication stores, user/machine environment and production launchers. The current campaign's candidate npm cache uses `D:\AlphaLensStorage\Caches\npm`; its isolated runtime/builds remain on D:. No junction, task or persistent environment was changed.

Private evidence: `.local-data/completion-20261024/storage_inventory.py`, `storage-inventory.private.json` when complete, `duplicate-check.private.json`; prior authorized hashes/rollback journal remain under `.local-data/disk-recovery-20261021`. Full scan totals, disk-free values and private application preservation are independent measurements. Final campaign drive values and protected-data verification are recorded in [the completion report](ALPHALENS_FINAL_COMPLETION_REPORT.md).
