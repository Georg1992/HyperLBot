# Indicator & Signal Inventory and Gap Analysis

**Date:** 2026-01-29  
**Scope:** All indicators/signals computed, written to `unified_data`, and consumed by StrategyManager, PredictionEngine, ReactiveEngine, RiskManager, consolidation/filters, dashboard, and FeatureVector.  
**Constraints:** Direction = momentum-based (no S/R leakage); Entry = locational (S/R, psych, ATR, spread); Squeeze = timing only; Deterministic, NO FALLBACKS; Two engines (Prediction limit + Reaction market).

---

## 1. Indicator & Signal Inventory

| # | Name | Source (module + function, file:line) | unified_data key path | Consumers (file:line) | Subsystem usage | Role | Measurement type |
|---|------|--------------------------------------|------------------------|------------------------|------------------|------|-------------------|
| 1 | RSI | RSICalculator.get_latest_analysis, `rsi_calculator.py:211` | `rsi`, `rsi_value` (flattened) | strategy_manager 294,298; momentum_detector 81,161,299,462; prediction_engine 1823–1855,2347–2355; reactive_engine 322–324; consolidation_tracker 334; calibration_hooks 205,223 | [Strategy] [Direction] [Entry] [Reactive] [Regime] [FeatureVector] [Calibration] | Direction, Entry | Candle-based; 0–100; rsi_trend (BULLISH/BEARISH/NEUTRAL), rsi_signal, rsi_momentum |
| 2 | Trend | TrendCalculator → TrendDataMapper.map_trend_data, `trend_calculator.py`, `trend_data_mapper.py:41–61` | `trend`, `trend_direction` (flattened) | strategy_manager 290–291,302; strategy_detector 64; momentum_detector 83,163,286–296,449–459; prediction_engine 1866–1876,2357–2360; reactive_engine 325–327; consolidation_tracker 116,125; market_conditions 82; calibration 203 | [Strategy] [Direction] [Entry] [Reactive] [Regime] [Dashboard] [FeatureVector] [Calibration] | Direction, Entry, Regime | Candle-based; multi-TF (15m,1h,4h,24h); direction (BULLISH/BEARISH/SIDEWAYS), strength 0–1, detailed_timeframes |
| 3 | Volatility 5m | VolatilityCalculator.calculate_candle_volatility, `volatility_calculator.py:72–134` | `volatility`, `volatility_5m`, `volatility_category` (flattened) | strategy_manager 280,295,363; momentum_detector 82,162,309–314,472–477; prediction_engine 167–169; reactive_engine 328–330; consolidation_tracker 117,265,316,637; calibration 201–202,216 | [Strategy] [Direction] [Reactive] [Regime] [FeatureVector] [Calibration] | Timing, Regime | Candle-based 5m; unitless decimal + %; level LOW/MODERATE/HIGH/EXTREME; spike_intensity NONE/MODERATE/HIGH/EXTREME |
| 4 | Volume | VolumeCalculator.get_latest_analysis, `volume_calculator.py:128–165` | `volume`, `volume_category` (flattened) | strategy_manager 296,365–369; momentum_detector 80,160,260–280,435–445; prediction_engine 169–170,1828,2327; reactive_engine 331; consolidation_tracker 118,256,316,479,637; calibration 204,217; volume_classifier 119,155 | [Strategy] [Direction] [Entry] [Reactive] [Regime] [FeatureVector] [Calibration] | Direction, Regime | Candle-based; category, percentile, trend, volume_trend_strength 0–1, volume_anomaly |
| 5 | Pressure | PressureCalculator.get_latest_analysis, `pressure_calculator.py:313–318` | `pressure` | strategy_manager 299,328–332; momentum_detector 79,159,268–280,418–432; prediction_engine 171–172,1879–1889,2363–2382; reactive_engine 333–334; consolidation_tracker 324,480; reaction_direction_scorer 36–45; calibration 212–213 | [Strategy] [Direction] [Entry] [Reactive] [Regime] [FeatureVector] [Calibration] | Direction, Entry | Orderbook/trade-based; direction STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL, strength, net_pressure, pressure_ratio |
| 6 | Support/Resistance | SupportResistanceCalculator.calculate_multi_timeframe_levels, `support_resistance_calculator.py:954–1002` | `support_resistance` | strategy_manager 297,121; strategy_detector 121–146; momentum_detector 78,158,94–106,401–416; prediction_engine 244,2481,2704,3185,3317,3451; reactive_engine 39–55,118–119; consolidation_tracker 109,522; pressure_calculator 236; RiskManager (via prediction_engine SL/TP) | [Strategy] [Entry] [Stop/Target] [Reactive] [Regime] [Dashboard] [FeatureVector] | Entry, Risk, Regime | Candle-based; levels[], metadata.atr_5m; level fields: type, price_level, power, status, etc. |
| 7 | Patterns | PatternRecognitionEngine.analyze_patterns, `pattern_recognition_engine.py`; `market_data_service.py:714–730` | `patterns` | strategy_manager 372–385; prediction_engine 1892–1902,2384–2387; dashboard_service 146; logging 240 | [Strategy] [Direction] [Entry] [Dashboard] [Logging] | Direction, Entry | Candle-based; patterns[], patterns_nested (reversal, continuation, triangle, channel, wedge, trend), overall_quality |
| 8 | Orderbook | OrderBookAnalyzer.analyze_orderbook, `orderbook_analyzer.py:29–98` | `orderbook_analysis` | strategy_manager 298,319–326; prediction_engine 173,2397–2405; reactive_engine 58–64,335–338; reaction_direction_scorer 26–32,49–59; calibration 210–211 | [Strategy] [Direction] [Entry] [Reactive] [FeatureVector] [Calibration] | Entry, Execution-cost, Direction (reaction) | Orderbook-based; bid_ask_spread.percentage, liquidity_depth.depth_score, order_imbalance.bias, etc. |
| 9 | IV Squeeze | IVSqueezeAnalyzer.get_latest_analysis, `iv_squeeze_analyzer.py:233–296` | `iv_squeeze` | prediction_engine (base_engine) 134; reactive_engine 97–102,339; models.fill_ivs_feature_vector 116–135; decision/base_engine 134 | [Reactive] [FeatureVector] [Timing] | Timing | Candle-based; is_squeeze, squeeze_strength, duration_minutes, squeeze_released, release_timestamp |
| 10 | Market conditions | MarketConditionsAnalyzer.analyze_trading_conditions, `market_conditions_analyzer.py:81–85,200–215` | `market_conditions` | strategy_manager 301,358–359; prediction_engine 1987–2003,2409–2418; market_conditions 81–85; calibration 216 | [Strategy] [Direction] [Entry] [FeatureVector] [Calibration] | Regime, Direction, Entry | Multi-source (RSI, trend, vol, volume, fear/greed, whale, news); condition, risk_level |
| 11 | Cross-asset | CrossAssetCorrelationAnalyzer.analyze_cross_asset_correlations, `cross_asset_correlation_analyzer.py:72–100` | `cross_asset_analysis` | strategy_manager (not in _extract; funding/cross_asset optional per strategy); prediction_engine 2011–2025 | [Direction] [FeatureVector] | Direction, Cross-asset | External (DXY, gold, stocks); dxy_correlation, gold_correlation, stock_correlation (correlation, strength, *_change_pct) |
| 12 | Funding | FundingRateAnalyzer.analyze_funding_rate, `funding_rate_analyzer.py:65–94` | `funding_analysis` | strategy_manager 300,337–356; calibration 214 | [Strategy] [Calibration] | Regime, Risk | API-based; funding_trend.direction/strength/rate_change, funding_volatility.category |
| 13 | Consolidation | ConsolidationTracker.detect_consolidation / detect_breakout, `consolidation_tracker.py:109–522` | via `get_consolidation_analysis(unified_data, current_price)`; not stored in unified_data | market_data_service 478–514; consolidation_tracker uses trend, volatility, volume, pressure, RSI, S/R | [Regime] | Regime | Derived from S/R, trend, volatility, volume, pressure, RSI; consolidation range, breakout direction/confidence |
| 14 | ATR 5m | SupportResistanceCalculator (metadata), `support_resistance_calculator.py:955–959` | `support_resistance.metadata.atr_5m` | momentum_detector (atr_5m arg); prediction_engine 2336,2481,2704+; reactive_engine 72–76,113+; RiskManager (config ATR mult); reaction_direction_scorer 71–92,94–116 | [Entry] [Stop/Target] [Reactive] [Risk] | Entry, Risk | Candle-based 5m; raw $ and % of price |
| 15 | Psychological levels | PsychologicalLevelGenerator (via S/R pipeline) | Part of `support_resistance.levels` or psych-specific usage | prediction_engine (psych distance, round-number nudge); level_utils | [Entry] | Entry | Derived from price; round-number proximity |
| 16 | Timestamp | SessionOrchestrator / MarketDataService (tick from candle) | `timestamp` | strategy_manager 182; momentum_processor 19; consolidation 475; calibration 126; prediction_engine 478,487; fill_ivs 126 | [Regime] [Reactive] [Calibration] [FeatureVector] | Quality | Candle-based (last closed 5m); Unix float |
| 17 | Current price | PriceUpdateHandler / WebSocket / API | `current_price` | All engines, RiskManager, orderbook, S/R, calibratoin | [Strategy] [Direction] [Entry] [Reactive] [Risk] [Dashboard] | — | Real-time |

**Notes on consumption:**

- **Strategy selection:** `strategy_manager._extract_market_data` uses volatility_category, volatility_5m, trend_direction, volume_category, rsi_value, trend (detailed_timeframes, strength), rsi (rsi_trend, rsi_signal, rsi_momentum), volume (volume_trend_strength, volume_anomaly), support_resistance (levels for S/R filter), orderbook_analysis (spread, liquidity), pressure, funding_analysis (trend, volatility), market_conditions (condition, risk_level), patterns (patterns_nested, overall_quality), spike_intensity. Strategy scorers use these via `data`; **S/R levels are not used for strategy selection** (filter_sr_levels_for_dashboard only).
- **Direction scoring (PredictionEngine):** RSI, trend, pressure, patterns, volume (and optionally market_conditions, cross_asset) via `direction_weights`. **S/R proximity removed from direction.**
- **Entry scoring (PredictionEngine):** support_resistance, rsi, trend, pressure, patterns, orderbook (optional), market_conditions (optional). Fill probability, liquidation safety, level strength, spread penalty use ENTRY_SCORING_WEIGHTS; ATR and S/R metadata drive distances.
- **Stop/Target:** RiskManager uses entry_price, direction, sr_stop_level, atr_5m, current_price, config. S/R and ATR are required.
- **Reactive scoring:** reaction_direction_scorer uses order_imbalance.bias, pressure (net_pressure, direction, strength), bid_ask_spread.percentage, support_resistance (levels) for level_proximity, volatility (volatility_percentage / volatility_5m) for volatility_momentum. IV squeeze used for **timing-only** boost on breakout when squeeze_released.
- **MomentumDetector:** S/R levels, pressure, volume, RSI, volatility, trend for breakout/breakdown confidence; **uses wall-clock** in `detected_at` and cooldown (separate from unified_data timestamp).
- **FeatureVector:** models.FEATURE_VECTOR_REQUIRED_KEYS; ivs_* from `iv_squeeze`; rsi, trend, volatility, volume, pressure, orderbook (spread), S/R (metadata atr, psych/sr distances) from unified_data in both prediction and reaction engines.
- **Calibration:** Uses nested paths per audit fixes: volatility_category, volatility_5m, trend_direction, volume_category, rsi_value (required); trend.strength, rsi.rsi_trend, orderbook_analysis.bid_ask_spread.percentage, liquidity_depth.depth_score, pressure net_pressure/pressure_ratio, funding_analysis.funding_trend.direction, volume.volume_trend_strength, volatility.spike_intensity, market_conditions.risk_level (optional).

---

## 2. Coverage by Category

| Category | What we have | Gaps |
|----------|----------------|------|
| **1) Momentum/Trend (direction)** | Trend (multi-TF direction + strength), RSI (value, trend, signal, momentum), pattern overall_quality and nested categories, volume trend/percentile. All used in direction scoring. | No explicit momentum oscillator (e.g. MACD histogram); no dedicated “momentum regime” (acceleration/deceleration). |
| **2) Volatility/Regime (timing)** | 5m volatility (basic, weighted, current, adaptive blend), spike detection (relative + absolute), classification (LOW/MODERATE/HIGH/EXTREME), spike_intensity. IV squeeze (BB/KC) for timing. Consolidation uses vol + trend + volume. | No term-structure or volatility-of-volatility; no explicit vol regime label beyond level. |
| **3) Liquidity/Microstructure** | Orderbook: spread, depth, imbalance (bias). Pressure (orderbook/trade-derived). Used in strategy selection, entry, reaction scoring, calibration. | No explicit trade-flow or aggressor-side metrics (buy/sell aggressor imbalance); no inventory-based liquidity. |
| **4) Participation/Volume** | Volume category, percentile, trend, volume_trend_strength, volume_anomaly. Used in strategy, direction, momentum, consolidation. | No volume-profile or VWAP deviation; no distinct “volume regime” flag. |
| **5) Structure/Levels (S/R + psych)** | S/R levels (multi-TF, power, touches, etc.), metadata.atr_5m, psych levels. Used for entry, SL/TP, reactive level_proximity, consolidation, dashboard. **Not used for direction.** | Liquidations only via config (maintenance margin) for risk; no explicit “liquidation heatmap” or cluster levels. |
| **6) Risk/Execution costs** | Spread (orderbook), liquidity depth; config spread thresholds, fill probability, liquidation safety, spread penalty in entry scoring. RiskManager stop/target. | No explicit slippage proxy; no latency or queue-depth metrics. |
| **7) Correlations/Cross-asset** | DXY, gold, stocks (correlation, strength, changes). Direction only; optional weight. | Single-asset focus for 5m; cross-asset used sparingly. |
| **8) Market conditions/Sentiment** | Market conditions (fear/greed, whale, news, risk_level, condition). Direction and entry (optional). | No dedicated sentiment score; condition is composite. |
| **9) Data quality/Latency** | `timestamp` from candle (deterministic). No wall-clock in unified_data build or decision pipeline. | No explicit latency or staleness metrics; no data-quality flags in unified_data. |

---

## 3. High-Value Missing Indicators (Ranked)

1. **Short-term trade-flow / aggressor imbalance (buy vs sell)**  
   - **Adds:** Better reaction direction and fill context; ML feature for confidence.  
   - **Use:** Reaction scoring (direction), optional entry (execution-cost). **Not** direction for limit engine.  
   - **Integration:** New `trade_flow` (or similar) in unified_data; reaction_direction_scorer weight; keep separate from S/R and direction logic.  
   - **Path:** `unified_data["trade_flow"]` e.g. `aggressor_imbalance`, `buy_volume`, `sell_volume`.  
   - **FeatureVector:** `trade_flow_imbalance` or similar.  
   - **Plan:** Implement in a small trade-flow module (from ticks/trades if available); wire to ReactionEngine + FeatureVector; unit tests.  
   - **Risks:** Tick data availability; overfitting to single venue.

2. **VWAP deviation (price vs VWAP)**  
   - **Adds:** Mean-reversion vs trend context; useful for 5m entries and regime.  
   - **Use:** Entry (locational), optional timing gate. **Not** direction.  
   - **Integration:** Compute from 5m candles; store e.g. `unified_data["vwap_deviation"]`; use only in entry/timing, never in direction.  
   - **Path:** `unified_data["vwap_deviation"]` (pct or ATR-scaled).  
   - **FeatureVector:** `vwap_deviation_pct` or `vwap_deviation_atr`.  
   - **Plan:** VWAP from daily (or 5m) fix; deviation calculator; wire to entry scoring and FeatureVector; tests.  
   - **Risks:** Session boundary handling; lookahead if using future VWAP.

3. **Volatility regime label (e.g. expanding/contracting/sideways)**  
   - **Adds:** Clearer timing/regime for when to act vs stand aside.  
   - **Use:** Timing gate, regime filters, optional Reaction boost. **Not** direction or entry price.  
   - **Integration:** Derive from existing vol pipeline (e.g. current vs baseline); add `volatility_regime` to `volatility` or top-level.  
   - **Path:** `unified_data["volatility"]["volatility_regime"]` or `unified_data["volatility_regime"]`.  
   - **FeatureVector:** `volatility_regime_categorical` or one-hot.  
   - **Plan:** Simple state machine or threshold rule over vol ratio; feed from current volatility output; tests.  
   - **Risks:** Redundancy with spike_intensity; keep single source of truth.

4. **Liquidation proximity / safety (distance to estimated liq)**  
   - **Adds:** Risk and positioning context; better sizing and filters.  
   - **Use:** Risk, entry (liquidation_safety already used), optional reaction “liquidation safety” factor.  
   - **Integration:** Use existing maintenance-margin logic; expose “distance to liq” (pct or ATR) in unified_data; keep out of direction.  
   - **Path:** `unified_data["risk"]` or `support_resistance.metadata` e.g. `liquidation_distance_pct`.  
   - **FeatureVector:** `liq_distance_pct` or similar.  
   - **Plan:** Centralize liq distance in one module; add to unified_data and FeatureVector; ensure no direction usage.  
   - **Risks:** Position-dependent; requires position context when live.

5. **Volume profile / value-area deviation (optional)**  
   - **Adds:** Context for mean reversion vs breakout.  
   - **Use:** Entry (locational), regime. **Not** direction.  
   - **Integration:** If data available, compute POC/VWAP/value area; deviation only in entry/regime.  
   - **Path:** `unified_data["volume_profile"]` or similar.  
   - **Plan:** Later; depends on historical volume-by-price.

6. **Explicit “momentum regime” (acceleration/deceleration)**  
   - **Adds:** Filters for trend-following vs mean-reversion.  
   - **Use:** Timing/regime, optional strategy filters. **Not** direction or entry price.  
   - **Integration:** Derive from trend strength deltas or RSI momentum; add to trend or dedicated key.  
   - **Path:** `unified_data["trend"]["momentum_regime"]` or `unified_data["momentum_regime"]`.  
   - **Plan:** Lightweight derivative of existing trend/RSI; tests.

7. **Staleness / data-quality flags**  
   - **Adds:** Safer backtest vs live; avoid trading on stale book.  
   - **Use:** Filters, optional confidence discount. **Not** direction or entry.  
   - **Integration:** Compare last update times to `timestamp`; boolean flags in unified_data.  
   - **Path:** `unified_data["data_quality"]` (e.g. `orderbook_stale`, `candle_stale`).  
   - **Plan:** Add where feeds expose timestamps; gate or dampen only.

8. **Funding rate momentum (rate of change)**  
   - **Adds:** Earlier shift in funding regime.  
   - **Use:** Regime, optional strategy selection. Already have funding_trend; extend with ROC.  
   - **Integration:** Add to funding_analysis; keep usage regime-only, not direction.  
   - **Path:** `unified_data["funding_analysis"]["funding_momentum"]` or similar.

9. **Spread momentum (recent spread change)**  
   - **Adds:** Execution-cost regime (tightening/widening).  
   - **Use:** Timing/execution-cost, optional reaction spread penalty.  
   - **Integration:** From orderbook_analysis; separate key or nested; no direction.

10. **Open interest delta (if available)**  
    - **Adds:** Positioning context for BTC perps.  
    - **Use:** Regime, optional reaction. **Not** direction or entry.  
    - **Integration:** External feed; new key; use only in regime/filters.

---

## 4. Minimal Integration Plan for Top 3

1. **Trade-flow / aggressor imbalance**  
   - **Owner:** New `core/analysis/real_time/trade_flow_analyzer` (or equivalent).  
   - **Inputs:** Tick/trade stream (if available from WebSocket or API).  
   - **Outputs:** `aggressor_imbalance` in [-1, 1], optional buy/sell volume.  
   - **Wire:** `market_data_service` registers module; append `trade_flow` to unified_data.  
   - **Reaction:** Add weight in `REACTION_DIRECTION_WEIGHTS`; use in `score_reaction_direction`; **do not** use in PredictionEngine direction.  
   - **FeatureVector:** Add `trade_flow_imbalance`; validate in ML schema.  
   - **Tests:** Unit tests for analyzer; integration test that reaction uses it and prediction direction does not.

2. **VWAP deviation**  
   - **Owner:** `core/calculations/vwap_calculator` or existing volume/price module.  
   - **Inputs:** 5m (or 1d) candles for VWAP; `current_price`, `timestamp`.  
   - **Outputs:** `vwap_deviation_pct` and/or `vwap_deviation_atr` (use metadata.atr_5m).  
   - **Wire:** Called from `market_data_service` or volume pipeline; `unified_data["vwap_deviation"]`.  
   - **Use:** Entry scoring only (e.g. discount entries far from VWAP in mean-reversion regimes); **never** direction.  
   - **FeatureVector:** `vwap_deviation_pct`, `vwap_deviation_atr`.  
   - **Tests:** Unit tests; ensure no direction consumption.

3. **Volatility regime**  
   - **Owner:** `VolatilityAnalyzer` or small helper using existing vol output.  
   - **Inputs:** `volatility_5m`, weighted/baseline from current pipeline.  
   - **Outputs:** `volatility_regime`: e.g. `EXPANDING` / `CONTRACTING` / `SIDEWAYS`.  
   - **Wire:** Add to `volatility` result; no new top-level key required.  
   - **Use:** Timing gate (e.g. prefer reaction in expanding); optional regime filter; **not** direction or entry price.  
   - **FeatureVector:** `volatility_regime_categorical` or one-hot.  
   - **Tests:** Unit tests; verify usage only in timing/regime.

---

## 5. Quick Wins vs Later Work

**Quick wins (minimal code, high clarity):**  
- **Volatility regime:** Derive from existing vol pipeline; add to `volatility` dict; use in timing/regime only.  
- **Funding momentum:** Add ROC to `funding_analysis`; use in strategy/regime only.  
- **Data-quality/staleness flags:** Add where timestamps exist; use for filtering only.

**Later work (new data or larger changes):**  
- **Trade-flow / aggressor imbalance:** Depends on tick/trade feed.  
- **VWAP deviation:** Requires clean session boundaries and possibly 1d data.  
- **Liquidation proximity:** Needs position context for live use.  
- **Volume profile / value area:** Needs volume-by-price history.  
- **Open interest delta:** External API and parsing.

---

## 6. Guardrails

### Indicators we should NOT add

- **S/R-based direction:** Do not use S/R proximity or level location to decide LONG/SHORT. Direction stays momentum-based (RSI, trend, pressure, patterns, volume, etc.).  
- **Squeeze-based direction or entry price:** IV squeeze is **timing only** (when to act). Do not use it to choose direction or entry price.  
- **Redundant volatility metrics:** Avoid duplicate volatility signals (e.g. multiple spike metrics) that overlap with current spike_intensity and classification. Prefer a single, config-driven vol pipeline.  
- **Sentiment or news as direction driver:** Use only as regime/condition context; do not overweight for direction.  
- **Cross-asset as primary direction:** Keep as optional, low-weight; BTC-specific momentum should dominate.

### Common misuse patterns

- **Using S/R to decide direction:** Risk of curve-fitting and entry-direction coupling. Keep S/R for entry, SL/TP, and reactive level_proximity only.  
- **Using squeeze to pick entry price:** Squeeze is timing-only. Entry stays S/R, psych, ATR, fill, liq safety, spread.  
- **Mixing timeframe contexts:** Use 5m (or explicit multi-TF) consistently for reaction and 5m-centric strategies; avoid implicit higher-TF info in 5m decisions.  
- **Using optional features as required:** Preserve NO FALLBACKS for required keys; optional features must be explicitly optional and never silence missing-data errors.  
- **Wall-clock in unified_data or decisions:** Use only candle/tick-derived `timestamp` for determinism and replay.

### Normalization inconsistencies to fix

- **RSI:** 0–100 (raw). RSI trend → numeric ±1 in FeatureVector; keep consistent.  
- **Scores (direction, entry):** 0–100; ensure all factor contributions and combined scores stay in [0, 100] or documented range.  
- **Pressure / orderbook:** Direction factors often [-1, 1] or [0, 1]; reaction_direction_scorer maps to long/short 0–100. Document mapping and keep it consistent.  
- **Spread:** Store as decimal or % consistently (e.g. `percentage` in orderbook); avoid mixing basis-point and percentage.

---

## 7. Summary

- **Inventory:** 17 indicator/signal groups tracked from source → `unified_data` → consumers (Strategy, Direction, Entry, Stop/Target, Reactive, Regime, Dashboard, FeatureVector, Calibration).  
- **Coverage:** Strong on trend, RSI, volatility, volume, pressure, S/R, orderbook, IV squeeze, market conditions, funding, cross-asset; gaps in trade-flow, VWAP deviation, explicit vol regime, and data-quality flags.  
- **Top missing:** (1) Trade-flow/aggressor imbalance, (2) VWAP deviation, (3) Volatility regime, then liquidation proximity, volume profile, momentum regime, staleness, funding momentum, spread momentum, OI delta.  
- **Integration:** Top 3 have clear ownership, data flow, and constraints (no direction/entry leakage). Guardrails and normalization fixes above keep the system aligned with direction vs entry vs timing separation and NO FALLBACKS.
