# SHERVANI saved-session evidence

This read-only investigation uses retained authorized observations and receipts.
It makes no provider call and changes no task, collection policy, candle, model or
forecast. The target is the latest completed session represented by the reviewed
25 October 2026 scheduled run: **23 October 2026**.

## Identity and session

| Field | Retained evidence |
|---|---|
| NSE symbol / company | `SHERVANI` / `SHERVANI INDUSTRIAL SYN L` |
| ISIN / provider key | `INE011D01013` / `NSE_EQ\|INE011D01013` |
| Exchange token | `764890`, in the retained 24 October master |
| Current classification | Ordinary common equity, `NSE_EQ`, instrument type `EQ`, provider security type `NORMAL` |
| Master observation time | 24 October 2026, 15:57:55.726385 UTC |
| Master raw SHA-256 | `cff324cd97a16c7603f4447f794bd304ebdcbd4a42b71ec27738a1ecc0711358` |
| Latest accepted candle | **19 October 2026** |
| Earlier accepted history | 36 observations, 17 August–15 October 2026; one additional accepted daily observation on 19 October |
| Target session | 23 October 2026, official saved NSE timing 03:45–10:00 UTC |

The current master establishes the provider's dated identity classification. It
does **not** establish historical membership, per-session tradability, a completed
trade, absence of suspension, or an obligation for a daily candle to exist.
The retained 23 October calendar fact has source SHA-256
`cece0c1f31f753a42047a08b0fb2a92d4ae8ea63c996c3b399ddd9bf4a08ee6b`.
The saved 25 October calendar response has no NSE session fact, consistent with
the worker using the latest completed session rather than inventing a Sunday bar.

## Genuine empty-response history

All six publication-attempt files below match their retained SHA-256 sidecars.
Each retained provider body reports `status: success` with an empty `candles`
array. Every receipt remains
`PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE`, with
`completed_capture: false`. HTTP status was not retained in these publication
attempts and therefore remains **unknown**, rather than being inferred as 200.

| Requested session | Provider receipt time, UTC | Retained publication-attempt ID |
|---|---|---|
| 21 October | 21 October 15:01:03.318723 | `ffd97976d7dc4e4287019db0faaed047` |
| 21 October | 21 October 16:02:02.602748 | `3c3735dc389d49ba8fbbe0107a77378a` |
| 21 October | 22 October 05:17:37.056408 | `d4a67b77e226450d910ff4b011201ddd` |
| 23 October | 24 October 16:03:30.257545 | `11130a35524c49cf9d3071926f5990fe` |
| 23 October | 24 October 17:06:10.184903 | `b9e40adbeac84f25bf25579dbf3406d0` |
| 23 October | 25 October 15:07:38.803339 | `73b6d409af444e80a9b87faeeb13a893` |

These immutable files are under
`.local-data/nse-market-expansion/daily/SESSION/INE011D01013/publication-attempts/`.
The three 23 October response bodies share SHA-256
`83d511d64ffda7e4c950b5f2c8f95130e5fa0c872af9b85a70e1a6bf3616428f`.
The most recent attempt belongs to the already-authorized scheduled run
`3227fd4510f3454b876e888249b9333a`; its publication receipt SHA-256 is
`9836b8f45bf1e302e6e7e669bab25042a5770f31185e1abe8411dddfccd14278`.
It was received after the first observed premature Scheduler `Ready` state;
this supports continued worker activity without converting an empty response
into an accepted candle.

## Listing, identity and corporate-action limitations

The retained masters consistently use the same ISIN, provider key, symbol and
token. The worker's reviewed run found 500 current identity-eligible keys and no
current identity exclusions. This check is separate from historical session
eligibility.

The saved SHERVANI action summaries are explicitly non-exhaustive:
`complete: false`, `OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE`, with hazard dates
18 May and 18 September 2026. The raw action reference was not retained. Those
summaries do not prove that an action, suspension, delisting, identity transition,
or no-trade session explains the missing 23 October candle. There is no retained
session-dated listing/suspension notice establishing such an explanation.

Consequently, the saved evidence supports **provider returned no candle**. It
does not establish whether the underlying cause is a no-trade session, source
coverage, delayed publication, suspension, or another provider limitation. No
local timestamp-validation or identity defect has been demonstrated for this
security. No candle is synthesized, forward-filled, or replaced with a future
observation.

## Coverage verdict

The reviewed scheduled run accepted RRECL and left only SHERVANI missing:
**499/500 configured securities (99.8%)** for 23 October. Its terminal receipt is
`.local-data/nse-market-expansion/operational/runs/3227fd4510f3454b876e888249b9333a.done.json`.

**500/500 is not demonstrated or currently achievable from the retained valid
observations.** Future genuine authorized evidence could establish a candle or
explain its absence. The historical session-eligible denominator remains
**unknown**; reporting 499/499 would be unsupported. Resolving Scheduler
supervision does not by itself supply this missing market observation.

## Patched-runtime readiness after lifecycle repairs

The previous candidate fingerprint
`ac15c85b392f795b447fee121c3768431a5b9ce67f6a3cc0eeccfd36532c35f6`
includes the collector's source tree and Windows launcher bytes, alongside its
installed-package and interpreter identity. In
`scripts/nse_collector_cutover.py`, `source_identity` covers the `workers` and
`scripts/windows` roots, other enumerated application roots, lock/project files,
the cutover tool and its focused tests. `candidate_identity` incorporates that
source identity. Changes to covered lifecycle code or launchers therefore require
a **new source fingerprint, fresh compatibility verification and a newly reviewed
action-only plan**. The old approved plan must not be reused after such changes,
even if the candidate's package versions and dependency-audit result are unchanged.

No second cutover is authorized by this investigation. The reviewed original task
action and rollback evidence remain the baseline until fresh explicit approval.
