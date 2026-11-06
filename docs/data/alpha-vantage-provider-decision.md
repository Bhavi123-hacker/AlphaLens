# Alpha Vantage operator credential and NSE decision

Verified 2026-10-12, existing P26 development preserved. SOURCE_NOT_CLEARED for P19 NSE ingestion.

The authorized plaintext input was imported into Windows Credential Manager, generic
credential target AlphaLens/AlphaVantage, scoped to the current Windows logon user.
Persistence survives operator logoff; it does not grant other Windows users access.
The operating system protects credential storage. Secret readback compared equal;
the key was never printed, placed in Git, frontend code, environment variables,
command arguments, logs, screenshots or reports. Same-user processes retain the
operator's privileges; this does not claim isolation from a compromised operator.
Existing differing credentials are refused rather than overwritten.

One authenticated SYMBOL_SEARCH request for RELIANCE succeeded, HTTP 200, received
2026-10-12T05:13:06.585056+00:00. Payload SHA256:
a56039205898a16dbbd60ac84940473cca0cad3732692483acfd9c1e22857460.
The exact RELIANCE result is RELIANCE.BSE, region India/Bombay, Equity, INR.
Other Indian search results also carry .BSE. No returned match establishes NSE.
Company identity alone is insufficient: BSE prices must never become NSE prices.

No price request, NSE observation, accessible NSE session, canonical ingestion,
feature update, inference, ranking or scheduler activation occurred. We did not
spend more quota on speculative aliases or download BSE prices. Search success
confirms the supplied credential works for this endpoint, not every API entitlement.
NSE coverage is NOT_ESTABLISHED, rather than a universal claim that every possible
Alpha Vantage NSE product is unsupported. A P19 price adapter is not activated or
prepared as supported without the required exchange evidence.

Primary evidence:
* https://www.alphavantage.co/documentation/ documents the India example as BSE,
  RELIANCE.BSE. Search provides symbols/regions, not authoritative NSE ISIN lineage.
* https://www.alphavantage.co/support/ states 25 requests/day on the normal free tier.
  No special educational/open-source entitlement was requested or assumed.
* https://www.alphavantage.co/terms_of_service/ sections 2-5 describe personal,
  private noncommercial research and retained intellectual-property interests.
  No explicit NSE exchange-data retention/ML-training grant was verified. This is
  a conditional personal-use basis, not complete P19 source or production clearance.

Additional blockers: stable NSE identity, source revisions, session completeness,
publication clocks, corporate-action semantics, local retention and derived-model
rights evidence. The 25-request allowance also cannot establish daily full-cohort
coverage of 2,589 observed research equities. No paid tier, brokerage access or KYC.
The existing frozen archive still ends 2026-10-06; current predictions remain blocked.

The explicit operator CLI counts attempts (including failures) transactionally,
limits this application to 25 over a rolling 24 hours, performs one fixed-host
search per invocation, has no redirects or automatic retries, and redacts upstream
error text. It cannot know calls made outside AlphaLens; its ledger is not proof
of remaining provider-side quota. The sanitized receipt and local request ledger
are outside Git in the Windows operator's protected LocalAppData/AlphaLens/provider-state.

Verified Windows commands (no secret command argument):

```cmd
cd /d C:\Users\Dell\AlphaLens
.venv\Scripts\python.exe -m alphalens_api.credentials import-alpha-vantage --file C:\Users\Dell\OneDrive\Desktop\apii.txt
.venv\Scripts\python.exe -m alphalens_api.credentials probe-alpha-vantage
```

Do not repeatedly run the probe to refresh the dashboard. It is an explicit
operator diagnostic, never frontend-triggered or scheduled collection.

**The original plaintext file can be removed by the operator:** protected storage
and readback were verified, and the key was successfully used from that store.
The file was intentionally not deleted. Future access does not depend on it.
