"""Explicit formulas and dependency lengths; registry is extensible, not executable plugins."""

from alphalens_features.models import BuildPlan, FeatureDefinition, FeatureSet


def default_set(plan: BuildPlan) -> FeatureSet:
    definitions: list[FeatureDefinition] = []

    def add(
        name: str,
        family: str,
        lookback: int,
        minimum: int,
        formula: str,
        inputs: tuple[str, ...] = ("close",),
        **parameters: int | str,
    ) -> None:
        definitions.append(
            FeatureDefinition.model_validate(
                dict(
                    feature_name=name,
                    feature_family=family,
                    lookback=lookback,
                    minimum_history=minimum,
                    formula=formula,
                    required_inputs=inputs,
                    parameters=parameters,
                    data_quality_policy=plan.quality_policy,
                )
            )
        )

    for n in (1, 5, 10, 20, 60):
        add(f"return_{n}", "RETURNS" if n == 1 else "MOMENTUM", n + 1, n + 1, "C[t]/C[t-n]-1", n=n)
    add("log_return_1", "RETURNS", 2, 2, "ln(C[t]/C[t-1])")
    for n in (5, 10, 20, 50, 100, 200):
        add(f"sma_{n}", "TREND", n, n, "sum(last n closes)/n", n=n)
        add(f"distance_sma_{n}", "TREND", n, n, "C[t]/SMA[n]-1", n=n)
    for n in (12, 26):
        add(
            f"ema_{n}",
            "TREND",
            50,
            n,
            "Trailing at most 50 closes; SMA[n] seed then alpha=2/(n+1)",
            n=n,
        )
    for name in ("macd", "macd_signal", "macd_histogram"):
        add(name, "TREND", 50, 34, "EMA12-EMA26; signal EMA9 SMA9 seed; histogram difference")
    add(
        "rsi_14",
        "MOMENTUM",
        50,
        15,
        "Wilder gains/losses SMA14 seed then alpha=1/14; flat=50, zero loss=100",
        n=14,
    )
    add(
        "atr_14",
        "VOLATILITY",
        50,
        15,
        "TR=max(H-L,abs(H-Cprev),abs(L-Cprev)); Wilder SMA14 seed alpha=1/14",
        ("high", "low", "close"),
        n=14,
    )
    for n in (5, 10, 20, 60):
        add(
            f"volatility_{n}",
            "VOLATILITY",
            n + 1,
            n + 1,
            "Sample standard deviation of last n simple session returns; ddof=1; unannualized",
            n=n,
        )
    add("volume_sma_20", "VOLUME", 20, 20, "mean(last 20 volumes)", ("volume",))
    add(
        "volume_ratio_20",
        "VOLUME",
        20,
        20,
        "V[t]/mean(last 20 volumes); zero mean=NULL",
        ("volume",),
    )
    add(
        "volume_zscore_20",
        "VOLUME",
        20,
        20,
        "(V[t]-mean(last 20 V))/sample stdev(last 20 V); zero stdev=NULL",
        ("volume",),
    )
    add("close_to_high_20", "TREND", 20, 20, "C[t]/max(last 20 highs)-1", ("close", "high"))
    add(
        "range_location_20",
        "TREND",
        20,
        20,
        "(C[t]-min(last 20 lows))/(max(last 20 highs)-min(last 20 lows)); zero range=NULL",
        ("close", "high", "low"),
    )
    add("drawdown_20", "TREND", 20, 20, "C[t]/max(last 20 closes)-1")
    add(
        "bollinger_location_20",
        "VOLATILITY",
        20,
        20,
        "(C[t]-(mean-2*sample stdev))/(4*sample stdev); zero stdev=NULL",
    )
    add("bollinger_width_20", "VOLATILITY", 20, 20, "4*sample stdev(last 20 C)/mean(last 20 C)")
    if plan.benchmark_security_id:
        add(
            "relative_return_20",
            "RELATIVE_STRENGTH",
            21,
            21,
            "Security return20 minus designated benchmark return20",
            ("close", "benchmark.close"),
        )
        add(
            "market_return_20",
            "MARKET_CONTEXT",
            21,
            21,
            "Designated benchmark return20",
            ("benchmark.close",),
        )
        add(
            "market_volatility_20",
            "MARKET_CONTEXT",
            21,
            21,
            "Designated benchmark sample stdev of last 20 simple returns",
            ("benchmark.close",),
        )
    add(
        "momentum_percentile_20",
        "CROSS_SECTIONAL",
        21,
        21,
        "Eligible return20 values: (less + (equal-1)/2)/(count-1); singleton=NULL",
    )
    return FeatureSet(definitions=tuple(definitions), plan=plan)
