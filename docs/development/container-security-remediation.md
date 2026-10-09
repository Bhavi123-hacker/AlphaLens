# Foundation container security review

Date: 2026-10-09. Baseline `8507f7f`; scope is the existing foundation image,
not P17 implementation or a change to the completed research runtime.

Latest baseline [GitHub Actions failure](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/37890069326)
passed the Python quality and TruffleHog steps and failed Trivy. Its summary
reported **55 Debian OS findings (53 HIGH, two CRITICAL)** and **one HIGH Rust
finding** in `/usr/local/bin/uv`. The retained text table contains 54 individually
extractable OS rows, plus the Rust row; the reported summary count is preserved
without inventing the additional row. Historical scan reports are unchanged.

## Verified remediation

The image now uses digest-pinned official **Python 3.12.15 / Debian trixie**,
keeping the supported Python 3.12 ABI. Available stable/security updates are
installed before the OpenMP runtime. Debian remains the sole OS package source;
no testing/unstable packages or unverified binary replacements are mixed in.

| Component | Verified image version | Result |
|---|---|---|
| SQLite | `3.46.1-7+deb13u2` | No findings for CVE-2025-7458 / CVE-2026-11822 / CVE-2026-11824 |
| OpenSSL | `3.5.7-1~deb13u3` | No CVE-2026-84782 finding |
| gzip | `1.13-1+deb13u1` | No CVE-2026-41992 finding |
| util-linux | `2.41.5-0+deb13u1` | CVE-2026-53613 cleared; four other CVEs remain |
| zlib | `1:1.3.dfsg+really1.3.1-1+b1` | No CVE-2023-45853 finding |
| Container build-only uv | `0.12.24`, checksum-pinned image | Upstream Cargo.lock uses `quinn-proto 0.11.18`; runtime installer absent |

Fix/version evidence: [SQLite integer overflow](https://security-tracker.debian.org/tracker/CVE-2025-7458),
[SQLite FTS5 patches](https://security-tracker.debian.org/tracker/CVE-2026-11822),
[second FTS5 patch](https://security-tracker.debian.org/tracker/CVE-2026-11824),
[OpenSSL](https://security-tracker.debian.org/tracker/CVE-2026-84782),
[gzip](https://security-tracker.debian.org/tracker/CVE-2026-41992),
[util-linux mount fix](https://security-tracker.debian.org/tracker/CVE-2026-53613),
and [zlib/MiniZip](https://security-tracker.debian.org/tracker/CVE-2023-45853).
Debian notes the old zlib binary did not contain the vulnerable MiniZip code;
this review nevertheless uses the patched newer base and adds no ignore rule.

The [Quinn advisory](https://github.com/quinn-rs/quinn/security/advisories/GHSA-4w2j-m93h-cj5j)
identifies `0.11.15` as the first patched version. The isolated container builder
uses [uv 0.12.24](https://github.com/astral-sh/uv/releases/tag/0.12.24) and its
[published Cargo.lock](https://github.com/astral-sh/uv/blob/0.12.24/Cargo.lock),
which records `quinn-proto 0.11.18`. BuildKit mounts `/uv` for installation only;
it is absent from the final filesystem and image layers. Removing an unnecessary
runtime installer is remediation, not scanner suppression. The original local
research uv `0.11.25`, `uv.lock`, model settings and frozen statistical sources
are retained unchanged. This does not retroactively claim the old local tool is
patched; it remains outside the runtime container and outside a new training run.

## Actual rescan and remaining blockers

The new image built successfully with `uv sync --frozen --no-dev --no-editable`.
Non-root UID 999, all nine AlphaLens package imports and sklearn, LightGBM,
CatBoost and XGBoost imports passed with networking disabled. No fit, prediction
or final-holdout evaluation ran. CI now repeats this lightweight smoke check.

Trivy **0.70.0**, matching the failed Actions scanner version, scanned the actual
saved Docker image with `--scanners vuln --severity HIGH,CRITICAL --exit-code 1`.
The official Windows release SHA256 matched its publisher checksum:
`eea5442eab86f9e26cd718d7618d43899e72a83767619e8bee47911bddbfb825`.
The first DB download timed out through the default mirror before scanning;
retrying the official `ghcr.io/aquasecurity/trivy-db:2` succeeded with a longer
timeout. Database updated at `2026-10-09T01:16:59.530806077Z`.

**Actual scanner exit: 1. Remaining: 44 HIGH OS findings, zero CRITICAL,
zero reported Rust/Python/npm HIGH/CRITICAL findings.** This is not a passed
container gate. Machine-readable before/after evidence, actual image ID,
scanner/database metadata and all remaining package/CVE instances are in
[the remediation receipt](container-security-remediation.json).

| Remaining source component | Package/CVE instances | CVEs | Supported trixie result / upstream route |
|---|---:|---|---|
| util-linux | 36 | 2026-76642, 2026-78408, 2026-78409, 2026-78410 | Still affected in 2.41.5; all four fixed together by testing/unstable 2.42.4 |
| ncurses | 4 | 2025-69720 | Still affected in 6.5+20250216; fixed in testing/unstable 6.6 |
| systemd | 2 | 2026-16742 | Still affected in 257.13; newer branches contain fixes |
| acl | 1 | 2026-54369 | Still affected in 2.3.2; 2.4.0 introduces ABI changes requiring compatibility review |
| Perl | 1 | 2026-9538 | Still affected in 5.40.1; newer package fixes remain postponed for stable pending regressions |

Official remaining-issue evidence:
[util-linux helper hooks](https://security-tracker.debian.org/tracker/CVE-2026-76642),
[cgroup authority](https://security-tracker.debian.org/tracker/CVE-2026-78408),
[subdirectory resolution](https://security-tracker.debian.org/tracker/CVE-2026-78409),
[bind-mount redirection](https://security-tracker.debian.org/tracker/CVE-2026-78410),
[ncurses](https://security-tracker.debian.org/tracker/CVE-2025-69720),
[systemd](https://security-tracker.debian.org/tracker/CVE-2026-16742),
[acl](https://security-tracker.debian.org/tracker/CVE-2026-54369),
and [Perl](https://security-tracker.debian.org/tracker/CVE-2026-9538).

These are source-package findings. Some affected commands/services may be absent
from the actual runtime, but that has not been used to waive any finding. There
is **no ignore list, severity downgrade, `ignore-unfixed`, `continue-on-error`,
VEX suppression or exit-code weakening**. Critical findings were removed through
verified package/base changes, not hidden. The remaining stable packages have no
fixed version in the actual scan. Upstream/testing fixes exist; their absence
from a compatible stable package is an unresolved remediation constraint, not a
claim that no upstream fix exists.

## Follow-up and readiness

Monitor stable/security point releases for the eight CVEs. Alternatively,
review a supported compatible runtime base or maintained backport as a separate
packaging change, testing native dependencies and rescanning it. Do not pull
unstable libc/core packages into the existing image merely to make a scan green.
Any future component-specific VEX requires actual binary/reachability evidence,
explicit justification and review; none is supplied or enabled here.

CI retains a strict HIGH/CRITICAL failure and now uploads its JSON even on failure,
with a 10-minute scan timeout. Automatic Actions on push are expected to remain
red while the unresolved stable OS findings persist. Full CI success is not
claimed. The completed 548-test/PostgreSQL 17 research gate is historical evidence
under unchanged financial/model code; it was not unnecessarily rerun.

P17 remains NOT_STARTED. Security readiness is blocked by the strict container
gate. The economic audit separately prevents complete portfolio-performance or
production champion claims. Research classification and production OPEN /
NOT_CLEARED restrictions remain unchanged.
