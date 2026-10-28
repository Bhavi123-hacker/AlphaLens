# NSE battery-policy execution — 28 October 2026

The reviewed two-setting change was applied at **08:42:36 IST** and verified at
**08:42:53 IST**. **Rollback was not required.** The authenticated private app
remains available at http://127.0.0.1:8041/nse-market.

## Authorization and exact change

The operator's latest “do it” instruction refers to the replacement plan presented
in the preceding delivery, not the expired 27 October plan. The authorization and
execution evidence are retained in
`.local-data/nse-battery-policy-activation-20261028-0816/`.
The approved replacement is
`.local-data/nse-battery-policy-review-20261027-final-v2/plan-INACTIVE.json`, SHA-256
`13ba808a167f863b84388378a2dad7f41790c5fc66d228c1024a5773b4df7981`,
valid until 28 October, 19:30 IST. Its sealed bytes were not regenerated or edited.

Only these settings on `AlphaLens-Private-NSE-Market-Research` changed:

| Task setting | Before | After |
| --- | --- | --- |
| `DisallowStartIfOnBatteries` | `true` | `false` |
| `StopIfGoingOnBatteries` | `true` | `false` |

The exact reviewed PowerShell artifact was copied without modification and
executed once. Full canonical XML comparison confirms that the action, principal,
triggers and every other setting remain unchanged. The task remains enabled,
idle and Ready. The live export SHA-256 changed from
`12ad71c4bdafeaa84f5ea8fc3ad00d1b2791af2d14663883463d7c1747fd73ef`
to `1ab7036ef3d2778a6e3d9b8d729b89f2f554e039189a44abe83e2bb02b5e2b42`.
Its canonical proposal hash matches
`8bd0b89cf9978037f4ef5e9b055b53e8ba6e40474a07a0d297129ea99c0937b8`.

The excluded `AlphaLens-Private-EOD-Watchlist` export remains exactly
`d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419`.
No scheduler action, interpreter, trigger, quota, cooldown, retry, credential,
database target, clock rule, model, forecast policy or Windows power policy changed.

## Fresh checks and preservation

The full runtime/installed-file check completed at 08:41:27 IST, before the write
and within the reviewed 240-second window. All four identity checks passed:

- Runtime fingerprint:
  `98d635dc30737ac7c034fbcd6bd463ac4a4553878e4efac906ee4f4701c05eac`.
- All 326 active source hashes match inventory
  `e13b20bbcbe5eb948ff5bc00dec9be27e8a655d198f2f7e6b18c546ddf77bf47`.
- Fresh dependency audit: zero advisories; 93 third-party distributions checked,
  nine exact local workspace projects explicitly have no PyPI advisory entry.
- Adequate known battery, no low/critical flag or observed imminent shutdown,
  zero matching collectors and the exact idle Ready task were verified. Battery
  charge was 69% immediately before the write. No stable-AC waiting rule was added.

Read-only checks preserved all 2,485 frozen research files (8,505,278,241 bytes),
47 original alerts and 945 original forecast bodies. Of the original market-store
paths, 19,499 immutable files match; four derived status pointers changed through
already-authorized runs. Their original immutable targets and reviewed receipts
remain intact. These pointer updates were separately proven, not treated as
permission to alter protected records.

Pre/post authentication, session, health, compiled frontend and PostgreSQL 17.11
checks passed. Database verification used a read-only transaction. The owned test
login session was logged out. No application restart was needed.

An initial execution invocation used the default Python, which lacked `psycopg`;
it stopped before any native write. The same frozen procedure then ran using the
existing application interpreter. No dependency or active source was changed.

Shared provider attempts remained **5,021 before and after** the change. That
count includes the separate existing 08:30 watchlist run. This campaign made zero
provider/NTP requests and started zero collectors. All original NSE reservations,
including 1,200 reserved requests on 27 October, remain intact; none was reset.

## Live verification remains pending

The next existing NSE trigger is **28 October, 20:30 IST**, followed by 21:30 and
22:30. No run was triggered manually. A finite hidden read-only observer is active;
it captures existing task states, process facts, terminal-receipt hashes, clock
states, shared accounting and publication-pointer changes through 23:40 IST. It
cannot start collection, change tasks or make network requests. Its output still
requires review of actual accepted candles and outcomes; provider HTTP success or
Scheduler success alone is insufficient.

The previous Scheduler result remains `0x8007042B` from 27 October. Changing the
settings does not erase that history or establish that tonight's run succeeds.
The 21:30 independent clock-refresh failure also remains a separate risk; no clock
acceptance was weakened. Battery permission cannot prevent sleep or exhaustion.

## Product evidence and remaining gates

| Capability | Current evidence | Status |
| --- | --- | --- |
| Exact two-setting activation and post-checks | Applied, canonical delta verified; no rollback | `VERIFIED_COMPLETE` |
| Private authentication, frontend and database | Fresh checks pass | `VERIFIED_COMPLETE` |
| Patched NSE collector dependency audit | Zero advisories; exact runtime preserved | `VERIFIED_COMPLETE` |
| Current-day Intraday V3 candle delivery | No successful candle delivery established yet | `FIXED_AWAITING_LIVE_VERIFICATION` |
| Retained price coverage | 499/500 for 23 October; SHERVANI missing that session | `BLOCKED_EXTERNAL_DATA` |
| Search coverage | 3,194 equities in the latest retained master; all 500 configured identities remain eligible | `VERIFIED_COMPLETE` for search only |
| Saved experimental predictions | 312 genuine saved outputs, based on 23 October observations; not today's forecasts | `VERIFIED_COMPLETE` for saved display only |
| Independently accepted models | Zero; retain `EXPERIMENTAL_RESEARCH` | `BLOCKED_MODEL_EVIDENCE` |
| Forward accuracy | 945 forecasts, 914 decisions, zero qualified matured outcomes; `NOT_YET_MEASURABLE` | `BLOCKED_EXTERNAL_DATA` |
| Separate shared watchlist runtime | Known advisories retained; task excluded from this approval | `BLOCKED_SECURITY` |
| Expanded collection/public market-data deployment | No expanded quota activation or public redistribution authorization | `BLOCKED_APPROVAL` |

The last unchanged-code release verification is commit
`c2a4ea9bfd4a3e5ebd244e7cec7298a585afa572`: 1,904 Linux/PostgreSQL tests passed,
30 skipped; 134 frontend tests passed; 70 focused Windows cases passed. The
separate 138 clock cases overlap and must not be added to the Windows total.
The strict container scan has zero HIGH/CRITICAL findings. The historical secret
scan has zero verified secrets and three exactly reviewed fixture findings; its
raw scan is not clean. These are prior verified checks on unchanged code, not
new full Windows/browser runs caused by this task-setting change.

The active checkout remains base commit
`6a5b73af588624cadc1e464d8ca90b5944421893` with exactly the two previously
authorized Intraday V3 source corrections. This execution report is delivered
from the isolated candidate to `alphalens-master-completion`; the active source
checkout is not advanced or reset. No full-production or investment-edge claim
is made.

Next action: review tonight's existing scheduled-run evidence, including actual
worker termination, independent clock acceptance, request counts, durable DONE
receipt and valid candle publication. Diagnose any independent failure from its
retained evidence. Do not start another collection or activation automatically.
