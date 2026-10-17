# Final Git-history secret finding audit

Reviewed 17 October 2026 on final-operational-research-delivery, baseline
12e7437. No finding value, credential-bearing URI, token or private credential
was copied into this report. The original source fixtures, scanner policy and
Git history remain unchanged.

## Actual automated result

The initial full-history foundation scan
[38931145686](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38931145686)
failed with **zero verified secrets and three unverified findings**. GitHub's
check-run annotations identify the locations and detectors below. The prior V1
full-history run
[38867588207](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/38867588207)
contains the same three annotations. The local saved V2 log also records three
unverified findings and zero verified results; its console output does not
include source/commit details, so those were obtained from annotations and a
separate local diagnostic.

| Detector | Historical location | Introducing commit | Source-context assessment |
|---|---|---|---|
| Postgres | docs/development/command-log.md:218 | 9fa82284936f8b7a34f5409ba25cdce3538747b6 | A documented configuration example assigns an explicit TEST_ONLY password placeholder and database URL before validating Docker Compose configuration. This is a literal test configuration example, not evidence of an exposed current operator or provider credential. |
| URI | tests/unit/test_configuration.py:31 | 9fa82284936f8b7a34f5409ba25cdce3538747b6 | An invalid database-configuration validation test supplies a credential-bearing HTTPS URI with an explicit TEST_ONLY secret marker, then asserts that the marker is absent from the error text. This is deliberate redaction-test input; it is not an authenticated database/provider connection. |
| URI | tests/integration/test_p17_api.py:248 | dceecad70531b955fd7e475c6ab805f612f187ec | A configuration test checks rejection of wildcard, public and user-info-bearing origins. The matched URI has a generic fixture credential and a loopback host; the test requires validation failure. It is validation-only fixture input. |

Historical line numbers belong to the scanned introducing snapshots. They need
not point to the same text in the latest, longer command log. The source-context
assessment inspected the corresponding committed files and exact introducing
commits, rather than treating the current line number as the complete evidence.

## Reproduced diagnostic, without exposing matched values

The [official TruffleHog **3.93.8** release](https://github.com/trufflesecurity/trufflehog/releases/tag/v3.93.8) Windows binary was downloaded for this audit
only into protected ignored local storage. Its archive SHA-256 matched the
publisher's versioned checksum file:

1a563dbf559b566cd9eee3ec310099f5978f2b2a800b019e2c3fa027931fcc85.

The native scanner initially could not scan this Git worktree: Windows file-URI
normalization produced an invalid duplicated drive path, and the worktree's
.git file was subsequently treated as an ordinary .git directory/index.
These attempts failed before scanning; they are not passing security evidence.
An isolated local clone of the existing branch resolved that scanner limitation
without resetting, rewriting or modifying the original checkout.

A full-history local **diagnostic** using all default detectors,
--no-verification --no-update --json --concurrency=4 --fail, then completed:
**three findings, exit 183**. Its paths, line numbers, detectors and introducing
commits exactly matched the three CI annotations. No detector/path exclusion,
entropy filter, severity reduction or suppression was added. The diagnostic did
not perform remote credential verification, so it is **not a replacement for the
strict CI verification result**.

Only safe metadata and SHA-256 fingerprints of matches were retained in the
sanitized diagnostic receipt:

| Detector and location | Matched-value fingerprint |
|---|---|
| Postgres, command log | fbda48787118de1b72d5de8c1764631d43ce54c31bc0b37acb720875a6afb90b |
| URI, configuration test | b1567381f69bd45bcfa6daf8e78cb830f60890a010ab3209add66856027b0078 |
| URI, API configuration test | b9689e752d07feae5919de93cdd6aa51285bc7e20dd6cd288bc50c92755c1b3a |

Receipt: .local-data/final-security-audit/history-diagnostic-sanitized.json.
The raw matched values were processed in memory and were not printed or committed.
The diagnostic binary and isolated clone are ignored local audit tools, not new
application/runtime dependencies.

## Disposition

**Human-readable source review:** the three reproduced findings are supported
test/configuration placeholders. None provides evidence of an exposed current
operator password, Windows Credential Manager secret or Upstox token.

**Automated full-history gate:** remains **FAILED** in the identified runs.
Reviewing fixture context does not turn a failed scanner exit into a pass.
There is no suppression, allowlist waiver, scanner removal, historical rewrite,
credential reset or original-fixture alteration in this delivery. Subsequent
changed-range scans must be reported with their actual, narrower scope; a clean
changed range does not erase the full-history result.

**Container gate:** independent. The rebuilt container's HIGH/CRITICAL result
belongs to its own current scan evidence and cannot be inferred from this
history audit.
