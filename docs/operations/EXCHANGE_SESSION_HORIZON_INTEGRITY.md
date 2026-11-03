# Exchange-session horizon integrity — operator hold

This is a release-blocking integrity issue for **forward model acceptance**, not a defect in the Private V1 dashboard or market collector.

The former settlement method advanced from observation session T to the next *available per-stock candle*. An NSE trading day absent from an instrument's retained data therefore shifted the registered T+1 open and T+H close. The signed original settlement records are immutable and **must not be deleted or silently overwritten**.

## Expected registered H5 windows

| Observed | Next NSE open (entry) | Fifth NSE close (exit) |
| --- | --- | --- |
| 2026-10-16 | 2026-10-19 | 2026-10-26 |
| 2026-10-19 | 2026-10-21 | 2026-10-27 |
| 2026-10-23 | 2026-10-26 | 2026-10-30 |
| 2026-10-28 | 2026-10-29 | 2026-11-04 |
| 2026-10-30 | 2026-11-02 | 2026-11-06 |

Official October 26 and October 27 trading-session evidence:
https://www.nseindia.com/static/reports/closing-auction-session-historical-data

NSE's special Muhurat session of Sunday 2026-11-08 also needs to be included when validating H5 horizons around Diwali:
https://www.nseindia.com/resources/exchange-communication-holidays

These dates derive from the official exchange calendar. A missing vendor candle is **not** an exchange holiday.

## Safe read-only Windows verification

From the *actual running code worktree*:

```powershell
Set-Location 'D:\al-research\p28-worktree\.campaign-worktree'
$ledger = '.\data\forecasts\matured_outcomes_ledger.db'
Get-FileHash $ledger -Algorithm SHA256
python scripts\audit_existing_exchange_horizons.py --ledger $ledger
Get-FileHash $ledger -Algorithm SHA256
```

The script uses SQLite read-only mode, reports each observation cohort's number of aligned, misaligned, and unverifiable rows, and produces no output file or mutation.

**Do not run live settlement or accept additional outcomes before reviewing its results.** If any row is misaligned, retain the original signed ledger unchanged, create a separate clearly labeled derived-correction ledger from authentic original pre-entry forecasts and valid EOD data, and re-evaluate model metrics only from qualified outcomes.

The proposed strict settlement option requires a verified NSE exchange calendar, all expected instrument candles for the registered horizon, and agreement between the forecast's stored entry-open date and the actual next exchange trading day.

The test/patch lives in a separate review branch and does not change Private V1. Explicit operator approval is required for any Windows scheduled-task change.

### If stopping the V2 task is needed pending review

Only the Windows operator may decide to disable the **V2 settlement task**, without modifying Private V1's 20:30/21:30/22:30 collectors:

```powershell
schtasks /change /tn "AlphaLens-Daily-Settlement-V2" /disable
```

Verify the task state via `schtasks /query /tn "AlphaLens-Daily-Settlement-V2" /fo LIST /v`. Do not re-enable until an exact-code local replay, backup verification, and full CI succeed.
