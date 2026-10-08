# D70 existing-run resume point

User steering on 2026-10-08: keep the existing local run, conserve Codex usage,
avoid frequent polling, and never restart completed fits or completed tests.
Do not change frozen hashes, thresholds, folds or holdout policy.

At the checkpoint, 25 of 144 development fits were complete. The latest completed
report was regression / 1-session / Ridge / 2023. All eighteen 1-session
classification development fits had completed. This is a dated checkpoint, not a
live counter or empirical acceptance claim.

The existing development worker was verified as PID 25924, created at local
2026-10-08 16:18:18. A PID alone is not durable identity: verify its command line
before any process action. Its command is:

```powershell
.tools/bin/uv.exe run --frozen python -m scripts.run_tejhq_research --data-root D:/al-research/tejhq-final-vintage-v1-r3 --output D:/al-research/tejhq-research-evaluation-v2-fit-parallel --stage development
```

**Do not launch this command while the existing worker is active.** It is recorded
for recovery after an actual interruption, not a request to restart the run.
The already-running local stage chain is
`data/tejhq-research/finish_d70_pipeline_v2.ps1`. It waits for all 144 development
reports and then executes backtest-selection, confirmation, final, summaries,
read-only fit diagnostics and report generation sequentially. Do not launch a
duplicate chain. Each dependent stage stops on a nonzero native exit.

Frozen supervised dataset:
`f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2`.
Frozen execution plan SHA256:
`ff421096b839224927e3ee4d96c8faa8593895837648fbb79f87ab6d4e92675c`.
The four plan-pinned code files and dependency lock matched their recorded hashes
at this checkpoint. No candidate lock or final-holdout evaluation lock existed.
The original serial reference run remains separately retained; it is not the
accepted run and must not replace this execution root.

Durable local artifacts:

- `D:/al-research/tejhq-research-evaluation-v2-fit-parallel/training-plan.json`
- `D:/al-research/tejhq-research-evaluation-v2-fit-parallel/p9/development-results.json`
- Per-fit reports in that `p9` directory, with exact model/OOS hashes and lineage.
- Checksum-pinned local model artifacts in `p9/models` and predictions in `p9/oos`.
- Progress log: `data/tejhq-research/d70-development-v2.log`.
- Stage-chain log: `data/tejhq-research/d70-v2-pipeline-chain.log`.

Each completed fit persists its model, OOS predictions and report, then updates
the development checkpoint. The existing evaluator reuses a completed report only
after validating dataset/fold identity and both artifact checksums; it does not
refit that completed model. Never delete reports or checksums to force a replay.
If interrupted, inspect partial artifacts before recovery. A final-holdout
attempt without a completed report requires explicit review and must not be
silently repeated; the existing guard fails closed.

After the chain completes, verify the actual 152 accepted fits, 504 backtests,
candidate/holdout lineage and final outputs, update acceptance documentation and
commit the empirical results separately. The latest coherent software gate is
548 passed / one expected live-provider skip, with PostgreSQL 17 replay/teardown
and static/security/dependency gates passed. Do not rerun completed gates without
a new change, failure or unresolved concern. Empirical acceptance remains pending.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY /
FINAL_VINTAGE_RESEARCH_ASSUMPTION. Production clearance OPEN; production use
NOT_CLEARED. P11-P14 calibration unchanged. P17 NOT_STARTED. Large market/model
artifacts remain local and out of Git.
