# Support/Resistance & Prediction Engine Design Review

## Executive Summary

**Overall Assessment:** Sophisticated multi-layer architecture with several critical design flaws that undermine reliability and create tight coupling between components.

**Severity Levels:**
- 🔴 Critical: System-breaking issues
- 🟡 Major: Significant design problems  
- 🟠 Moderate: Noteworthy concerns
- 🔵 Minor: Optimization opportunities

---

## 1. S/R Calculation Pipeline

### Architecture Flow
```
Database → Liquidation Filter → Swing Detection → Clustering → MTF Alignment → 
Power Scoring → Deduplication → Liquidation Filter (again) → Prediction Engine
```

### 🔴 CRITICAL ISSUES

#### 1.1 Double Liquidation Filtering (Data Waste)
**Location:** `support_resistance_calculator.py` lines 423 + 545

**Problem:**
- Fetches data within liquidation range ±2% expansion (line 423)
- Then filters AGAIN by exact liquidation range (lines 545-555)
- Result: ~80% of fetched/processed data is discarded after expensive computation

**Evidence:**
```python
# Line 423: Fetch with expansion
additional_5m_candles = self._data_provider._fetch_candles_in_liquidation_range(
    current_price, long_liquidation, short_liquidation, days
)

# Lines 545-555: Filter again (strict)
if long_liquidation <= level.level <= current_price:
    levels_within_range.append(level)
else:
    logger.debug(f"⚠️ Support ${level.level:.2f} filtered: outside liquidation range")
```

**Impact:**
- Wasted database queries (fetches support at $87k, filters it out)
- Wasted CPU (clustering/scoring levels that get discarded)
- Misleading logs (user sees "found 627 swing points" → only ~50 used)

**Fix:** Either fetch strict OR filter strict, not both.

---

#### 1.2 Liquidation Range is Too Restrictive for Strategy Planning
**Location:** `support_resistance_calculator.py` lines 535-555

**Problem:**
- With 40x leverage, liquidation range is only ±1.2% from current price
- This filters out valid S/R levels at $87k-$89k support, $92k-$94k resistance
- Traders need to see levels beyond immediate liquidation for:
  - Multi-level entries
  - Wider stop losses
  - Market structure understanding
  - Breakout targets

**Current behavior:**
```
Current: $90,778
Long Liq: $89,665 (1.2% below)
Short Liq: $91,891 (1.2% above)

Filtered out:
- Support: $87,442, $87,325, $87,395 (all 2-4% below, valid levels!)
- Resistance: $93,821, $94,100, $93,944 (all 3-4% above, valid levels!)
```

**Impact:**
- Blinds system to important price levels
- Strategy manager can't see range boundaries
- Breakout detection impossible (needs levels beyond liquidation)

**Fix:** Make liquidation filtering optional or expand to 2-3x liquidation range.

---

### 🟡 MAJOR ISSUES

#### 1.3 Power Calculation Happens Too Late
**Location:** `support_resistance_calculator.py` line 570

**Problem:**
- Levels are clustered, MTF-aligned, filtered BEFORE power is calculated
- But clustering quality depends on level strength (should use power, not just touches)
- Filtering by liquidation before scoring means we lose high-power levels outside range

**Flow:**
```
1. Detect swings (strength=raw)
2. Cluster (uses strength, not power)
3. MTF align
4. Filter by liquidation
5. Calculate power ← TOO LATE
```

**Impact:**
- Weak levels with many touches rank higher than strong levels with fewer touches
- Can't optimize clustering based on actual level quality

**Fix:** Calculate preliminary power before clustering, refine after MTF.

---

#### 1.4 Cluster Size Filter is Arbitrary
**Location:** `support_resistance_calculator.py` lines 560-566

**Problem:**
- Requires `cluster_size >= 2` to be valid S/R level
- But a single strong swing point (e.g., daily high with 15 touches) is discarded
- No justification for why 2 is the magic number

```python
if level.cluster_size >= 2:
    scorable_levels.append(level)
# Single isolated swing points (cluster_size=1) are discarded
```

**Impact:**
- Loses significant levels that don't happen to have nearby swing points
- Especially problematic in low-volatility periods (fewer swing points)

**Fix:** Use power threshold instead of cluster size (power >= 40 = valid).

---

### 🟠 MODERATE ISSUES

#### 1.5 Progressive Time Expansion is Inefficient
**Location:** `support_resistance_calculator.py` lines 397-465

**Problem:**
- Loops through 1m, 3m, 6m, 1y, 2y, 5y until finding 2+ levels per side
- But doesn't check if more time will help (if 6 months has 0 levels, 1 year won't either)
- Each iteration refetches overlapping data

**Impact:**
- Can query 5+ years when 1 month would suffice
- Or waste time checking 5 years when problem is liquidation range too strict

**Fix:** Check if levels exist in range before expanding time, or fetch all upfront.

---

## 2. Prediction Engine Integration

### Architecture
```
Unified Data → Generate All Setups → Score Entry + Direction → Select Best → 
Calculate SL/TP → Return Prediction
```

### 🔴 CRITICAL ISSUES

#### 2.1 Entry Price Determination is Circular
**Location:** `prediction_engine.py` lines 1746-1888

**Problem:**
- Generates 4 candidate entry prices around S/R level
- Scores each using S/R proximity factor
- But proximity is based on distance from S/R level
- So it always picks the entry AT the level (distance=0, best score)
- The other 3 candidates are pointless

```python
candidates = []
candidates.append(level_price)  # This always wins
candidates.append(level_price + offset * 0.3)  # Lower score
candidates.append(level_price + offset * 0.6)  # Even lower
candidates.append(level_price + offset * 1.0)  # Lowest score
```

**Impact:**
- Wasted computation (3 of 4 candidates never win)
- Doesn't account for spread/slippage (always picks exact level)
- Comment says "for spread/slippage" but logic doesn't support it

**Fix:** Use different scoring for candidates (e.g., fill probability) or remove candidates.

---

#### 2.2 Direction Scoring Applies Contextual Factors Asymmetrically
**Location:** `prediction_engine.py` lines 1299-1308

**Problem:**
- For a LONG setup, applies proximity/recency/strength to LONG score only
- Keeps SHORT score as base (no adjustment)
- Then compares contextual LONG vs base SHORT (unfair comparison)

```python
if entry_direction == "LONG":
    contextual_long_score = base_long_score * proximity * recency * strength * alignment
    contextual_short_score = base_short_score  # No adjustment!
```

**Impact:**
- Artificially inflates LONG score relative to SHORT
- Can pick LONG even when SHORT signals are stronger
- Direction determination is biased toward the setup direction

**Fix:** Apply distance decay to BOTH scores, or compare base scores directly.

---

### 🟡 MAJOR ISSUES

#### 2.3 Stop Loss Calculation Ignores Liquidation Price
**Location:** `prediction_engine.py` lines 587-650 (approx, need to verify)

**Problem:**
- Calculates stop loss based on ATR or S/R level
- But doesn't check if SL is beyond liquidation price
- With 40x leverage, a 1% SL could hit liquidation first

**Impact:**
- SL might be unreachable (liquidation happens first)
- Risk calculations are wrong (actual risk is to liquidation, not SL)

**Fix:** Cap SL at liquidation price, adjust position size to maintain R:R.

---

#### 2.4 Entry Quality and Direction Support Are Not Independent
**Location:** `prediction_engine.py` lines 1890-1970 (approx)

**Problem:**
- Claims to score "entry quality" and "direction support" separately
- But both use the same level_data (power, proximity, recency)
- Direction scoring applies contextual factors using entry_price
- So they're tightly coupled, not orthogonal

**Impact:**
- Can't tell if setup is good because entry is strong OR direction is strong
- Double-counts some factors (e.g., level power used in both)

**Fix:** Make direction scoring truly independent (only use trend, RSI, pressure, patterns).

---

### 🟠 MODERATE ISSUES

#### 2.5 Strategy-Specific Entry Weights Are Ignored
**Location:** `prediction_engine.py` line 1508

**Problem:**
- Defines `entry_weights` in config (SR=50%, RSI=20%, etc.)
- But these are default fallback weights, not strategy-specific
- Code comment says "config defaults are OK" (not sophisticated)

**Impact:**
- All strategies use same entry weights (scalping = swing = trend following)
- Strategy config has no effect on entry scoring

**Fix:** Add strategy-specific entry_weights to config, use them.

---

## 3. Stop Loss / Take Profit Logic

### 🟡 MAJOR ISSUES

#### 3.1 R:R Ratio is Calculated But Not Enforced
**Location:** `prediction_engine.py` `_calculate_stop_and_target`

**Problem:**
- Calculates R:R ratio after setting SL/TP
- But doesn't reject setups with poor R:R (e.g., 0.8:1)
- Just logs it and continues

**Impact:**
- System can take trades with negative expectancy
- No minimum R:R filter (should be >= 1.5:1)

**Fix:** Add R:R threshold to config, reject setups below it.

---

#### 3.2 Take Profit Uses Fixed % But Market is Dynamic
**Location:** Config defaults (profit_target = 0.012 for standard)

**Problem:**
- TP is fixed % from entry (1.2% for standard strategy)
- Ignores next resistance level, volatility, trend strength
- Might close before reaching obvious target (resistance at +2%)
- Or hold too long in ranging market (TP beyond resistance)

**Impact:**
- Suboptimal exits (leaves money on table or holds too long)
- Doesn't adapt to market structure

**Fix:** Calculate TP as "next S/R level" or "current S/R + 2×ATR", whichever is closer.

---

## 4. Data Flow & Dependencies

### Current Architecture
```
SRCalculator ←→ DataProvider ←→ Database
     ↓
SRScorer (power)
     ↓
SRLevelFilter
     ↓
PredictionEngine → Setups
     ↓
StrategyManager → Decision
```

### 🔴 CRITICAL ISSUES

#### 4.1 Circular Dependency: Strategy → SR → Strategy
**Problem:**
- `SRCalculator` needs strategy to filter levels (`max_distance_pct`)
- But strategy is determined by `StrategyManager`
- Which needs S/R levels to make decision
- Circular: Strategy → SR → Strategy

**Current workaround:**
- Uses "standard" strategy for S/R fetch
- Then strategy manager selects actual strategy
- Then prediction engine uses different strategy
- Result: S/R levels fetched for wrong strategy

**Impact:**
- Scalping strategy gets S/R levels filtered for 3% range (standard)
- But scalping only needs 0.5% range
- Wasted data and wrong levels

**Fix:** Break cycle - fetch S/R strategy-agnostic, filter per-strategy in prediction engine.

---

#### 4.2 Level Filtering Happens in 3 Different Places
**Locations:**
- `SRCalculator._process_candles_to_levels` (liquidation filter)
- `SRLevelFilter.filter_for_entry_setup` (strategy filter)
- `PredictionEngine._generate_all_setups` (additional filter?)

**Problem:**
- No single source of truth for "which levels are valid"
- Each layer applies different filters
- Hard to reason about what levels actually reach prediction engine

**Impact:**
- Debugging is nightmare (which filter removed my level?)
- Can't easily add new filter (have to update 3 places)
- Filters might conflict (one allows, another blocks)

**Fix:** Single filter chain in one place, configurable by strategy.

---

## 5. Sophistication Assessment

### ✅ Well-Designed Aspects

1. **Multi-Timeframe Alignment:** Confirms levels across 5m/15m/1h/1d (good)
2. **Power Scoring Formula:** Touch + reversal_probability + volume with weights (solid)
3. **Proximity-Based Decay:** Exponential decay for distance relevance (sophisticated)
4. **Strategy-Specific Configs:** Different parameters per strategy (good intent, poor execution)
5. **NO FALLBACKS Policy:** Fails fast instead of degrading silently (excellent)

### ❌ Poorly-Designed Aspects

1. **Double Liquidation Filtering:** Fetches then discards (wasteful)
2. **Circular Dependencies:** Strategy ↔ SR (architectural flaw)
3. **Entry Price Candidates:** Always picks level (circular logic)
4. **Asymmetric Direction Scoring:** Biased comparisons (unfair)
5. **Ignored Liquidation in SL:** Risk calculations wrong (dangerous)
6. **Fixed TP Targets:** Ignores market structure (suboptimal)
7. **Triple Filtering:** 3 places filter levels (scattered responsibility)

---

## 6. Prioritized Recommendations

### 🔴 Critical Fixes (Do First)

1. **Remove double liquidation filtering**
   - Keep fetch expansion OR final filter, not both
   - Saves 80% wasted computation

2. **Expand liquidation range or make optional**
   - Use 2-3x liquidation range for S/R discovery
   - Filter by strategy `max_distance_pct`, not liquidation

3. **Fix circular strategy dependency**
   - Fetch S/R without strategy filter
   - Apply strategy-specific filter in prediction engine

4. **Cap stop loss at liquidation price**
   - Prevents unreachable SLs
   - Adjust position size to maintain R:R

### 🟡 Major Improvements (Do Second)

5. **Replace cluster size filter with power threshold**
   - `power >= 40` instead of `cluster_size >= 2`
   - Keeps strong single-point levels

6. **Make direction scoring independent**
   - Don't use entry_price/level_data in direction scoring
   - Only use trend/RSI/pressure/patterns

7. **Use adaptive TP based on next S/R level**
   - TP = min(next_resistance, entry + 2×ATR)
   - Respects market structure

8. **Add minimum R:R threshold**
   - Reject setups with R:R < 1.5:1
   - In config per strategy

### 🟠 Moderate Enhancements (Do Third)

9. **Optimize progressive time expansion**
   - Check if time expansion will help before fetching
   - Or fetch all upfront (5y data is only ~200k candles)

10. **Remove pointless entry candidates**
    - Just use level_price directly
    - Add spread offset separately if needed

11. **Consolidate filtering logic**
    - Single filter chain in SRLevelFilter
    - Called once from prediction engine

---

## 7. Conclusion

**Sophistication Level:** 6/10
- Strong foundation (MTF, power scoring, proximity decay)
- Undermined by architectural flaws (circular deps, double filtering, asymmetric scoring)

**Reliability:** 4/10
- Critical issues with liquidation handling, SL placement, circular dependencies
- Will produce incorrect trades in edge cases

**Maintainability:** 5/10
- NO FALLBACKS policy is excellent
- But scattered filtering and tight coupling make changes risky

**Recommendation:** Address critical fixes before production trading. Current design will lose money on trades where SL is beyond liquidation or where important S/R levels are filtered out.
