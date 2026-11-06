# Research ranking policy v1 — registered 24 October 2026

Registered before implementing or evaluating the optional risk ordering. This is an **engineering assumption**, not a validated investment rule, a fitted model, calibrated probability, expected return or evidence of superior performance. No historical model or frozen evaluation changes.

The opt-in API parameter is `rank_policy=risk_adjusted`. Its ordering value is the saved five-session classifier score minus one times the saved daily-return standard deviation, both expressed as fractions. Sort descending by this value, then ascending by exact security key. Preserve the original classifier score and describe it as uncalibrated. The default `rank_policy=model_score` preserves descending original score, then exact key.

Only the supported five-session view applies model ordering. Existing 10/20-session views remain descriptive volatility ordering and must not imply trained forecasts. Stale five-session candidates are excluded before ordering and pagination. Risk-adjusted rows require a genuine numeric, finite, nonnegative daily-return standard deviation; missing, boolean, nonfinite or negative values are excluded and counted. No artificial candidate fills missing ranks.

Weight one is an explicit development assumption. It has not been selected by backtest, optimized against final outcomes or validated for predictive/economic benefit. Future outcome tracking retains original frozen selections; this interactive policy does not rewrite existing declarations or claim their results. Any empirical policy comparison requires separately frozen future selection evidence.
