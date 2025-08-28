# Variability Threshold Adjustment Guide

## Overview

This guide explains the variability threshold adjustment system that optimizes trading decisions based on market volatility and price variability patterns.

## 🎯 What is Variability Analysis?

Variability analysis measures the consistency and predictability of price movements to determine optimal trading conditions. It helps the bot avoid trading during chaotic or unpredictable market periods.

## 📊 Key Concepts

### **Variability Score**
- **Range**: 0.0 to 1.0 (0 = very predictable, 1 = very chaotic)
- **Calculation**: Based on price movement consistency over time
- **Update Frequency**: Every price update (real-time)

### **Threshold Levels**
- **LOW VARIABILITY (0.0-0.3)**: Very predictable market conditions
- **MEDIUM VARIABILITY (0.3-0.7)**: Normal market conditions
- **HIGH VARIABILITY (0.7-1.0)**: Chaotic or unpredictable conditions

### **Trading Decisions**
- **LOW VARIABILITY**: Optimal for trading, lower thresholds
- **MEDIUM VARIABILITY**: Standard trading conditions
- **HIGH VARIABILITY**: Reduced trading, higher thresholds

## 🔧 Configuration

### **Default Thresholds**

```python
VARIABILITY_THRESHOLDS = {
    "low_volatility": {
        "min_confidence": 0.5,
        "min_win_probability": 0.5,
        "risk_per_trade": 0.025,
        "max_leverage": 40
    },
    "medium_volatility": {
        "min_confidence": 0.6,
        "min_win_probability": 0.55,
        "risk_per_trade": 0.02,
        "max_leverage": 30
    },
    "high_volatility": {
        "min_confidence": 0.7,
        "min_win_probability": 0.6,
        "risk_per_trade": 0.015,
        "max_leverage": 20
    }
}
```

### **Adjustment Factors**

#### **Confidence Threshold**
- **Low Variability**: -10% (easier to trade)
- **Medium Variability**: No change (standard)
- **High Variability**: +10% (harder to trade)

#### **Win Probability Threshold**
- **Low Variability**: -5% (easier to trade)
- **Medium Variability**: No change (standard)
- **High Variability**: +5% (harder to trade)

#### **Risk Per Trade**
- **Low Variability**: +25% (can take more risk)
- **Medium Variability**: No change (standard)
- **High Variability**: -25% (reduce risk)

#### **Maximum Leverage**
- **Low Variability**: +33% (can use higher leverage)
- **Medium Variability**: No change (standard)
- **High Variability**: -33% (reduce leverage)

## 🚀 Usage Examples

### **Basic Threshold Adjustment**

```python
from core.analysis.historical.market_volatility_analyzer import VariabilityAnalyzer

# Initialize analyzer
analyzer = VariabilityAnalyzer(lookback_periods=100)

# Add price data
analyzer.add_price_data(current_price, volume=current_volume)

# Get variability score
variability_score = analyzer.get_variability_score()

# Adjust thresholds based on variability
adjusted_thresholds = analyzer.adjust_thresholds(base_thresholds, variability_score)

print(f"Variability Score: {variability_score:.2f}")
print(f"Adjusted Confidence: {adjusted_thresholds['min_confidence']:.2f}")
```

### **Advanced Usage with Trading Bot**

```python
def should_trade_based_on_variability(self, base_threshold: float) -> Dict[str, Any]:
    """Determine if should trade based on variability analysis"""
    
    # Get current variability score
    variability_score = self.variability_analyzer.get_variability_score()
    
    # Determine variability category
    if variability_score < 0.3:
        category = "low_volatility"
        adjustment_factor = 0.9  # Easier to trade
    elif variability_score < 0.7:
        category = "medium_volatility"
        adjustment_factor = 1.0  # Standard
    else:
        category = "high_volatility"
        adjustment_factor = 1.1  # Harder to trade
    
    # Adjust threshold
    adjusted_threshold = base_threshold * adjustment_factor
    
    # Get optimal trading parameters
    optimal_params = self.variability_analyzer.get_optimal_trading_params(variability_score)
    
    return {
        "should_trade": True,  # Always true if called
        "variability_score": variability_score,
        "variability_category": category,
        "adjusted_threshold": adjusted_threshold,
        "optimal_trading_params": optimal_params,
        "reason": f"Variability analysis: {category} conditions"
    }
```

## 📈 Performance Impact

### **Before Variability Adjustment**
- **Trade Frequency**: High (trades in all conditions)
- **Success Rate**: Variable (depends on market conditions)
- **Risk Management**: Static (same risk in all conditions)
- **Performance**: Inconsistent

### **After Variability Adjustment**
- **Trade Frequency**: Adaptive (fewer trades in chaotic conditions)
- **Success Rate**: Improved (better trade selection)
- **Risk Management**: Dynamic (adjusts risk based on conditions)
- **Performance**: More consistent

## 🔄 Real-Time Adjustment

### **Continuous Monitoring**
```python
def update_variability_analysis(self, current_price: float, volume: float = None):
    """Update variability analysis with new price data"""
    
    # Add new price data
    self.variability_analyzer.add_price_data(current_price, volume=volume)
    
    # Get updated score
    current_score = self.variability_analyzer.get_variability_score()
    
    # Log significant changes
    if abs(current_score - self.last_variability_score) > 0.1:
        logger.info(f"📊 Variability changed: {self.last_variability_score:.2f} → {current_score:.2f}")
        self.last_variability_score = current_score
    
    # Update trading parameters if needed
    if self.should_update_trading_params(current_score):
        self.update_trading_parameters(current_score)
```

### **Adaptive Trading Parameters**
```python
def get_optimal_trading_params(self, variability_score: float) -> Dict[str, Any]:
    """Get optimal trading parameters based on variability"""
    
    if variability_score < 0.3:
        # Low variability - can be more aggressive
        return {
            "position_size": 0.0005,  # Larger positions
            "leverage": 40,           # Higher leverage
            "stop_loss": 0.15,        # Tighter stops
            "profit_target": 0.3      # Smaller targets
        }
    elif variability_score < 0.7:
        # Medium variability - standard parameters
        return {
            "position_size": 0.00035, # Standard positions
            "leverage": 30,           # Standard leverage
            "stop_loss": 0.2,         # Standard stops
            "profit_target": 0.4      # Standard targets
        }
    else:
        # High variability - more conservative
        return {
            "position_size": 0.0002,  # Smaller positions
            "leverage": 20,           # Lower leverage
            "stop_loss": 0.25,        # Wider stops
            "profit_target": 0.5      # Larger targets
        }
```

## 📊 Monitoring and Optimization

### **Performance Tracking**
```python
def track_variability_performance(self):
    """Track performance by variability category"""
    
    performance_data = {
        "low_volatility": {"trades": 0, "wins": 0, "win_rate": 0.0},
        "medium_volatility": {"trades": 0, "wins": 0, "win_rate": 0.0},
        "high_volatility": {"trades": 0, "wins": 0, "win_rate": 0.0}
    }
    
    # Analyze trade history
    for trade in self.trade_history:
        category = self.get_variability_category(trade["variability_score"])
        performance_data[category]["trades"] += 1
        
        if trade["was_profitable"]:
            performance_data[category]["wins"] += 1
    
    # Calculate win rates
    for category in performance_data:
        trades = performance_data[category]["trades"]
        wins = performance_data[category]["wins"]
        if trades > 0:
            performance_data[category]["win_rate"] = wins / trades
    
    return performance_data
```

### **Threshold Optimization**
```python
def optimize_thresholds(self, performance_data: Dict):
    """Optimize thresholds based on performance data"""
    
    for category, data in performance_data.items():
        win_rate = data["win_rate"]
        trades = data["trades"]
        
        if trades >= 10:  # Minimum sample size
            if win_rate < 0.5:
                # Poor performance - make thresholds stricter
                self.adjust_thresholds_stricter(category)
            elif win_rate > 0.7:
                # Good performance - can relax thresholds
                self.adjust_thresholds_relaxed(category)
```

## 🎯 Best Practices

### **1. Gradual Adjustment**
- Don't make sudden large changes to thresholds
- Use small incremental adjustments
- Monitor impact before making further changes

### **2. Performance Monitoring**
- Track performance by variability category
- Adjust thresholds based on actual results
- Maintain minimum sample sizes for statistical significance

### **3. Market Condition Awareness**
- Consider broader market conditions
- Don't trade against strong trends
- Adapt to changing market regimes

### **4. Risk Management**
- Always maintain proper risk controls
- Don't increase risk too much in low variability
- Be extra cautious in high variability conditions

## 🔧 Troubleshooting

### **Common Issues**

#### **Too Many Trades in High Variability**
```python
# Increase thresholds for high variability
VARIABILITY_THRESHOLDS["high_volatility"]["min_confidence"] = 0.8
VARIABILITY_THRESHOLDS["high_volatility"]["min_win_probability"] = 0.7
```

#### **Too Few Trades in Low Variability**
```python
# Decrease thresholds for low variability
VARIABILITY_THRESHOLDS["low_volatility"]["min_confidence"] = 0.4
VARIABILITY_THRESHOLDS["low_volatility"]["min_win_probability"] = 0.45
```

#### **Poor Performance in Medium Variability**
```python
# Adjust medium volatility parameters
VARIABILITY_THRESHOLDS["medium_volatility"]["risk_per_trade"] = 0.015
VARIABILITY_THRESHOLDS["medium_volatility"]["max_leverage"] = 25
```

### **Debugging Tools**
```python
def debug_variability_analysis(self):
    """Debug variability analysis"""
    
    print(f"Current Variability Score: {self.variability_analyzer.get_variability_score():.3f}")
    print(f"Price History Length: {len(self.variability_analyzer.price_history)}")
    print(f"Volume History Length: {len(self.variability_analyzer.volume_history)}")
    print(f"Last 10 Prices: {self.variability_analyzer.price_history[-10:]}")
    print(f"Variability Trend: {self.variability_analyzer.get_variability_trend()}")
```

---

**Note**: Variability threshold adjustment is a powerful tool for optimizing trading performance. Regular monitoring and adjustment based on actual results will help maximize trading success across different market conditions.
