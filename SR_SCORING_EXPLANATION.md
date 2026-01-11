# SR Scoring Components - Why They're Separate

## The Question
Why is `reversal_probability` separate from other components (proximity, touch, volume, recency)?

## Answer: They Measure Different Things

### 1. **touch_score** (0-100)
**What it measures**: How many times price touched the level
- 1 touch = 20 points
- 2 touches = 40 points  
- 3 touches = 60 points
- 4 touches = 80 points
- 5+ touches = 80 + 5*(n-4) points

**Purpose**: Measures SIGNIFICANCE - "Is this level important?"
- More touches = more significant level
- Doesn't care what happened after the touch

### 2. **reversal_probability** (0-100%)
**What it measures**: What happened AFTER each touch
- Analyzes historical touches: did price reverse or break through?
- Calculates: `P(reversal) = reversals / total_touches * 100%`

**Purpose**: Measures EFFECTIVENESS - "Did this level actually work as S/R?"
- A level with 5 touches where all 5 reversed = 100% reversal_probability
- A level with 5 touches where all 5 broke through = 0% reversal_probability
- Same touch count, different effectiveness

### 3. **proximity_score** (0-100)
**What it measures**: How close the level is to current price
- Uses exponential decay: `score = exp(-k * distance_pct)`
- Closer = higher score

**Purpose**: Measures RELEVANCE - "Is this level actionable right now?"

### 4. **recency_score** (0-100)
**What it measures**: How recent was the last touch
- Uses exponential decay: `score = exp(-k * hours_old)`
- More recent = higher score

**Purpose**: Measures ACTIVITY - "Is this level still active?"

### 5. **volume_score** (0-100)
**What it measures**: Volume at the level
- Based on touch activity and volume spikes
- Higher volume = more liquidity

**Purpose**: Measures LIQUIDITY - "Can we trade at this level?"

## Why They're Separate

They measure **different dimensions** of a level:

| Component | Dimension | Question |
|-----------|-----------|----------|
| touch_score | Significance | How important is this level? |
| reversal_probability | Effectiveness | Did it work as S/R? |
| proximity_score | Relevance | Is it actionable now? |
| recency_score | Activity | Is it still active? |
| volume_score | Liquidity | Can we trade it? |

## Example

**Level A**: 5 touches, all reversed, 1% away, touched 2 hours ago
- touch_score = 85 (5 touches = significant)
- reversal_probability = 100% (all reversed = very effective)
- proximity_score = 90 (close = relevant)
- recency_score = 95 (recent = active)
- volume_score = 80 (high activity)

**Level B**: 5 touches, all broke through, 1% away, touched 2 hours ago
- touch_score = 85 (5 touches = significant) ← SAME
- reversal_probability = 0% (all broke through = ineffective) ← DIFFERENT
- proximity_score = 90 (close = relevant) ← SAME
- recency_score = 95 (recent = active) ← SAME
- volume_score = 80 (high activity) ← SAME

**Result**: Level A scores much higher because `reversal_probability` shows it actually works.

## The Weighted Sum

All components are combined:
```
final_score = (
    touch_score * weight_touch +
    reversal_probability * weight_reversal +
    proximity_score * weight_proximity +
    recency_score * weight_recency +
    volume_score * weight_volume
)
```

This allows strategies to prioritize:
- **Scalping**: High weight on proximity (need close levels)
- **Swing trading**: High weight on touch + reversal_probability (need strong, effective levels)
- **Standard**: Balanced weights

## Conclusion

`reversal_probability` is separate because it measures **effectiveness** (did it work?), while `touch_score` measures **significance** (how important is it?). They're complementary, not redundant.
