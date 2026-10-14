# P30 Windows application and database

Run from `D:\al-research\p28-worktree`:

```powershell
.\scripts\windows\start-p30-alphalens.cmd
# Open http://127.0.0.1:8017/login and use your existing operator account.
.\scripts\windows\project-python.cmd -m alphalens_api.local.cli --config .local-data\p30-runtime\operator-config.json check
.\scripts\windows\stop-p30-alphalens.cmd
```

Start is a foreground command: keep that terminal open. Stop from another terminal.
The owned PostgreSQL cluster starts first on loopback port15430, followed by the
private application on8017. Stop requests cooperative application shutdown, then
smart shutdown of that exact owned cluster. Helpers verify binary hashes, cluster
directory, server major version and current-user storage permissions. An unrelated
listener on15430 is rejected. Existing C-drive PostgreSQL directories/services are
not modified. A combined stop/restart was actually verified.

The additive private config is `.local-data/p30-runtime/operator-config.json`.
The P29 config and original account remain unchanged. The existing operator's
actual login and logout were verified through a local dialog without password
reset, conversation input or saved credentials. PostgreSQL credentials and the
separate Upstox credential use current-user Windows Credential Manager.

## Private data and database

PostgreSQL17.11 portable binaries came from the official EDB Windows archive.
Selected bin/lib/share members were downloaded with verified range responses,
ZIP CRCs and a local SHA manifest. No independent full-archive vendor checksum or
code-signing clearance is claimed. The cluster uses SCRAM and loopback-only access.

The guarded P29 bootstrap created only dedicated AlphaLens roles/database.
The application role has SELECT-only financial access; an actual write attempt was
rejected. P15/P16 schemas/migrations and four immutability triggers were verified.
Actual financial account/transaction/paper-account/event counts are all zero; no
holdings, balances, fills or transactions were fabricated. A custom-format backup
was restored to an isolated newly named database and verified without modifying
the source database. Actual isolated PostgreSQL integration tests also passed.

The private RELIANCE view requires pressing its load button. Backend requests and
the ten-minute memory cache provide genuine provider observations; range changes
do not repeat ingestion. Latest availability, UNKNOWN basis and evidence exclusions
are displayed separately from the frozen archive. The market map/screener retain
historical scope; the private provider watchlist is explicitly one instrument.

## Daily workflow

```powershell
.\scripts\windows\p30-daily-readiness.cmd .local-data\p30-runtime\daily-config.json
.\scripts\windows\p30-daily-update.cmd .local-data\p30-runtime\daily-config.json
```

Both commands are safe with the present configuration: readiness reports precise
blockers, and update returns BLOCKED_SOURCE before network calls or price storage.
Do not flip rights flags to bypass evidence. The prepared task XML is disabled and
not registered. Its configurable19:30 time is a development setting, not a verified
provider-publication SLA. Current source/calendar facts cover only explicit dates;
unknown weekdays do not become trading sessions.

See [daily/model audit](p30-daily-and-model-readiness.md) for exact activation
requirements. No trading endpoints, paid fallbacks or outbound alerts are enabled.

## Public demo and credential cleanup

[Published synthetic demo](https://bhavi123-hacker.github.io/AlphaLens/).
GitHub Pages serves only the independent synthetic static bundle. It has no
private backend, database, operator authentication, provider cache or real prices.
The deployment branch permission is explicitly scoped to the P30 branch; the
repository default branch is preserved.

Secure token import/readback and genuine API validation succeeded. The original
`C:\Users\Dell\OneDrive\Desktop\apii.txt` was not changed or deleted. The operator
can now manually delete that plaintext file and any unnecessary OneDrive copies.
Do not paste credentials into Git, commands, screenshots or conversation.
