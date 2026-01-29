# How Reactions Work (ReactiveEngine)

This document explains the reaction system for another AI. It covers the contract, **how direction is calculated**, the microstructure scorer, and the data flow.

---

## 1. Overview and contract

- **ReactiveEngine** always produces a **DecisionResult** (never `None`). Same “always an active best setup” contract as **PredictionEngine**.
- **Reaction** = “best market-order candidate right now.” **Direction is always LONG or SHORT (never NONE).** “Not executable” is decided later by confidence/execution gate (not yet implemented).
- **Entry type**: always `"market"`. **Confidence / executable**: not implemented → `confidence=None`, `executable=False`, `execution_gate_reason="confidence_not_implemented"`.
- **MomentumProcessor** calls ReactiveEngine each tick, maps the `DecisionResult` into `unified_data["reaction"]`. The dashboard always renders it (LONG or SHORT; no “No reaction signal” from NONE).

---

## 2. Direction scorer (microstructure)

**`score_reaction_direction(unified_data, current_price, atr_5m, strategy)`** (in `core/execution/reaction_direction_scorer.py`) returns `long_score`, `short_score` (0..100), `reasoning`, and `breakdown`. It uses **only** current-tick `unified_data` (deterministic, replay-safe).

### Factors (all from `unified_data`)

| Factor | Source | Range | Effect |
|--------|--------|-------|--------|
| **orderbook_imbalance** | `orderbook_analysis.order_imbalance.bias` | [-1, 1] | Positive → buy bias |
| **pressure** | `pressure.net_pressure` or `direction` + `strength` | [-1, 1] | Positive → buy |
| **spread_penalty** | `orderbook_analysis.bid_ask_spread.percentage` vs `REACTION_SPREAD_WIDE_PCT` | [0, 1] | Reduces effective magnitude |
| **level_proximity** | Nearest S/R vs `current_price`, distance in ATR | [-1, 1] | Near support → long bias; near resistance → short |
| **volatility_momentum** | `volatility` range vs ATR | [0, 1] | Scales magnitude (not direction) |

Weights live in **`TradingConfig.REACTION_DIRECTION_WEIGHTS`** (must sum to 1.0). Example:

```text
orderbook_imbalance 0.30, pressure 0.25, spread_penalty 0.10, level_proximity 0.15, volatility_momentum 0.20
```

- `directional = w_imb * imbalance + w_press * pressure + w_level * level_proximity`, clamped to [-1, 1].
- `effective = directional * (1 + 0.5 * vol_momentum) * (1 - spread_penalty * w_spread)`.
- `long_score = clamp(50 + 50 * effective, 0, 100)`, `short_score = clamp(50 - 50 * effective, 0, 100)`.

---

## 3. How direction is calculated (explicit)

1. **Compute base long/short scores**  
   `long_score`, `short_score` = `score_reaction_direction(...)`.

2. **Optional breakout boost**  
   If `MomentumDetector.evaluate_breakouts` returns a long (short) signal and `iv_squeeze.squeeze_released`, add `_squeeze_timing_boost` to long (short) score. Clamp each to [0, 100].

3. **Pick LONG vs SHORT**  
   - If `long_total > short_total` → **direction = "LONG"**.  
   - If `short_total > long_total` → **direction = "SHORT"**.  
   - If **tied**:  
     - Use `last_reaction_direction` (engine state or `unified_data["last_reaction_direction"]`) if in `("LONG","SHORT")`.  
     - Else use pressure sign: `net_pressure > 0` → LONG, `< 0` → SHORT.  
     - Else **LONG**.

4. **Set `direction`**  
   `direction` is always **"LONG"** or **"SHORT"** (never `"NONE"`).

5. **Best candidate**  
   - `setup_type`: `"breakout"` if we used a breakout signal for the chosen side, else `"market_follow_through"`.  
   - `entry_price = current_price`.  
   - SL/TP: from breakout when available, else from `_compute_sl_tp_for_direction` (nearest S/R or ATR-based synthetic).

---

## 4. Candidates and selection (current design)

- **market_follow_through LONG / SHORT**: Always present. Base scores from `score_reaction_direction`.
- **breakout LONG / SHORT**: When `MomentumDetector` returns a signal, that side’s score gets the squeeze boost; we still choose **best of LONG vs SHORT** as above.

There is **no “none” candidate**. Direction is always LONG or SHORT.

---

## 5. Pipeline and DecisionResult

1. `build_context(unified_data, strategy)`  
   Uses `current_price`, `timestamp`, `atr_5m`, strategies from `unified_data`.

2. `compute_direction(context)`  
   Runs `score_reaction_direction`, adds optional breakout boost, applies tie-break, picks LONG or SHORT. Returns `DirectionResult(direction, long_score, short_score, reasoning, reaction_best=best)`.

3. `compute_entry(context, direction)`  
   Uses `direction.reaction_best`; `entry_price = current_price`, `setup_type` = `market_follow_through` or `breakout`.

4. `compute_sl_tp`  
   SL/TP from `best` (breakout) or `_compute_sl_tp_for_direction` (nearest S/R or ATR-based).

5. `build_feature_vector` → `build_result`  
   Produces `DecisionResult` with `engine_type="reaction"`, `entry_type="market"`, `setup_type`, `direction` (LONG or SHORT), `confidence=None`, `executable=False`, plus `breakdown` (including `long_score`, `short_score`, `entry_score`). Feature vector matches ML schema (ivs_*, spread_pct, etc.) and is validated.

---

## 6. MomentumProcessor → dashboard

- **MomentumProcessor** always writes `unified_data["reaction"]` with `direction` **LONG** or **SHORT** (stub uses LONG when engine missing).
- **Dashboard** always renders the reaction card (no “No reaction signal” from NONE). Low scores are shown as low-quality reaction; confidence remains `None` for now.

---

## 7. Summary

- **Direction** = **LONG** or **SHORT** only, from the better of long vs short score (with tie-break: `last_reaction_direction` then pressure sign).
- **Scores** come from `score_reaction_direction` (microstructure) plus optional breakout squeeze boost.
- **Relevant modules**: `core/execution/reactive_engine.py`, `core/execution/reaction_direction_scorer.py`, `core/services/momentum_processor.py`, `config.config` (`REACTION_*`).
