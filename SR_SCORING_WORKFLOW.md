# SR Scoring System - Complete Workflow

## Overview
The SR (Support/Resistance) scoring system calculates the **reversal probability** (0-100%) for each level. This represents the likelihood that price will reverse at that level.

## Architecture

### 1. **Configuration** (`config/config.py`)
Each strategy has scoring weights that sum to 1.0:
```python
"scoring_weights": {
    "proximity": 0.15,           # How close the level is to current price
    "touch": 0.50,               # How many times price touched this level
    "reversal_probability": 0.20, # Historical reversal rate (calculated from data)
    "recency": 0.10,             # How recent was the last touch
    "volume": 0.05               # Volume at the level
}
```

### 2. **Initialization** (`SRScorer.__init__`)
- Loads weights from config (or learned weights if available)
- Validates weights sum to 1.0
- Sets proximity decay constant (`proximity_decay_k`)

### 3. **Level Detection** (`SRDetector`)
- Detects swing points (peaks/valleys) from candles
- Clusters nearby levels together
- Creates `Level` objects with initial metadata

### 4. **Scoring Process** (`SRScorer.score_levels_enhanced`)

For each level, calculate:

#### Step 1: Calculate Reversal Probability (PRIMARY)
```python
reversal_probability = calculate_reversal_probability(level, current_price, atr_5m, candles_data)
```
- Analyzes historical touches: did price reverse or break through?
- Uses Bayesian shrinkage for small samples
- Applies small trend adjustment only
- **Note**: Proximity and recency are NOT applied here - they're separate components in the weighted sum
- Returns 0-100% probability

#### Step 2: Calculate Component Scores (0-100 each)
- **MTF Score**: Multi-timeframe confirmation (currently 0% - disabled)
- **Proximity Score**: Distance from current price (exponential decay)
- **Touch Score**: Number of touches (logarithmic scaling)
- **Volume Score**: Volume at level (percentile-based)
- **Recency Score**: Time since last touch (exponential decay)

#### Step 3: Weighted Combination
```python
final_score = (
    (mtf_score / 100.0) * weights['mtf'] +
    (proximity_score / 100.0) * weights['proximity'] +
    (touch_score / 100.0) * weights['touch'] +
    (reversal_probability / 100.0) * weights['reversal_probability'] +
    (volume_score / 100.0) * weights['volume'] +
    (recency_score / 100.0) * weights['recency']
) * 100.0
```

Result: **Final score = 0-100% reversal probability**

## Data Flow

```
1. Config → SRScorer.__init__()
   └─> Load weights from config
   └─> Validate sum = 1.0

2. Candles → SRDetector.detect_swing_points()
   └─> Find peaks/valleys
   └─> Cluster nearby levels
   └─> Create Level objects

3. Levels → SRScorer.score_levels_enhanced()
   └─> For each level:
       ├─> calculate_reversal_probability() → historical analysis
       ├─> _calculate_proximity_score() → distance decay
       ├─> _calculate_touch_score() → touch count
       ├─> _calculate_volume_score() → volume percentile
       ├─> _calculate_recency_score() → time decay
       └─> _calculate_weighted_score() → combine all factors

4. Scored Levels → SupportResistanceCalculator
   └─> Sort by score (highest first)
   └─> Select top N levels per strategy
   └─> Return to dashboard
```

## Key Points

1. **Reversal Probability is Primary**: It's calculated from actual historical data (reversals vs breakouts)
   - Analyzes past touches: did price reverse or break through?
   - Uses Bayesian shrinkage for small samples
   - Small trend adjustment applied (±5%)

2. **Weights are Strategy-Specific**: Different strategies prioritize different factors:
   - Scalping: favors proximity (closer levels)
   - Swing trading: favors touch count (stronger levels)
   - Standard: balanced approach

3. **All Weights Sum to 1.0**: This ensures the final score is a proper weighted average

4. **Component Scores are 0-100**: Each factor is normalized to 0-100 before weighting

5. **No Double Application**: 
   - Proximity and recency are calculated ONCE as separate components
   - They are NOT applied to reversal_probability (that would be double-counting)
   - All factors combined via weighted sum: `score = Σ(component_i * weight_i)`

6. **Final Score = Reversal Probability**: The output represents the probability (0-100%) that price will reverse at this level

## Example

For a level with:
- 5 touches
- 2% away from current price
- 60% historical reversal rate
- Last touched 6 hours ago
- High volume

Using "standard" weights (proximity=0.15, touch=0.50, reversal_prob=0.20, recency=0.10, volume=0.05):

```
reversal_probability = 60% (from historical data)
proximity_score = 85 (close to price)
touch_score = 75 (5 touches)
recency_score = 89 (recent)
volume_score = 80 (high volume)

final_score = (0.00 * 0.00) + (85 * 0.15) + (75 * 0.50) + (60 * 0.20) + (80 * 0.05) + (89 * 0.10)
            = 0 + 12.75 + 37.5 + 12.0 + 4.0 + 8.9
            = 75.15% reversal probability
```
