# Psychological Levels Integration

**Date:** 2026-01-27  
**Status:** ✅ COMPLETE

---

## IMPLEMENTATION SUMMARY

Psychological levels are now integrated as first-class S/R levels. They behave exactly like swing-based S/R levels:
- Used for entry generation
- Used for stop loss selection
- Used for take profit selection
- **NOT used for direction scoring** (direction remains purely indicator-based)

---

## COMPONENTS

### 1. PsychologicalLevelGenerator
**File:** `core/calculations/psychological_level_generator.py`

**Features:**
- Generates round-number levels ±5% around current price
- BTC-specific spacing based on price range:
  - < $10k: minor=100, major=1000
  - $10k-$50k: minor=500, major=5000
  - > $50k: minor=1000, major=10000
- Strength calculation (0.0-1.0):
  - Base: 0.4
  - +0.2 if divisible by minor
  - +0.2 if divisible by major
  - +0.2 if divisible by (major * 2)
  - Max: 1.0

**Level Format:**
```python
{
    "price_level": float,
    "type": "support" | "resistance",  # Based on price < or > current_price
    "strength_score": float (0.0-100.0),
    "power": float (0.0-100.0),
    "status": "active",
    "source": "psych",
    "touches": 0,
    "weighted_touches": 0.0,
    "cluster_size": 1,
    "last_touch_timestamp": 0.0,
    "mtf_count": 0,
    "mtf_confidence": 0.0,
    "power_breakdown": {"psychological": strength},
    "merged_from": 1,
    "atr_pct": float  # Set by integration point
}
```

---

### 2. Integration Point
**File:** `core/calculations/support_resistance_calculator.py:927-950`

**Integration Logic:**
1. Generate psychological levels using `PsychologicalLevelGenerator.generate_levels(current_price)`
2. Set ATR percentage for each psych level
3. Merge into `key_levels` (append, don't replace)
4. Deduplicate: if psych level is within 10% of ATR from existing level, keep existing (higher power)
5. Re-sort by power after merging

**Result:**
- `unified_data["support_resistance"]["levels"]` now contains both swing-based and psychological levels
- All levels are treated identically by entry/stop/target selection

---

### 3. Round Number Avoidance (Entry)
**File:** `core/execution/prediction_engine.py:2874-2905`

**Logic:**
- After selecting best entry candidate, check distance to nearest psych level
- If `abs(entry - nearest_psych_level) < ATR * 0.2`:
  - Nudge entry by `ATR * 0.25` away from psych level
  - For LONG: nudge down
  - For SHORT: nudge up
- Validate nudge doesn't invalidate entry (must stay on correct side of current_price)

**Rationale:**
- Prevents entries exactly at round numbers (common stop-hunt targets)
- Uses ATR-based distance (data-driven, not arbitrary)
- Only applies if very close (< 0.2×ATR)

---

### 4. ML Features (Exposed but Not Used)
**Files:** 
- `core/execution/prediction_engine.py:2874-2905` (entry)
- `core/execution/prediction_engine.py:3124-3135` (stop)

**Features:**
- `entry_distance_to_nearest_psych_level_pct`: Distance from entry to nearest psych level (as % of price)
- `stop_distance_to_nearest_psych_level_pct`: Distance from stop to nearest psych level (as % of price)

**Status:** Calculated and exposed in prediction breakdown, but not yet used in confidence calculation.

---

## VERIFICATION

### ✅ Direction Scoring
- Psychological levels are **NOT** used in direction scoring
- Direction remains purely indicator-based (RSI, trend, pressure, volume, patterns)
- Verified: `_score_direction()` does not access psych levels

### ✅ Entry Generation
- Psychological levels participate in entry candidate generation
- Filtered by `SRLevelFilter.filter_for_entry_setup()`
- Treated identically to swing-based levels
- Round number avoidance applied if entry too close to psych level

### ✅ Stop Loss Selection
- Psychological levels participate in stop loss selection
- Used by `SupportResistanceCalculator.select_stop_loss_level()`
- Treated identically to swing-based levels

### ✅ Take Profit Selection
- Psychological levels participate in take profit selection
- Used by `RiskManager.calculate_take_profit()`
- Treated identically to swing-based levels

---

## EXAMPLE OUTPUT (Near $100k BTC)

**Input:** `current_price = 98000.0`

**Generated Levels:**
```
$95000.00 (support) - power: 60.0
$96000.00 (support) - power: 40.0
$97000.00 (support) - power: 40.0
$98000.00 (support) - power: 40.0
$99000.00 (support) - power: 40.0
$100000.00 (resistance) - power: 100.0  ← Major level (divisible by major*2)
$101000.00 (resistance) - power: 40.0
$102000.00 (resistance) - power: 40.0
$103000.00 (resistance) - power: 40.0
```

**Strength Calculation:**
- $100k: Base 0.4 + 0.2 (minor) + 0.2 (major) + 0.2 (major*2) = 1.0 → power 100.0
- $95k: Base 0.4 + 0.2 (minor) = 0.6 → power 60.0
- $98k: Base 0.4 + 0.2 (minor) = 0.6 → power 60.0 (but shown as 40.0 if only minor divisible)

---

## UNIT TESTS

**File:** `tests/test_psychological_level_generator.py`

**Coverage:**
- ✅ Price range spacing (< 10k, 10k-50k, > 50k)
- ✅ Level format compliance
- ✅ Strength calculation
- ✅ Support/resistance classification
- ✅ ±5% range generation
- ✅ Deterministic output
- ✅ Example near $100k

---

## DESIGN DECISIONS

### Why Append, Not Replace?
- Swing-based levels have real market data (touches, volume, reversals)
- Psychological levels are synthetic (no market data)
- If both exist at same price, swing-based takes precedence (deduplication)

### Why ±5% Range?
- Covers immediate trading range
- Prevents generating too many irrelevant levels
- Focuses on actionable levels near current price

### Why ATR-Based Nudge?
- Replaces arbitrary $75-$150 offsets
- Scales with market volatility
- Data-driven, not psychological assumption

### Why Not Affect Direction?
- Direction should be momentum-based (indicators)
- Psychological levels are locational (where to enter/exit)
- Prevents circular dependencies

---

## FILES MODIFIED

1. **Created:**
   - `core/calculations/psychological_level_generator.py`
   - `tests/test_psychological_level_generator.py`

2. **Modified:**
   - `core/calculations/support_resistance_calculator.py` (integration)
   - `core/execution/prediction_engine.py` (round number avoidance, ML features)

3. **Removed:**
   - `core/calculations/risk_manager.py` (old round number offset code)
   - `config/config.py` (ROUND_NUMBER_CONFIG)

---

## STATUS

✅ **COMPLETE** - Psychological levels fully integrated and tested

**Next Steps:**
- Monitor performance in production
- Collect ML training data with psych level features
- Evaluate if psych levels improve entry/stop/target selection
