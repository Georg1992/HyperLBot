# ML Learning System: What It Learns and How We Use It

## Executive Summary

The ML system learns **optimal weights for scoring Support/Resistance (S/R) levels** by analyzing historical data. These learned weights replace static weights to improve the accuracy of S/R level strength predictions.

## What the ML System Learns

### 🎯 Objective: Optimize SR Scoring Weights

The ML system learns the **optimal combination weights** for scoring S/R levels. Instead of using fixed weights from config, it learns weights that maximize profitability based on historical data.

### 📊 Current Static Weights (from `config/config.py`)

```python
SR_SCORING_WEIGHTS = {
    "proximity": 0.15,      # 15% - Distance from current price
    "touch": 0.50,          # 50% - Number of touches (primary factor)
    "reversal_probability": 0.20,  # 20% - Historical reversal rate
    "recency": 0.10,        # 10% - Time since last touch
    "volume": 0.05          # 5% - Volume at level
}
```

**What ML learns**: The optimal percentages for each factor (may differ from static values).

## How the ML System Learns

### 1. **Training Data Collection**

The system extracts features and targets from historical BTC candle data:

**Features (Inputs):**
- `touch_count` (0-100): Normalized number of times price touched the level
- `reversal_probability` (0-100): Historical reversal rate at this level
- `proximity_atr` (normalized): Distance from current price, normalized by ATR
- `recency` (normalized): Hours since last touch, normalized
- `volume_at_touch` (0-100): Normalized volume at the level

**Target (What We Want to Predict):**
- `reversal_magnitude = (MFE - MAE) / ATR`
  - **MFE** (Maximum Favorable Excursion): How much price moved away from level (reversed)
  - **MAE** (Maximum Adverse Excursion): How much price moved through level (broke out)
  - **Normalized by ATR**: Adjusts for volatility

**Example:**
- If price touched a support at $90,000
- Price dropped to $89,500 (MAE = -$500, broke through)
- Then reversed to $90,800 (MFE = +$800, reversed higher)
- ATR = $300
- Reversal magnitude = (800 - (-500)) / 300 = 4.33
- **Higher value = better reversal (stronger level)**

### 2. **Training Process**

**Walk-Forward Training** (prevents look-ahead bias):
- **Training window**: 12 months of historical data
- **Test window**: 1 month (used for validation)
- **Stride**: 1 month (slides window forward)
- **Multiple windows**: Trains on many 12-month periods, averages results

**Model**: ElasticNet Regression
- Combines L1 (Lasso) and L2 (Ridge) regularization
- Prevents overfitting
- Returns feature importance as weights

**Example Training Flow:**
```
Month 1-12: Train → Learn weights₁
Month 2-13: Train → Learn weights₂
Month 3-14: Train → Learn weights₃
...
Average all weights → Final learned weights
```

### 3. **What Gets Learned**

The model learns **optimal weights** that maximize reversal magnitude prediction:

```python
# Example learned weights (might be different from static)
learned_weights = {
    'touch': 0.45,                 # Was 0.50 (static)
    'reversal_probability': 0.30,  # Was 0.20 (increased!)
    'proximity': 0.12,             # Was 0.15 (decreased)
    'recency': 0.08,               # Was 0.10 (decreased)
    'volume': 0.05                 # Was 0.05 (same)
}
```

**Interpretation:**
- Historical reversal rate (`reversal_probability`) is more important than we thought (30% vs 20%)
- Touch count is still important but less so (45% vs 50%)
- Proximity and recency matter less than we thought
- These weights are optimized based on actual market behavior

## How We Use the Learned Weights

### 1. **Automatic Replacement in SR Scoring**

When learned weights are available, they **automatically replace** static weights:

```python
# In SRScorer.__init__()
learned_weights = self._load_learned_weights(strategy)

if learned_weights:
    # Use learned weights (ML-optimized)
    self._scoring_weights = {
        'proximity': learned_weights.get("proximity", 0.15),
        'touch': learned_weights.get("touch", 0.50),
        'reversal_probability': learned_weights.get("reversal_probability", 0.20),
        'recency': learned_weights.get("recency", 0.10),
        'volume': learned_weights.get("volume", 0.05)
    }
else:
    # Fall back to static weights from config
    self._scoring_weights = TradingConfig.SR_SCORING_WEIGHTS
```

### 2. **SR Level Scoring**

The learned weights are used to calculate S/R level scores:

```python
# In _calculate_weighted_score()
score = (
    (touch_score / 100.0) * learned_weights['touch'] +
    (reversal_probability / 100.0) * learned_weights['reversal_probability'] +
    (proximity_score / 100.0) * learned_weights['proximity'] +
    (recency_score / 100.0) * learned_weights['recency'] +
    (volume_score / 100.0) * learned_weights['volume']
) * 100.0
```

**Result**: S/R levels are scored using ML-optimized weights instead of static weights.

### 3. **Impact on Trading Decisions**

**Before (Static Weights):**
- Level A: 17 touches, 60% reversal_prob, 2% away → Score: 72%
- Level B: 8 touches, 85% reversal_prob, 1% away → Score: 68%
- **Result**: Level A ranked higher (more touches = higher score)

**After (Learned Weights - if reversal_probability weight increased):**
- Level A: 17 touches, 60% reversal_prob, 2% away → Score: 69%
- Level B: 8 touches, 85% reversal_prob, 1% away → Score: 73%
- **Result**: Level B ranked higher (better reversal probability matters more)

**Impact**: The bot selects better S/R levels for trading, leading to:
- Better entry points
- More accurate stop loss placement
- Higher probability trades

## Benefits of ML-Learned Weights

### ✅ 1. **Data-Driven Optimization**

- Weights are optimized based on **actual market behavior**
- Not based on assumptions or intuition
- Adapts to what actually works historically

### ✅ 2. **Automatic Adaptation**

- As market conditions change, weights can be retrained
- New data → Better weights → Better predictions
- Static weights become stale; learned weights stay relevant

### ✅ 3. **Better Trade Selection**

- Identifies S/R levels with higher actual reversal probability
- Improves entry/exit decisions
- Increases win rate and profitability

### ✅ 4. **No Manual Tuning**

- No need to manually adjust weights in config
- ML finds optimal values automatically
- Saves time and improves results

## Training Frequency

**Automatic Retraining**:
- **Interval**: Every 7 days (configurable)
- **Background**: Runs in background thread (non-blocking)
- **Walk-Forward**: Uses rolling window of recent data

**Manual Training**:
```bash
python scripts/train_sr_weights.py
```

## Storage and Loading

**Saved to**: `data/sr_weights/{strategy}_elasticnet_weights.json`

**Format**:
```json
{
  "weights": {
    "touch": 0.45,
    "reversal_probability": 0.30,
    "proximity": 0.12,
    "recency": 0.08,
    "volume": 0.05
  },
  "strategy": "standard",
  "method": "elasticnet",
  "timestamp": 1705123456.789,
  "feature_names": ["touch_count", "reversal_probability", "proximity_atr", "recency", "volume_at_touch"]
}
```

**Loading**: Automatically loaded when `SRScorer` is initialized (if file exists).

## Fallback Behavior

If learned weights are **not available** (training never run, file missing, or ML disabled):
- ✅ Bot uses static weights from `config/config.py`
- ✅ Bot continues to work normally
- ✅ No errors or failures
- ✅ ML is optional enhancement, not required

## Example: Real Impact

**Scenario**: Finding the best resistance level for a SHORT trade

**Static Weights (Touch = 50%, Reversal Prob = 20%):**
1. Level at $91,000: 15 touches, 65% reversal_prob → **Score: 76%** ✅ (Wins)
2. Level at $91,500: 6 touches, 92% reversal_prob → Score: 58%

**Learned Weights (Touch = 35%, Reversal Prob = 35% - if ML found this):**
1. Level at $91,000: 15 touches, 65% reversal_prob → Score: 68%
2. Level at $91,500: 6 touches, 92% reversal_prob → **Score: 74%** ✅ (Wins)

**Result**: With learned weights, bot selects the level with **better actual reversal probability** (92% vs 65%), leading to better trades.

## Summary

**What ML Learns**: Optimal weights for combining S/R scoring factors (touch, reversal_probability, proximity, recency, volume) to maximize reversal magnitude prediction.

**How We Use It**: Learned weights automatically replace static weights in SR scoring, improving the accuracy of S/R level strength predictions and leading to better trading decisions.

**Impact**: Better S/R level selection → Better entry points → Higher win rate → Increased profitability.
