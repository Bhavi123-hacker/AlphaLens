# Collector cutover preparation, 25 October 2026

**Third activation: FIXED_AWAITING_LIVE_VERIFICATION.** The operator supplied a
new exact-plan approval, and the single reviewed action replacement was applied
on26 October2026 at04:51:49 UTC. Fresh preflight and post-change identity,
configuration, security and watchlist checks passed; no rollback was needed.
The next existing trigger is26 October20:30 IST. No manual collection was
started. Actual scheduled lifecycle and publication remain unverified until
genuine receipts exist. See
[third-cutover evidence](ALPHALENS_THIRD_COLLECTOR_CUTOVER_2026-10-26.md).
The clock recovery and new source-bound proposal are recorded in
[ALPHALENS_CLOCK_GATE_RECOVERY.md](ALPHALENS_CLOCK_GATE_RECOVERY.md).
The new preparation tool has no scheduler mutation, registration, disabling,
launch or live-collection mode. The original scheduled tasks, shared environment,
private port 8041 application, configurations, reservations and financial/research
records remain preserved. Only the explicitly approved market-task action changed.

## Exact proposed change

Only `AlphaLens-Private-NSE-Market-Research` is in the proposed action scope.
`AlphaLens-Private-EOD-Watchlist`, including the original RELIANCE workflow, is
exported for preservation and is excluded from any proposed change.

Both actions use the native Windows `System32\cmd.exe` and working directory
`D:\al-research\p28-worktree`. The tool verifies the existing command against
the Windows directory obtained through the native Windows API; it does not trust
PATH or accept another executable merely because it is named `cmd.exe`.

Reviewed existing arguments:

```text
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-market.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json" auto --scheduled"
```

Proposed arguments:

```text
/d /c ""D:\al-research\p28-worktree\scripts\windows\run-nse-collector-isolated.cmd" "D:\al-research\p28-worktree\.local-data\full-nse-runtime\market-workflow-500.json""
```

The first wrapper reaches the preserved shared `.venv` through
`project-python.cmd`. The proposed wrapper pins
`.local-data/production-collector-runtime-20261024/venv/Scripts/python.exe` and
the same checkout's imports, with the existing CPU thread guards. No fallback
to the shared interpreter is allowed if the candidate is missing or fails.
Executing the candidate wrapper with this real configuration requests collection;
it is not an offline test command and was not executed here.
The observed original `.venv` resolves to
`D:\al-research\p17-api\workspace-venv-original`. Its redirector executable hash
is `41123879d2e991377997acadf5f0cf8f34fa10d86362eded8c69b6041e2893b5`;
the separate package-version inventory is private and preserved in the plan.

The proposal preserves principal, interactive logon, enabled state, trigger
boundaries, retry settings, execution limit, `IgnoreNew`, start-when-available,
the exact protected config and approval, all storage/model/forecast policies and
the existing 500-security cohort. The unchanged limits are 250 securities/run,
600 reserved GETs/run, 1,800/day, three collecting reservations/day, 60-minute
conservative cooldown and 20:30/21:30/22:30 IST triggers. Existing consumed and
interrupted reservations are never cleared.

## Read-only preparation and preflight

`scripts/nse_collector_cutover.py` supports only `prepare` and `verify-plan`.
Preparation writes into a fresh, owner-protected child under this checkout's
`.local-data`; it rejects existing output locations and reparse paths. Task XML
is captured through fixed local getter/export commands and remains private.
Unexpected task arguments are rejected before any action text is reported.

Example commands use a **new absent child directory**. They neither change a task
nor cause an Upstox request:

```powershell
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.nse_collector_cutover prepare --directory D:/al-research/p28-worktree/.local-data/operational-acceptance-20261025/cutover-REVIEW-NEW --run-focused-tests
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.nse_collector_cutover verify-plan --directory D:/al-research/p28-worktree/.local-data/operational-acceptance-20261025/cutover-REVIEW-NEW
```

The private artifact set contains exact `market-before.xml`, an action-only
`market-proposed.xml`, byte-preserving `market-rollback.xml`, the separate original
`watchlist-preserved.xml`, `plan.json` and a hash-bound focused test log. XML
comparison covers all elements and attributes outside the action. Preflight also
reconstructs and checks the reviewed action-only proposal. Restoring the complete
task/principal from exported XML is not proposed.

Actual exported XML omits some default values. The tool does not assume those
values: an omitted run level requires the independent native principal getter
to report `Limited`, and each omitted trigger-enabled field requires its native
getter to report true. Explicit elevation, disabling, changed trigger times,
unreviewed arguments or a non-system command are rejected.

## Candidate identity and its limits

The installation receipt records frozen lock SHA-256
`908c05de617b9870c6b7b3e3f77aaf51dc65507bf063beee46e2cbea5f2e6ce8`, base
Python SHA-256
`fd5c46d73d29ba21b04c844bbaf9096066136526911230645a2a040d23fb612b`, copy-mode
installation and package versions. It **does not contain a prior complete venv
file manifest**. The tool therefore never claims historical bitwise identity.

It independently checks current lock/base-interpreter/package versions against
that receipt, validates installed distribution RECORD hashes and paths, and
establishes a new fingerprint of installed records, the candidate launcher,
`pyvenv.cfg`, runtime source/configuration inputs and all other non-bytecode
files inside the candidate venv. The external base interpreter is compared by
its recorded executable hash; this does not certify every external stdlib or
Windows file byte-for-byte. Unregistered files and unhashed RECORD entries are listed in the
private report and included in the fresh fingerprint; they are not represented
as independently RECORD-verified files. Regenerable `.pyc` files are explicitly
excluded, and no bytecode cleanup is performed.

Runtime hashing uses four bounded read-only workers. It imports no installed
estimator/provider code, makes no request, installs nothing and changes no package
or interpreter. Source identity is checked before the audit and after its fixed
offline compatibility tests. Any source/runtime drift invalidates the proposal.
The original shared interpreter's resolved path, executable hash and package
versions are captured separately and must also remain unchanged at preflight.

The fixed focused test selection covers the cutover tool, launcher/process
diagnostics, malformed-response and action-resume isolation, daily publication
and zero-GET replay, fair batch selection and operational quotas. It runs only
TEST_ONLY fixtures under the candidate, with bytecode writes and pytest caching
disabled. Prior full application/model/research tests are reused through their
existing reports; these focused tests do not replace the final release's
candidate-environment regression or security gates.

An initial actual frozen-source audit verified all four identity gates and
15,387 RECORD-listed files, with 15,404 non-bytecode files in the fresh manifest.
The 17 additional files were uv-created activation/bootstrap files, interpreter
redirectors, environment markers and `pyvenv.cfg`; their exact paths and hashes
are included in the private report. Its 102 unhashed RECORD entries were included
in the fresh fingerprint. These are measured inventory facts, not prior bitwise
identity proof.

## Verification and safe failure

The unit cases verify action-only XML changes, exact in-memory rollback,
unreviewed argument rejection, elevation/trigger/concurrency policy rejection,
native qualification of omitted XML defaults, hardened XML parsing, RECORD
tampering, path escape rejection, bytecode exclusion and preflight rejection of
changed tasks/backups/test receipts/runtime identities. The rollback exercise is
an offline state simulation; it is not a claim that Windows Task Scheduler makes
multi-step updates transactional.

Two in-progress read-only hash audits were stopped after confirming their exact
owned PID, parent and command because source was still changing. No application,
scheduled worker or unrelated process was terminated. No successful identity
claim is based on those interrupted audits; their locations remain preserved.
The final artifact identity and exact passing check results are recorded in the
campaign's final evidence after source freeze.

The first full bound compatibility run in `cutover-frozen-final` retained
**42 passes / five failures**: its test harness placed temporary fixtures under
the long private review directory, exceeding Windows path limits when immutable
attempt filenames were added. The production path and financial logic were not
changed to accommodate the test. The harness now sets the existing
`ALPHALENS_TEST_TEMP_ROOT=D:/al-tests` and lets `tests/conftest.py` allocate a
fresh absent owned short child; it supplies no explicit `--basetemp` and deletes
no existing directory. The failed plan and its test log remain preserved and
blocked. Direct verification under the short root passed all **47** selected
compatibility cases; the corrected tool's own cases passed **15**.

The standalone tool's unsuppressed Bandit findings are the low-severity advisory
for importing `subprocess` and its two fixed-argv calls: native read-only task
getters and the fixed offline pytest selection. There is no `shell=True`, free
command input or raw exception output. These advisory findings are reported;
no scanner setting or exclusion was changed.

## Final measured checkpoint

The corrected protected plan was prepared **25 October 2026, 08:28:09 UTC** in
`.local-data/operational-acceptance-20261025/cutover-approved-scope-final`.
The directory name describes a proposed approval scope; no approval was granted.

| Gate | Result |
|---|---|
| Fixed candidate offline compatibility selection | VERIFIED_COMPLETE: **47 passed in 9.40 seconds** |
| Tool-only post-harness checks | VERIFIED_COMPLETE: **15 passed in 0.51 seconds** |
| Frozen lock/base executable/package version/installed RECORD comparison | VERIFIED_COMPLETE: all four true |
| Source stable across audit and candidate fingerprint stable before/after tests | VERIFIED_COMPLETE: both true |
| Fresh read-only `verify-plan` after preparation | VERIFIED_COMPLETE; same fingerprint and unchanged original tasks/config/environment |
| Focused Ruff/format/strict typing | VERIFIED_COMPLETE; Windows and Linux-target typing of the two new source/test files passed |
| Standalone tool Bandit | Three unsuppressed LOW advisories; zero MEDIUM/HIGH |
| Scheduled collector action replacement | BLOCKED_APPROVAL; not performed |
| Actual candidate scheduled collection | BLOCKED_APPROVAL; not launched or live verified |
| Original shared/RELIANCE environment security | BLOCKED_SECURITY; preserved, with the known advisory limitations |

Review identifiers:

```text
plan.json SHA256:
c91635db2a204ee4d47e08ccb44a0ae3026bffe0c76e563fb66da7d731c55a23
fresh candidate/source fingerprint:
ac15c85b392f795b447fee121c3768431a5b9ce67f6a3cc0eeccfd36532c35f6
runtime source manifest (317 files):
377290d39abd78dadcb2225ee137bc21a8be2971f93ee1774cfaf4ce929fd424
original and exact rollback task XML:
a6b76cd4fd6336873ddf0c33d24502a8cce03c77230db31d5da3a2fc56798820
proposed action-only task XML:
fd8ab60d851b47b83d06dce4a63847dc6de7cbaeac0420f24950bcd481eeac8a
preserved RELIANCE/watchlist task XML:
d10e3c79242a9601418d8c22d2e9f4e367a5b2799aba4ab0fa2b4a8ee1b72419
unchanged protected 500-stock configuration:
6ced3ac164064bb8f94458059bbfe0299035e880b27e51a47ccc4f3a69e36a6d
unchanged approved collection policy:
4f580e46d8b8fdf94f5a1777ad412d3b0f94a1b9b0a6c810d5133f58f59f5778
```

The observed task was **Ready**, with the next existing trigger
**25 October 15:00 UTC / 20:30 IST**. These observations are dated, not a promise
of a future successful collection. Every tool result records zero provider
requests and `tasks_modified=false`; full preflight still returns
`status=BLOCKED_APPROVAL` and `prior_bitwise_identity_claimed=false`.

## Approval scope and later verification

Future approval must identify the final protected plan/fingerprint and authorize
only the action replacement on `AlphaLens-Private-NSE-Market-Research`, together
with conditional restoration of the reviewed original action if critical
post-change checks fail. The approval must explicitly acknowledge that restoration
reinstates the original runtime's 41 recorded dependency advisories and
**BLOCKED_SECURITY** status. If that conditional rollback is not authorized up
front, do not begin cutover. Before any
approved action, require unchanged source/runtime/config/approval/XML hashes,
successful focused and final release checks, and the original enabled task in
`Ready` state rather than `Running`, `Queued` or an unverified state. A
successful preparation or preflight remains **BLOCKED_APPROVAL** and grants no
authority to modify or launch a task.

The following is a future operator procedure **only after that approval**. The
prepared tool does not run these commands. Use the final reviewed directory,
confirm its plan SHA-256 against the approval, and first run its read-only
`verify-plan` command. A nonzero exit stops the procedure. Do not run a task or
the collection wrapper to test the change.

```powershell
$review = 'D:\al-research\p28-worktree\.local-data\operational-acceptance-20261025\cutover-approved-scope-final'
& .local-data/production-collector-runtime-20261024/venv/Scripts/python.exe -m scripts.nse_collector_cutover verify-plan --directory $review
if ($LASTEXITCODE -ne 0) { throw 'Reviewed cutover preflight did not pass' }
$plan = Get-Content -LiteralPath (Join-Path $review 'plan.json') -Raw | ConvertFrom-Json
$taskName = 'AlphaLens-Private-NSE-Market-Research'
$current = Get-ScheduledTask -TaskName $taskName
if ($current.State -ne 'Ready') { throw 'Expected the original enabled task idle and Ready' }
$proposed = $plan.actions.proposed_action
$newAction = New-ScheduledTaskAction -Execute $proposed.Command -Argument $proposed.Arguments -WorkingDirectory $proposed.WorkingDirectory
# APPROVAL REQUIRED: change only the reviewed task action.
Set-ScheduledTask -TaskName $taskName -Action $newAction
```

After an approved change, compare the re-exported task against the reviewed
proposal and confirm the RELIANCE task is unchanged. Wait for an existing approved
trigger. Genuine independent-clock acceptance, actual bounded requests, a durable
terminal receipt, accepted per-security observations, published derived data and
immutable forecast lineage are required before live collector verification can
be claimed. No manual collection, new trigger, quota increase or public deployment
is included.

The rollback artifact identifies the exact old action. Conditional restoration
must be recorded with its failed check and operator identity under the upfront
approval; it is not a silent interpreter fallback. No second permission request
is needed when that approval already covers restoration after critical failure.
First confirm that the current task is
idle and still has the reviewed proposed action and unchanged invariant XML.
Restore only the old action, rather than registering the complete exported task:

```powershell
[xml]$before = Get-Content -LiteralPath (Join-Path $review 'market-rollback.xml') -Raw
$old = $before.Task.Actions.Exec
$oldAction = New-ScheduledTaskAction -Execute ([string]$old.Command) -Argument ([string]$old.Arguments) -WorkingDirectory ([string]$old.WorkingDirectory)
# Execute only under the upfront conditional rollback approval; record failure/operator.
Set-ScheduledTask -TaskName $taskName -Action $oldAction
```

Re-export and compare the restored action and all invariant fields with the
protected original XML, and verify the separate watchlist task is unchanged.
`verify-plan` expects the original action; it deliberately rejects a task after
cutover instead of treating that changed state as another approved plan.
Retain both runtimes and all evidence. This preparation does not clear public
data rights, independent model acceptance, or the separate preserved RELIANCE
runtime's security limitations.
