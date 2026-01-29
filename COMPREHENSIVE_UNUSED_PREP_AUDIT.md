# Comprehensive Unused Prep / Dead Feature Audit

**Date:** 2026-01-29  
**Scope:** unified_data producers/consumers, config constants, modules/functions, ML/calibration wiring, scoring factors.  
**Method:** Grep + static traversal; precise file:line references. No production code modified.

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| **Unused unified_data keys** (produced, never consumed) | 4 |
| **Dashboard-only keys** (consumed only by dashboard/UI) | 6+ |
| **Logging-only keys** (consumed only for logs) | 2 |
| **ML-only keys** (calibration/feature vector only) | 5+ |
| **Orphan consumers** (read, no producer) | 8+ |
| **Unused modules / functions** | 5 |
| **Unused config constants** (candidates) | 15+ |

---

## 2. Unused / Underused unified_data Keys

### 2.1 Producers (where keys are written)

| Key path | Produced at | Source |
|----------|-------------|--------|
| `current_price` | `market_data_service.py:566` | `get_unified_analysis_data` |
| `timestamp` | `market_data_service.py:567` | `time.time()` (wall-clock; requested deterministic audit note) |
| `strategy` | `market_data_service.py:568`; `strategy_detector.py:86-87`; `session_orchestrator.py:450` | multiple |
| `trend_direction` | `market_data_service.py:571` | from `trend_data["direction"]` |
| `volatility_5m` | `market_data_service.py:572` | from `volatility_data` |
| `volatility_category` | `market_data_service.py:573` | from `volatility_data["level"]` |
| `volume_category` | `market_data_service.py:574` | from `volume_data` |
| `rsi_value` | `market_data_service.py:575` | from `rsi_data["rsi"]` |
| `rsi` | `market_data_service.py:578` | `rsi_data` |
| `trend` | `market_data_service.py:579` | `trend_data` |
| `volatility` | `market_data_service.py:580` | `volatility_data` |
| `volume` | `market_data_service.py:581` | `volume_data` |
| `support_resistance` | `market_data_service.py:582` | `get_support_resistance_analysis()` |
| `pressure` | `market_data_service.py:583` | `get_pressure_analysis()` |
| `patterns` | `market_data_service.py:585` | `get_pattern_analysis()` |
| `market_conditions` | `market_data_service.py:587` | `get_market_conditions_analysis()` |
| `cross_asset_analysis` | `market_data_service.py:589` | `get_cross_asset_analysis()` |
| `funding_analysis` | `market_data_service.py:589` | `get_funding_analysis()` |
| `orderbook_analysis` | `market_data_service.py:590` | `get_orderbook_analysis()` |
| `raw_data_access` | `market_data_service.py:593-597` | hyperliquid/binance APIs |
| `iv_squeeze` | `market_data_service.py:603` | `get_iv_squeeze_analysis()` |
| `state_strategy` | `strategy_detector.py:86` | strategy detection |
| `prediction_strategy` | `strategy_detector.py:92,95` | strategy detection |
| `prediction` | `session_orchestrator.py:468,485` | prediction engine / None |
| `reaction` | `momentum_processor.py:71,83,111,130` | ReactiveEngine or stub |
| `volatility_baseline` | `volatility_calculator.py:134` | volatility pipeline |
| `volatility_ratio` | `volatility_calculator.py:135` | volatility pipeline |

Additional keys from extra `_analysis_modules` (e.g. `module_name` → `unified_data[module_name]`) at `market_data_service.py:612`.

### 2.2 Unused / Underused Keys (Table)

| Key path | Produced at | Consumed at | Category | Recommendation |
|----------|-------------|-------------|----------|----------------|
| `volatility_baseline` | `volatility_calculator.py:134` | **none** | **unused** | **REMOVE** or **WIRE**: Either drop from result (log-only) or document as debug and consume in dashboard/ML. |
| `volatility_ratio` | `volatility_calculator.py:135` | **none** | **unused** | Same as above. |
| `raw_data_access` | `market_data_service.py:593-597` | **none** (deleted before dashboard at `session_orchestrator.py:809-810`) | **unused** | **REMOVE** or **WIRE**: Never read; explicitly stripped. Either stop producing or use (e.g. debug UI). |
| `data_quality` | `market_data_service.py:1067-1072` | **none** | **unused** | **REMOVE**: Part of `get_real_time_market_data()` output; that function is **never called** (see §3). `data_quality` is dead. |
| `trend_strength` (top-level) | **never** | `calibration_hooks.py:191` | **orphan consumer** | **WIRE**: Calibration uses `unified_data.get("trend_strength", 0.0)`. Flatten from `trend["strength"]` into `unified_data["trend_strength"]` if ML should use it, or keep default. |
| `spread_pct` (top-level) | **never** | `calibration_hooks.py:194` | **orphan consumer** | **WIRE**: Spread lives in `orderbook_analysis.bid_ask_spread.percentage`. Add top-level `spread_pct` when building unified_data or have calibration read from nested structure. |
| `liquidity_score` (top-level) | **never** | `calibration_hooks.py:195` | **orphan consumer** | **WIRE**: Exists in `orderbook_analysis.liquidity_depth.depth_score`. Flatten or point calibration there. |
| `net_pressure` (top-level) | **never** | `calibration_hooks.py:196` | **orphan consumer** | **WIRE**: In `pressure["net_pressure"]`. Flatten or use nested. |
| `pressure_ratio` (top-level) | **never** | `calibration_hooks.py:197` | **orphan consumer** | **WIRE**: In `pressure` (e.g. `pressure_ratio`). Flatten or use nested. |
| `funding_direction` (top-level) | **never** | `calibration_hooks.py:198` | **orphan consumer** | **WIRE**: Derive from `funding_analysis` / funding trend. |
| `volume_trend_strength` (top-level) | **never** | `calibration_hooks.py:199` | **orphan consumer** | **WIRE**: In `volume["volume_trend_strength"]`. Flatten or use nested. |
| `spike_intensity` (top-level) | **never** | `calibration_hooks.py:201` | **orphan consumer** | **WIRE**: In `volatility` result; calculator emits it. Ensure it flows into `unified_data["volatility"]` and either add top-level or have calibration read from `unified_data["volatility"]["spike_intensity"]`. |
| `risk_level` (top-level) | **never** | `calibration_hooks.py:202` | **orphan consumer** | **WIRE**: Comes from `market_conditions["risk_level"]`. Flatten or use nested. |
| `prediction_data` | `market_data_service.py:1101` (inside `get_dashboard_data`) | `web_dashboard` uses `predictions` / `prediction`, not `prediction_data` | **unused** | **REMOVE**: Empty dict, never read. |
| `dashboard_ready` | `market_data_service.py:1103` | **none** | **unused** | **REMOVE** or **WIRE**: Set but never read. |
| `ai_system_status` | `web_dashboard.py:319` (from `market_data_dict`) | `web_dashboard.py:364` | dashboard-only | **KEEP** if UI uses it; else **REMOVE**. |
| `candleData` | `dashboard_service.py:110`; `web_dashboard.py:370` | Dashboard UI | dashboard-only | **KEEP**. |
| `execution_gate_reason` | reaction/prediction objects | `realtime_dashboard.html` (reaction status), tests | dashboard + tests | **KEEP**. |

**Reasoning (short):**

- **volatility_baseline / volatility_ratio**: Added for debugging; no consumer. Either log-only and remove from result, or expose in UI/ML.
- **raw_data_access**: Produced then removed before dashboard. Nothing uses it; omit or use explicitly.
- **data_quality / get_real_time_market_data**: `get_real_time_market_data` is dead (see §3). `data_quality` is unused.
- **Calibration top-level keys**: Calibration uses `unified_data.get(...)` for multiple keys that exist only nested. Either flatten those into unified_data or change calibration to read nested (e.g. `volatility`, `pressure`, `orderbook_analysis`, `market_conditions`).
- **prediction_data / dashboard_ready**: Set in dashboard payload, never read. Safe to remove.

---

## 3. Unused Modules / Classes / Functions

| Symbol | Location | Why unused | Tests reference? |
|--------|----------|------------|------------------|
| `get_real_time_market_data` | `market_data_service.py:1017` | No callers; only definition. | No |
| `validate_prediction_features` | `ml_feature_validator.py:50` | Never called; direction/entry validation used instead. | No |
| `log_outcome` | `calibration_hooks.py:251` | Defined only; never called. Outcome logging for ML not wired. | No |
| `DataProvider` (Protocol) | `market_conditions_analyzer.py:27-33` | Protocol for dependency injection; used only as type hint. Not “dead” but no runtime implementation beyond implict `market_data_service`. | N/A |
| `create_dashboard_service` | Used in `web_dashboard` | Verify singleton vs factory usage; not dead. | N/A |

**Recommendation:**

- **get_real_time_market_data**: **REMOVE** or **WIRE**. Currently dead; contains `data_quality` etc. Either delete or switch a caller to use it and clarify vs `get_unified_analysis_data` / `get_dashboard_data`.
- **validate_prediction_features**: **REMOVE** or **WIRE** (e.g. post-prediction validation) if you want prediction-level ML validation.
- **log_outcome**: **WIRE** when implementing ML outcome logging (e.g. trade results → calibration DB).

---

## 4. Unused Config Constants

Candidates (config or constants) with no references found:

| Name | File:line | Suggested action |
|------|-----------|------------------|
| `VOLATILITY_THRESHOLDS` | `config.py:163-166` | Grep: minimal use. **Consolidate** with `VOL_LVL_*` / volatility classifier if they overlap. |
| `VOLATILITY_5M_VERY_LOW` … `VOLATILITY_5M_EXTREME` | `constants.py:263-267` | Volatility classifier uses `VOL_LVL_*` from config. **Consolidate** with config; avoid duplicate thresholds. |
| `VOLATILITY_CATEGORY_*` | `constants.py:214-220` | Largely unused; classifier uses LOW/MODERATE/HIGH/EXTREME. **Remove** or **wire** if needed for display. |
| `VOLATILITY_WEIGHT`, `MOMENTUM_WEIGHT`, `VOLUME_WEIGHT`, `PATTERN_WEIGHT` | `constants.py:275-278` | **Grep**: no references. **Remove** or **wire** into strategy/ML weights. |
| `VOLUME_CV_*` | `constants.py:281-283` | **Grep**: no references. **Remove** or **wire**. |
| `OPTIMAL_TRADING_SCORE`, `GOOD_TRADING_SCORE`, `POOR_TRADING_SCORE` | `constants.py:270-272` | **Grep**: no references. **Remove** or **wire**. |
| `MagicNumbers` (partial) | `constants.py` | Some attributes used (e.g. pressure, RSI). Audit per key; **remove** unused, **wire** or **consolidate** rest. |
| `MIN_MOMENTUM_CONFIDENCE` | `config.py:75` | **Grep**: no references. **Remove** or **wire** (e.g. momentum filter). |
| `MIN_LIQUIDITY_SCORE` | `config.py:76` | **Grep**: scalping validation. **KEEP**. |
| `STRATEGY_SWITCH_COOLDOWN_*` | `config.py:992-995` | **Grep**: used in strategy_detector. **KEEP**. |
| `ADAPTIVE_PRE_FILTER_*` | `config.py:999-1000` | **Grep**: used. **KEEP**. |
| `MIN_PERF_TRADES`, `ENABLE_PERFORMANCE_TIEBREAK` | `config.py:1005-1006` | **Grep**: minimal/no use. **Remove** or **wire**. |
| `ENTRY_CANDIDATE_OFFSET_FACTORS` | `config.py:1011` | **Grep**: used in prediction flow. **KEEP**. |

**Recommendation:** Prefer `config.config` as single source for trading/volatility thresholds; **consolidate** or **remove** duplicates in `constants.py`.

---

## 5. Always-Inactive / Renormalized Factors

### 5.1 Direction / entry weights

- **`sr_proximity`**: Removed from config; weight redistributed (see config comments). Effectively **inactive**.
- **`reversal` / `sweep_revert`** (reaction): Implemented as placeholder candidates with score 0. **Always inactive** until implemented; “none” used to win often (now replaced by always LONG/SHORT, but reversal/sweep_revert still zero).

### 5.2 Calibration features always defaulted

Because `trend_strength`, `spread_pct`, `liquidity_score`, `net_pressure`, `pressure_ratio`, `funding_direction`, `volume_trend_strength`, `spike_intensity`, `risk_level` are **not** top-level in `unified_data`, calibration always uses `.get(..., default)`. Those features are **effectively inactive** for ML.

### 5.3 Suggestion

- **Reversal / sweep_revert**: Either implement scoring or remove from candidate set to avoid “always zero” factors.
- **Calibration**: **WIRE** unified_data so calibration either receives flattened keys (e.g. `trend_strength`, `spread_pct`, …) or reads from nested structures (`trend`, `orderbook_analysis`, `pressure`, `volatility`, `market_conditions`, etc.).

---

## 6. Feature Vector vs Validator vs Storage

- **Feature vector**: `FEATURE_VECTOR_REQUIRED_KEYS` in `models.py`; engines build `fv` and call `validate_feature_schema(fv)`. **Validated**.
- **Calibration**: `log_prediction` builds `features` from `unified_data.get(...)` and stores `features_json`. Multiple keys missing at top-level → **always defaulted**; schema consistency with `fv` not enforced.
- **MLFeatureValidator**: `validate_direction_features` and `validate_entry_features` are used; `validate_prediction_features` is **not** used.

**Recommendation:** Use a **single** feature schema for both engines and calibration; validate before logging. Wire missing unified_data keys or have calibration read from nested data.

---

## 7. Dashboard-Only vs Logging-Only vs Tests-Only

- **Dashboard-only (examples):** `candleData`, `ai_system_status`, `session.*`, `market` (structure for UI), `prediction`, `reaction`, `trades`, `orderbook` (structure), `connection_status`, `data_source`.
- **Logging-only:** Various keys inside `trading_logger` (e.g. `support_resistance`, `patterns`) when logging analysis/trades.
- **Tests-only:** `ud["support_resistance"]`, `ud["pressure"]`, `ud["volatility"]`, `ud["orderbook_analysis"]`, `ud["iv_squeeze"]` in `test_momentum_processor`, `test_decision_engines`, `test_iv_squeeze_integration`.

---

## 8. References (File:Line)

### Producers

- `market_data_service.py:565-612` – unified_data initial build and `iv_squeeze`
- `market_data_service.py:606-612` – extra modules → `unified_data[module_name]`
- `strategy_detector.py:86-87,92,95` – `state_strategy`, `strategy`, `prediction_strategy`
- `session_orchestrator.py:450,468,485,500` – `strategy`, `prediction`, `reaction`
- `momentum_processor.py:71,83,111,130` – `reaction` (stub or engine)
- `volatility_calculator.py:125-135` – volatility result including `volatility_baseline`, `volatility_ratio`
- `dashboard_service.py:126-134,179` – `market`, `prediction`, `reaction`, `session`

### Consumers (representative)

- `base_engine.py:45-52,134` – `current_price`, `timestamp`, `support_resistance`, `state_strategy`, `prediction_strategy`, `iv_squeeze`
- `momentum_detector.py:78-83,158-163` – `support_resistance`, `pressure`, `volume`, `rsi`, `volatility`, `trend`
- `consolidation_tracker.py:109-118,256-266,316-334,479-480,522,637-638` – `support_resistance`, `trend`, `volatility`, `volume`, `pressure`, `rsi`
- `prediction_engine.py:244,522,1826,1845-1847,1892-1995,2010,2309-2413,2481,2704,2898,3185,3317,3410-3412` – `support_resistance`, `orderbook_analysis`, `patterns`, `market_conditions`, `cross_asset_analysis`, etc.
- `reactive_engine.py:39,58,97,177,317,326,358` – `support_resistance`, `orderbook_analysis`, `iv_squeeze`, `pressure`, `trend`, etc.
- `reaction_direction_scorer.py:26,50` – `orderbook_analysis`
- `strategy_detector.py:64,121` – `volatility_category`, `trend`, `support_resistance`
- `strategy_manager.py:295-410,483-988` – `volatility`, `support_resistance`, `pressure`, `volume`, `orderbook_analysis`, `funding_analysis`, `market_conditions`, etc.
- `calibration_hooks.py:188-201` – `unified_data.get(...)` for calibration features
- `models.py:116-126` – `iv_squeeze`, `timestamp`
- `dashboard_service.py:41-43,109-110,114-119,126-134,146` – `strategy`, `patterns`, `candleData`, `market`, `prediction`, `reaction`
- `web_dashboard.py:312-346,364-370` – `session`, `market`, `prediction`, `reaction`, `ai_system_status`, `candleData`, etc.
- `trading_logger.py:179,241` – `support_resistance`; `patterns` (logging)

---

## 9. Top 20 Findings (Summary)

1. **`get_real_time_market_data`** never called → dead; `data_quality` unused.
2. **`volatility_baseline`**, **`volatility_ratio`** produced, never consumed.
3. **`raw_data_access`** produced then removed; never read.
4. **`log_outcome`** (calibration) never called → outcome logging not wired.
5. **`validate_prediction_features`** never called.
6. **Calibration** reads top-level `trend_strength`, `spread_pct`, `liquidity_score`, `net_pressure`, `pressure_ratio`, `funding_direction`, `volume_trend_strength`, `spike_intensity`, `risk_level` → **none produced**; always defaults.
7. **`prediction_data`**, **`dashboard_ready`** set in dashboard payload, never used.
8. **`VOLATILITY_5M_*`** / **`VOLATILITY_CATEGORY_*`** in `constants.py` duplicate or overlap config; **consolidate**.
9. **`VOLATILITY_WEIGHT`**, **`MOMENTUM_WEIGHT`**, **`VOLUME_WEIGHT`**, **`PATTERN_WEIGHT`** unreferenced.
10. **`MIN_MOMENTUM_CONFIDENCE`** unreferenced.
11. **Reversal / sweep_revert** reaction candidates always 0 → **inactive**.
12. **`sr_proximity`** weight removed and redistributed → **inactive**.
13. **Feature vector** validated; **calibration** schema not aligned with `fv` and uses many missing keys.
14. **Dashboard** uses `session`, `market`, `prediction`, `reaction`, `candleData`, etc. — **dashboard-only**; keep if UI needs them.
15. **`execution_gate_reason`** — dashboard + tests; **keep**.
16. **`ai_system_status`** — dashboard-only; confirm UI use or remove.
17. **`timestamp`** in unified_data from `time.time()` → **non-deterministic**; audit constraint.
18. **Strategy keys** (`state_strategy`, `prediction_strategy`, `strategy`) **produced and consumed**; keep.
19. **`support_resistance`, `pressure`, `volatility`, `trend`, `volume`, `patterns`, `market_conditions`, `orderbook_analysis`, `funding_analysis`, `cross_asset_analysis`, `iv_squeeze`** — **consumed** in strategy, prediction, reaction, consolidation, dashboard; **keep**.
20. **`spike_intensity`** lives in `volatility` result; calibration expects top-level → **wire** or change calibration.

---

*End of audit. No production code was modified.*

---

## 10. Follow-up Fixes (2026-01-29)

Implementations applied per audit:

| Item | Change |
|------|--------|
| **A) Calibration hooks** | Read from nested `unified_data` (e.g. `trend.strength`, `pressure.net_pressure`, `orderbook_analysis.bid_ask_spread.percentage`). Required keys validated; missing optional → `inactive_features`. `log_prediction` raises on required-key failure (NO FALLBACKS). |
| **B) Debug-only outputs** | Removed `volatility_baseline` / `volatility_ratio` from volatility result; removed `raw_data_access` from unified_data; removed `prediction_data` / `dashboard_ready` from dashboard payload. |
| **C) Dead pipeline** | Deleted `get_real_time_market_data` and `data_quality`. |
| **D) Volatility constants** | Removed duplicate `VOLATILITY_5M_*` / `VOLATILITY_CATEGORY_*` from `constants.py`. Single source of truth: `config.config` `VOL_LVL_*`. Added `test_classifier_thresholds_match_config`. |
| **E) ReactiveEngine inactive candidates** | `breakdown["inactive_candidates"]` with `reversal` / `sweep_revert`: `implemented=False`, `score=-1`, `score_reason="not_implemented"`. Debug log for each. |
| **F) Determinism** | `unified_data["timestamp"]` from latest closed 5m candle (`get_last_timestamp`). Orchestrator sets `data_ts` from candle, `set_tick_timestamp` before analysis. `get_unified_analysis_data` uses `get_tick_timestamp()`; consolidation uses `unified_data["timestamp"]`. Removed `time.time()` from calibration `log_outcome` (uses `outcome["outcome_timestamp"]`). |
| **G) Tests** | `tests/test_determinism_no_wall_clock.py`: grep-based checks for `time.time()` in builder, strategy_manager, prediction_engine, reactive_engine, calibration_hooks; orchestrator uses candle ts. `tests/test_calibration_hooks.py`: nested read and `inactive_features` coverage. |
