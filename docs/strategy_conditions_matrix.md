# Strategy Conditions Matrix - Non-Overlapping

## 🎯 Distinct Strategy Conditions

| Strategy | Volatility Range | Volatility % | Trend Requirement | Volume Requirement | RSI Range | Liquidity | Priority |
|----------|------------------|--------------|-------------------|-------------------|-----------|-----------|----------|
| **Spike Hunting** | EXTREME | >5% | Any | Any | Any | Any | 1 (Highest) |
| **Scalping** | MODERATE | 0.5% - 2% | Any | NORMAL/HIGH/VERY_HIGH | 30-70 | Tight spreads + High liquidity | 2 |
| **High Volatility** | HIGH | 2% - 5% | NOT strong trending | Any | Any | Any | 3 |
| **Trend Following** | MODERATE | 1% - 2% | STRONG_UPTREND/DOWNTREND | HIGH/VERY_HIGH | Any | Any | 4 |
| **Low Volatility Range** | LOW/VERY_LOW | <1% | Any | Any | Any | Any | 5 |
| **Standard** | Any | Any | Any | Any | Any | Any | 6 (Fallback) |

## 🔍 Detailed Conditions

### 1. Spike Hunting (Priority 1)
- **Volatility**: EXTREME category + >5% actual volatility
- **Conditions**: Market chaos, extreme price movements
- **Example**: BTC drops 8% in 5 minutes
- **Profit Target**: 3.5% (highest)
- **Risk**: Highest

### 2. Scalping (Priority 2)
- **Volatility**: MODERATE category + 0.5% - 2% actual volatility
- **RSI**: 30-70 (avoid extreme zones)
- **Volume**: NORMAL/HIGH/VERY_HIGH
- **Liquidity**: Tight spreads (<0.01%) + High liquidity
- **Example**: BTC moves 1.2% with tight spreads
- **Profit Target**: 0.2% (smallest but frequent)
- **Risk**: Low per trade, high frequency

### 3. High Volatility (Priority 3)
- **Volatility**: HIGH category + 2% - 5% actual volatility
- **Trend**: NOT strong trending (avoid trend following overlap)
- **Example**: BTC moves 3% but no clear trend direction
- **Profit Target**: 2% (medium)
- **Risk**: Medium

### 4. Trend Following (Priority 4)
- **Volatility**: MODERATE category + 1% - 2% actual volatility
- **Trend**: STRONG_UPTREND or STRONG_DOWNTREND
- **Volume**: HIGH/VERY_HIGH (need volume for trends)
- **Example**: BTC in strong uptrend with 1.5% volatility
- **Profit Target**: 1.2% (medium)
- **Risk**: Medium

### 5. Low Volatility Range (Priority 5)
- **Volatility**: LOW/VERY_LOW category + <1% actual volatility
- **Example**: BTC moves 0.3% in 5 minutes
- **Profit Target**: 0.3% (small)
- **Risk**: Low

### 6. Standard (Priority 6 - Fallback)
- **Conditions**: Everything else that doesn't fit above
- **Example**: Unclear market conditions
- **Profit Target**: 0.8% (balanced)
- **Risk**: Balanced

## 🚫 Overlap Prevention

### Volatility Ranges (Non-Overlapping):
- **<1%**: Low Volatility Range only
- **1% - 2%**: Trend Following (if strong trend) OR Scalping (if perfect liquidity)
- **2% - 5%**: High Volatility only
- **>5%**: Spike Hunting only

### Trend Conditions:
- **Strong Trending**: Only Trend Following
- **Not Strong Trending**: High Volatility, Scalping, or others
- **Any Trend**: Spike Hunting, Low Volatility Range, Standard

### Volume Conditions:
- **HIGH/VERY_HIGH**: Required for Trend Following
- **NORMAL/HIGH/VERY_HIGH**: Required for Scalping
- **Any**: All other strategies

## 🎯 ML Decision Tree

```
1. Is volatility >5%? → Spike Hunting
2. Is volatility 0.5%-2% + perfect liquidity? → Scalping
3. Is volatility 2%-5% + no strong trend? → High Volatility
4. Is volatility 1%-2% + strong trend + high volume? → Trend Following
5. Is volatility <1%? → Low Volatility Range
6. Everything else → Standard
```

## 📊 Profitability Ranking

1. **Spike Hunting**: Highest profit per trade (3.5%) but highest risk
2. **High Volatility**: High profit (2%) with medium risk
3. **Trend Following**: Good profit (1.2%) with medium risk
4. **Standard**: Balanced profit (0.8%) with balanced risk
5. **Low Volatility Range**: Small profit (0.3%) with low risk
6. **Scalping**: Smallest profit (0.2%) but highest frequency

## 🔄 Strategy Switching Logic

- **Immediate Switch**: When conditions change dramatically
- **Cooldown Period**: 5 minutes between switches
- **Priority Order**: Higher priority strategies override lower ones
- **Fallback**: Always falls back to Standard if no conditions match
