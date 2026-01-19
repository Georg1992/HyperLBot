# Single Source of Truth - Status Report

## ✅ **Fixed Issues**

### 1. **Distance Calculations** - FIXED ✅
- **Before**: `abs(price1 - price2) / reference_price` repeated 4+ times
- **After**: `core/utils/distance_utils.py` with `calculate_distance_pct()`
- **Refactored**: `prediction_engine.py` (4 locations)

### 2. **Time Calculations** - FIXED ✅
- **Before**: `hours_since_touch = (time.time() - timestamp) / 3600.0` repeated 3+ times
- **After**: `core/utils/time_utils.py` with `calculate_hours_since_touch()`
- **Refactored**: `prediction_engine.py`, `entry_price_calculator.py`

### 3. **Power Retrieval** - FIXED ✅
- **Before**: `level_data.get("power") or level_data.get("strength_score", 50.0)` repeated 3+ times
- **After**: `core/utils/level_utils.py` with `get_level_power()`
- **Refactored**: `prediction_engine.py` (3 locations), `entry_price_calculator.py`

### 4. **Recency Calculations (Prediction Engine)** - FIXED ✅
- **Before**: 2 different recency calculations in `prediction_engine.py` with duplicate code
- **After**: `core/calculations/recency_calculator.py` with strategy-aware methods
- **Refactored**: 
  - `_score_direction_for_entry()` → uses `RecencyCalculator.calculate_recency_factor()`
  - `_determine_optimal_entry_price()` → uses `RecencyCalculator.calculate_entry_recency_factor()`

### 5. **Proximity Calculations (Prediction Engine)** - FIXED ✅
- **Before**: 2 different proximity calculations in `prediction_engine.py` with duplicate code
- **After**: `core/calculations/proximity_calculator.py` with strategy-aware, context-aware method
- **Refactored**:
  - `_score_direction_for_entry()` → uses `ProximityCalculator.calculate_proximity_factor(context="direction")`
  - `_determine_optimal_entry_price()` → uses `ProximityCalculator.calculate_proximity_factor(context="entry")`

### 6. **R:R Calculation Duplication** - FIXED ✅
- **Before**: `_calculate_stop_and_target` calculated R:R but didn't return it, then `_predict_standard` recalculated
- **After**: `_calculate_stop_and_target` returns `(stop_loss, take_profit, rr_ratio, stop_loss_pct, take_profit_pct)`
- **Refactored**: `_predict_standard` uses returned values

---

## ⚠️ **Remaining Issues (Lower Priority)**

### 1. **SRScorer Proximity** - INTENTIONAL DIFFERENCE
**Location**: `core/calculations/sr_scorer.py::_calculate_proximity_score_enhanced()`

**Formula**: Exponential decay `100 * exp(-distance / (k * atr_5m))` with too-close penalty
**Purpose**: Scoring S/R levels during detection (0-100 score)
**Context**: Different from prediction engine proximity (which is a factor, not a score)

**Decision**: Keep separate - different purpose (scoring vs. factor adjustment)

---

### 2. **SRDetector Proximity/Recency** - INTENTIONAL DIFFERENCE
**Location**: `core/calculations/sr_detector.py::_calculate_point_score()`

**Formulas**:
- Proximity: `exp(-distance / (25.0 * atr_5m))` (k=25.0, different from scorer k=0.15)
- Recency: `exp(-0.02 * hours_since_touch)` (exponential decay, different from step function)

**Purpose**: Initial scoring during level clustering (before power calculation)
**Context**: Different from prediction engine (which uses step functions with strategy thresholds)

**Decision**: Keep separate - different purpose (initial clustering vs. entry/direction scoring)

---

### 3. **ATR Calculation Duplication** - LOW PRIORITY
**Locations**:
- `SRDataProvider.calculate_atr()` - Main implementation (used by calculator)
- `SRWeightTrainer._calculate_atr()` - Duplicate (used only in ML training)

**Issue**: Two implementations with potentially different logic

**Impact**: Low - only affects ML training, not main bot logic

**Recommendation**: Make `SRWeightTrainer` use `SRDataProvider.calculate_atr()` or shared utility (future improvement)

---

### 4. **EntryPriceCalculator Recent Action** - INTENTIONAL DIFFERENCE
**Location**: `core/calculations/entry_price_calculator.py::_calculate_recent_action_multiplier()`

**Logic**: Hardcoded thresholds (6h, 24h, 72h) with different multipliers (1.15, 1.05, 1.0, 0.95)
**Purpose**: Entry price offset adjustment (wider offset for recently tested levels)
**Context**: Different from scoring recency (which prefers recent levels)

**Decision**: Keep separate - different purpose (entry offset vs. scoring)

**Note**: Now uses `calculate_hours_since_touch()` utility for time calculation ✅

---

## 📊 **Summary**

### Fixed (Single Source of Truth):
- ✅ Distance calculations (4 locations)
- ✅ Time calculations (3 locations)
- ✅ Power retrieval (4 locations)
- ✅ Recency in prediction engine (2 locations)
- ✅ Proximity in prediction engine (2 locations)
- ✅ R:R calculation (1 duplication)

### Intentional Differences (Different Purposes):
- ⚠️ SRScorer proximity (scoring vs. factor)
- ⚠️ SRDetector proximity/recency (clustering vs. scoring)
- ⚠️ EntryPriceCalculator recent action (offset vs. scoring)

### Low Priority (Future Improvement):
- ⚠️ ATR duplication in SRWeightTrainer (only affects ML training)

---

## ✅ **Result**

**Main prediction engine now uses single source of truth for:**
- Distance calculations
- Time calculations
- Power retrieval
- Recency factors (strategy-aware)
- Proximity factors (strategy-aware, context-aware)
- R:R calculations

**All critical duplicate calculations in prediction flow have been eliminated.**
