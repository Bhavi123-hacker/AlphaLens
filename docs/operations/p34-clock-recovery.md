# P34 Windows clock diagnosis and safe recovery

No application timestamp tolerance, receipt-time substitution, NTP offset applied
to prices, artificial delay or manually invented clock value is permitted.

The administrator's14:27:02IST resync succeeded. Success means a synchronization
request completed; it does not guarantee negligible remaining phase error. The
following independent read-only measurements were made afterward:

| Source / measurement | Result |
| --- | --- |
| time.windows.com,14:28 | median server-minus-local350.8443ms; maximum reported distance25.80145ms |
| time.google.com,14:32 | median355.5743ms; maximum reported distance27.5637ms |
| time.nist.gov,14:32 | median358.9628ms; maximum reported distance124.8573ms (longer RTT) |
| time.windows.com,14:48 | median345.2751ms; maximum reported distance26.0203ms |
| Native clock adjustment,14:32 | adjusted/nominal156250/156250; programmed rate difference0ppm |
| Precise wall clock vs monotonic,14:32 | +11.10microseconds over30.000645seconds;0.37ppm |
| Native clock adjustment,14:47–14:48 |156265/156250; programmed rate difference+96ppm |
| Precise wall clock vs monotonic,14:48 | +2.9113ms over30.000513seconds;+97.04ppm |

Windows has therefore begun reporting/measurably applying a slow rate correction,
after the earlier nominal-rate observation. It is **not yet accurately synchronized
enough for current quote acceptance**. A345ms phase error would take roughly an
hour at a constant96ppm net correction; this is illustrative, not an ETA, because
rate, oscillator drift, network delay and service state can change. Do not repeatedly
reset error statistics just to obtain a successful resync message.

Reported distance = half roundtrip + half nonnegative server root delay + server
root dispersion. These are unauthenticated NTP error estimates under NTP/path
assumptions, not cryptographic proof of UTC or permission to accept future quotes.
Clock precision119ns is not accuracy. HTTPS Date has one-second precision and
cannot resolve this discrepancy. Cloudflare's initial five probes timed out;
Google and NIST subsequently responded and corroborated Microsoft's positive lag.

Windows Time remained RUNNING/Automatic, Leap0/Stratum5, source time.windows.com.
At14:48 it still reported Hold, last successful sync14:27:02, phase offset348.6535ms,
root dispersion8.1189337seconds and last error2 (stale time data). Registry reads:
MaxAllowedPhaseOffset1second, PhaseCorrectRate1, FrequencyCorrectRate4,
UpdateInterval360000, HoldPeriod5, SpecialPollInterval32768seconds. No settings
were changed by the agent. HypervisorPresent alone does not prove a competing VM
time provider; do not disable Hyper-V, VBS, security or time providers speculatively.

Microsoft documents that an offset within MaxAllowedPhaseOffset is normally
corrected through clock rate, while a larger offset can be stepped. See
[Windows Time tools/configuration and phase correction](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/windows-time-service-tools-and-settings#configure-a-computer-clock-reset)
and [read-only native adjustment query](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getsystemtimeadjustmentprecise).
The precise adjustment export was unavailable on this host; the documented
GetSystemTimeAdjustment fallback supplied the displayed increments. Actual wall
rate used GetSystemTimePreciseAsFileTime against the monotonic counter.

## Safest next action

Keep Windows Time running and allow its measured correction to converge, checking
offset periodically with a small bounded sample. Do not poll provider quotes while
the independently measured hundreds-of-milliseconds lag persists. For example:

```bat
cd /d D:\al-research\p28-worktree
scripts\windows\project-python.cmd scripts\p34_clock_diagnostics.py --source time.windows.com --output .local-data\p34-clock-next-check.json
```

Use a new output filename for each check. No resync, service restart, registry
write or financial-price acquisition occurs in this command.

If immediate correction is required, an administrator should review effective
Windows Time/Group Policy and service events in a maintenance window, preserve
the current configuration, and arrange a **trusted-NTP-based clock step** through
the documented phase policy rather than typing a guessed time. The current1second
threshold routes this~350ms error into gradual correction. Temporarily lowering
that threshold to0, resynchronizing from the verified source, verifying actual
offset, then restoring the original value is an administrator-reviewed option;
it was **not executed or silently authorized here**. Stop AlphaLens and coordinate
other timestamp-sensitive applications before any system-wide step. Do not
override domain policy or permanently alter unrelated settings to make one quote
pass. Successful command output must still be followed by a measured offset check.

Also investigate stale service samples/UDP123 transport: Microsoft's documentation
distinguishes the service's UDP123 source port from stripchart's ephemeral source
port. Successful stripchart probes alone do not verify the service's transport.
Full effective-configuration query required elevation and was denied; no second
elevation was requested after the user's one successful administrator resync.

After repair, use one bounded six-stock verification and the strict browser case.
It must pass trade_time <= quote_generated_at <= actual local_receipt with no
tolerance. The dated EOD fallback browser case is a separate criterion and never
turns a failed CURRENT_QUOTES check into a pass.

## Follow-up measurement, 15 October 2026, 15:14 IST

Five samples per source, taken concurrently, still show a positive phase error:

| Source | Median server minus local | Maximum reported distance |
| --- | --- | --- |
| time.windows.com | +242.9655 ms | 38.32955 ms |
| time.google.com | +243.2004 ms | 20.0738 ms |

Every sampled uncertainty interval was positive. These estimates remain subject
to the unauthenticated-NTP/path limitations above. Native programmed correction
was +64 ppm; precise wall time gained 2.083700 ms over 30.000131 seconds of
monotonic time (+69.4564 ppm). Compared with the earlier 345 ms observation,
correction is progressing, but **convergence FAILED**. No provider quote was
requested in this follow-up: the user's condition for that request was not met.

The verbose status still reported Hold, stale-data error 2, phase 249.5303 ms,
last successful sync 14:27:02 and root dispersion 8.1189337 seconds. The separate
peer query reported Active, one valid sample, last peer sync successful, peer
poll 17 (reported out of valid range), host poll 10 and approximately 29,743 seconds
until the next peer poll. Existing NtpServer flags are 0x9 and SpecialPollInterval
is 32,768 seconds. Thus the peer's special polling schedule and the sub-one-second
phase threshold help explain continued correction from an old sample. The status
and peer success fields are distinct; neither proves negligible clock error.
System events show valid provider data at 14:27:02 (event 37); no newer time-service
event was found in the bounded two-hour System-log query. This does not prove
blocked UDP, DNS failure, or a competing hypervisor clock. No firewall, time
provider, service policy or registry setting was modified.

## Administrator-reviewed maintenance and rollback procedure

This is a procedure for review, **not an instruction already executed by the
agent**. Waiting for the measured gradual correction is the least disruptive
option. If prompt correction is necessary, the administrator can review the
documented phase-step option below. A successful resync alone is insufficient.

1. Coordinate a maintenance window for timestamp-sensitive applications. Stop
   only the owned AlphaLens app using `scripts\windows\stop-alphalens.cmd
   .local-data\p33-runtime\operator-config.json`; leave unrelated processes alone.
2. In an Administrator PowerShell, capture `w32tm /query /configuration /verbose`,
   `w32tm /query /status /verbose` and `w32tm /query /peers /verbose` to a new private
   diagnostic directory. Check domain membership/effective Group Policy and the
   configured peer. If policy-managed, stop and have the policy administrator
   review it. Do not override domain settings. The non-elevated follow-up found
   no W32Time policy registry root, but that is not a substitute for this review.
3. Verify both trusted-source offsets again. If they disagree materially or show
   a large/unexpected error, investigate instead of stepping. Review service UDP
   123 transport if stale samples persist; successful stripchart uses a different
   source port and cannot establish service transport health.
4. For this reviewed standalone configuration only, the following block saves the
   original DWORD and restores it even if the update/resync fails. Run from the
   repository root, with a **new** backup filename. It changes only the phase
   threshold temporarily; it does not set a hand-entered time, change peers,
   alter polling frequency, or relax application validation.

```powershell
$phaseKey = 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config'
$phaseBackup = '.local-data\p34-phase-policy-before-maintenance.json'
if (Test-Path -LiteralPath $phaseBackup) { throw 'Use a new backup filename' }
if ((Get-CimInstance Win32_ComputerSystem).PartOfDomain) {
    throw 'Domain administrator review required; do not override policy'
}
if (Test-Path 'HKLM:\SOFTWARE\Policies\Microsoft\W32Time') {
    throw 'Policy review required; do not override policy'
}
$phaseKind = (Get-Item -LiteralPath $phaseKey).GetValueKind('MaxAllowedPhaseOffset')
if ($phaseKind -ne [Microsoft.Win32.RegistryValueKind]::DWord) {
    throw 'Expected existing DWORD; inspect configuration first'
}
$phaseOriginal = [int](Get-ItemPropertyValue -LiteralPath $phaseKey -Name MaxAllowedPhaseOffset)
@{ MaxAllowedPhaseOffset = $phaseOriginal } | ConvertTo-Json |
    Set-Content -LiteralPath $phaseBackup -Encoding utf8 -ErrorAction Stop
try {
    Set-ItemProperty -LiteralPath $phaseKey -Name MaxAllowedPhaseOffset -Value 0 -ErrorAction Stop
    & "$env:SystemRoot\System32\w32tm.exe" /config /update
    if ($LASTEXITCODE -ne 0) { throw 'Configuration reload failed' }
    & "$env:SystemRoot\System32\w32tm.exe" /resync /rediscover
    if ($LASTEXITCODE -ne 0) { throw 'Resync failed; original threshold will be restored' }
} finally {
    Set-ItemProperty -LiteralPath $phaseKey -Name MaxAllowedPhaseOffset -Value $phaseOriginal -ErrorAction Stop
    & "$env:SystemRoot\System32\w32tm.exe" /config /update
    if ($LASTEXITCODE -ne 0) { throw 'Restored registry value; service reload needs administrator review' }
}
```

5. If the shell or machine is interrupted before restoration, recover from that
   exact backup in Administrator PowerShell, then verify the effective value:

```powershell
$phaseKey = 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config'
$phaseBackup = '.local-data\p34-phase-policy-before-maintenance.json'
$phaseSaved = Get-Content -LiteralPath $phaseBackup -Raw | ConvertFrom-Json
if ($null -eq $phaseSaved.MaxAllowedPhaseOffset) { throw 'Original value missing' }
Set-ItemProperty -LiteralPath $phaseKey -Name MaxAllowedPhaseOffset -Value ([int]$phaseSaved.MaxAllowedPhaseOffset) -ErrorAction Stop
& "$env:SystemRoot\System32\w32tm.exe" /config /update
if ($LASTEXITCODE -ne 0) { throw 'Service reload failed; administrator review required' }
& "$env:SystemRoot\System32\w32tm.exe" /query /configuration /verbose
```

   The observed original value was 1 second; use the captured value, not an
   assumed default. This rolls back **policy**, not elapsed time. Do not set the
   clock backward to undo a legitimate NTP correction, import the entire service
   registry, unregister the service, or restore unrelated settings.
6. Verify actual offsets against Microsoft and Google and inspect new service
   status/events. Restart the owned app with the same operator configuration:
   `scripts\windows\start-alphalens.cmd .local-data\p33-runtime\operator-config.json`.
   Only after convergence, run one fresh six-stock test and the authenticated
   strict browser case. No finite NTP error estimate guarantees a provider
   chronology pass: actual provider generation/trade/receipt ordering remains
   decisive. If provider time still leads after independent clock convergence,
   preserve rejected metadata and escalate the measured provider discrepancy.

The phase-policy behavior and source-port distinction are documented in the
Microsoft tools/settings link above. This procedure has been syntax-reviewed;
no administrator configuration mutation or clock-step success is claimed.
