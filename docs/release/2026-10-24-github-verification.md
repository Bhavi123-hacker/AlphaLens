# GitHub verification receipt — 24 October 2026

Verified code checkpoint: `876dceee8a42c4f7648a9a3a6de36ca987eccd7d`, branch
`alphalens-master-completion`. Final report commits change documentation only.

| Workflow / job | Observed result |
|---|---|
| [Frontend40089744561](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40089744561) | **SUCCESS**;119 tests, types/lint/build, API generation parity, retained runtime licenses, npm audit and4 actual isolated synthetic-demo browser cases. |
| [Foundation40089744569](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40089744569) | **SUCCESS** for both quality and strict-container. Real Linux/PostgreSQL17 regression:1579 passed /13 skipped,251.63s. Ruff/format/mypy/Bandit/pip-audit passed. |
| [Strict container120859822348](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40089744569/job/120859822348) | **SUCCESS**; image build, runtime/authentication checks and fresh strict Trivy scan. Artifact independently parsed:0 HIGH/0 CRITICAL; created2026-10-24T11:25:33.635131742Z; image sha256:35aacadcf66dcb65328a7e3895ca97541da8cf631fbb8c7395c758f609574c22. |
|876dcee secret step | **SUCCESS for this push range only**:2 chunks /176 bytes,0 verified /0 unverified. The176-byte notice update is not whole-history evidence. |
| [First implementation foundation40089709456](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40089709456) | **FAILURE at strict secret scan**; other quality and container checks passed. Broader implementation-branch scan:3706 chunks /11344835 bytes,0 verified /3 unverified, exit183. No suppression, ignore rule, severity change or history rewrite was applied. |
| [First implementation frontend40089709474](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40089709474) | **FAILURE** on stale Zod license-version metadata. Regenerated notices in876dcee corrected it; current frontend workflow above passed. |

The current code-checkpoint workflows are green. **Historical secret acceptance
remains BLOCKED_EVIDENCE**: a successful notice-only push scan cannot clear the
broader scan's three findings. The existing historical review remains evidence,
not a waiver. Production/public readiness also requires market-data rights and
independent model/forward acceptance, regardless of CI color.

Private logs and downloaded vulnerability artifact:
`.local-data/completion-20261024/ci-code-876dcee/`. Raw scanner material and private
application records were not copied into this receipt. No public real-data
deployment or main merge was performed. Subsequent documentation-only workflows
may run again; their state must be inspected separately if that exact tip is used.
