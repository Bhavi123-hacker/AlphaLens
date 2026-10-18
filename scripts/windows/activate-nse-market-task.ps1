param(
    [Parameter(Mandatory=$true)][string]$Config,
    [Parameter(Mandatory=$true)][string]$ApprovedPolicySha256,
    [Parameter(Mandatory=$true)][string]$ProposalXml
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$configPath = (Resolve-Path -LiteralPath $Config).Path
$xmlPath = (Resolve-Path -LiteralPath $ProposalXml).Path
$taskName = 'AlphaLens-Private-NSE-Market-Research'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw 'Expanded task already exists; inspect it instead of overwriting its policy'
}
# This entrypoint records an already received explicit operator approval.
# Passing a hash alone does not confer source rights or change the configured scope.
$receipt = @'
import json,sys
from pathlib import Path
from datetime import UTC,datetime
from workers.nse_market import engine,operational
from alphalens_api.auth.permissions import verify
p=Path(sys.argv[1]); c=operational.configured(p); policy=operational.policy(c)
if policy['policy_sha256']!=sys.argv[2] or not all((operational.readiness(c)['running_user_matches'], operational.readiness(c)['protected_credential_available'])):
 raise ValueError('EXACT_APPROVED_POLICY_AND_OPERATOR_REQUIRED')
if c.recurring_acquisition_enabled: raise ValueError('ALREADY_ENABLED_REQUIRES_REVIEW')
folder=c.root/'operational'; folder.mkdir(exist_ok=True)
approval=folder/'collection-approval.json'
if not approval.exists():
 engine._checked(approval,dict(policy_sha256=policy['policy_sha256'],approved_by='LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL',approved_at=datetime.now(UTC).isoformat(),scope='500_FIXED_STOCKS_250_PER_RUN_600_GET_PER_RUN_1800_GET_PER_IST_DAY_2030_2130_2230_60MIN_COOLDOWN_31DAY_CATCHUP',storage='ESTIMATED_5_TO_20_MB_PER_SESSION_EXCLUDING_BACKUPS',user_authorization='EXPLICIT_APPROVAL_IN_CURRENT_INVESTMENT_EVIDENCE_EXECUTION'))
value=json.loads(p.read_bytes());value['recurring_acquisition_enabled']=True
p.write_text(json.dumps(value,indent=2),encoding='utf-8');verify(p,directory=False)
operational._approval(operational.configured(p),policy)
print(json.dumps({'policy_sha256':policy['policy_sha256'],'run_user':c.run_user,'root':str(c.root)}))
'@
[xml]$xml = Get-Content -LiteralPath $xmlPath -Raw
$ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace('t','http://schemas.microsoft.com/windows/2004/02/mit/task')
$action = $xml.SelectSingleNode('//t:Actions/t:Exec/t:Arguments',$ns).InnerText
if (-not $action.Contains($configPath) -or -not $action.EndsWith('auto --scheduled"')) {
    throw 'Task action does not match exact approved protected configuration'
}
if ($xml.SelectSingleNode('//t:RunLevel',$ns).InnerText -ne 'LeastPrivilege' -or
    $xml.SelectSingleNode('//t:LogonType',$ns).InnerText -ne 'InteractiveToken') {
    throw 'Least privilege interactive operator required'
}
$json = $receipt | & (Join-Path $PSScriptRoot 'project-python.cmd') - $configPath $ApprovedPolicySha256
if ($LASTEXITCODE -ne 0) { throw 'Exact approval could not be recorded; task not registered' }
$checked = $json | ConvertFrom-Json
foreach ($node in $xml.SelectNodes('//t:Enabled',$ns)) { $node.InnerText = 'true' }
$xml.SelectSingleNode('//t:Description',$ns).InnerText = 'Explicitly approved bounded private 500-stock AlphaLens research; no orders; each run independently guarded'
try {
    # COM receives a Unicode BSTR, so omit the conflicting UTF-8 declaration.
    Register-ScheduledTask -TaskName $taskName -Xml $xml.DocumentElement.OuterXml -ErrorAction Stop | Out-Null
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if ($null -eq $task -or $task.State -eq 'Disabled') { throw 'Registered enabled task was not verified' }
} catch {
    # Registration failure leaves collection disabled; retain the immutable approval.
    $disable = @'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);v=json.loads(p.read_bytes());v['recurring_acquisition_enabled']=False;p.write_text(json.dumps(v,indent=2),encoding='utf-8')
'@
    $disable | & (Join-Path $PSScriptRoot 'project-python.cmd') - $configPath
    throw
}
$activation = @'
import json,sys
from pathlib import Path
from datetime import UTC,datetime
import uuid
from workers.nse_market import engine,operational
c=operational.configured(Path(sys.argv[1]));p=operational.policy(c);operational._approval(c,p)
folder=c.root/'operational'/'task-events';folder.mkdir(exist_ok=True);path=folder/(uuid.uuid4().hex+'.json')
engine._checked(path,dict(task_name='AlphaLens-Private-NSE-Market-Research',state='REGISTERED_ENABLED_LAST_VERIFIED',verified_at=datetime.now(UTC).isoformat(),policy_sha256=p['policy_sha256'],fixed_scope=c.expected_securities,cadence_ist=list(c.cadence_ist),maximum_get_per_run=c.max_requests_per_run,maximum_get_per_day=c.max_requests_per_day,least_privilege=True,interactive_token=True,original_reliance_task_modified=False,collection_success_claimed=False))
engine._pointer(c.root,'task-registration-latest.json',path)
print(json.dumps({'state':'REGISTERED_ENABLED_LAST_VERIFIED','source_requests':0,'new_session_capture_proven':False}))
'@
$activation | & (Join-Path $PSScriptRoot 'project-python.cmd') - $configPath
if ($LASTEXITCODE -ne 0) { throw 'Task registered; activation evidence write failed, inspect task before retrying' }
