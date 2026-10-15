# Bounded private quote receipt policy — p34.quote-clock-interval.v1

Authorized by the user's 15 October request for bounded NTP calibration. This
explicitly replaces local-receipt-only validation for private terminal/watchlist
quotes; historical strict-local results remain failures, not retroactive passes.
It does not set Windows time or alter ingestion, calendars, ML, risk, financial
advice, redistribution, authentication or security gates. No added dependency.

## Trust and acquisition

Only fixed independent operators `time.windows.com` and `time.google.com` are
queried. Each supplies three on-demand samples one second apart, concurrently
across sources. Three valid samples per source remain mandatory. Following the
explicit indicative-display authorization, a single UDP timeout per source may
be retried once: at most eight probes per 30 seconds **per backend process**.
Malformed replies, disagreement and failed bounds are never discarded or retried
into acceptance. Failures have the same cooldown. No scheduled probing or provider polling. Each
socket has a two-second timeout; an eight-second source deadline rejects delayed
work. DNS uses the OS resolver and its timeout; this is not a hard wall-clock
bound on OS DNS resolution. Late samples cannot become fresh evidence.

Connected UDP restricts responses to the resolved peer address/port. Each request
has a fresh 64-bit random originate challenge. Reject wrong originate, non-48-byte
packets/extensions, unsupported version/mode, leap warning, stratum outside 1–15
(including Kiss-o'-Death), implausible precision, negative root delay, excessive
root uncertainty, zero timestamps and backwards server processing chronology.

**Public NTP is unauthenticated.** This private research policy assumes configured
providers/OS DNS are trustworthy, independent, and not subject to a common-path
active attacker. Two agreeing unauthenticated sources cannot prove that assumption.
An on-path attacker capable of forging both sources is outside this policy's
assurance; no cryptographic time attestation or production security is claimed.
Deployments requiring that threat protection need independently authenticated time
evidence before activation. The dashboard exposes the assumption alongside the
actual interval. No HTTPS Date-based override is used.

References: [NTPv4 protocol and security](https://www.rfc-editor.org/rfc/rfc5905.html),
[Google leap-smear semantics](https://developers.google.com/time/smear),
[Python elapsed-time clock API](https://docs.python.org/3.12/library/time.html#time.perf_counter).
Leap warnings, source disagreement or nonoverlapping intervals fail closed;
Google's smear is not silently treated as identical to another provider at a leap.

## Receipt bounds and rejection rules

Let t2/t3 be NTP server receive/transmit UTC, t4 local precise receive UTC and d
the local high-resolution elapsed request time. With nonnegative network delays,
UTC at reception lies between t3 and t2+d. Expand both sides by server root error
(nonnegative root delay/2 + root dispersion + stated precision), a 1 ms capture
guard and a conservative 1000 ppm drift envelope. Do not assume symmetric paths.

Limits are conservative engineering assumptions, not a financial forecast:

| Check | Limit |
| --- | --- |
| Per-sample elapsed time | >0 and <=100 ms |
| Server root error | <=50 ms |
| Sample age when combined | <=10 s |
| Absolute offset interval | within +/-2 s |
| Source median disagreement | <=20 ms |
| Within-source intervals | must overlap |
| Best-latency interval from each source | must overlap |
| Combined bound | conservative union of those two intervals, <=100 ms |
| Evidence age at actual provider receipt | <=30 s |
| Projected receipt interval width | <=100 ms |
| Local precise-clock discontinuity | reject beyond 5 ms + drift envelope |
| Receipt capture span | <=1 ms |
| Quote worst-case age at receipt | <=30 s |

Anchor the accepted offset interval to precise local UTC and high-resolution
`perf_counter`; project through elapsed time with drift uncertainty. On this
Python 3.12 Windows host the initial use of coarse local clocks falsely triggered
discontinuity checks. The corrected implementation reads native
`GetSystemTimePreciseAsFileTime`, while **preserving the original** `datetime.now`
provider receipt separately. It never overwrites provider generation/last-trade
timestamps or the raw local receipt. Original source timestamp strings are retained
in accepted quote envelopes; time-only diagnostics retain no prices.

Acceptance requires **last_trade <= quote_generation <= receipt_lower_bound**.
Generation inside the interval is ambiguous and rejected by **strict VERIFIED
acceptance** even when below the upper bound. Missing/stale/contradictory calibration has no strict-local or HTTP
fallback on these calibrated endpoints. A failed measurement avoids the quote
GET entirely. Malformed/future/stale quotes expose no LTP. Previous-close change
still uses only `prev_close_price` with Decimal arithmetic.

Calibration and quote proofs remain memory-only. Cache reads cannot extend their
lease: server display strips expired LTP/change fields; chart processing consumes
the same lease. The frontend expires the headline one second before the remaining
lease, preserving the dated provider EOD chart and manual refresh. No automatic
refresh was added. Candle/archive separation and original ten-minute maximum
transient chart retention remain; an expired quote does not become a current price.

## Genuine result and smallest remaining requirement

One fresh six-key API batch at 16:19:31 IST accepted **0/6**. All six generation
timestamps were `2026-10-15T16:19:31.153+05:30`; raw local receipt was
`2026-10-15T10:49:31.002348+00:00`. Corrected receipt interval:
`10:49:31.146659` through `10:49:31.200154` UTC. The common generation timestamp
was **6.341 ms after the lower bound**, so the policy correctly rejected ambiguity.
No accepted genuine previous-close change is claimed. The observed cohort is six,
not complete NSE breadth; no current ML result follows.

This 6.341 ms is **uncertainty overlap**, not an instruction to move Windows by
6.341 ms. Correcting Windows does not itself remove NTP/network uncertainty from
this interval policy. Strict VERIFIED acceptance needs tighter independently supported time bounds
or a future response whose generation clearly precedes the lower bound; do not
add delay, average away uncertainty, widen limits or switch to the upper bound.
For the captured response, the original raw-local-only check was short by
150.652 ms. That is a historical diagnostic, not a manual clock-setting target
or guaranteed correction for a future response. The existing
[administrator-reviewed Windows recovery/rollback](p34-clock-recovery.md) remains
the alternative for restoring independently verified local time. No OS change here.

## Separate private indicative display

The user's subsequent authorization permits a separate sibling field
`indicative_quote`, state `INDICATIVE_PROVIDER_QUOTE_TIME_UNCERTAIN`, for
**lower_bound < generation <= upper_bound**, valid last-trade chronology and all
original clock/source/identity/price checks. The strict `quote` field, validator,
acceptance counter and rejection remain unchanged. Generation above the upper
bound, stale/malformed/mismatched responses or missing/contradictory time evidence
provide no indicative price.

Only authenticated private educational viewing is permitted. The dashboard says
“Provider quote — timing not independently verified”, exposes original clocks,
last-trade freshness and uncertainty, and never calls it VERIFIED or a final close.
Financial consumer cache copies omit this sibling entirely: no ML, ranking,
signal, alert, portfolio economic valuation, ingestion or execution may consume it.
The same remaining proof lease applies, with passive backend/frontend removal
and the dated EOD chart retained. No automatic refresh or quote retention was added.
Unauthenticated NTP limitations above still apply; this is not independently
attested time. See the [separate verification report](../development/p34-indicative-display-report.md).
