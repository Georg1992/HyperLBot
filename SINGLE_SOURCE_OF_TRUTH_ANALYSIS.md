# Single Source of Truth Analysis

## Issues Found

### 1. **ATR Calculation - DUPLICATE IMPLEMENTATION** ⚠️
**Locations:**
- `SRDataProvider.calculate_atr()` - Main implementation (used by calculator)
- `SRWeightTrainer._calculate_atr()` - Duplicate implementation (different logic)

**Issue**: Two different ATR calculation methods with potentially different results.

**Fix**: `SRWeightTrainer` should use `SRDataProvider.calculate_atr()` or a shared utility.

---

### 2. **Recency Calculations - MULTIPLE LOGICS** ⚠️⚠️
**Locations with different logic:**

1. **`SRScorer._calculate_recency_score()`**:
   - Exponential decay with half-life = 24h
   - Formula: `100 * exp(-lambda * time_since_touch)`
   - Returns: 0-100 score

2. **`SRDetector._calculate_point_score()`**:
   - Exponential decay with k=0.02
   - Formula: `exp(-0.02 * hours_since_touch)`
   - Returns: 0-1 multiplier

3. **`PredictionEngine._score_direction_for_entry()`**:
   - Strategy-specific thresholds (very_recent_hours, recent_hours, old_hours)
   - Step function: 1.0, 0.85, 0.70, 0.55
   - Returns: 0.55-1.0 factor

4. **`PredictionEngine._determine_optimal_entry_price()`**:
   - Strategy-specific thresholds (same as above)
   - Step function: 1.0, 0.95, 0.90, 0.85
   - Returns: 0.85-1.0 factor

5. **`EntryPriceCalculator._calculate_recent_action_multiplier()`**:
   - Hardcoded thresholds (6h, 24h, 72h)
   - Step function: 1.15, 1.05, 1.0, 0.95
   - Returns: 0.95-1.15 multiplier

**Issue**: 5 different recency calculation methods with different formulas and thresholds!

**Fix**: Create unified recency calculation utility with strategy-aware configuration.

---

### 3. **Proximity Calculations - MULTIPLE LOGICS** ⚠️⚠️
**Locations with different logic:**

1. **`SRScorer._calculate_proximity_score_enhanced()`**:
   - Exponential decay: `100 * exp(-distance / (k * atr_5m))`
   - k from config (default 0.15)
   - Too-close penalty
   - Returns: 0-100 score

2. **`SRDetector._calculate_point_score()`**:
   - Exponential decay: `exp(-distance / (25.0 * atr_5m))`
   - k=25.0 (hardcoded, different from scorer!)
   - Returns: 0-1 multiplier

3. **`PredictionEngine._score_direction_for_entry()`**:
   - Strategy-specific ATR thresholds (close_atr, medium_atr, far_atr)
   - Step function based on distance_atr
   - Returns: 0.55-1.0 factor

4. **`PredictionEngine._determine_optimal_entry_price()`**:
   - Strategy-specific ATR thresholds (optimal_atr, acceptable_atr, too_far_atr)
   - Step function based on distance_atr
   - Returns: 0.8-1.1 factor

5. **`PredictionEngine._score_entry_sr_factor()`**:
   - Strategy-specific ATR thresholds (optimal_atr, acceptable_atr, too_far_atr)
   - Step function with bonuses/penalties
   - Returns: adjusted score

**Issue**: 5 different proximity calculation methods with different formulas!

**Fix**: Create unified proximity calculation utility with strategy-aware configuration.

---

### 4. **Distance Calculations - DUPLICATE CODE** ⚠️
**Pattern found multiple times:**
```python
distance_pct = abs(entry_price - level_price) / current_price if current_price > 0 else 0.0
distance_pct = abs(current_price - support_price) / current_price if support_price > 0 else 1.0
distance = abs(level_price - current_price)
distance_atr = distance_pct / atr_pct if atr_pct > 0 else 10.0
```

**Issue**: Same distance calculation repeated in multiple places.

**Fix**: Create utility function for distance calculations.

---

### 5. **Time Calculations - DUPLICATE CODE** ⚠️
**Pattern found multiple times:**
```python
import time
current_time = time.time()
hours_since_touch = (current_time - last_touch_timestamp) / 3600.0 if last_touch_timestamp > 0 else 999.0
```

**Issue**: Same time calculation repeated in multiple places.

**Fix**: Create utility function for time calculations.

---

### 6. **Power/Strength Retrieval - INCONSISTENT** ⚠️
**Pattern found:**
```python
level_power = level_data.get("power") or level_data.get("strength_score", 50.0)
support_power = closest_support.get("power") or closest_support.get("strength_score", 50.0)
```

**Issue**: Same fallback logic repeated, inconsistent default values.

**Fix**: Create utility function for power retrieval.

---

## Recommended Fixes

### Priority 1: Create Utility Functions

1. **`core/utils/distance_utils.py`**:
   - `calculate_distance_pct(price1, price2, reference_price) -> float`
   - `calculate_distance_atr(distance_pct, atr_pct) -> float`

2. **`core/utils/time_utils.py`**:
   - `calculate_hours_since_touch(last_touch_timestamp) -> float`

3. **`core/utils/level_utils.py`**:
   - `get_level_power(level_data, default=50.0) -> float`

### Priority 2: Unify Recency Calculation

Create **`core/calculations/recency_calculator.py`**:
- Single recency calculation method
- Strategy-aware configuration
- Returns consistent factor (0-1) or score (0-100) based on context

### Priority 3: Unify Proximity Calculation

Create **`core/calculations/proximity_calculator.py`**:
- Single proximity calculation method
- Strategy-aware configuration
- Returns consistent factor or score based on context

### Priority 4: Fix ATR Duplication

- Make `SRWeightTrainer` use `SRDataProvider.calculate_atr()` or shared utility

---

## Impact Assessment

**High Impact** (affects scoring consistency):
- Recency calculations (5 different methods)
- Proximity calculations (5 different methods)

**Medium Impact** (code duplication, maintenance):
- Distance calculations
- Time calculations
- Power retrieval

**Low Impact** (isolated, less critical):
- ATR duplication (only in ML training)

---

## Estimated Effort

- **Priority 1** (Utilities): 1 hour
- **Priority 2** (Recency): 2 hours
- **Priority 3** (Proximity): 2 hours
- **Priority 4** (ATR): 30 min

**Total**: ~5.5 hours
