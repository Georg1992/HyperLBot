# Prediction Accuracy & Confidence Calibration - Fundamental Architecture Proposal

## Current Problems

1. **Hardcoded Signal Probabilities**: RSI < 30 = 0.75 probability (assumption, not data-driven)
2. **Hardcoded Signal Confidences**: RSI oversold = 0.85 confidence (arbitrary)
3. **Equal Weighting**: Bayesian fusion averages signal confidences (no performance weighting)
4. **No Calibration**: Confidence % may not match actual win rates
5. **No Outcome Tracking**: No validation loop to improve weights
6. **Static Weights**: DirectionRecognizer uses fixed weights (RSI 35%, S/R 35%, etc.)

## Proposed Solution: Multi-Layer Calibration System

### Layer 1: Signal Performance Database

**Track historical performance of each signal:**

```python
class SignalPerformanceTracker:
    """
    Tracks actual win rates for each signal type/value combination
    """
    
    # Store: signal_name -> {signal_value: {wins, losses, win_rate}}
    # Example:
    # "RSI" -> {30: {wins: 45, losses: 15, win_rate: 0.75}}
    # "RSI" -> {40: {wins: 120, losses: 80, win_rate: 0.60}}
    
    def record_outcome(self, signal_name: str, signal_value: Any, 
                      prediction_confidence: float, actual_outcome: bool):
        """Record whether prediction was correct"""
        
    def get_actual_probability(self, signal_name: str, signal_value: Any) -> float:
        """Return actual win rate for this signal value"""
        # Use historical win rate, not hardcoded probability
```

### Layer 2: Confidence Calibration System

**Ensure confidence % matches actual win rates:**

```python
class ConfidenceCalibrator:
    """
    Calibrates confidence scores to match actual win rates
    Uses calibration curves (Platt scaling / isotonic regression)
    """
    
    def calibrate(self, raw_confidence: float, market_context: Dict) -> float:
        """
        Calibrate raw confidence to realistic win probability
        
        If raw confidence = 70% but historical shows 60% win rate,
        calibrate to 60%
        """
        
    def update_calibration_curve(self, predictions: List[Prediction], 
                                outcomes: List[bool]):
        """Update calibration curve based on actual outcomes"""
```

### Layer 3: Performance-Based Signal Weights

**Weight signals by their predictive power, not hardcoded values:**

```python
class AdaptiveSignalWeighter:
    """
    Dynamically weight signals based on:
    1. Historical win rate when signal fires
    2. Information gain (signal reduces uncertainty)
    3. Market regime (different signals work in different conditions)
    """
    
    def calculate_signal_weight(self, signal: Signal, market_context: Dict) -> float:
        """
        Calculate weight based on:
        - Historical win rate when this signal fires
        - Current market regime (trending vs ranging)
        - Signal strength (how extreme is the value)
        - Recency (recent performance matters more)
        """
        
    def update_weights(self, signal_outcomes: Dict[str, List[bool]]):
        """Update weights based on recent performance"""
```

### Layer 4: Market Regime Detection

**Different signals work better in different market conditions:**

```python
class MarketRegimeClassifier:
    """
    Classify current market regime and adjust signal weights accordingly
    """
    
    REGIMES = {
        "STRONG_TREND": {...},  # Trend signals more valuable
        "RANGING": {...},        # RSI/SR signals more valuable  
        "HIGH_VOLATILITY": {...}, # Risk management signals more valuable
        "LOW_VOLATILITY": {...},  # Mean reversion signals more valuable
    }
    
    def get_regime_weights(self, regime: str) -> Dict[str, float]:
        """Get optimal signal weights for this regime"""
```

### Layer 5: Outcome Validation Loop

**Track predictions → outcomes → improve system:**

```python
class PredictionOutcomeValidator:
    """
    Track every prediction and its outcome, then use for improvement
    """
    
    def record_prediction(self, prediction: Prediction, market_data: Dict):
        """Store prediction with all signal values"""
        
    def record_outcome(self, prediction_id: str, actual_outcome: bool, 
                      actual_pnl: float):
        """Record whether prediction was correct"""
        
    def generate_performance_report(self) -> Dict:
        """
        Report:
        - Win rate by confidence bucket (e.g., 60-65% confidence -> actual win rate?)
        - Signal performance rankings
        - Best/worst performing signal combinations
        - Calibration curve accuracy
        """
```

## Implementation Strategy

### Phase 1: Signal Performance Tracking (Week 1)

1. Add `SignalPerformanceTracker` to record signal outcomes
2. Modify Bayesian fusion to look up actual probabilities from tracker
3. Start collecting historical data

### Phase 2: Confidence Calibration (Week 2)

1. Add `ConfidenceCalibrator` using Platt scaling
2. Track predictions → outcomes to build calibration curve
3. Apply calibration before using confidence for execution

### Phase 3: Adaptive Weighting (Week 3)

1. Replace hardcoded signal weights with performance-based weights
2. Implement `AdaptiveSignalWeighter`
3. Update weights based on rolling window of recent performance

### Phase 4: Market Regime Awareness (Week 4)

1. Add `MarketRegimeClassifier`
2. Adjust signal weights based on detected regime
3. Track regime-specific performance

### Phase 5: Continuous Improvement (Ongoing)

1. `PredictionOutcomeValidator` continuously tracks and improves
2. Automated weight optimization based on performance
3. Regular recalibration of confidence curves

## Expected Improvements

1. **Realistic Confidence**: 60% confidence = 60% actual win rate (calibrated)
2. **Data-Driven Probabilities**: Signal probabilities from historical data, not assumptions
3. **Adaptive Weights**: Signals that perform better get higher weights automatically
4. **Regime Awareness**: Different strategies for different market conditions
5. **Continuous Learning**: System improves with every trade outcome

## Key Metrics to Track

1. **Calibration Accuracy**: How well does confidence match win rate?
2. **Signal Information Gain**: Which signals actually reduce uncertainty?
3. **Regime-Specific Performance**: Which signals work in which regimes?
4. **Signal Interaction Effects**: Do certain signal combinations work better?
5. **Confidence Distribution**: Are we overconfident or underconfident?

## Technical Details

### Bayesian Fusion Enhancement

**Current**: 
- Signal confidence = hardcoded (0.85 for RSI oversold)
- Overall confidence = average of signal confidences

**Proposed**:
- Signal confidence = performance-based (e.g., RSI < 30 has 75% win rate → confidence = 0.75)
- Overall confidence = weighted average (weights from performance)
- Apply calibration curve before returning final confidence

### Signal Probability Calculation

**Current**:
```python
if rsi < 30:
    probability = 0.75  # Hardcoded
```

**Proposed**:
```python
if rsi < 30:
    # Look up historical win rate when RSI < 30
    probability = signal_tracker.get_actual_probability("RSI", 30)
    # Returns 0.73 if historically RSI < 30 → 73% win rate
```

### Confidence Calibration Example

**Before Calibration**:
- Raw confidence: 70%
- Actual win rate at 70% confidence: 62% (overconfident)

**After Calibration**:
- Calibrated confidence: 62% (matches actual win rate)
- Trading decision uses 62%, not 70%

## Validation Metrics

1. **Brier Score**: Measures probability forecast accuracy
2. **Calibration Plot**: Confidence vs actual win rate (should be diagonal)
3. **Information Gain**: How much does each signal improve predictions?
4. **Sharpe Ratio**: Risk-adjusted returns improvement
5. **Win Rate by Confidence Bucket**: Should match confidence value

