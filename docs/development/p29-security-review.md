# P29 security review and independent blockers

New authenticated read routes inherit P21 protections. Offline/API tests cover
401, foreign-Origin403, invalid scopes, preserved policy restrictions and safe
missing inputs. No deserialization occurs for compatibility/status reads; the
actual loader still requires all original authorization/checksum/type gates.
Private frontend validation also rejects daily/provider store overlap.
Page render/import failures show a generic recovery control, never raw details.

PG preparation is explicit/new-only/loopback/17/read-only and current-user
credential protected, not automatically executed. Original stores are untouched.
Public demo is separate original synthetic data, no API/auth/provider dependency,
connect-src none, scoped licence and retained package notices. No publication.

Initial Bandit found1LOW B105 on a diagnostic boolean flag named password_printed.
An earlier multi-command final exit masked that finding; local JSON confirmed it.
Renamed the noncredential flag sensitive_output and verified explicit Bandit exit0
and corrected CI success. No detector exclusions or secret behavior changes.
pip-audit passed; no dependency or scanner weakening.
P28 actual frontend38224098502 passed; foundation38224098734 failed at enabled
full-history TruffleHog (zero verified/three historical unverified candidates),
Docker/Trivy skipped. Values are never reproduced. No history rewrite, detector
exclusion or fabricated revocation. P29 workflow results are recorded separately.

All eight official Debian CVE tracker pages were rechecked2026-10-12. The
supported trixie versions remain vulnerable; no safe stable fix established:

| CVE | Supported installed source family | Tracker state |
| --- | --- | --- |
| [2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses6.5+20250216-2 | no-DSA; newer6.6 fixed |
| [2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd257.13-1~deb13u1 | no-DSA; newer261.2+ fixed |
| [2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl2.3.2-2 | point-release pending;2.4.0 new ABI |
| [2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux2.41.5-0+deb13u1 | no-DSA; newer2.42.3+ fixed |
| [2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux same | no-DSA;2.42.4 fixed |
| [2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux same | no-DSA;2.42.3+ fixed |
| [2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux same | no-DSA;2.42.3+ fixed |
| [2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | Perl5.40.1-6+deb13u1 | postponed;5.42.3/Archive::Tar3.10 fixed |

Prior actual final-image scan remains44HIGH package instances/eight uniqueCVEs/
zeroCRITICAL. No newer local image scan is claimed: shared Docker bounded probe
failed and no restart/prune was authorized. P29 only packages the new worker;
base/native dependency versions stay unchanged. Current-head CI must establish
actual build/import/scan outcomes. No unstable packages, ignore-unfixed, severity
change, broad ignore, continue-on-error or scanner disablement. Production
security and live market-data/model/rights gates remain blocked independently.

## Actual corrected-image verification

955bb2b foundation38241808202:909passed/8skipped275.60s, actual guardedPG17
bootstrap/read-only role/no fabricated accounts passed. Ruff/format/mypy/Bandit/
dependency audit and scoped TruffleHog passed. Docker/native NumPy/pandas/SciPy/
sklearn/LightGBM/CatBoost/XGBoost worker imports, non-root auth/operational smoke
passed. Actual final-image Trivy failed:44HIGH/eightCVEs/zeroCRITICAL, unchanged
from prior44/0. No fixed installed stable versions are reported. See
p29-ci-security-status.json for exact packages, scanner receipt SHA and step states.
Frontend38241808140 passed including3 actual synthetic browser scenarios.
This scoped push scan does not erase earlier full-history example findings.
