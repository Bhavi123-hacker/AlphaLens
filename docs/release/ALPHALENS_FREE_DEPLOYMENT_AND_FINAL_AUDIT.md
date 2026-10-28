# AlphaLens free deployment and final audit — 28 October 2026

The private saved-data application works at <http://127.0.0.1:8041/nse-market>.
The selected public deployment is the independent, explicitly synthetic preview at
<https://bhavi123-hacker.github.io/AlphaLens/>. The complete private application
has **not** been deployed to free cloud infrastructure. It requires persistent
protected state that the evaluated free web service does not supply.

## Source and execution boundaries

Preparation starts from `a1297873ed3541b06b634e18ddc41adc1822fd6a` on
`alphalens-master-completion`, in the isolated development worktree. The active
Windows source remains `6a5b73af588624cadc1e464d8ca90b5944421893` plus the exact
previously approved two-file Intraday V3 correction. This campaign does not advance
the collector checkout, change tasks, restart the private application, run a
collector manually, query a market provider or NTP server, or alter frozen models.

The public build emits `release.json` with its exact source commit and
`SYNTHETIC_ONLY`, `backend:false`, `provider_requests:false`. Publication is limited
to a new separate static output directory. `.local-data`, private app bundles,
credentials, databases and trained models are not deployment inputs.

## Feature acceptance

These statuses describe actual private browser/API observations unless stated
otherwise. A loaded page is not evidence of enabled financial writes.

| Feature | Status | Evidence and limit |
|---|---|---|
| Login, logout, protected navigation | WORKING | Actual browser session; protected API401 after logout and unauthenticated access. |
| Sessions, CSRF, origin checks | WORKING | HttpOnly/Strict cookies; missing CSRF and hostile Origin403; session remains intact after rejected operations. Loopback HTTP cookie is intentionally not Secure; hosted HTTPS tests require Secure. |
| Dashboard/navigation | WORKING | 22 deployed routes, no JavaScript errors or unexpected provider calls. |
| Stock search | WORKING | 3,194 current master equities; matched and unmatched queries200. Current master is not historical membership or a complete listing-status audit. |
| Stock details and unavailable states | WORKING | Saved-data stocks, master-only AAKAAR, insufficient-history HINDADH and unsupported identity states exercised. No fabricated fallback. |
| Prices, candles, volume | PARTIALLY WORKING | 500 saved price histories; 449,477 retained candles. Latest retained session23October has499 observations. Other2,694 searchable equities lack saved prices. |
| Indicators and risk | PARTIALLY WORKING | Saved-history charts/statistics work; insufficient data remains unavailable. No risk estimate is manufactured for master-only identities. |
| Experimental Top5/10/20 | WORKING | Fresh authenticated requests return deterministic nested5/10/20 prefixes over all312 eligible saved scores, before pagination. Observation date remains23October. |
| Trained model inference | WORKING | Same-day pinned-model execution reproduced312 feature vectors and saved numerical scores with maximum error0. Source/model/view hashes rechecked unchanged. This is replay, not new forecasts. |
| Daily fresh predictions | BLOCKED | No newer validated observations; saved inference25October20:39:11IST must not be represented as today's signal. |
| Forecast history/version/lineage | WORKING | 945 immutable forecast bodies,914 decisions,31 overlapping records; source, feature and target lineage retained. |
| Probabilities/independent acceptance | BLOCKED | Scores are experimental, not calibrated gain probabilities;0 independently accepted models among63 reviewed versions. |
| Forward outcomes/accuracy | BLOCKED |0 qualified outcomes.602 decisions are calendar-mature but lack qualified subsequent prices;312 lack all required official future session dates. Six known action-related target exclusions overlap these categories. No accuracy denominator exists. |
| Historical models/backtests | PARTIALLY WORKING |152 saved models; persisted backtest directory loads. Original504 runs and474 unresolved economic outcomes remain separate from forward evidence. |
| Portfolio, named watchlists, journal, rules | PARTIALLY WORKING | Pages and empty-state APIs work; current operator has0 portfolios/watchlists/journal/rules and `mutations_enabled=false`. No end-to-end user write or valuation claim. |
| Original decision desk | BLOCKED |503 `PRIVATE_PROVIDER_VIEW_DISABLED`; separate from saved NSE experimental research. |
| Original accepted-model path | BLOCKED | Its source/calendar/38-feature/PIT/action/risk/acceptance gates remain unmet; this does not negate the separate312-score experimental pipeline. |
| Alerts and operational diagnostics | WORKING |47 original alerts readable; genuine collection receipts and stale/partial states displayed. No acknowledgement/deletion attempted. |
| Personal paper account | PARTIALLY WORKING | View loads with0 accounts. No broker order functionality. |
| Mobile/tablet/desktop | WORKING |15 private route-width checks at390/768/1600, no document overflow; zero Axe violations on five tested pages. Scoped evidence, not full accessibility certification. |
| Settings/opportunities wording | FIXED | Candidate removes obsolete global inference/scheduling-disabled assertions, links dated experimental predictions and actual collection evidence. Active compiled UI remains preserved. |
| Synthetic public controls | FIXED | Search/filter recovery, whitespace search, dynamic counts, selected state, source links and light contrast corrected; capability limits explicit. |
| Complete private cloud service | BLOCKED | Persistent state/import/restart acceptance and permitted synchronization are unqualified. No empty replacement database is presented as success. |

## Daily delivery and model correctness

Read-only audit at13:49IST found both existing tasks enabled/Ready, zero matching
workers and unchanged XML hashes. NSE uses the patched runtime, original500-stock
cohort,250-stock batches,600 GET reservations/run,1,800/day,60-minute cooldown and
existing20:30/21:30/22:30IST triggers. Approved battery settings are preserved.
Shared provider attempt count remains5,021; no campaign provider requests occurred.
There were no28October NSE receipts at that audit time. Daily success rate is
unknown;499/500 retained-session coverage is not today's update success rate.

The27October21:30 terminal failure is
`DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE`: initial evidence passed but fresh
post-cooldown evidence was unavailable. This does not prove a clock jump. The
22:30 run retained one successful instrument-master GET, then ancestor interruption,
with no terminal DONE or validated candle. DC-power transitions correlate with
interruption; the exact terminating actor was not recorded. The approved battery
policy change has not yet demonstrated successful fresh delivery.

Historical V3 remains the completed-date route; current-date Intraday V3 routing
has offline successful/empty-response coverage. No genuine successful candle
under the newly active routing is claimed. SHERVANI (`INE011D01013`) remains the
23October configured gap, last observed19October. Genuine provider-empty evidence
does not authorize an invented candle. Current official28October calendar facts
were not retained in the audited status; do not infer a session merely from weekday.

The separate unchanged watchlist exited1 at08:30 with
`DAILY_DATE_CHANGED_OR_CLOCK_ROLLBACK`. A comparison of trusted time with mutable
provider wall receipt time is a hypothesis; the second trusted interval was not
retained, so the exact rejection cause is unresolved. No clock comparison was
removed, tolerance widened, task replaced or provider probe initiated.

The full universe would require13 batches and7,800 reserved GETs under the current
scheme, exceeding1,800/day. At least five quota days are needed arithmetically
before retries/holidays; that is not daily coverage or expansion authorization.
Actual elapsed time/storage growth for expanded collection is unmeasured. Keep
incremental instrument-key/date caching, idempotent persistence, missing-only
planning and original cooldown/reservation enforcement; activation needs a separate
measured cohort/cadence/quota/storage approval.

The retained complete decision audit and frozen acceptance review remain binding.
No final holdout was rerun, model retrained, forecast body overwritten or score
redated. Forecast maturation requires genuine qualified target observations,
identity/action evidence and official sessions; zero qualified results means
`NOT_YET_MEASURABLE`, not zero-percent accuracy.

## Free hosting comparison

Official limits were checked28October2026. No paid service, disk, cron job, database,
custom domain or second collector was provisioned.

| Target | Monthly cost | Compute/backend | Storage, auth and automation | Decision |
|---|---|---|---|---|
| Render Free web |₹0 base; complete app BLOCKED | Python/Docker supported;0.1CPU/512MB; sleeps after15idle minutes with cold start | Files disappear on restart/redeploy; no free disk. Free Postgres expires30days. Existing auth is compatible but persistent imported state is missing; no free collector worker/cron. | Cannot pass requested durable private-app acceptance. |
| Vercel Hobby |₹0 within personal plan | Vite frontend works; functions are a different finite-lifetime runtime, not verified collector hosting | No provisioned durable private store or qualified auth/API integration. Existing reviewed config is synthetic-only. | Viable static alternative; not selected and no resource created. |
| Render Static Site |₹0 base within included usage | Vite static build/CDN; no Python backend or model process | Durable published assets, HTTPS; no account DB/ML/collector. Workspace overage/spend controls must be established before hard₹0 provisioning. | Compatible synthetic alternative; workspace selection pending. |
| Existing GitHub Pages |**₹0** | Static CDN, no server compute/DB | Published synthetic assets survive process restarts; no passwords, real-data sync or collector. Existing public repository and custom Actions deployment. | Selected deployable preview; private app stays local. |

Render's documented restart/storage and quota constraints are decisive, not a
disabled application health check. [Render Free](https://render.com/docs/free)
also documents possible bandwidth/build overage billing when a payment method
exists. We do not assert a verified Render account spending cap.
[Compute plans](https://render.com/docs/compute-plans) give the actual free sizing;
[static-site documentation](https://render.com/docs/static-sites) describes the
separate CDN product. [Vercel Hobby](https://vercel.com/docs/plans/hobby) lists free
personal usage; [function limits](https://vercel.com/docs/functions/limitations)
do not establish persistent collector compatibility. [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
permit public-repository static hosting and prohibit sensitive transactions and
commercial SaaS use. This noncommercial synthetic project preview accepts neither.

Render tools became available during this campaign and exposed one workspace.
The connector explicitly requires operator workspace confirmation; none was
assumed. Vercel service access is not connected. These facts do not block updating
the existing authorized synthetic Pages site.

## Security, verification and preservation

Latest completed backend baseline, exact commit`a129787`: Linux/PostgreSQL17
**1,970 passed/30 skipped**, frontend134 passed, strict foundation and hosted images
each0HIGH/0CRITICAL. Hosted/config/auth64 focused Windows cases passed with warnings
as errors; backup13 and deployment37 are separate overlapping suites, not totals
to add. No full new Windows-suite count is claimed.

Full reachable history at that baseline:173 commits,0verified secrets,3 exact
reviewed fixtures,0unexpected findings. Raw scanner exit183 is retained;
`raw_scan_clean=false`. Exact fixture handling is not scanner suppression.
Patched collector runtime has0 advisories; separate original watchlist runtime
still has43 known advisories and is **not security-cleared**. Its replacement needs
separate reviewed authorization; no silent fallback or task change was made.

Fresh private browser evidence:22 routes, authentication/CSRF/session tests,
15responsive checks, five pages with Axe0; saved-market integration separately
tests search/charts/Top-N/history/unavailable states. All312 real saved predictions
replayed exactly; complete914-decision audit retained. Public six-case browser
suite additionally tests synthetic provenance, controls, dark/light contrast,
keyboard/mobile layouts and zero API/third-party requests. Final-commit CI and
actual public deployment receipts are appended after execution below.

Preserved:2,485 frozen research files (8,505,278,241bytes),47 original alerts,
945 forecast bodies, frozen models, genuine candles, operator state, PostgreSQL,
task XML, quota reservations and both runtimes. The same-day verified portable
research backup contains20,056 files; it remains private and was not uploaded.
There is no cloud synchronization, public real NSE data or exposed local database.
Private retention evidence does not establish public redistribution rights.

Private evidence: `.local-data/free-deployment-20261028/{daily,private-features,demo}`,
with unchanged-module replay/security evidence under
`.local-data/app-completion-20261028-1205/`. Test fixtures are never marketed as
genuine market observations.

## Deployment execution, remaining work and rollback

The preview was genuinely published from
`8478657038010c8c6f1410e42f10b1e00e9485f2` at19:19IST. Its public `release.json`
returned that exact commit, not the old preview. Six actual public-browser cases
passed in17.6seconds: charts, filters, empty-state recovery, source/limits,
desktop/tablet/mobile, light/dark accessibility, preferences/FIFO/journal examples
and no private API or third-party requests. The artifact contains2,197,710bytes of
static files; archive SHA256 is
`3d184076f32319dd4c310eac97583def5e2ee2a75d301a621bd250c3be69fe9c`.
Its independent provenance/extension/link/content checks found no private stores
or provider/API markers. The demo has no account database or server-side writes;
its synthetic form state is not durable private portfolio storage.

| Executed check | Result / exact evidence |
|---|---|
| Linux/PostgreSQL17 backend, release source8478657 |1,970 passed/30 skipped,271.50seconds; [foundation40699708140](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40699708140). Ruff/format/mypy/Bandit/frozen dependency audit also passed. |
| Frontend, release source8478657 |136 passed; TypeScript, lint, generated client/licenses, production builds and npm audit0 vulnerabilities; [dashboard40699710244](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40699710244). |
| Windows frontend |136 passed on unchanged-assertion rerun; initial cold Settings route wait timed out. No timeout/assertion/test was removed or relaxed. Lint/typecheck/build passed under pinned Node22.23.3. |
| Preview CI build/deployment |6 browser cases passed before artifact upload; [Pages40699708208](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40699708208) succeeded. No backend, disk, database or paid resource created. |
| Actual HTTPS public browser |6passed,0skipped,0flaky,17.6seconds; `demo/browser-report-public-specific.json`. Public source marker separately checked. |
| Foundation image, release source8478657 |0HIGH/0CRITICAL; image`sha256:4f5c753c870857edea6ea0f470b9ea4a1423cc349453ed3aaf5659af4113d03d`. |
| Hosted full-stack image, implementation68ecc2f |0HIGH/0CRITICAL; image`sha256:07f9a7972ed57adad5a7cf2148f458df038f36824e60952d5456e8297d912ee9`; [hosted40699546129](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/40699546129). This image was tested, not hosted publicly. |
| Full history, release source8478657 |175 reachable commits,0verified secrets,3exact reviewed fixtures,0unexpected; raw exit183 and raw-cleanfalse retained. |
| Fresh private preservation check19:19IST |945 original bodies/914decisions/0outcomes unchanged; all326active source files and both task hashes match;5021provider attempts,0today NSE receipts,0workers. Health endpoint200 at19:23. |

The three raw secret findings remain explicit test/documentation fixtures in
`docs/development/command-log.md` (source453/scanner218),
`tests/unit/test_configuration.py:31`, and
`tests/integration/test_p17_api.py:248`, at their registered original commits.
[Exact source review](../security/reviewed-secret-fixtures-v1.json) binds their
content hashes. No real credential was found and no rotation is claimed necessary
for these fixtures; any new/unmatched/verified finding fails the unchanged gate.

The first publication attempt at68ecc2f failed workflow validation before upload:
`runner.temp` is unavailable in job-level environment expressions. Moving path
selection into a running step fixed it; no failed artifact was published. Actual
internet browser testing also exposed an ambiguous test locator while several
charts were loading. The result-count assertion now selects the result-count
status specifically, retaining all checks rather than ignoring loading states.
Vite's existing >500kB chunk warning remains visible; no bundle warning threshold
was raised. Generated demo output is excluded from source lint/Git alongside the
existing generated production output, without excluding source or security tests.

The final delivery commit contains this report and the precise locator correction;
publication reruns for that commit. Its exact SHA, final-commit CI/container
receipts and verified public marker are retained in
`.local-data/free-deployment-20261028/FINAL_EXECUTION_ATTESTATION.json` after those
checks finish. The final response supplies the delivery SHA. The checks above are
explicit completed source-bound runs, not predictions about pending CI.

The workflow now accepts only the dedicated completion branch on relevant demo
paths, runs type/lint/dependency/browser checks and uploads only a fresh synthetic
directory. The Pages environment gained permission for that branch; no existing
branch policy, default branch or unrelated service was changed.

Rollback only the synthetic publication by dispatching `public-demo.yml` at the
previous reviewed source ref, or reverting this campaign's static changes in the
dedicated branch and passing the same checks. Preserve failed logs/artifacts.
Never reset the active Windows worktree, task action, database, forecast ledger,
reservations or models as a static-site rollback.

Remaining blockers: genuine new provider candle delivery; fresh qualified
features/predictions; forward target/calendar/action evidence; independent model
acceptance; original watchlist runtime/clock diagnostics; persistent private
hosting/import/restart acceptance; separately permitted synchronization and
documented rights plus approval for public real-data display. No approval is
requested to incur costs or weaken these gates. Existing Windows scheduled
collection remains the only authorized automatic market-data writer.
