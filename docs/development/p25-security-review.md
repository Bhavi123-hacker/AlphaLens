# P25 local security review and independent production blockers

Verified 2026-10-11. Existing P21 account/session/CSRF boundaries remain in force;
new monitoring is private, compiled shell serves only allowlisted assets/pages,
unknown API paths never return frontend HTML and native stop is an owner-restricted
nonce-matched cooperative request, not an unauthenticated HTTP mutation or PID kill.
No credential/database/cache/data artifact is packaged in Git or the frontend.

Actual deployed browser testing identified a concurrent SQLite sidecar race:
last-close removal during ACL inspection could cause a false 503. Only a sidecar
that no longer exists is tolerated. Existing sidecars, main database and directory
still require the original permissions; negative ACL test rejects unsafe existing
files. Tests verify sessions/auth checks rather than adding a retry bypass.

Two actual UI defects were repaired: changed preferences remounted their form and
lost success confirmation; the monitoring scroll table lacked keyboard focus.
Notification tests now filter the genuine paginated event history and respect
already acknowledged states without resetting/deleting evidence. Expiry injection
remains restricted to explicitly isolated TEST_ONLY authentication storage.

## Container findings and supported fixes

The P22/P24 CLI liveness review also removed a false-positive API status: it now
verifies bounded loopback health independently of the running checker. No private
endpoint, session bypass, credentials or automatic external request is involved.
Three new cases cover an offline API, an invalid local response and an actual
minimal local response; affected regression checks pass with strict warnings.

P21 approved baseline foundation run
[38155812994](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155812994)
was rechecked and is FAILED at de80e3d, with prior actual-image receipts retained.
44 HIGH package instances across eight unique CVEs, zero CRITICAL; installed
package families/versions and reachability evidence remain in the
[P21 review](p21-container-security-review.md). Presence is not harmlessness.

All eight primary Debian tracker pages were rechecked on 2026-10-11:

| CVE / source | Supported trixie state | Newer-branch fix |
| --- | --- | --- |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720), ncurses | 6.5+20250216-2 vulnerable, no-DSA | 6.6 branch |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742), systemd | 257.13-1~deb13u1 vulnerable, no-DSA | 261.2; upstream 258.10 |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369), acl | 2.3.2-2 vulnerable, point-release fix pending | 2.4.0 ABI; not individually backportable |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), util-linux | 2.41.5-0+deb13u1 vulnerable, no-DSA | 2.42.3 |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), util-linux | same supported family vulnerable | 2.42.4 |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), util-linux | same supported family vulnerable | 2.42.3 |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410), util-linux | same supported family vulnerable | 2.42.3 |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538), perl | 5.40.1-6+deb13u1 vulnerable, postponed | Perl 5.42.3 / Archive::Tar 3.10 |

No compatible supported stable remediation was established. Replacing the runtime
base cannot be claimed to fix these unchanged stable package findings. Native ML
requirements and Python functionality are retained. No unstable packages, broad
ignore rules, ignore-unfixed, severity downgrade or continue-on-error are used.
The image keeps its pinned official Python/uv digests, non-root runtime and prior
SUID removal. Only required P22 schema/worker bridge and finite recovery smoke were
added to packaging. All market archives remain external, never copied into layers.

The shared Docker daemon again did not answer a bounded client probe. Only that
client was stopped; no restart, pruning or shared-container change. Current-head
GitHub CI is required for actual build/native/recovery smoke and strict rescan;
its final results are recorded in the final verification/delivery report.

## Secrets, private state and external gates

Latest P21 TruffleHog passed with zero verified/unverified findings. Three historical
unverified examples/negative fixtures remain documented in P21/P20 reports; their
values are never printed and history/detectors are unchanged. Current head is
reported separately after the enabled scan actually runs.

Owner-only authentication/operations/backup roots, transactional SQLite backup,
hash-checked new-location restore and restored-session revocation remain required.
No destructive recovery of a real account or overwrite of immutable research.
The native demonstration uses isolated TEST_ONLY credentials outside Git and a
separate clone of genuine alert evidence; original 47 records remain untouched.

P19_LIVE_DATA_ACTIVATION = BLOCKED. P1_PRODUCTION_DATA_CLEARANCE = OPEN.
PRODUCTION_MARKET_DATA_USE = NOT_CLEARED. P21_SECURITY_READINESS =
BLOCKED_FOR_PRODUCTION. CONTAINER_SECURITY_GATE = FAILED until an actual passing
supported-image scan. Public/HTTPS/multi-owner deployment, stock signals/economic
validation and external delivery are not cleared by local software acceptance.
