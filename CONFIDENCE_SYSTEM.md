# Trading Bot Confidence System

## Overview
The confidence score is a **comprehensive aggregation** of all market factors that determine trade quality. It represents the probability that a trade will be profitable.

## Formula
```
Final_Confidence = Base_Confidence + Σ(All_Market_Factors)
```

Where:
- `Base_Confidence = tanh(|ML_Score|)` - Baseline from ML model (0-76% typically)
- Market factors are additive boosts or penalties
- Final confidence is bounded [0, 1]

---

## Factor Weights & Rationale

### CORE FACTORS (Critical for profitability)

#### 1. Expected Value (EV) - **20% weight**
**Why**: Most important factor. Represents mathematical expectation of profit/loss.
- **+20%** if EV > 0.1% (Excellent trade)
- **+10%** if EV > 0.05% (Good trade)
- **-25%** if EV < -0.05% (Bad trade)

**Rationale**: At 40x leverage, even small positive EV compounds. Negative EV should be heavily penalized.

#### 2. RSI Signal Strength - **15% weight**
**Why**: Strong technical indicator for overbought/oversold conditions.
- **+15%** if RSI < 30 (LONG) or RSI > 70 (SHORT) - Very extreme
- **+8%** if RSI < 40 (LONG) or RSI > 60 (SHORT) - Moderate extreme

**Rationale**: Extreme RSI values have high mean-reversion probability, especially with 40x leverage.

#### 3. Volume Confirmation - **10% weight**
**Why**: High volume validates price movements, low volume indicates weak signals.
- **+10%** if volume is HIGH/VERY_HIGH/EXTREME
- **-5%** if volume is LOW/VERY_LOW

**Rationale**: Volume is the fuel for price movements. Low volume = unreliable signals.

#### 4. Orderbook Pressure - **8% weight**
**Why**: Shows real-time market momentum (only meaningful with high volume).
- **+8%** if high volume + pressure aligned with direction
- **-8%** if high volume + pressure opposite to direction

**Rationale**: High volume + aligned pressure = strong momentum. Opposite pressure = warning signal.

#### 5. Pattern Confirmation - **6% weight**
**Why**: Technical patterns provide setup validation.
- **+6%** if pattern setup confirms direction (BULLISH for LONG, BEARISH for SHORT)

**Rationale**: Patterns like Head & Shoulders, Double Top/Bottom have proven predictive value.

#### 6. Macro Trend Alignment - **5% weight**
**Why**: Trading with the 7-day trend increases probability of success.
- **+5%** if 7-day trend supports direction
- **-5%** if fighting the 7-day trend

**Rationale**: "Trend is your friend." Fighting macro trends is risky.

#### 7. Support/Resistance Proximity - **10% weight**
**Why**: Entry/exit quality is critical for tight SL/TP at 40x leverage.
- **+10%** if price within 1% of support (LONG) or resistance (SHORT)

**Rationale**: S/R levels are high-probability reversal zones. Optimal entry points.

#### 8. Market Quality - **8% weight**
**Why**: Market tradability affects execution quality.
- **+8%** if market quality is EXCELLENT
- **+4%** if market quality is GOOD
- **-10%** if market quality is POOR

**Rationale**: Poor market quality (low liquidity, high spread) = bad execution.

---

### SECONDARY FACTORS (Strategy optimization)

#### 9. Range Trading Bonus - **8% weight**
**Why**: Range trading is optimal for 40x leverage scalping.
- **+8%** if market is in low-volatility range

**Rationale**: Tight ranges allow precise SL/TP placement with high win rate.

#### 10. Volatility Penalty - **Up to -12%**
**Why**: Risk management. High volatility = unpredictable price action.
- **-12%** if volatility is EXTREME
- **-6%** if volatility is HIGH

**Rationale**: At 40x leverage, extreme volatility can trigger SL prematurely.

---

### MINOR FACTORS (Fine-tuning, 2-3% each)

These factors provide incremental improvements:

- **Sentiment Alignment** (+3%): Fear & Greed Index
- **Funding Rate Alignment** (+3%): Perpetual futures funding
- **Global Volume** (+3%): High Binance volume confirms activity
- **Volume Profile POC** (+3%): Price near Point of Control
- **Cross-Asset Correlation** (+2%): DXY/Gold correlation (uses UUP ETF for USD strength tracking)

**Rationale**: Each provides marginal edge. Combined, they add ~10-15% to confidence.

**Note**: Minor factors fail gracefully. If external data is temporarily unavailable, neutral values (0.0) are used with no impact on confidence. 

**Updated 2025-10-12**: Fixed delisted symbols:
- DXY tracking uses UUP ETF (Invesco DB US Dollar Index Bullish Fund) instead of delisted DX-Y.NYB
- Gold tracking uses GLD ETF (SPDR Gold Shares) instead of delisted GC=F futures

---

### PENALTIES

- **Conflicting Patterns** (-5%): When multiple patterns disagree

---

## Total Possible Range

- **Maximum Boost**: ~80% (all factors aligned perfectly)
- **Maximum Penalty**: ~25% (worst case scenario)

**Typical confidence range**: 40-85%

---

## Strategy-Specific Thresholds

Different strategies have different confidence requirements:

| Strategy | Min Confidence | Rationale |
|----------|---------------|-----------|
| **Standard** | 65% | Safe default |
| **Range Trading** | 52% | Optimal conditions, lower threshold OK |
| **Scalping** | 50% | Fast trades, many opportunities |
| **Trend Following** | 60% | Needs strong trend confirmation |
| **Breakout** | 58% | High volatility, moderate threshold |
| **High Volatility** | 55% | Riskier, needs decent confidence |
| **Spike Hunting** | 70% | Very risky, needs high confidence |

---

## Why This Works

1. **Comprehensive**: Aggregates ALL market information
2. **Weighted**: Important factors have higher weights
3. **Bounded**: Stays within [0, 1] probability range
4. **Additive**: Independent factors sum logically
5. **Interpretable**: Each factor has clear rationale
6. **Tested**: Weights based on trading experience and 40x leverage requirements

---

## Example Calculation

**Scenario**: LONG trade, RSI 28, High volume, Positive EV, Near support

```
Base Confidence: 0.45 (from ML model)

+ EV (0.08%) = +10%     (Good EV)
+ RSI (28) = +15%       (Very oversold)
+ Volume = +10%         (High volume)
+ Pressure = +8%        (Buy pressure + high volume)
+ S/R = +10%            (Near support)
+ Market Quality = +4%  (Good market)

Final = 0.45 + 0.57 = 1.02 → capped at 1.00 (100%)
```

This trade has **maximum confidence** because all critical factors align perfectly.

---

## Trade Execution

**Rule**: Trade executes if `Final_Confidence >= Strategy_Min_Confidence`

No other checks. Confidence is the **single source of truth** for trade execution.

