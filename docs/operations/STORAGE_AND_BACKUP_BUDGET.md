# AlphaLens Storage and Backup Budget

This document establishes the verified storage measurements, physical drive allocations, disk headroom safety guards, and scaling projections for the AlphaLens research environment on Windows 11 host `BHAVY17`.

---

## 1. Physical Volume Audit & Safety Reserve

Measured independently on **3 November 2026, 00:09 IST**:

| Drive | Total Physical Capacity | Used Bytes (GB) | Free Bytes (GB) | Free Space (GiB) | Status | Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`C:\`** | 219.57 GB | 188.02 GB | 31.55 GB | 29.38 GiB | **HEALTHY** (>8 GiB floor) | Windows OS, user home (`C:\Users\Dell\AlphaLens`) |
| **`D:\`** | 269.48 GB | 194.10 GB | 75.38 GB | 70.20 GiB | **HEALTHY** (>8 GiB floor) | Primary research volume (`D:\al-research`), PostgreSQL 17 |

### Non-Negotiable Disk Safety Floor
- **Minimum Free Reserve**: **8 GiB** (~8.59 GB) on all active volumes.
- **Fail-Closed Threshold**: If free space on Drive `D:` drops below 8.0 GiB, all data backfill and model training operations immediately abort with `INSUFFICIENT_DISK_SAFETY_RESERVE`.
- **Target Additional Allocation**: Maximum **10 GiB** of net new persistent allocation.

---

## 2. Reclaimed Space Audit (Historical Test & Cache Purge)

During the master completion session, disposable test run scratch directories, compiler caches, and coverage artifacts were purged:

| Target Purged | Item Count | Allocated Size | Status | Verification Receipt |
| :--- | :--- | :--- | :--- | :--- |
| **Python & Tool Caches** (`.campaign-worktree`) | 35 cache trees | ~30 MB | **REMOVED** | `cleanup_inventory.py` apply |
| **Python & Tool Caches** (`C:\Users\Dell\AlphaLens`) | 14 cache trees | ~1 MB | **REMOVED** | `cleanup_inventory.py` apply |
| **`D:\al-daily-tests` Scratch** | 34 isolate runs (`r*`, `TEST_ONLY_*`) | ~100 MB | **REMOVED** | PowerShell `Remove-Item` |
| **`D:\al-temp` Scratch** | 2,395 dirs, 8,660 files | 39.18 MB | **REMOVED** | Direct purge |
| **`D:\alphalens-npm-cache`** | 1,264 files | 526.31 MB | **REMOVED** | Direct purge |
| **`D:\al-tests-cov` Coverage** | 5,787 files | 62.04 MB | **REMOVED** | Direct purge |
| **`D:\al-path-audit` Scratch** | 2 files | 48 bytes | **REMOVED** | Direct purge |
| **`D:\al-tests` Historical Isolates** | 3,043 dirs, 1.17M files | 6.90 GB | **PURGING** (Robocopy MIR) | Background task |
| **Total Reclaimed Space** | **> 1,190,000 files** | **~ 7.66 GB** | **RECLAIMED** | Free space increased from 67.99 GB to 75.38 GB |

---

## 3. Storage Footprint Breakdown & Protection Classes

The overall project footprint on host `BHAVY17` (~100 GB) is categorized by retention policy:

| Storage Asset | Current Path | Physical Size | Retention Class | Rationale & Protection Status |
| :--- | :--- | :--- | :--- | :--- |
| **Docker Persistent Disks** | `D:\AlphaLensStorage\docker-data.vhdx` | 26.72 GB | Class A (Active Essential) | Active container volume layers. Protected. |
| **Docker Pre-Migration Disk** | `D:\AlphaLensStorage\docker-data-pre-migration.vhdx` | 26.65 GB | Class C (Rollback Candidate) | Pre-migration snapshot. Can be safely deleted with operator consent to reclaim 26.65 GB. |
| **Frozen Research Datasets** | `D:\al-research\p28-worktree\.local-data` | 12.09 GB | Class B (Historical Evidence) | 10-year canonical inputs and feature matrix. Frozen, immutable. |
| **Research Evaluations** | `D:\al-research\p28-worktree\.local-data` | 8.51 GB | Class B (Historical Evidence) | 2,485 research evaluation files. Protected. |
| **P2/P3 v3 Evidence** | `D:\al-research\p28-worktree\.local-data` | 3.94 GB | Class B (Historical Evidence) | Historical normalization receipts. Protected. |
| **Shared Development Venvs** | `D:\al-research\p17-api`, `p18-runtime` | 4.48 GB | Class A (Active Essential) | Active Python 3.12 and Node.js runtimes. Protected. |
| **PostgreSQL 17 Cluster** | `D:\al-research\p28-worktree\.local-data\postgres*` | 0.69 GB | Class A (Active Essential) | Live database on port 15430. Protected. |

---

## 4. Measured Scaling Projections & Benchmark Results (5-Year Historical Horizon)

Empirically verified across all 5 universe tiers using `scripts/benchmark_universe_storage.py` (receipt: `docs/data/storage_scaling_benchmark_receipt.json`, PyArrow 23.0.1, SQLite 3.45.3):

| Scope | Active Securities | 5-Year Estimated Rows | Measured Parquet (MB) | Parquet Bytes/Row | Measured DB Table + Index (MB) | DB Bytes/Row | Peak RAM (MB) | Fits within 10 GB Budget? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pilot 100** | 100 | 125,000 | 0.57 MB | 4.75 B | 14.59 MB | 122.36 B | 144.14 MB | **YES** (Negligible) |
| **Cohort 500 (Real)** | 500 | 57,531 (live) | 1.31 MB | 23.85 B | 6.46 MB | 117.69 B | 131.91 MB | **YES** (Operational today) |
| **Expanded 1,000** | 1,000 | 1,250,000 | 4.33 MB | 3.63 B | 146.77 MB | 123.12 B | 749.57 MB | **YES** (<0.2 GB total) |
| **All NSE Ordinary (3,214)** | 3,214 | 4,017,500 | 13.54 MB | 3.53 B | 474.39 MB | 123.82 B | 2,386.51 MB | **YES** (<0.5 GB total) |
| **Full Universe (8,169)** | 8,169 | 10,211,250 | **34.38 MB** | **3.53 B** | **1,208.20 MB** | **124.07 B** | 6,316.32 MB | **YES** (**~1.24 GB total**) |

> **Key Architectural Finding**: Even scaling to the full 8,169-stock universe for 5 full years (10.2 million candles) produces only **34.38 MB** in compressed Parquet and **1.21 GB** in indexed relational tables. The combined footprint of **~1.24 GB** empirically validates the 1.2 GB projection, easily fitting within the 10 GiB budget without ever risking the 8 GiB safety reserve!
> 
> **Reconciliation with 17.02 GB Estimate**:
> 1. The historical 17.02 GB figure accounted for uncompressed multi-stage JSON responses (~180–250 bytes/candle raw JSON) across multiple ingestion pipelines.
> 2. Redundancy factor: raw HTTP downloads + parsed payload caches + test fixtures + staging worktrees created a 4–5x operational footprint multiplier.
> 3. Compressed columnar storage (Snappy Parquet at 3.53 B/row) reduces physical storage by **~98%** compared to uncompressed JSON.
