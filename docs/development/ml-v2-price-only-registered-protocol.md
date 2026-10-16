# V2 price-only availability companion protocol

Registered 16 October 2026 before inspecting primary model metrics or fitting the
companion. This is a separately versioned experiment, not an amendment to the
locked 20-feature primary experiment. Preserve its models, failed coverage and
evaluation. No acceptance threshold changes.

Availability evidence: the genuine fixed 50-stock snapshot contains 59,400 daily
observations through 16 October. Only 31 stocks pass the conservative 61-observed-
session corporate-action exclusion on 15 October, below the primary contract's
40-stock minimum for cross-sectional context. This is a coverage constraint,
not evidence about which indicators predict returns.

The companion contract `nse.adjusted-price-only.16.v2` contains exactly the first
16 features of the pinned `nse.adjusted-price-context.20.v2` contract, in the
same order and using identical formulas. It omits all four fixed-cohort context
features. It requires the same complete per-stock 61-slot lookback, dated source
basis, hazard exclusions, valid identity, chronology and missing-session checks.
It has no cross-sectional feature and therefore no cross-sectional denominator
or context-coverage threshold. Missing input is never imputed.

Use a separate immutable artifact/evaluation directory. The source dataset and
the adjusted next-session-open to fifth-session-close price-return target remain
identical to the primary protocol. No dividends, total returns or executed profit
are inferred. Known corporate-action windows remain excluded, including all
conservatively parsed action dates. Unknown historical action completeness and
availability remain limitations.

The four configurations, annual shared-date folds, 20-session purge and embargo,
2023–2025 date-rank-IC selection, fixed-order ties, known-2026 diagnostic status,
train-only preprocessing, seed, baselines, costs, block uncertainty and prospective
acceptance criteria are exactly those of `ml-v2-registered-protocol.md` SHA256
`442811892836665af150967b406a9dab2eb30872a9cd33f2a5c819fbd34d8151`.
The additional budget is at most 16 annual fold fits plus one selected full refit.
No parameter search or retrospective promotion. All historical observations are
development evidence, including dates already observed during V1.

Both experiments and their failed results must remain in the audit trail.
If the companion supports current scoring, the dashboard must identify the exact
16-feature model, this protocol and its own measured evaluation. Do not represent
it as the original 20-feature result. A score may be frozen prospectively only
after actual inference and before the independently evidenced next opening.
No new scheduled acquisition is enabled. Independent acceptance still requires
the original predeclared future sample, statistical/economic evidence and an
actual external review; Codex cannot supply that review.
