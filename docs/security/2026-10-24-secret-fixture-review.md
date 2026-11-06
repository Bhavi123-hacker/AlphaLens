# Full-history secret finding disposition — 24 October 2026

Status: **VERIFIED_COMPLETE** for source classification and the local exact-fixture
review gate. CI and container results for the final release commit are recorded
separately in the final blocker report; this document does not infer them.

The user's final-blocker Task D explicitly authorizes narrowly scoped accepted
handling for demonstrated false positives. The scope is recorded in DECISIONS.md.
This changes the previous disposition-only policy for these three exact fixtures.
It does not change scanners, detectors, severity thresholds or verification.

## Reproduction and classification

The checksum-verified native TruffleHog **3.93.8** scanned all **144 reachable
commits** through `f90531362a8300b052a830766969f5498fbf4024` in an isolated local
clone. No `since-commit`, maximum depth, detector/path exclusion, entropy filter,
verification bypass or trusted-local-Git bypass was used. The scanner completed
**3,722 chunks / 11,367,696 bytes**, **zero verified / three unknown findings**,
with **raw exit 183**. It is not a clean raw scan.

Command, using the protected ignored audit root:

```powershell
.local-data/completion-runtime/venv/Scripts/python.exe -m scripts.verify_secret_history `
  --scanner .local-data/final-security-audit/trufflehog.exe `
  --repository .local-data/blocker-resolution-20261024/history-repository `
  --output-dir .local-data/blocker-resolution-20261024/full-history-reviewed-baseline
```

The wrapper runs `git file://<owned-clone>` with the exact HEAD, `--no-update`,
`--json`, `--fail`, `--fail-on-scan-errors`, `--results=verified,unknown` and four
workers. Raw matched values remain private and are never printed or uploaded.
The receipt contains only fingerprints, reviewed source locations and scan counts.

| Finding | Historical scanner location | Exact committed source review | Disposition |
| --- | --- | --- | --- |
| Postgres | `docs/development/command-log.md:218`, `9fa82284936f8b7a34f5409ba25cdce3538747b6` | Explicit TEST_ONLY Docker configuration assignment before compose validation. Scanner normalizes the URI and reports its chunk line; the actual assignment is source line **453**, beside the explicit placeholder password assignment. | VERIFIED_COMPLETE — configuration fixture |
| URI | `tests/unit/test_configuration.py:31`, same `9fa8228…` | Invalid configuration redaction test requires validation failure and verifies that its explicit TEST_ONLY marker is absent from the error. | VERIFIED_COMPLETE — negative-test fixture |
| URI | `tests/integration/test_p17_api.py:248`, `dceecad70531b955fd7e475c6ab805f612f187ec` | User-info-bearing loopback origin supplied alongside wildcard/public origins to a test requiring configuration rejection. | VERIFIED_COMPLETE — negative-test fixture |

No matched value is reproduced here. These are not evidence of exposed active
provider, operator or database credentials. Credential rotation is not required
for these specific deliberately invalid/example fixtures. Any genuine exposure
found later remains a blocking incident requiring removal and rotation.

## Exact accepted handling

`reviewed-secret-fixtures-v1.json` registers each detector, introducing commit,
reported file/line, matched-value SHA-256 and immutable source-blob SHA-256.
The normalized Postgres match additionally binds the actual source-line hash.
Other matches must occur on their exact reviewed source line.

`scripts/verify_secret_history.py` requires all registered findings, exactly once,
the pinned scanner version, a complete non-shallow history, positive scan counts,
one completed summary, zero verified secrets, consistent counts and raw exit 183.
It rejects missing/malformed output, error logs, new findings, different values,
locations, source blobs or verified results. It preserves `raw_scan_clean: false`
and `raw_scanner_exit: 183` even when the separate disposition gate succeeds.
There is no blanket exception for tests, documentation, URI or Postgres detectors.

CI now scans complete reachable history on **every push/PR**, replacing the
action's event-dependent changed-range selection. The same official Linux scanner
archive is pinned by publisher SHA-256
`b965dd2a4106dc3c194dfcaa93931fe0a93571261e3e1f46f2d1728b6612e019`.
Only its sanitized disposition receipt is retained as a CI artifact. Dependency,
Bandit and strict HIGH/CRITICAL container scans remain independent required gates.

Nineteen TEST_ONLY gate tests cover changed matches/locations, verified findings,
source drift, duplicates, missing/error summaries, inconsistent counts/version,
wrong exits and the exact unrestricted full-history scanner command. They passed
locally; Ruff and strict mypy passed for both gate sources.

The final blocker report records the subsequent full-history scan and CI scope
for the exact release commit. Earlier 17 October reports remain historical.
