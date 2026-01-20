# Execution Engines Architecture

**Two Sides of One Coin: Predictions vs Reactions**

---

## Overview

The bot has **two complementary execution engines** that work in parallel:

### 1. **PredictionEngine** (Strategic/Planned)
- **When**: Analyzes market structure and **predicts** future setups
- **Order Type**: LIMIT orders at S/R levels
- **Entry**: Waits for price to reach strategic levels
- **Use Case**: "I see a LONG setup at $93,000 support"

### 2. **ReactiveEngine** (Tactical/Opportunistic)
- **When**: Detects momentum breakouts **happening now**
- **Order Type**: MARKET orders immediately
- **Entry**: Executes at current price instantly
- **Use Case**: "Price is breaking $94,000 resistance NOW"

---

## Unified Architecture

Both engines follow **identical structure** for consistency:

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED POSITION SIZER                   │
│                   (position_sizer.py)                       │
│                                                             │
│  Shared Logic:                                              │
│  - Calculate R:R multiplier (0.5x - 1.5x)                   │
│  - Get balance from simulator                               │
│  - Apply strategy position_size%                            │
│  - Scale by R:R (better R:R → bigger size)                  │
│  - Convert to BTC                                           │
└─────────────────────────────────────────────────────────────┘
               ↑                           ↑
               │                           │
   ┌───────────┴────────┐      ┌──────────┴──────────┐
   │  PredictionEngine  │      │  ReactiveEngine     │
   │  (Strategic)       │      │  (Tactical)         │
   └────────────────────┘      └─────────────────────┘
```

---

## Structural Comparison

| Aspect | PredictionEngine | ReactiveEngine |
|--------|------------------|----------------|
| **Signal Type** | `TradingPrediction` | `MomentumSignal` |
| **Signal Fields** | direction, entry_price, stop_loss, take_profit, confidence, reasoning, strategy, timestamp, **risk_reward_ratio** | direction, entry_price, stop_loss, take_profit, confidence, reasoning, detected_at, breakout_level, expected_move_pct, **risk_reward_ratio** |
| **Entry Method** | `generate_prediction()` | `process_market_data()` → `execute_momentum_trade()` |
| **Position Sizing** | `PositionSizer.calculate_position_size()` | `PositionSizer.calculate_position_size()` |
| **Order Placement** | (Future: LIMIT order at S/R level) | `hyperliquid_simulator.place_order()` (MARKET) |
| **Cooldown** | Per-strategy prediction cooldown | Per-level breakout cooldown |

---

## Position Sizing Flow (Identical for Both)

Both engines follow this exact flow:

```python
# 1. Generate signal/prediction with risk_reward_ratio
signal = engine.generate_signal(...)  # Contains R:R

# 2. Get strategy configuration
strategy_config = TradingConfig.STRATEGY_CONFIGS[strategy]
base_position_size_pct = strategy_config["position_size"]  # e.g., 0.20 (20%)
leverage = strategy_config["max_leverage"]  # e.g., 40

# 3. Get balance
balance = PositionSizer.get_balance_from_simulator()  # e.g., $10,000

# 4. Calculate position size (SHARED LOGIC)
position_sizing = PositionSizer.calculate_position_size(
    balance=balance,
    base_position_size_pct=base_position_size_pct,
    risk_reward_ratio=signal.risk_reward_ratio,  # Dynamic scaling
    leverage=leverage,
    entry_price=signal.entry_price
)

# 5. Extract results
position_size_btc = position_sizing["position_size_btc"]  # e.g., 1.075 BTC
rr_multiplier = position_sizing["rr_multiplier"]  # e.g., 1.25x
adjusted_position_size_pct = position_sizing["adjusted_position_size_pct"]  # e.g., 0.25 (25%)

# 6. Place order
place_order(size=position_size_btc, ...)
```

---

## Position Sizing Formula (Unified)

```python
# Step 1: Get R:R multiplier based on achieved R:R
rr_multiplier = PositionSizer.calculate_rr_multiplier(risk_reward_ratio)
# R:R 1.0 → 0.7x (trade smaller)
# R:R 1.5 → 1.0x (trade normal)
# R:R 3.0 → 1.3x (trade bigger)

# Step 2: Adjust position size
adjusted_position_size_pct = base_position_size_pct * rr_multiplier
# 20% × 1.3x = 26%

# Step 3: Calculate position value (with leverage)
position_value_usd = balance * adjusted_position_size_pct * leverage
# $10,000 × 26% × 40x = $104,000

# Step 4: Convert to BTC
position_size_btc = position_value_usd / entry_price
# $104,000 / $93,000 = 1.118 BTC
```

---

## Why This Design? (SRP Compliance)

### ❌ **Before (Violated SRP)**:
- Position sizing logic **duplicated** in both engines
- Different implementations → inconsistent behavior
- Hard to maintain (change in 2 places)

### ✅ **After (Follows SRP)**:
- `PositionSizer`: **Single Responsibility** = Calculate position sizes
- `PredictionEngine`: **Single Responsibility** = Generate strategic predictions
- `ReactiveEngine`: **Single Responsibility** = Execute tactical breakouts
- **Both engines delegate** position sizing to `PositionSizer`

---

## Key Principle: "Two Sides of One Coin"

**Predictions** and **Reactions** are complementary strategies, not competing ones:

- **Predictions**: "Wait for the perfect setup at the right level"
  - Pro: Better entry price, higher R:R
  - Con: Might miss the move if price doesn't retrace

- **Reactions**: "Catch the momentum before it's gone"
  - Pro: Don't miss explosive moves
  - Con: Worse entry price (market order slippage)

**Both use identical position sizing** to ensure consistency:
- Same balance management
- Same R:R-based scaling
- Same leverage application
- Same risk management

---

## Usage Examples

### Example 1: Strategic Entry (PredictionEngine)
```
📊 Analysis: Strong support at $93,000
🎯 Prediction: LONG @ $93,000 (IF price reaches it)
💰 Position sizing: R:R 2.5 → 1.0x → 0.20 BTC
📝 Order: LIMIT BUY 0.20 BTC @ $93,000
```

### Example 2: Tactical Entry (ReactiveEngine)
```
⚡ Alert: Price breaking $94,000 resistance NOW!
🎯 Signal: LONG @ $94,050 (current price)
💰 Position sizing: R:R 1.8 → 0.95x → 0.19 BTC
📝 Order: MARKET BUY 0.19 BTC @ MARKET
```

---

## File Structure

```
core/execution/
├── position_sizer.py         # 💰 Shared position sizing logic
├── prediction_engine.py       # 🎯 Strategic predictions (LIMIT orders)
├── reactive_engine.py         # ⚡ Tactical reactions (MARKET orders)
└── momentum_detector.py       # 📊 Detects breakout momentum
```

---

## Future Enhancement: Order Execution Layer

Currently:
- **ReactiveEngine**: Calls `hyperliquid_simulator.place_order()` directly
- **PredictionEngine**: Returns `TradingPrediction` (no order placement yet)

Future (Unified Order Executor):
```
Both Engines → TradingSignal → OrderExecutor → hyperliquid_simulator
```

This would further unify the architecture by separating:
- **Signal Generation** (Prediction/Reaction engines)
- **Position Sizing** (PositionSizer)
- **Order Execution** (OrderExecutor)

---

## Summary

✅ **Unified position sizing** via `PositionSizer`  
✅ **Consistent structure** (both generate signals with R:R)  
✅ **SRP compliance** (clear separation of concerns)  
✅ **Two complementary strategies** (strategic + tactical)  
✅ **Identical risk management** (same sizing formula)  

**Result**: Predictions and Reactions work as "two sides of one coin" with shared, maintainable logic.
