# Codebase Audit: SRP, Fallbacks, Hardcoded Values
**Date:** 2026-01-23

## 🔴 CRITICAL: FALLBACK LOGIC VIOLATIONS (NO FALLBACKS POLICY)

### 1. `core/calculations/pressure_data_provider.py:141-145`
**Issue:** Fallback logic violates NO FALLBACKS policy
```python
# Fallback to depth_5 if depth_10 unavailable
if total_depth_10 == 0.0:
    total_depth_10 = depth_metrics.get("total_depth_5", 0.0)
    bid_depth_10 = depth_metrics.get("bid_depth_5", 0.0)
    ask_depth_10 = depth_metrics.get("ask_depth_5", 0.0)
```
**Fix:** Should raise `ValueError` if depth_10 is unavailable

### 2. `core/calculations/pressure_calculator.py:125-131`
**Issue:** Fallback logic violates NO FALLBACKS policy
```python
# Fallback to depth_5 if depth_10 unavailable
if ("total_depth_10" not in depth_metrics or depth_metrics["total_depth_10"] == 0.0):
    if ("total_depth_5" not in depth_metrics or depth_metrics["total_depth_5"] == 0.0):
        raise ValueError("No orderbook depth available for pressure calculation - NO FALLBACKS")
    # Use depth_5 as fallback
    depth_metrics["total_depth_10"] = depth_metrics["total_depth_5"]
```
**Fix:** Should raise immediately if depth_10 is unavailable (no fallback to depth_5)

---

## 🟡 HARDCODED VALUES (Should be in Config/Constants)

### Support/Resistance Calculator
1. **`core/calculations/support_resistance_calculator.py:96`**
   - `atr_tolerance_multiplier = 0.25` → Should be in `TradingConfig.ATR_MULTIPLIERS`

2. **`core/calculations/support_resistance_calculator.py:402`**
   - `expansion_factor = 3.0` → Should be in `TradingConfig` (e.g., `LIQUIDATION_EXPANSION_FACTOR`)

3. **`core/calculations/support_resistance_calculator.py:237,249,269,281,301,313`**
   - Strength values: `80.0`, `90.0`, `100.0` → Should be in `TradingConfig` or `MagicNumbers`

### Pressure Calculator
4. **`core/calculations/pressure_calculator.py:57`**
   - `self._ema_alpha = 0.4` → Should be in `TradingConfig` (e.g., `PRESSURE_EMA_ALPHA`)

### Session Orchestrator
5. **`core/services/session_orchestrator.py:242`**
   - `310` (5 minutes 10 seconds) → Should be in `TradingConstants` (e.g., `CANDLE_UPDATE_TIMEOUT`)

6. **`core/services/session_orchestrator.py:329`**
   - `0.02` (default 2%) → Should use `TradingConfig` strategy config

7. **`core/services/session_orchestrator.py:423`**
   - `0.001` (0.1%) → Should be in `TradingConfig` (e.g., `PRICE_CHANGE_THRESHOLD`)

8. **`core/services/session_orchestrator.py:544`**
   - `0.1` (100ms delay) → Should be in `TradingConstants` (e.g., `ANALYSIS_COMPLETION_DELAY`)

### SR Data Provider
9. **`core/calculations/sr_data_provider.py:338,342`**
   - `0.0005` (0.05% of price), `0.1` (absolute minimum) → Should be in `TradingConfig` (e.g., `ATR_MIN_PCT`, `ATR_ABSOLUTE_MIN`)

### Market Data Service
10. **`core/services/market_data_service.py:34,38`**
    - `0.1` (100ms), `0.5` (500ms) → Should be in `TradingConstants` (e.g., `PRICE_UPDATE_INTERVAL`, `RSI_DASHBOARD_UPDATE_INTERVAL`)

11. **`core/services/market_data_service.py:1244`**
    - `0.1` (RSI change threshold) → Should be in `TradingConfig` (e.g., `RSI_CHANGE_THRESHOLD`)

### Strategy Manager
12. **`core/services/strategy_manager.py:573,576,579`**
    - `0.0001`, `-0.0001`, `0.00005` (funding rate thresholds) → Should be in `TradingConfig` (e.g., `FUNDING_RATE_CHANGE_THRESHOLDS`)

13. **`core/services/strategy_manager.py:601,604,607`**
    - `0.7`, `0.5`, `0.3` (volume trend strength thresholds) → Should be in `TradingConfig` (e.g., `VOLUME_TREND_STRENGTH_THRESHOLDS`)

14. **`core/services/strategy_manager.py:1031,1033`**
    - `0.03` (3%), `0.01` (1%) (volatility thresholds) → Should be in `TradingConfig` (e.g., `VOLATILITY_THRESHOLDS`)

---

## 🟢 SRP VIOLATIONS (Single Responsibility Principle)

### Potential Issues (Need Review)

1. **`core/services/market_data_service.py`**
   - **Responsibility:** Coordinates processed analysis data
   - **Potential Issue:** Also handles price updates, RSI initialization, trend mapping
   - **Recommendation:** Consider splitting into:
     - `MarketDataCoordinator` (coordination only)
     - `PriceUpdateHandler` (price updates)
     - `TrendDataMapper` (trend mapping)

2. **`core/services/session_orchestrator.py`**
   - **Responsibility:** Orchestrates trading session
   - **Potential Issue:** Also handles strategy detection, momentum processing, dashboard updates
   - **Recommendation:** Consider extracting:
     - Strategy detection → `StrategyDetector`
     - Momentum processing → `MomentumProcessor`
     - Dashboard updates → `DashboardUpdater`

3. **`core/calculations/support_resistance_calculator.py`**
   - **Responsibility:** Calculate S/R levels
   - **Status:** ✅ Good - Uses dependency injection, delegates to specialized components
   - **Note:** Well-structured with SRP compliance

---

## 📋 SUMMARY

### Critical Issues: 2
- Fallback logic in pressure calculation (2 locations)

### Hardcoded Values: 14
- Should be moved to `TradingConfig` or `TradingConstants`

### SRP Violations: 2 (Potential)
- `MarketDataService` - multiple responsibilities
- `SessionOrchestrator` - multiple responsibilities

---

## ✅ RECOMMENDATIONS

1. **Immediate:** Remove fallback logic in pressure calculation
2. **High Priority:** Move hardcoded values to config/constants
3. **Medium Priority:** Review SRP violations and consider refactoring
