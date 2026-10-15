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
