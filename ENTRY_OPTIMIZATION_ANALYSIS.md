# Entry Price Optimization Analysis
**Date:** 2026-01-27  
**Issue:** Closest S/R level always wins instead of true multi-factor optimization

---

## ROOT CAUSE ANALYSIS

### Problem 1: Aggressive Pre-filtering
**Location:** `core/execution/prediction_engine.py:2553-2558`

**Current Behavior:**
- Levels are pre-filtered if `level_distance_atr > max_distance_atr`
- Only the closest levels get candidates generated
- Stronger but farther levels never compete

**Impact:** 
- Example: Level at 5.1×ATR with power 0.95 is skipped entirely
- Level at 4.0×ATR with power 0.60 gets all candidates
- System never evaluates if strong far level could win

---

### Problem 2: Fill Probability Dominance (40% weight)
**Location:** `core/execution/prediction_engine.py:2672-2693`

**Current Formula:**
```
fill_probability = 100 * exp(-distance_atr / 3.0)
```

**Score Impact by Distance:**
- 0.5×ATR: fill_prob ≈ 84.6 → **33.8 points** (40% weight)
- 2.0×ATR: fill_prob ≈ 51.3 → **20.5 points**
- 4.0×ATR: fill_prob ≈ 26.4 → **10.6 points**

**Gap:** 23.2 points difference between close and far entries

---

### Problem 3: Level Strength Double-Penalized (15% weight)
**Location:** `core/execution/prediction_engine.py:2733-2747`

**Current Formula:**
```
level_strength = level_power * exp(-distance_atr / 2.5)
```

**Score Impact:**
- Strong level (0.9 power) at 0.5×ATR: 0.9 * 0.82 ≈ 0.74 → **11.1 points** (15% weight)
- Strong level (0.9 power) at 4.0×ATR: 0.9 * 0.20 ≈ 0.18 → **2.7 points**

**Gap:** 8.4 points difference

**Issue:** Level strength is already proximity-weighted, but then fill_probability ALSO penalizes distance. This is double-counting distance penalty.

---

### Problem 4: Per-Level Optimization, Not Global
**Location:** `core/execution/prediction_engine.py:2349-2395`

**Current Flow:**
1. Loop through each level
2. Generate candidates for that level
3. Score candidates for that level
4. Return best candidate from that level
5. Compare best candidates from all levels

**Problem:** If only closest level has valid candidates (due to pre-filtering), it always wins.

---

## MATHEMATICAL ANALYSIS

### Current Scoring Example:

**Scenario:** Two levels competing
- **Level A:** 0.5×ATR away, power 0.60, entry at 0.3×ATR offset
- **Level B:** 3.5×ATR away, power 0.95, entry at 0.3×ATR offset

**Level A Candidate (at 0.8×ATR total distance):**
- Fill prob: 100 * exp(-0.8/3) ≈ 77.0 → 40% * 77 = **30.8 points**
- Liq safety: ~50 (assuming adequate buffer) → 35% * 50 = **17.5 points**
- Level strength: 0.60 * exp(-0.8/2.5) ≈ 0.44 → 15% * 44 = **6.6 points**
- Spread penalty: ~8.0 → -10% * 8 = **-0.8 points**
- **Total: ~54.1 points**

**Level B Candidate (at 3.8×ATR total distance):**
- Fill prob: 100 * exp(-3.8/3) ≈ 28.2 → 40% * 28.2 = **11.3 points**
- Liq safety: ~50 (same) → 35% * 50 = **17.5 points**
- Level strength: 0.95 * exp(-3.8/2.5) ≈ 0.21 → 15% * 21 = **3.2 points**
- Spread penalty: ~0.0 (far) → -10% * 0 = **0.0 points**
- **Total: ~32.0 points**

**Result:** Level A wins by 22.1 points, even though Level B is much stronger (0.95 vs 0.60).

---

## PROPOSED SOLUTIONS

### Solution 1: Adaptive Pre-filtering (Allow Strong Levels)
**Change:** Instead of hard cutoff, allow levels slightly beyond max_distance if they're very strong

```python
# Current: Hard cutoff
if level_distance_atr > max_distance_atr:
    return None

# Proposed: Adaptive cutoff
strength_threshold = 0.8  # Very strong level
if level_distance_atr > max_distance_atr:
    # Allow strong levels up to 1.2× max_distance
    if level_power >= strength_threshold and level_distance_atr <= max_distance_atr * 1.2:
        logger.debug(f"📊 Strong level ${level_price:.2f} (power: {level_power:.2f}) allowed despite distance {level_distance_atr:.2f}×ATR")
    else:
        return None
```

---

### Solution 2: Adjust Fill Probability Decay (Flatter Curve)
**Change:** Make fill probability decay slower so farther entries aren't as penalized

**Current:** `fill_decay_factor = 3.0` (steep decay)
**Proposed:** `fill_decay_factor = 5.0` (slower decay)

**Impact:**
- 0.5×ATR: fill_prob ≈ 90.5 (was 84.6) → **36.2 points**
- 4.0×ATR: fill_prob ≈ 44.9 (was 26.4) → **18.0 points**
- **Gap reduced:** 18.2 points (was 23.2)

---

### Solution 3: Increase Level Strength Weight
**Change:** Increase level_strength weight from 15% to 25%, decrease fill_probability from 40% to 30%

**New Weights:**
- Fill probability: 30% (was 40%)
- Liquidation safety: 35% (unchanged)
- Level strength: 25% (was 15%)
- Spread penalty: 10% (unchanged)

**Impact:**
- Level A (0.60 power): 25% * 44 = **11.0 points** (was 6.6)
- Level B (0.95 power): 25% * 21 = **5.3 points** (was 2.7)
- **Gap reduced:** Stronger levels get more weight

---

### Solution 4: Remove Proximity Weighting from Level Strength
**Change:** Use raw level power, not proximity-weighted

**Rationale:** Fill probability already penalizes distance. Double-penalizing in level strength is unfair to strong far levels.

**Current:** `level_strength = level_power * proximity_factor`
**Proposed:** `level_strength = level_power` (raw power, no decay)

**Impact:**
- Level A (0.60 power): 25% * 60 = **15.0 points** (was 11.0)
- Level B (0.95 power): 25% * 95 = **23.8 points** (was 5.3)
- **Gap:** Level B now gets 8.8 more points from strength

---

### Solution 5: Global Candidate Pool (Best Approach)
**Change:** Collect ALL candidates from ALL levels, then score and select globally

**Current Flow:**
```
For each level:
  Generate candidates
  Score candidates
  Return best candidate from this level
Select best from all level winners
```

**Proposed Flow:**
```
For each level:
  Generate candidates
  Add to global candidate pool
Score all candidates in global pool
Select best candidate globally
```

**Benefits:**
- Strong far levels can compete directly
- True multi-factor optimization
- No per-level bias

---

## RECOMMENDED IMPLEMENTATION

### Priority 1: Global Candidate Pool (Solution 5)
**Impact:** HIGH - Enables true optimization
**Complexity:** MEDIUM - Requires refactoring candidate collection

### Priority 2: Adjust Weights (Solution 3)
**Impact:** MEDIUM - Better balance
**Complexity:** LOW - Config change

### Priority 3: Flatter Fill Decay (Solution 2)
**Impact:** MEDIUM - Reduces distance bias
**Complexity:** LOW - Config change

### Priority 4: Remove Proximity Weighting (Solution 4)
**Impact:** HIGH - Eliminates double penalty
**Complexity:** LOW - Code change

### Priority 5: Adaptive Pre-filtering (Solution 1)
**Impact:** LOW - Edge case handling
**Complexity:** LOW - Code change

---

## IMPLEMENTATION PLAN

1. **Refactor to global candidate pool** (Solution 5)
2. **Adjust entry scoring weights** (Solution 3)
3. **Remove proximity weighting from level strength** (Solution 4)
4. **Flatten fill probability decay** (Solution 2)
5. **Add adaptive pre-filtering** (Solution 1)
6. **Add debug logging** for candidate scores

---

## EXPECTED OUTCOMES

After fixes:
- Strong far levels (power >0.8) can compete with weak close levels
- Level strength properly influences selection
- True multi-factor optimization across all candidates
- Better entry selection for 40x leverage (stronger levels = better bounces)
