# Reactive Engine Implementation Summary

## Overview

The reactive engine has been fully implemented to detect unexpected moves and call trade execution (without actual execution logic). It works in parallel with the prediction engine without conflicts.

## Key Features

### 1. Timely Detection
- **Check Interval:** 2 seconds (reduced from 5 seconds for faster reaction)
- **High Volatility Detection:** Lower confidence threshold (60% vs 65%) for HIGH/EXTREME volatility
- **Real-time Monitoring:** Continuously monitors market data for momentum breakouts

### 2. Trade Execution Call (No Execution Logic)
- **API Integration:** Calls `hyperliquid_simulator.place_order()` when momentum detected
- **Order Type:** MARKET orders (immediate execution)
- **No Conflicts:** Works alongside prediction engine (LIMIT orders)
- **Position Tracking:** Prevents duplicate positions in same direction

### 3. Conflict Prevention

**Between Reactive Engine and Prediction Engine:**
- **Reactive Engine:** Uses MARKET orders for unexpected moves
- **Prediction Engine:** Uses LIMIT orders at S/R levels
- **Position Check:** Prevents duplicate positions in same direction
- **Pending Order Check:** Prevents duplicate calls within 30 seconds

**Example:**
- Prediction engine: LONG limit order at $90,500 (support level)
- Reactive engine: Can still detect LONG breakout and call market order
- But: If position already exists, reactive engine skips (no conflict)

### 4. High Volatility Strategy Detection

**Timely Detection:**
- Checks every 2 seconds (vs 5 seconds for normal)
- Lower confidence threshold for HIGH/EXTREME volatility (60% vs 65%)
- Prioritizes `high_volatility` strategy config for unexpected moves

**Detection Signals:**
1. Price near strong S/R (0.3-1% away)
2. Orderbook pressure building (STRONG_BUY/STRONG_SELL)
3. Volume surge (above 75th percentile)
4. Price acceleration (momentum)
5. RSI momentum alignment
6. High volatility (EXTREME category)

## Implementation Details

### Reactive Engine Flow

```
Every 2 seconds:
  ↓
Get unified market data
  ↓
Detect momentum (6-factor scoring)
  ↓
Check confidence threshold (60-65% depending on volatility)
  ↓
Check for existing positions (prevent conflicts)
  ↓
Check for pending orders (prevent duplicates)
  ↓
Call trade execution API (hyperliquid_simulator.place_order)
  ↓
Track pending order
  ↓
Return execution call result
```

### Trade Execution Call

**Method:** `_execute_momentum_trade()`

**Parameters:**
- `order_type`: "MARKET"
- `side`: "BUY" or "SELL"
- `size`: Position size (calculated from strategy config)
- `symbol`: "BTC"
- `price`: None (market order)
- `leverage`: From strategy config (default 20x)
- `stop_loss`: Calculated (2×ATR or max 1%)
- `take_profit`: Calculated (1.5:1 R:R minimum)
- `metadata`: Signal details (confidence, reasoning, etc.)

**API Call:**
```python
hyperliquid_simulator.place_order(
    order_type="MARKET",
    side=order_side,
    size=position_size_btc,
    symbol="BTC",
    price=None,
    leverage=leverage,
    stop_loss=signal.stop_loss,
    take_profit=signal.take_profit,
    metadata=order_metadata
)
```

**Note:** This is the execution CALL, not actual execution. The simulator handles the call, but actual trade execution logic is not implemented yet (as requested).

### Conflict Prevention Logic

1. **Position Check:**
   ```python
   if self._has_active_position(signal.direction):
       return None  # Skip - position exists
   ```

2. **Pending Order Check:**
   ```python
   if self._has_pending_order(signal.direction):
       return None  # Skip - order already called
   ```

3. **Cooldown:**
   - 30 seconds between pending orders in same direction
   - Prevents duplicate calls

## Integration Points

### Session Orchestrator
- Reactive engine initialized with API manager
- Called every loop iteration (after unified data preparation)
- Runs in parallel with prediction engine

### API Manager
- Provides access to Hyperliquid simulator
- Simulator handles order execution calls
- No actual execution logic (as requested)

## Status

✅ **Detection:** Complete and timely (2-second checks)
✅ **Execution Call:** Complete (calls API, no execution logic)
✅ **Conflict Prevention:** Complete (no conflicts with prediction engine)
✅ **High Volatility:** Complete (lower threshold, faster reaction)
✅ **Integration:** Complete (integrated into main loop)

## Next Steps (When Ready)

1. **Trade Execution Logic:** Implement actual order execution in trade executor
2. **Position Management:** Track positions, handle stop loss/take profit
3. **Risk Management:** Add position sizing, leverage limits, etc.
4. **Testing:** Test during volatile periods to verify detection and calls

The system is ready to detect unexpected moves and call trade execution!