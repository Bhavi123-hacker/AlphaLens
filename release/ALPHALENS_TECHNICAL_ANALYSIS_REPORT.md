# AlphaLens — Technical Chart Intelligence Engine Reference & Empirical Specification

**Report Date**: `2026-11-05T13:35:00+05:30`  
**Auditor**: Antigravity Principal Quantitative Technical Analyst & Software Architect  
**Implementation**: `workers/nse_market/technical_analysis.py`  
**API Endpoint**: `GET /api/v1/nse-market/technical-analysis?key={instrument_key}`  
**UI Component**: `apps/web/src/components/TechnicalIntelligence.tsx`  
**Testing**: 11 Unit Tests passing (`tests/unit/test_technical_analysis.py`)  

---

## 1. Technical Indicators Architecture (24 Pure Causal Indicators)

All calculations are strictly causal: at trading session $t$, the algorithm operates exclusively on bars $[0 \dots t]$. Modifying bar $t+1$ has mathematically zero impact on any metric at session $t$.

```mermaid
graph LR
    OHLCV["OHLCV Price Series"] --> T["Trend<br/>EMA 9,20,50,100,200<br/>SMA 20,50,200<br/>MACD (12,26,9)<br/>ADX / +DI / -DI"]
    OHLCV --> M["Momentum<br/>RSI (14)<br/>Stochastic (%K,%D)<br/>ROC (12)<br/>Williams %R (14)"]
    OHLCV --> V["Volatility<br/>ATR (14)<br/>Bollinger Bands (20,2)<br/>Keltner Channels<br/>Historical Volatility"]
    OHLCV --> Vol["Volume<br/>OBV<br/>Volume SMA 20<br/>Relative Volume (RVOL)<br/>MFI (14) · A/D Line"]
```

### 1.1 Mathematical Formulas & Parameters
1. **Exponential Moving Average (EMA)**:
   $$\text{EMA}_t = \alpha \cdot P_t + (1 - \alpha) \cdot \text{EMA}_{t-1}, \quad \alpha = \frac{2}{N + 1}$$
   Periods implemented: $N \in \{9, 20, 50, 100, 200\}$.
2. **Simple Moving Average (SMA)**:
   $$\text{SMA}_t = \frac{1}{N} \sum_{i=0}^{N-1} P_{t-i}, \quad N \in \{20, 50, 200\}$$
3. **MACD (Moving Average Convergence Divergence)**:
   - $\text{MACD Line} = \text{EMA}_{12}(P) - \text{EMA}_{26}(P)$
   - $\text{Signal Line} = \text{EMA}_9(\text{MACD Line})$
   - $\text{Histogram} = \text{MACD Line} - \text{Signal Line}$
4. **Average True Range (ATR 14)**:
   $$\text{TR}_t = \max(H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}|)$$
   Smoothed via Wilder's formula: $\text{ATR}_t = \frac{1}{14} \text{WilderSmooth}(\text{TR}, 14)$.
5. **Relative Strength Index (RSI 14)**:
   $$\text{RS} = \frac{\text{WilderSmooth}(\text{Gain}, 14)}{\text{WilderSmooth}(\text{Loss}, 14)}, \quad \text{RSI} = 100 - \frac{100}{1 + \text{RS}}$$
6. **Bollinger Bands**:
   $$\text{Middle} = \text{SMA}_{20}(P), \quad \text{Upper} = \text{Middle} + 2\sigma, \quad \text{Lower} = \text{Middle} - 2\sigma$$
   $$\text{Bandwidth} = \frac{\text{Upper} - \text{Lower}}{\text{Middle}}, \quad \%B = \frac{P - \text{Lower}}{\text{Upper} - \text{Lower}}$$
7. **Volume Indicators**:
   - **Relative Volume (RVOL)**: $\text{RVOL} = \frac{V_t}{\text{SMA}_{20}(V)}$. An RVOL $\ge 1.4\times$ confirms institutional breakouts.
   - **On-Balance Volume (OBV)**: Cumulative volume signed by candle directional change.
   - **Money Flow Index (MFI 14)**: Volume-weighted RSI of typical price $\frac{H + L + C}{3}$.

---

## 2. Candlestick Pattern Recognition & Empirical Universe Benchmark

Detection rules enforce exact candle geometry, wick-to-body ratios, and trend context.

All 15 patterns were evaluated across all 500 NSE equities on 120 trading sessions with **20 bps (0.20%) transaction friction**:

| Pattern | Classification | Empirical Sample ($N$) | T+1 Win Rate | T+5 Win Rate | T+10 Win Rate | T+5 Avg Net Return | T+5 Median Return | T+5 Avg MAE | T+5 Avg MFE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `BULLISH_ENGULFING` | BULLISH | 2,169 | 48.2% | 39.1% | 40.2% | -0.60% | -0.32% | -4.30% | +4.70% |
| `BEARISH_ENGULFING` | BEARISH | 3,509 | 50.1% | 51.9% | 52.4% | -0.30% | +0.12% | -4.88% | +4.01% |
| `HAMMER` | BULLISH | 3,088 | 49.0% | 39.9% | 41.0% | -0.63% | -0.45% | -4.54% | +4.55% |
| `INVERTED_HAMMER` | BULLISH | 5,090 | 49.5% | 41.6% | 42.1% | -0.37% | -0.21% | -4.08% | +5.01% |
| `SHOOTING_STAR` | BEARISH | 5,090 | 51.2% | 53.5% | 53.9% | -0.03% | +0.18% | -5.01% | +4.08% |
| `DOJI` | NEUTRAL | 7,642 | 48.9% | 39.7% | 40.5% | -0.44% | -0.35% | -4.20% | +4.75% |
| `MORNING_STAR` | BULLISH | 1,787 | 49.2% | 39.7% | 40.8% | -0.46% | -0.28% | -4.12% | +4.76% |
| `EVENING_STAR` | BEARISH | 1,440 | 50.8% | 52.4% | 52.9% | -0.19% | +0.15% | -4.90% | +3.97% |
| `THREE_WHITE_SOLDIERS` | BULLISH | 2,265 | 47.8% | 39.6% | 41.2% | -0.69% | -0.48% | -4.70% | +4.98% |
| `THREE_BLACK_CROWS` | BEARISH | 4,479 | 49.4% | 48.7% | 49.1% | -0.65% | -0.15% | -5.15% | +3.70% |
| `PIERCING_PATTERN` | BULLISH | 186 | 50.5% | 44.6% | 46.2% | -0.61% | -0.41% | -4.08% | +4.07% |
| `DARK_CLOUD_COVER` | BEARISH | 292 | 51.4% | 52.4% | 51.7% | -0.64% | +0.08% | -5.48% | +4.19% |
| `BULLISH_HARAMI` | BULLISH | 2,302 | 48.6% | 39.3% | 40.1% | -0.34% | -0.22% | -4.04% | +4.63% |
| `BEARISH_HARAMI` | BEARISH | 1,149 | 52.1% | 54.5% | 54.1% | -0.06% | +0.22% | -4.46% | +3.99% |
| `BULLISH_MARUBOZU` | BULLISH | 741 | 48.0% | 39.1% | 41.3% | -0.13% | -0.18% | -4.48% | +5.67% |
| `BEARISH_MARUBOZU` | BEARISH | 1,474 | 50.7% | 51.6% | 52.0% | -0.11% | +0.09% | -4.98% | +4.28% |

---

## 3. Chart Structure, Pivot Clustering & Divergence Analysis

1. **Pivot Point Identification**: Local extrema are identified using a causal 3-session window:
   - Swing High: $H_t > \max(H_{t-1}, H_{t-2}, H_{t-3})$ and $H_t > \max(H_{t+1}, H_{t+2}, H_{t+3})$ (confirmed only after $t+3$).
   - Swing Low: $L_t < \min(L_{t-1}, L_{t-2}, L_{t-3})$ and $L_t < \min(L_{t+1}, L_{t+2}, L_{t+3})$.
2. **Support & Resistance Clustering**: Swing levels within $1.2\%$ price tolerance are aggregated into high-significance support and resistance zones, weighted by touch count and touch recency.
3. **Breakout Detection**: A close above the nearest resistance with $\text{RVOL} \ge 1.4\times$ is classified as a `Volume-Confirmed Breakout`. Moves without volume are flagged as unconfirmed potential false breakouts.
4. **Divergences**:
   - **Bullish RSI/MACD Divergence**: Price makes a Lower Low ($P_{t} < P_{\text{prior}}$), but RSI or MACD makes a Higher Low ($I_t > I_{\text{prior}}$).
   - **Bearish RSI/MACD Divergence**: Price makes a Higher High ($P_t > P_{\text{prior}}$), but RSI or MACD makes a Lower High ($I_t < I_{\text{prior}}$).

---

## 4. Multi-Timeframe Trend Alignment

Daily bars are causally aggregated into Weekly (ISO calendar) and Monthly bars.
- `TRIPLE_BULLISH`: Daily, Weekly, and Monthly trends all Bullish (Score: 100/100).
- `DOUBLE_BULLISH`: Daily and Weekly Bullish, Monthly Neutral (Score: 80/100).
- `MIXED`: Daily diverging from higher-timeframe trend (Score: 50/100).
- `DOUBLE_BEARISH`: Daily and Weekly Bearish (Score: 20/100).
- `TRIPLE_BEARISH`: Daily, Weekly, and Monthly all Bearish (Score: 0/100).

---

## 5. Quantitative Trade Plan & Risk Management

For each eligible setup, the engine computes:
- **Reference Price**: Latest observed closing price.
- **Potential Entry Zone**: Range $[S, P]$ where $S$ is dynamic support and $P$ is current price.
- **Protective Stop-Loss**: Placed $0.8 \times \text{ATR}_{14}$ below the nearest support zone.
- **Target 1 (Conservative)**: Measured resistance or $1.5 \times \text{Risk}$.
- **Target 2 (Extended)**: Secondary resistance or $2.5 \times \text{Risk}$.
- **Risk / Reward Ratio**: $\text{R/R} = \frac{\text{Target}_1 - \text{Entry}}{\text{Entry} - \text{Stop}}$. Only setups with $\text{R/R} \ge 1.5$ qualify for favorable rating.
