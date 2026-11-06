# P19 security review

The P18 foundation run `37947866188`, quality job `113878729241`, failed at the
strict TruffleHog Git-history scan: zero verified findings and three unverified
findings, exit 183. GitHub check annotations identify:

| Location in history | Finding | Investigation |
|---|---|---|
| `docs/development/command-log.md`, annotated historical line 218 | Postgres | Documented disposable TEST_ONLY compose/database example; internal Docker service hostname, explicit test identity. Historical copies retain the same test example. No operational/private database credential established. |
| `tests/unit/test_configuration.py`, line 31 | URI | Explicit credential-shaped loopback URL used to verify that local-origin configuration rejects userinfo. This is a negative validation fixture. |
| `tests/integration/test_p17_api.py`, line 248 | URI | Explicit credential-shaped loopback URL used to test the API security/configuration boundary. This is a negative test fixture. |

Values are deliberately omitted. Private raw logs/annotations stay outside Git on
D:. Source/history inspection supports classification as harmless documented test
examples, not real credentials. No evidence requiring credential rotation was
found. This finding review does **not** waive the scanner: its results filter,
failure behavior and history scanning remain unchanged. Historical findings may
continue to fail CI until an independently approved scanner disposition exists;
P19 does not rewrite history or silently suppress them.

The 44 unresolved HIGH OS findings from the approved container review remain open.
No Trivy exclusion, severity reduction, weakened exit code, daemon reset or global
prune is introduced. Production deployment remains blocked. The foundation Bandit
scope is extended to include the new worker package. No external dependency or
provider secret, broker credential, public listener or remote write endpoint is
added. Schedule generation creates disabled XML only.

Resume review on 2026-10-11 reconfirmed the P18 run's actual job sequence on
GitHub: Python/PostgreSQL/static/dependency gates succeeded, TruffleHog failed,
and the downstream image-build/container scan did not execute. The retained
44 HIGH container findings come from the separately documented actual scan.
No P19 finding disposition, exclusion, results filter or exit-code change was
introduced. The delivered branch's Actions result must be reported independently.
