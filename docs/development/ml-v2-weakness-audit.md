# V2 measured weakness and prospective lifecycle audit

17 October 2026. This is a software and descriptive research audit of saved
results, not independent model acceptance. No model was fitted, provider queried,
forecast rewritten, protocol amended or future outcome manufactured for this audit.

## Evidence inspected

The protected V2 snapshot has 59,400 genuine observations, 50 current fixed-cohort
securities and 1,188 observed dates from 3 January 2022 through 16 October 2026.
There are zero missing slots within that observed grid. This does not certify an
exhaustive historical exchange calendar or historical membership. The quality
report retains 170 per-security hazard-date exclusions; all 50 action reference
responses parsed, but their historical completeness remains unverified.

Saved evaluation SHA256:

- Primary20: `78a2facc1509cea6007615dc235c36d3013adbd9dd479144b477291fefcd61cc`.
- Price-only16: `e75701e6aa883fa0a90a4543b6e8b30a7aa62a38d216e819ecb526b839fab552`.

The primary20 contract produced 34,908 evaluation samples on 702 dates, with no
eligible2026 context: 31 action-safe current securities fell below its original
40-of-50 context requirement. That failure remains preserved. The separately
registered16-feature companion produced 39,847 evaluation samples on934 dates,
including the already-known2026 diagnostic period. None is an untouched test.

## What the measured results show

| Saved companion configuration | Balanced accuracy | Mean date rankIC | Brier score |
| --- | ---: | ---: | ---: |
| Logistic | 50.2819% | −0.00563 | 0.251796 |
| Ridge transformed return score | 49.2773% | −0.00348 | 0.250529 |
| Random forest | 49.9634% | 0.00562 | 0.250274 |
| Selected histogram boosting | 50.1085% | 0.00200 | 0.252864 |
| Training-majority baseline | 50.0000% | Constant within date | 0.249375 |
| Five-slot momentum baseline | 48.8842% | −0.03982 | 0.275767 |
| Five-slot mean reversion baseline | 51.1131% | 0.03982 | 0.269959 |

Scores are uncalibrated. Ridge's bounded transform is a ranking score, not a
probability; its squared score error does not establish probability calibration.
The selected algorithm followed the registered2023–2025 mean date-rankIC rule,
not the highest pooled balanced accuracy. Random forest's slightly higher pooled
IC is not a reason to change that selection after seeing diagnostics.

The positive-label fraction is52.4105%, so an always-positive forecast can look
reasonably accurate while offering no balanced-accuracy advantage. Selected
boosting recalls76.6711% of positives but its overall balanced accuracy remains
50.1085%. This points to directional bias rather than demonstrated discrimination.

Calibration bins expose unstable score interpretation: the0.60–0.80 bin averages
0.6411 while only54.6595% of its6,138 observations are positive. The0.80–1.00 bin
has only12 observations and25% positives. These small/high-score bins cannot
support a claimed confidence level. Majority has lower Brier error than every
candidate; no calibration benefit has been demonstrated.

Boosting date-rankIC changes from0.00848/0.01094/0.03915 in2023/2024/2025 to
−0.06680 in the known2026 diagnostic period. Its2026 balanced accuracy is47.5633%
and Brier error0.262107. The cohort also contracts from50 securities to48 with
only3,345 eligible2026 samples. This is evidence of instability under a changed
sample/time mix, not proof of a particular causal mechanism.

The pooled selected model's Bonferroni-adjusted balanced-accuracy improvement
interval versus majority is[−0.00934,0.01241]; versus mean reversion it is
[−0.03331,0.01031]. Both include zero. Date-block rankIC improvement versus mean
reversion has adjusted interval[−0.12077,0.01525]. The observed mean-reversion
baseline is useful comparative evidence, not independently validated advice.

## Costs, coverage and limitations

The saved nonoverlapping Top5 price-reference simulation spans187 exposures.
Its gross compounded price component is+47.1775%. With the predeclared25bps
round-trip assumption and5bps slippage per side, the same arithmetic becomes
−23.5106%, with rebalance-endpoint reference drawdown−42.5750%. Equal cohort is
−33.5133%, momentum Top5−31.5559% and low-volatility Top5−43.6803% under that
same assumption. These are hypothetical reference scenarios, not executed profit,
total shareholder return, actual fees or complete within-holding drawdown.

Saved Top5/10/20 membership turnover is62.58%/53.50%/39.79% respectively.
Frequent selection changes and small ranking separation make cost sensitivity
material. No constant feature or pair with absolute correlation≥0.95 was found
in the saved feature audit. That removes two simple implementation explanations;
it does not establish that the feature family has useful predictive information.

Current identities, selected liquid securities, adjustment-vintage uncertainty,
incomplete corporate-action history, unknown publication vintages and the absence
of a source-compatible independent benchmark limit interpretation. The price
target excludes dividends. More stocks or more indicators would not resolve these
limitations by themselves. The evidence supports **NO_DEMONSTRATED_EDGE**.

## Operational outcome and remaining evidence

The31 original eligible forecasts remain unchanged. At this audit there are zero
matured prospective outcomes. Their frozen next opening is19 October; five actual
subsequent eligible sessions, genuine published prices, official consecutive
session evidence and action checks must precede outcome calculation. No final
date is invented from weekdays. Before that opening, diagnostics truthfully show
zero observed target sessions and five still required. After entry, unavailable
progress evidence is null rather than an invented count; missing published bars,
excluded outcomes and research-only records have separate counts.

Prospective ranking statistics require complete frozen cohorts. Missing/excluded
members invalidate cohort comparisons; survivors are never reranked. Price-cost
scenarios compound only nonoverlapping intervals and remain separate by model.
Corrections append immutable revisions and preserve their original records.

Acceptance still requires126 future decision dates,1,000 matured forecasts,
30 securities, two quarters, the original statistical/economic requirements and
independent external review. Companion16 lacks the original cohort-regime feature;
its market-regime acceptance evidence remains missing. A caller-supplied review
ID or green economic flags cannot establish verified independent approval.
External document/identity/hash verification and the exact registered criteria
remain mandatory. The accepted publication adapter stays unavailable.

No V3 is trained in this audit. Choosing another model or feature family from
these known outcomes would create another development selection, not independent
confirmation. Continue the frozen prospective process and preserve failures.
