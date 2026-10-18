# AlphaLens private Windows runbook

Run from PowerShell in `D:\al-research\p28-worktree`. Keep the existing operator,
private configuration and Windows Credential Manager entries. These commands do
not create another account or reset a password.

## Start, inspect and stop

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\start-p33-alphalens.cmd
```

This starts the owned local PostgreSQL instance and the compiled private app.
Open <http://127.0.0.1:8017/login> and use the existing operator credentials.
The experimental workspace is <http://127.0.0.1:8017/experimental-ai-v2>.
The expanded saved-market workspace is <http://127.0.0.1:8017/nse-market>.
From a second PowerShell window:

```powershell
.\scripts\windows\check-alphalens.cmd .local-data\p33-runtime\operator-config.json
.\scripts\windows\stop-p33-alphalens.cmd
```

The stop command stops the matched native app and owned PostgreSQL process.
To stop only that app while retaining PostgreSQL, use:

```powershell
.\scripts\windows\stop-alphalens.cmd .local-data\p33-runtime\operator-config.json
```

## Use the research application

Open `/nse-market` for the saved current ordinary-equity universe and the actual
observed cohort. The dated master has 3,198 verified common equities; the current
qualified historical pilot has 500 securities and 447,483 observations. Search
does not download all their history. Open a selected stock's provider chart to
request its supported observations under the separate bounded terminal controls.
Read the distinct discovery, historical, technical, model and accepted counts.
If the saved master is stale, use the explicit identity-refresh control. The
authenticated `universe?refresh=true` request performs one official master GET;
default search/status/research reads remain saved-only. Refreshing identities
does not acquire their prices/history or automatically expand the 500-stock plan.

The expanded V2 model has 300 genuinely scored securities and Top 5/10/20 lists.
The separately registered LSTM study has 43 current experimental scores. Those
cohorts overlap. Neither score is an independently calibrated profit probability
or buy/sell instruction. The LSTM's historical point improvement remains uncertain
and its assumed-cost reference strategies were negative. Review the linked
baseline comparisons and known-period limitations before using the shortlist as
a research starting point. Exact private prices/leaderboard bodies stay behind
authentication and must not be copied into a public report or public demo.

Search an NSE symbol in Stock Analysis and explicitly load provider observations.
Read the provider timestamps, freshness and delayed/indicative label. Switch the
chart source to inspect the frozen archive separately. A displayed quote is not
an execution or official portfolio mark.

Experimental AI Stock Research V2 shows saved model scores, company identity,
dated technical evidence, preferences and recorded portfolio cost concentration.
Top 5/10/20 never pads unavailable securities. The page refreshes saved local
evidence every minute while visible; it does not acquire prices or train models.
Use the linked charts, Evidence Passport, historical leaders and Research Decision
Desk to investigate. Preferences filter research; they do not alter model scores.
Portfolio cost weights are distinct from market-value exposure.
For supported holdings, a verified retained private V2 EOD mark can supply
indicative portfolio/scenario research after the terminal cache expires. Its
label states adjusted EOD and unreconciled actions; it is never an execution,
official close or accepted economic valuation. Future/identity-mismatched/known
excluded marks and marks older than seven calendar days are unavailable. The
private EOD cache expires after 60 seconds and invalidates source changes.

Forward Evaluation shows pending, excluded, missing and unknown evidence. Zero
matured outcomes means prospective performance is not yet measurable. The entry
timestamp and five subsequent eligible sessions must genuinely occur; a missed
entry is never backdated. Accepted rankings remain unavailable until independent
research, economic and review requirements actually pass.

## Bounded manual daily workflow

The commands below preserve the original 50-stock V2 workflow. The expanded
configured-cohort engine is separate; its recurring acquisition remains disabled
until its exact stock scope, schedule, maximum requests and storage consequences
have the required explicit approval. Do not use an older V2 approval or the
RELIANCE schedule as authorization for expanded recurring acquisition.

For the fixed 500-stock guarded workflow, the working zero-provider-request check is:

```powershell
.\scripts\windows\run-nse-market.cmd .local-data\full-nse-runtime\market-workflow-500.json auto --dry-run
```

The dry run verifies the pinned plan, current operator, protected credential and
independent clock, and reports pending session lookup without inventing it. After
an eligible session, an explicit authorized manual collection uses the same
configuration with `--collect`. Automatic selection uses dated official sessions;
publication delay, unavailable observations and empty history stay pending.
Catch-up is bounded to thirty-one calendar days and preserves original receipts.
Successful unchanged source replay uses zero instrument downloads.

The expanded proposal is **disabled and unregistered**. Its exact scope is the
pinned 500-stock plan, at most 250 securities/600 GET attempts per run, at most
three attempts/1,800 GETs per IST day, sixty-minute independent-clock cooldown,
and 20:30/21:30/22:30 IST. Missed triggers may run at the next login under the same
caps. A conservative completed 500-stock session can require up to 1,071 requests,
including bounded calendar work and one master refresh; missing publication can
leave the session incomplete. The full 3,198-stock universe cannot be updated by
three 250-stock batches daily. No new identity is automatically added to the fixed
approved scope. Retained raw/versioned observations and forecast evidence grow
private storage; these limits do not authorize automatic deletion.

Before enabling that task, obtain the required explicit approval of its exact
scope, cadence, quota, missed-login behavior and storage consequences. Inspect the
disabled XML under `.local-data\full-nse-runtime\task-proposal-20261018` and the
recorded readiness receipt. An XML export is not an enabled task. Check registration
without changing it:

```powershell
Get-ScheduledTask -TaskName AlphaLens-Private-NSE-Market-Research -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskName AlphaLens-Private-EOD-Watchlist
Get-ScheduledTaskInfo -TaskName AlphaLens-Private-EOD-Watchlist
```

The original RELIANCE task remains separate and must not be replaced by this proposal.

The preserved 50-stock V2 commands follow:

```powershell
.\scripts\windows\run-v2-research.cmd .local-data\final-operational-runtime\v2-workflow.json --dry-run
```

The dry run checks local evidence and clock readiness without requesting provider
prices. After an eligible session closes, this explicit manual command permits
the guarded acquisition/reconciliation/inference sequence:

```powershell
.\scripts\windows\run-v2-research.cmd .local-data\final-operational-runtime\v2-workflow.json --collect
```

The private configuration bounds one session per run, catch-up, cooldown and
provider quotas. Current limits are 120 GETs/run, at most three runs/day and a
60-minute cooldown. Missing publication stays pending; rerun only when permitted
by the recorded cooldown. Successful replay does not redownload complete sessions.
New evidence appends immutable snapshots and forecasts; it never retrains a model
on a dashboard visit. Check Saved Research Operations for the latest state and
sanitized failure stage before retrying.

The existing `AlphaLens-Private-EOD-Watchlist` RELIANCE task remains separate at
08:30 IST. The larger V2 proposal is prepared, **not activated**. Its proposed
20:30/21:30/22:30 IST slots are conservative operational choices, not a guaranteed
provider publication time. Expanded recurring collection requires the specific
recorded approval. Both workflows require Windows running, the same operator
logged in and the original protected credential available.
`StartWhenAvailable` permits a missed V2 trigger to run at the next login,
including outside those evening slots; the same three-attempt daily limit and
independent-clock cooldown still apply. The dashboard's last successful run can
be a dry run or holiday check; inspect its source stage and observation date to
confirm an actual capture.

```powershell
Get-ScheduledTask -TaskName AlphaLens-Private-EOD-Watchlist
Get-ScheduledTaskInfo -TaskName AlphaLens-Private-EOD-Watchlist
.\scripts\windows\check-v2-research-task.ps1 -Config .local-data\final-operational-runtime\v2-workflow.json
```

The check prepares no task, enables no collection and requests no provider prices.
If data, clock, credentials, identity or calendar evidence fails, keep the reported
failure; inspect the named prerequisite before another bounded run. Do not edit
timestamps, feature values, model weights or receipts to clear a check.
An enabled task is not proof its last run succeeded: inspect `LastTaskResult`.
After resolving a missed/failed RELIANCE run, manually resume that existing task
with `Start-ScheduledTask -TaskName AlphaLens-Private-EOD-Watchlist`; this preserves
its original schedule and bounded worker. Do not use that command to register or
enable the separate V2 proposal without its required approval.

## Back up and restore personal operational records

Use new destinations. Pause manual record edits while taking a cross-store backup.
The existing tool uses SQLite online backup and integrity/checksum manifests:

```powershell
$stamp = Get-Date -Format yyyyMMdd-HHmmss
.\scripts\windows\backup-alphalens.cmd .local-data\p33-runtime\operator-config.json ".local-data\operator-backup-$stamp"
.\scripts\windows\project-python.cmd -m alphalens_api.operations.cli restore --source ".local-data\operator-backup-$stamp" --destination ".local-data\operator-restored-$stamp"
```

Restore writes a new isolated location, verifies file integrity and removes copied
login sessions. It does not replace the running stores or alter the source backup.
Review the restored records before considering a configuration change. Existing
online-backup/isolated-restore tests cover authentication, personal FIFO records,
alerts and operations. The backup includes the configured P19 prospective store
when present; it does **not** claim to back up PostgreSQL, Windows Credential
Manager, the frozen archive or the separate V1/V2 experimental evidence/ledgers.
Keep those preserved private roots intact and keep backups out of Git/public demo.

For separate research evidence, use the complementary research bundle. Its current
default includes V1/V2 data/models/inference/forecast ledgers and, when present,
the saved NSE universe, expanded market dataset/ledgers and sequence-study evidence.
It uses online SQLite backup, preserves source hashes, validates the model and
restores only into a new private folder:

```powershell
$stamp = Get-Date -Format yyyyMMdd-HHmmss
.\scripts\windows\project-python.cmd -m scripts.backup_research backup --destination ".local-data\research-backup-$stamp"
.\scripts\windows\project-python.cmd -m scripts.backup_research restore --source ".local-data\research-backup-$stamp" --destination ".local-data\research-restored-$stamp"
```

Pause manual collection/inference while creating a research bundle. Keep the
personal and research bundles together; neither exports Credential Manager
secrets or claims to include PostgreSQL/the original frozen archive. A failed
bundle must not be used for recovery. Existing destinations are refused.
Retain both original and engineering-corrected sequence reports: the derivative
removes only inappropriate Ridge probability diagnostics and adds a later timing
attestation. It does not overwrite the original model, results or predictions.

## Optional sequence research environment

The native dashboard reads saved numeric model state; it does not require PyTorch
or train a model on page load. The completed research fit used a separate protected
`.local-data\lstm-cpu-env` environment with official checksum-verified PyTorch 2.14.1.
Its isolated dependency audit found zero vulnerabilities after the environment's
pip update; the main dependency lock and application runtime were not changed.

The optional environment must run the original trusted environment's `.pth`
bootstrap as well as resolve its packages. Its existing
`Lib\site-packages\alphalens_existing_env.pth` contains:

```python
import site

site.addsitedir(r"D:\al-research\p28-worktree\.venv\Lib\site-packages")
```

Merely appending that directory to `sys.path` omits native Windows bootstrap hooks
needed for the owner-protected ACL checks. The initial bootstrap failure occurred
before an experiment attempt or fit and was corrected. Use only the trusted local
environment path; a `.pth` file can execute Python and must not be sourced from an
untrusted project or copied from an unreviewed download.

`run-sequence-benchmark.cmd` sets two CPU threads and uses that optional environment.
The completed immutable experiment refuses re-execution into its existing output
root. Do not delete its attempt marker, overwrite artifacts or rerun fits to obtain
a better result. Any future experiment needs a separately registered protocol and
a new private output root. The recorded study has one LSTM and five traditional
fits plus three baselines, no accepted rankings and no LSTM prospective forecasts.

Read-only preservation verification is available through:

```powershell
.\scripts\windows\project-python.cmd -m scripts.verify_ml_v2_preservation
.\scripts\windows\project-python.cmd -m scripts.verify_final_research_preservation
```

This hashes frozen research and original alerts, checks V1 artifacts, accounts
and personal records, and writes a new private metadata receipt. It performs no
provider price request or original research rerun.
