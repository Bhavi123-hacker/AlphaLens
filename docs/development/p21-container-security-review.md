# P21 bounded container and secret-scan review

Verified 2026-10-11. Baseline P20 `eaeb01d`; strict policies remain unchanged.
This adds local authentication runtime checks and removes unnecessary privilege
elevation from retained mount helpers. It does not claim that removing SUID bits
fixes affected package versions or clears a Trivy finding.

## Confirmed baseline

[Actual foundation run 38140990151](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38140990151)
passed Python/PostgreSQL (689 passed / eight skipped), Ruff, mypy, Bandit,
dependency audit, TruffleHog (zero verified / zero unverified), Docker build and
runtime imports. Its strict container scan failed: **44 HIGH package/CVE instances,
eight unique CVEs, zero CRITICAL**. Raw JSON is retained at
`D:\al-research\p20-runtime\ci-eaeb01d-trivy\trivy-results.json`; the prior
[remediation report](container-security-remediation.md) and receipts are unchanged.
No FixedVersion was supplied for these package instances in that actual scan.

## Supported remediation paths investigated

The current digest-pinned official Python 3.12.15 slim-trixie keeps the frozen
Python ABI and native glibc/OpenMP dependencies. The official maintained
[Python image manifest](https://raw.githubusercontent.com/docker-library/official-images/master/library/python)
still lists 3.12.15 for this ABI. Its
[upstream Dockerfile](https://github.com/docker-library/python/blob/master/3.12/slim-trixie/Dockerfile)
uses trixie. A newer Python ABI would require changing existing requirements and
ML compatibility; it is not an OS-CVE fix. Current stable apt upgrades are already
applied. Bookworm remains affected for these source packages and is not a demonstrated
safe replacement. Debian testing/unstable fixes exist, but mixing their core
libraries into this supported runtime is prohibited.

A maintained Ubuntu base is not established as a fixed compatible replacement:
its [util-linux advisory](https://ubuntu.com/security/CVE-2026-76642) still reports
supported LTS releases needing evaluation. That is not a verified patched image.
Alpine/musl and a custom/distroless native dependency closure require independent
ML compatibility testing and actual scans; neither was substituted without proof.
The existing build-only uv mount already excludes the installer from final layers.
Removing libncurses/readline, SQLite, libacl or util-linux package dependencies
without runtime validation could break Python/native tools. No essential package
or Python feature was deleted to hide findings.

The shared local Docker daemon did not answer the bounded client probe; only the
session-owned client was stopped. Docker Desktop, shared containers and images
were not restarted, stopped or pruned. Consequently local candidate build/scan
was unavailable. GitHub CI supplies the actual final build/import/authentication
smoke and strict scan; completed run receipts are recorded separately below.

## Targeted hardening and verification

The only OS hardening change is `chmod u-s /usr/bin/mount /usr/bin/umount` after
all package installation. AlphaLens does not mount filesystems. These binaries
and their package metadata remain available to the scanner; native Python/ML
dependencies remain intact. The image remains non-root. Existing Compose already
requests no-new-privileges, drops capabilities and uses a read-only filesystem;
no public deployment is authorized by this change.

CI now runs `scripts/verify_p21_runtime.py` in the actual image with networking
disabled. It imports NumPy, pandas, SciPy, sklearn, LightGBM, CatBoost, XGBoost,
P19/P20 and FastAPI, initializes an isolated TEST_ONLY auth store, exercises
Argon2id/session/revocation, confirms no mount/umount SUID elevation and prints
only sanitized component presence. It loads no model or market archive and runs
no fit, prediction, evaluation or backtest. `db/auth` is copied for explicit schema
initialization; no real operator credential is baked into the image.

The read-only [saved baseline layer inventory](p21-baseline-component-inventory.json)
matches image configuration SHA256 `394ad80e61abadafa985ee009755f0bf0df4632e32281b4aa88dc054f68c4df2`.
It establishes that mount was SUID, nsenter/infocmp/perl and relevant libraries
were present. No systemd-homed or Archive/Tar.pm appeared in the selected final
baseline filesystem paths. This is bounded presence evidence, not a proof of
unreachability for every component, not the new P21 image and not a VEX waiver.

## Remaining CVEs

All rows are HIGH in the baseline scan. Trixie is supported; the listed installed
versions remain affected in the reviewed Debian tracker. Current forky/sid fixed
packages are not compatible stable backports approved for this image.

| CVE | Source / installed packages | Installed version | Known newer fix / technical evidence | Current blocker / future route |
|---|---|---|---|---|
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses; libncursesw6, libtinfo6, ncurses-base, ncurses-bin (4) | 6.5+20250216-2 | Newer 6.6 Debian branch; upstream infocmp fix after 6.5-20251213; infocmp/library present | Trixie no-DSA, stable fix absent; await supported update |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd; libsystemd0, libudev1 (2) | 257.13-1~deb13u1 | 261.2/258.10 fixes; current forky/sid 262; libraries present, homed service not found in saved baseline | No stable 257 fix; absence evidence does not clear strict source-package findings |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl; libacl1 (1) | 2.3.2-2+b1 | 2.4.0 adds acl_*_at ABI; libacl present | Stable point update pending; ABI/tar conflicts prevent arbitrary patch mixing |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux (9) | 2.41.5-0+deb13u1 family | Newer 2.42.4 branch; failed mount-helper post-hook authority | Stable affected; SUID removal reduces helper elevation but is not package remediation |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux (9) | 2.41.5-0+deb13u1 family | Newer 2.42.4; privileged nsenter --join-cgroup authority; nsenter present | No compatible stable fix; non-root/capability limits are not a CVE waiver |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux (9) | 2.41.5-0+deb13u1 family | 2.42.3 fix, current newer package 2.42.4; X-mount.subdir traversal | Stable affected; retained mount has no SUID after verified hardening, finding stays visible |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux (9) | 2.41.5-0+deb13u1 family | 2.42.3 fix, current newer package 2.42.4; restricted bind-mount redirection | Stable affected; await supported upgrade, no package/severity suppression |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | perl; perl-base (1) | 5.40.1-6+deb13u1 | Archive::Tar 3.10; forky/sid Perl 5.42.3; parser module not found in saved baseline paths | Stable fix postponed pending upstream regressions; retain finding until independent gate clears |

The util-linux nine-package family is bsdutils, libblkid1, liblastlog2-2, libmount1,
libsmartcols1, libuuid1, login, mount and util-linux. Libraries use
`2.41.5-0+deb13u1`; bsdutils/mount/util-linux use epoch
`1:2.41.5-0+deb13u1`; login uses `1:4.16.0-2+really2.41.5-0+deb13u1`.
These four CVEs create 36 package instances. No exploit was executed and no
runtime-wide harmlessness claim follows from limited component presence evidence.

## Historical TruffleHog findings

The final P20 scan passed, while the initial P20 new-branch history scan retained
three unverified findings: command-log.md:218 (historical TEST_ONLY Postgres
example), test_configuration.py:31 and test_p17_api.py:248 (negative URI fixtures).
Their values are deliberately omitted. No live credential was established;
unverified findings are not retroactively erased. P21 test transport/import/OpenAPI
changes do not change those negative fixture values. No history rewrite, detector
disable, ignore rule or automatic credential revocation was performed. A genuinely
verified credential would require operator revocation/rotation, not a log dump.

Normal push-range scanning remains enabled with verified/unknown results and
strict failure. A later incremental scan passing does not erase an initial
history-scan failure. Every head-specific CI result is reported honestly.

## Final-image result

Actual [P21 foundation run 38155163814](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38155163814)
at `4ad6bdc8db36898d72ce8f00ed9f26ee16eab2af` built the image and passed native
imports plus authentication/P19/P20 startup smoke. Mount and umount are present
without SUID; nsenter/infocmp/perl are present without SUID; systemd-homed and
the checked Archive::Tar module paths are absent. These presence checks are not
proof of complete unreachability and are not scanner suppressions.

Strict Trivy failed: **44 HIGH before/after, zero CRITICAL before/after, eight
unique CVEs**. Every affected package/version/CVE instance matches the baseline.
The actual OS is Debian 13.7; no FixedVersion appears in the scanner receipt.
[Sanitized receipt](p21-container-scan-status.json) pins image
`sha256:5adae3e280afe89a35152f01ce76417627ad7f871e8ef2b2610aa27be77f15f0`
and raw report SHA256
`37bcb03415a15e72474348d2d0e4e3ebdc2246989b89ea90d781d3a320d9b4cf`.
Raw JSON remains in the GitHub `trivy-results` artifact and
`D:\al-research\p21-runtime\ci-4ad6bdc-trivy\trivy-results.json`.

The scan keeps HIGH/CRITICAL exit 1, no ignore-unfixed, no broad ignore list and
no continue-on-error. Current TruffleHog passed (zero verified/unverified findings);
the historical three unverified fixtures/examples remain recorded above.
CONTAINER_SECURITY_GATE = FAILED; P21_SECURITY_READINESS = BLOCKED_FOR_PRODUCTION.
Supported stable fixes remain the external blocker; no unsafe distribution
mixing or untested alternative image was substituted. Production security stays
blocked until independent supported-image and deployment gates actually pass.
