# Indicator Inventory and Gaps

**Date:** 2026-01-29  
**Scope:** Indicators used in decisions; computed but unused; high-value missing.  
**Constraints:** Direction = momentum-based (no S/R); Entry = locational; Squeeze = timing only; Deterministic, NO FALLBACKS.

---

## 1. Indicators / features currently USED in decisions

### Strategy selection

| Indicator | unified_data path | Source module | Required / optional |
|-----------|-------------------|---------------|---------------------|
| Volatility category | `volatility_category`, `volatility.level` | `volatility_calculator`, `volatility_classifier` | Required |
| Volatility 5m | `volatility_5m` | `volatility_calculator` | Required |
| Trend direction | `trend_direction`, `trend.direction` | `trend_calculator`, `trend_data_mapper` | Required |
| Trend strength, timeframes | `trend.strength`, `trend.detailed_timeframes` | same | Required |
| RSI | `rsi_value`, `rsi` | `rsi_calculator` | Required |
| Volume category | `volume_category`, `volume` | `volume_calculator`, `volume_classifier` | Required |
| Volume trend strength, anomaly | `volume.volume_trend_strength`, `volume.volume_anomaly` | same | Required |
| Support/resistance | `support_resistance` (levels for filter) | `support_resistance_calculator` | Required |
| Orderbook spread, liquidity | `orderbook_analysis.bid_ask_spread`, `orderbook_analysis.liquidity_depth` | `orderbook_analyzer` | Required |
| Pressure | `pressure` | `pressure_calculator` | Required |
| Funding trend, volatility | `funding_analysis.funding_trend`, `funding_analysis.funding_volatility` | `funding_rate_analyzer` | Required (selection waits until ready) |
| Market conditions | `market_conditions.condition`, `market_conditions.risk_level` | `market_conditions_analyzer` | Required |
| Patterns | `patterns.patterns_nested`, `patterns.overall_quality` | `pattern_recognition_engine` | Required |
| Spike intensity | `volatility.spike_intensity` | `volatility_analyzer` | Required (e.g. spike_hunting) |

### Prediction direction

| Indicator | unified_data path | Source module | Required / optional |
|-----------|-------------------|---------------|---------------------|
| RSI | `rsi`, `rsi_value` | `rsi_calculator` | Required |
| Trend | `trend` | `trend_calculator` | Required |
| Pressure | `pressure` | `pressure_calculator` | Required |
| Patterns | `patterns` | `pattern_recognition_engine` | Required |
| Volume | `volume`, `volume_category` | `volume_calculator` | Required |
| Market conditions | `market_conditions` | `market_conditions_analyzer` | Optional (strategy-dependent) |
| Cross-asset | `cross_asset_analysis` | `cross_asset_correlation_analyzer` | Optional (strategy-dependent) |

### Prediction entry / stop–target

| Indicator | unified_data path | Source module | Required / optional |
|-----------|-------------------|---------------|---------------------|
| Support/resistance | `support_resistance` (levels, metadata.atr_5m) | `support_resistance_calculator` | Required |
| ATR 5m | `support_resistance.metadata.atr_5m` | same | Required |
| RSI, trend, pressure, patterns | `rsi`, `trend`, `pressure`, `patterns` | same as direction | Required |
| Volume category | `volume_category` | `volume_calculator` | Required |
| Orderbook | `orderbook_analysis` | `orderbook_analyzer` | Optional (strategy-dependent) |
| Market conditions | `market_conditions` | `market_conditions_analyzer` | Optional (strategy-dependent) |

### ReactiveEngine direction / candidate scoring

| Indicator | unified_data path | Source module | Required / optional |
|-----------|-------------------|---------------|---------------------|
| Orderbook imbalance | `orderbook_analysis.order_imbalance.bias` | `orderbook_analyzer` | Optional (0 if missing) |
| Pressure | `pressure` (net_pressure, direction, strength) | `pressure_calculator` | Optional (0 if missing) |
| Bid-ask spread | `orderbook_analysis.bid_ask_spread.percentage` | `orderbook_analyzer` | Optional |
| Support/resistance | `support_resistance.levels` (level_proximity) | `support_resistance_calculator` | Optional |
| Volatility | `volatility` (volatility_percentage / volatility_5m) | `volatility_calculator` | Optional |
| IV squeeze | `iv_squeeze` (timing boost when squeeze_released) | `iv_squeeze_analyzer` | Optional |
| RSI, trend, volume | `rsi`, `trend`, `volume` | same as above | For feature vector / breakdown |

---

## 2. Indicators computed but NOT used in decision logic

- **Volatility baseline / volatility ratio**  
  Previously produced in `volatility_calculator`; removed. Not consumed elsewhere.

- **`raw_data_access`**  
  Was produced then stripped; dead. Removed.

- **`prediction_data` / `dashboard_ready`**  
  Produced in dashboard path; not read. Removed or unused.

- **Whale activity**  
  Used inside `market_conditions_analyzer` (e.g. whale risk). No separate top-level consumer; effectively part of market_conditions.

- **Consolidation result**  
  Built via `get_consolidation_analysis`; not stored in `unified_data`. Used only for consolidation/breakout detection, not direction or entry.

- **Candlestick pattern names**  
  `patterns_nested.candlestick_patterns` used in pattern scoring. Other nested keys (reversal, continuation, etc.) are used.

---

## 3. High-value missing indicators (ranked)

1. **Short-term trade-flow / aggressor imbalance (buy vs sell)**  
   - **Adds:** Better reaction direction and fill context; ML feature for confidence.  
   - **Where:** Reaction scoring (direction), optional execution-cost. **Not** limit-engine direction.  
   - **unified_data path:** `unified_data["trade_flow"]` e.g. `aggressor_imbalance`, `buy_volume`, `sell_volume`.  
   - **Data source:** Ticks/trades from exchange or gateway.  
   - **Integration:** New trade-flow module; wire to ReactionEngine + FeatureVector; keep separate from S/R and direction.

2. **VWAP deviation (price vs VWAP)**  
   - **Adds:** Mean-reversion vs trend context; 5m entry and regime.  
   - **Where:** Entry (locational), optional timing gate. **Not** direction.  
   - **unified_data path:** `unified_data["vwap_deviation"]` (pct or ATR-scaled).  
   - **Data source:** 5m (or 1d) candles for VWAP.  
   - **Integration:** VWAP + deviation calculator; entry scoring and FeatureVector only.

3. **Volatility regime (e.g. expanding / contracting / sideways)**  
   - **Adds:** Clearer timing/regime for when to act.  
   - **Where:** Timing gate, regime filters, optional Reaction boost. **Not** direction or entry.  
   - **unified_data path:** `unified_data["volatility"]["volatility_regime"]` or top-level.  
   - **Data source:** Existing vol pipeline (e.g. current vs baseline).  
   - **Integration:** Simple state machine or thresholds; single source of truth with spike_intensity.

4. **Liquidation proximity (distance to estimated liq)**  
   - **Adds:** Risk and sizing context.  
   - **Where:** Risk, entry (liquidation_safety), optional reaction. **Not** direction.  
   - **unified_data path:** `unified_data["risk"]` or `support_resistance.metadata` e.g. `liquidation_distance_pct`.  
   - **Data source:** Maintenance margin config + position context when live.

5. **Funding rate momentum (rate of change)**  
   - **Adds:** Earlier funding regime shift.  
   - **Where:** Regime, optional strategy selection.  
   - **Data source:** Existing funding history.  
   - **Integration:** Add ROC to `funding_analysis`; use only for regime.

6. **Staleness / data-quality flags**  
   - **Adds:** Safer backtest vs live; avoid stale book.  
   - **Where:** Filters, optional confidence discount. **Not** direction or entry.  
   - **unified_data path:** `unified_data["data_quality"]` (e.g. `orderbook_stale`, `candle_stale`).  
   - **Data source:** Feed timestamps vs `unified_data["timestamp"]`.

7. **Volume profile / value-area deviation**  
   - **Adds:** Mean reversion vs breakout context.  
   - **Where:** Entry (locational), regime. **Not** direction.  
   - **Data source:** Volume-by-price history; implement later.

8. **Open interest delta (if available)**  
   - **Adds:** Positioning context for BTC perps.  
   - **Where:** Regime, optional reaction. **Not** direction or entry.  
   - **Data source:** External API.

---

## 4. Guardrails

- **Do not use S/R for direction.** S/R is for entry, stop/target, and reactive level_proximity only.  
- **Do not use IV squeeze for direction or entry price.** Squeeze is timing only.  
- **Do not add redundant volatility metrics.** Keep a single vol pipeline; avoid overlap with spike_intensity.  
- **No wall-clock in unified_data or decision path.** Use `unified_data["timestamp"]` (candle-based) only.  
- **Normalization:** Keep RSI 0–100; direction/entry scores 0–100; document any [-1,1] vs [0,1] mappings (e.g. pressure, orderbook) for ML parity.

---

## 5. References

- Full inventory, coverage, and integration details: `INDICATOR_INVENTORY_AND_GAP_ANALYSIS.md`.  
- Unused prep audit: `COMPREHENSIVE_UNUSED_PREP_AUDIT.md`.
