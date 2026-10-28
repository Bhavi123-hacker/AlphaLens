# Render preparation and working private application

The existing authenticated application at http://127.0.0.1:8041/nse-market is
working with genuine saved data. The operator requests Render hosting and has a
Render account that is not yet connected to AlphaLens. This release implements
the previously missing secure hosted mode; it does not claim that a Render
service or new live market feed has already been deployed.

## Working application evidence

Actual private-browser workflows passed: stock search, price/volume charts,
Top5/10/20, research explanations, forecast history, pending outcomes, mobile
layout and unavailable/insufficient-history/unsupported-stock states. Seven
saved-data and health APIs returned200. Current saved coverage is3,194 searchable
equities,500 price histories and499 observations for the latest retained session,
23 October. The database contains945 forecasts and914 unique decisions.

Genuine saved candles regenerated all312 feature vectors and executed the pinned
trained model, reproducing every saved score exactly. These are dated experimental
outputs, not newly created forecasts. All63 evaluated model versions remain
experimental, and zero qualified forward outcomes means accuracy is not yet
measurable. Software execution does not establish an investment edge.

Private evidence is retained under
`.local-data/app-completion-20261028-1205/`, including browser reports, the complete
decision audit and numerical replay. No provider/NTP call or manual collector was
started. The existing collector and both Windows task definitions are preserved.

## Changes delivered

- Explicit `hosted_private` API mode, with a single HTTPS browser origin, exact
  host allowlist, mandatory original authentication/CSRF/rate limits and Secure,
  HttpOnly, SameSite Strict cookies. Forwarded headers confer no identity trust.
- Platform port/bind configuration and fail-closed checks for imported protected
  state, compiled frontend and an existing active operator. Local mode remains
  the default with its original loopback restrictions.
- Non-root full-stack Render image, inactive reviewed blueprint, container CI and
  a concrete [deployment runbook](ALPHALENS_HOSTED_PRIVATE_DEPLOYMENT.md).
- Cross-platform backup manifests: new exports use POSIX relative paths; retained
  Windows separators can be verified on Linux without changing original manifest
  bytes. Absolute paths, traversal and alternate data streams are rejected.
- Keyboard focus and scrolling for the mobile collection-alert table. The
  isolated mobile check now reports zero Axe violations.

Focused verification passed:64 hosted/config/auth tests,37 deployment checks,
13 backup cases and4 frontend component cases. The92 ML/forward cases are a
separate overlapping run; these counts must not be combined into a full-suite
total. Ruff, mypy, Bandit and focused frontend lint passed. No security scanner
waiver was added. The new image's build and HIGH/CRITICAL scan are recorded by
the release commit's `hosted-private-container-readiness` CI, separately from the
earlier local image's results.

## Remaining deployment decisions

Connect the Render account to `Bhavi123-hacker/AlphaLens`, selecting branch
`alphalens-master-completion`. Review blueprint path
`infra/deploy/render-private.review-only.yaml` before creating resources.
The proposed service/disk are chargeable and not approved; no paid resource has
been created. Render's free service cannot preserve this application's local
stores across restarts. A persistent target and explicit cost approval or an
existing suitable server are still required.

Import and verify the private dataset/model/forecast snapshot and operator state
before startup. The initial Render disk-seeding procedure and actual target
capacity remain unqualified; neither is hidden by initializing empty stores.
Configure any required cloud PostgreSQL target separately without exposing the
local database or copying its Windows credentials into source control.

The existing Windows collector remains the sole approved scheduled writer.
Automatic cloud collection or private synchronization requires its own exact
storage, clock, quota and cutover policy; running two independent collectors is
not authorized. Public redistribution rights are also distinct from ownership
of the AlphaLens code. This release keeps all real-data APIs authenticated.
