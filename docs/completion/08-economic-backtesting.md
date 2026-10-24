# Economic backtesting — 24 October 2026

Status: **PARTIAL** accounting implementation; **BLOCKED_EVIDENCE** for complete historical economic returns. The original 504 backtests and all original results remain preserved. No final-holdout simulation, accounting rewrite, retuning or fabricated terminal consideration was performed.

The saved machine-readable `docs/backtesting/real-research-economic-audit.json` was parsed directly. It records `CONSISTENT_WITH_FROZEN_ENGINE`, zero lifecycle/valuation inconsistencies detected by that prior bounded audit, and the following mutually exclusive partition:

| Original run group | Count | Missing evidence |
| --- | ---: | --- |
| Action uncertainty only | 258 | Verified entitlements, effective quantities and dated cash flows |
| Action and source/identity gaps | 198 | Both action reconciliation and missing dated observations |
| Source/identity gaps only | 18 | Genuine marks, continuity or terminal consideration |
| Full raw-price diagnostics | 30 | Still not certified complete total-return accounting |

Thus **474 economically unresolved runs remain unresolved**. They are not 474 demonstrated software defects. Recorded terminal states include 93,399 CLOSED, 1,032 UNRESOLVED_RAW_ECONOMIC_ACTION, 231 UNRESOLVED_MISSING_EXIT and 87 OPEN, repeated across cost scenarios. A legitimate open position does not authorize an invented exit value. Unknown prior NAV cannot be repaired by a later observed price.

The audit's 288 deduplicated action events comprise 266 dividends, 14 bonuses, 5 rights, 2 demergers and 1 split. Of 71 missing-price events, 67 have no matching original source observation and 4 require alternative-ISIN reconciliation. Calendar slots, suspension/delisting uncertainty and dated identity changes must remain visible. Generic split formulas do not establish dividend entitlement, record/payment dates, rights elections or demerger consideration.

Existing exact money/cost/FIFO/portfolio modules and conservative unknown-value propagation remain useful. A future separate versioned ledger needs source-qualified settled quantities, ex/record/effective/payment dates, receivables versus paid cash, quantity/cost-basis conservation, explicit election cash and dated terminal claims. Missing components prevent a complete NAV claim. Original artifacts must stay immutable; any corrected economic study requires pre-registered methodology and valid new source evidence.

Separate fixed-current-cohort research already exists in `workers/nse_market/economic_research.py`. Its saved report SHA256 was independently checked: `0a55dd7c1483fd0da79db5e2b849132fc612f8a707f70a76a9be91d4f387c09f`. It uses 27,820 saved historical predictions / 420 dates / 97 securities and four pre-registered sparse-entry policies, without new fits or provider requests. Known 2025–2026 periods remain development information. This study is price-reference cost sensitivity, not a repair of the original 504 simulations, independent evidence of profit or an executable portfolio valuation.

Regression command: `.venv/Scripts/python.exe -m pytest tests/unit/test_nse_market_forward_cohort.py tests/unit/test_nse_market_stock_history.py tests/unit/test_experimental_nse_v2_forward.py tests/unit/test_investment_economic_research.py -q --basetemp D:/al-temp/completion-model-forward` — **67 passed in 11.17 s**. These are TEST_ONLY software checks, not reruns of frozen research or evidence of investable profit.

Further deduplicated source findings and preserved original cost results are retained in [economic accounting](05-economic-accounting.md). The campaign retains all evidence gaps rather than manufacturing economics to force release acceptance.
