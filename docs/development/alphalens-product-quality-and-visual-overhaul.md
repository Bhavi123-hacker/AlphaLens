# Product quality and visual overhaul acceptance

Evidence dates: 18–19 October 2026. Baseline:
`5d86dd84d3ab25c46212d9bd3a2aeddd5879ad6c` on
`alphalens-investment-evidence-completion`. Both requested tasks are delivered
together on `alphalens-visual-overhaul`; main and the baseline branch were not
modified. Product commit: `b0e62eb`; visual software commit:
`b17bccba03af0d429e4471de333272c7c6b1dc8a`. Final responsive-card correction:
`9666097d01c329bc1947fcbfedd8b8ec9a1b728b`.

## Delivered behavior

| Deliverable | Result | Actual implementation/evidence |
|---|---|---|
| Investor research journey | PASS | Search first, four anchored steps, progressive coverage disclosure, readable preference reasons and wider candidate evidence drawer. Saved evidence only until an explicit provider control is used. |
| Candidate investigation | PASS | Exact identity, dated V2/LSTM scores, technical/risk/missing evidence, directly accessible sizing and existing portfolio context. Existing watchlists accept the security identity with revision/conflict checks. |
| Model comparison | PASS | Matched sequence study models and baselines show samples, dates, metrics, paired uncertainty, gross/net reference returns, drawdown and membership turnover. Original V2 remains a separate evaluation. |
| Automation presentation | PASS | Protected checksummed task observation records actual state/result/next trigger and observation time. Saved collection results, quota reservations and forecasts remain separate from Windows task status. No page invokes Scheduler or the provider for this status. |
| Professional case study | PASS | [Architecture, methodology, real results, limitations and demonstration](../case-studies/alphalens-investment-intelligence.md). |
| Visual identity | PASS | Obsidian/graphite, electric lime, burnt orange and ivory; authoritative dark/light tokens, grouped navigation, editorial dashboard hero, coverage instrument, portfolio overview and consistent cards/forms/tables. Existing primitive overrides were removed from terminal CSS. |
| Charts and interactions | PASS | Canvas options resolve theme tokens, preserving values/nulls/formatters; cohesive series, tooltip and crosshair colors; focus states, lightweight hover/loading states and reduced-motion support. No dependency added. |
| Responsive/accessibility | PASS within tested scope | No horizontal document overflow at 390/1024/1920px in both themes; dashboard, NSE Market and Portfolio automated WCAG A/AA checks have zero violations in both themes; mobile navigation Escape restores focus. Canvas/other automated incomplete checks still require manual assessment; this is not full accessibility certification. |
| Compiled preview | PASS | Authenticated `http://127.0.0.1:8029/nse-market`, isolated existing QA account/personal store. |
| Production-like visual promotion | PASS | Promoted the tested build to `http://127.0.0.1:8017` during the verified 19 October 11:23 IST quiet window: zero collecting workers, both tasks Ready, next expanded trigger hours later. Original account/records retained, app-only restart; PostgreSQL PID 19512 unchanged. Prior build/config remain recoverable. |

The visual commit modifies frontend source/tests only. Small backend changes are
confined to the preceding product task: projecting existing saved comparison
fields and validating/reading protected task observations. No financial formula,
Upstox behavior, model/protocol, authentication contract, forecast writer, quota
reservation or scheduled-task definition was changed.
Deployment changed only the original operator configuration's `frontend_root`;
the private backup retains its prior bytes. No auth/store/source fields changed.

## Research and source honesty

The preserved snapshot contains 3,198 current common-equity identities, 500
historical securities, 447,483 qualified candles, 300 expanded V2 scores and 43
compatible LSTM scores. These are different coverage measures, not full-market
prediction coverage. No market-data acquisition or model training occurred here.

Sequence balanced accuracy: LSTM 51.1185%, random forest 52.0173%, histogram
boosting 52.1404%, XGBoost 52.1928%, mean reversion 50.6571%. Relevant paired
whole-date uncertainty intervals include zero. Original V2 is separately
50.1085% versus mean reversion 51.1131%; different eligible samples prevent a
pooled improvement claim. These inspected historical periods are development
evidence, not new independent unseen outcomes.

At 50 bps round-trip costs plus 5 bps slippage each side, saved Top 5 net reference
returns remain LSTM −44.9781%, XGBoost −31.7746% and mean reversion −25.6199%.
The page visibly retains these losses. Membership turnover is distinguished from
the policy's five-session liquidation/re-entry; endpoint drawdown is incomplete
intraperiod risk evidence. Classifier scores remain uncalibrated, with no invented
rupee target or profit probability. **NO_DEMONSTRATED_EDGE** remains unchanged.

All 31 original plus 300 expanded V2 forecast bodies match their protected backup.
Zero matured outcomes and zero accepted models/rankings remain. The independently
checked current time on 19 October was 11:13 IST: that session was in progress,
not a completed published EOD session. No five-session outcome can be inferred.
No new quote check was performed: the earlier 3 strict / 3 indicative observations
are historical evidence, not a new six-quote result for this frontend execution.

## Verification

| Check | Genuine result and evidence |
|---|---|
| Focused backend | 56 passed in the existing targeted product modules; separate new task-observation/sequence API run 16 passed. These overlap and are not summed as distinct tests. |
| Full backend CI on product commit | 1,462 passed, eight skipped; PostgreSQL, Ruff/format, mypy (384 source files), Bandit and dependency audit passed. See CI caveat below. |
| Final local frontend | 113 passed, 22 files; TypeScript, ESLint, production build and npm audit passed (zero reported vulnerabilities). ECharts' existing large-chunk advisory remains. |
| Compiled authenticated browser | Eight passed, one worker, 1.1 minutes: discovery and exact Top 5/10/20 backend matching; preferences edit/restore; FIFO and indicative exit separation; horizons/economics/sizing; stock-specific model/observed evidence; identity-only watchlist save; dark/light/mobile checks. No provider acquisition. |
| Final layout correction | Screenshot review found the existing `stat-grid` class lacked the `stats-grid` layout. Both now share the same responsive primitive; final two-case visual/browser run passed with a four-column computed-layout assertion. Four additional dark/light NSE/Portfolio accessibility scans passed, zero acquisition requests. A literal hue audit found zero blue/cyan colors among 67 runtime color literals. |
| Actual failures and corrections | Initial visual browser run: six passed/two failed. A candidate drawer hid direct sizing, and light-theme `kbd` opacity reduced contrast to 4.07:1. Restored direct sizing without duplicate actions and removed dimmed shortcut text. Final eight-case run passed; no timeout or accessibility threshold was weakened. |
| Frozen preservation | 2,485 original frozen files and 47 original alerts checksum verified; original model/research checks passed. |
| Current inference preservation | All 300 saved V2 vectors recomputed/reloaded with maximum score/vector difference zero; 23 sequence artifact files byte-identical; 331 frozen bodies unchanged; zero new forecasts/outcomes. |
| Personal/credential preservation | 240 immutable files, original account/password and personal-record bodies unchanged; four protected credential fingerprints match. New compiled build: 233 files scanned for actual credential values/encodings, none found. No Credential Manager writes. |
| Runtime/backup | Original compiled 8017 index and authentication boundaries passed; online backup of auth/alerts/operations/prospective/personal stores restored in isolation with identical records, revoked restored sessions and no original-state modification. Actual PostgreSQL SELECT-only/no-write checks passed. |
| Provider budget | Saved shared ledger remained 1,498 successful attempts; interrupted 600-request reservation preserved. This work consumed zero provider GETs and created no collecting attempt. |

Private evidence is under `.local-data/`: `visual-frontend-final.log`,
`visual-browser-final.log`, `product-visual-browser/final-acceptance/report.json`,
`visual-frozen-preservation.json`, `visual-personal-preservation.json`,
`visual-research-preservation.log`, `operational-native-verification.json`,
`visual-security.json` and `visual-compiled-secret-isolation.json`.
Post-deployment checks: `visual-native-deployed.json`,
`visual-personal-deployed.json`, `visual-final-ledger-preservation.json`,
`visual-deployment-preflight.json`; actual build identity is
`37ef1d1f328f26b9e50813d9073971818bf609e64dd953fc3b9852d10703ac1b`.
Fresh 19 October checks again confirmed 1,498 shared attempts, 331 unchanged
forecast bodies, zero matured outcomes and 23 unchanged sequence artifact files.

## Task observations and real pending work

Read-only task inspection on 19 October confirmed both tasks **Ready/enabled**,
Interactive/Limited, with their existing action paths and approved triggers.
The expanded task retains last result 267014 (interrupted, not successful
collection), with next actual run **19 October 20:30 IST**, followed by 21:30 and
22:30. Approved scope remains fixed 500; 250 securities/run; 600 reserved GETs/run;
1,800/day; three attempts/day; 60-minute cooldown; 31-day catch-up.

The RELIANCE task's latest read-only observation changed naturally between dates:
on 18 October its last result was zero; on 19 October its last run was 11:12:39 IST,
result **3221225786 / 0xC000013A**, with next trigger 20 October 08:30 IST. Its saved
completed receipt still dated 18 October. This is an interrupted/terminated task
result requiring operational inspection, not a successful 19 October capture.
This frontend execution neither altered nor restarted it, and makes no causal
claim about that termination. Do not reset reservations or trigger unnecessary
source requests to make a visual demonstration pass.

The first fresh expanded capture remains **PENDING** genuine session completion,
provider publication and per-security immutable receipts. Preserve forecast entry,
five-session maturity and independent acceptance gates. No new session, profit,
strict quote acceptance or accepted ranking is claimed by this delivery.

## CI and security

Product commit: [frontend success](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39145214426),
[foundation result](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39145214474).
Foundation's tests, static/dependency gates and strict container job passed;
downloaded Trivy artifact reports **zero HIGH and zero CRITICAL**. The workflow
overall **FAILED** at full-history TruffleHog: zero verified, three unverified
historical findings. These are the previously disclosed reviewed fixture findings
in [the history audit](../security/final-secret-history-audit.md), not resolved or
suppressed by this change. No scanner, severity policy or history was modified.

Visual commit CI: [frontend](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39206005122),
[foundation/container](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39206004988).
Frontend and strict container passed; foundation overall failed at the same three
historical unverified findings (zero verified). Its backend result was 1,462 passed,
eight skipped in 333.93s. The following meaningful documentation commit's
[foundation run passed](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39206190497),
including its changed-range scan; that does not erase the full-history failure.
Final layout commit: [frontend passed](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39206609300),
[foundation/container passed](https://github.com/Bhavi123-hacker/AlphaLens/actions/runs/39206609265):
1,462 backend passes/eight skips in 213.83s; strict Trivy zero HIGH/CRITICAL;
changed-range TruffleHog zero verified/unverified findings, five scanned chunks.
Frontend CI also passed its four isolated synthetic-demo browser checks, build,
types, lint and dependency audit. This clean changed-range result does not claim
the historical full-history findings have been removed.

## Private before/after browser evidence and handoff

Actual authenticated compiled screenshots (not mockups) remain local:

- `.local-data/product-visual-browser/before-dashboard.png`
- `.local-data/product-visual-browser/after-dashboard.png`
- `.local-data/product-visual-browser/before-nse-market.png`
- `.local-data/product-visual-browser/after-nse-market.png`
- `.local-data/product-visual-browser/final-acceptance/premium-dashboard-light.png`
- `.local-data/product-visual-browser/final-acceptance/premium-candidate-evidence.png`

They can contain private licensed observations and are deliberately not committed
or publicly redistributed. [Operator commands and preview sign-in boundaries](../operator/alphalens-runbook.md#tested-product-and-visual-preview)
explain the separate QA account. Existing original-operator commands remain:

```powershell
Set-Location D:\al-research\p28-worktree
.\scripts\windows\start-p33-alphalens.cmd
.\scripts\windows\stop-p33-alphalens.cmd
```

Do not use the stop command during collection: it stops the owned app/PostgreSQL.
Preview-only start/stop uses `start-alphalens.cmd` / `stop-alphalens.cmd` with
`.local-data\final-operational-browser-runtime\operator-config.json` instead.

## Exact changed-file inventory

The following paths are relative to the repository and include both tasks:

```text
README.md
apps/api/src/alphalens_api/nse_market.py
apps/web/src/App.tsx
apps/web/src/components/CandidateEvidence.tsx
apps/web/src/components/ChartCanvas.tsx
apps/web/src/components/NseOperations.tsx
apps/web/src/components/ResearchSizing.tsx
apps/web/src/components/SaveResearchCandidate.tsx
apps/web/src/components/SequenceResearch.tsx
apps/web/src/components/StockResearch.tsx
apps/web/src/components/Visuals.tsx
apps/web/src/lib/chart-options.ts
apps/web/src/lib/chart-theme.ts
apps/web/src/lib/visual-options.ts
apps/web/src/pages/Backtests.tsx
apps/web/src/pages/Discovery.tsx
apps/web/src/pages/NseMarket.tsx
apps/web/src/pages/Overview.tsx
apps/web/src/pages/Personal.tsx
apps/web/src/styles.css
apps/web/src/terminal.css
apps/web/tests/browser/product-visual-quality.spec.ts
apps/web/tests/candidate-save.test.tsx
apps/web/tests/chart-theme.test.ts
apps/web/tests/nse-market.test.tsx
docs/case-studies/alphalens-investment-intelligence.md
docs/development/alphalens-product-quality-and-visual-overhaul.md
docs/operator/alphalens-runbook.md
scripts/observe_nse_task.py
tests/integration/test_nse_market_sequence_api.py
tests/unit/test_nse_task_observation.py
workers/nse_market/engine.py
workers/nse_market/task_observation.py
```
