# ML Training Workflow: How It Actually Works

## Current Implementation

### ❌ Not Exactly What You Described

The current implementation does **NOT** automatically switch to new weights when training completes. Here's how it actually works:

## Actual Workflow (Current)

### Scenario 1: First Launch (No Existing Weights)

1. **You launch bot**
   - `SRScorer` initializes
   - Tries to load learned weights → **File doesn't exist**
   - **Uses static weights** from config
   - Logs: No learned weights found

2. **Training manager initializes** (if enabled)
   - Checks if weights file exists → **No**
   - Checks if training is needed → **Yes (weights are old/missing)**
   - **Starts training in background thread**

3. **Training runs in background** (non-blocking)
   - Progress: 0% → 50% → 100%
   - Takes time (30 minutes - 2 hours depending on data)
   - **Bot continues trading with static weights**

4. **Training completes**
   - Saves weights to `data/sr_weights/standard_elasticnet_weights.json`
   - Updates status: `completed`
   - **Bot STILL uses static weights** (SRScorer already initialized)

5. **New weights are picked up**
   - **Only on NEXT bot restart**
   - When you restart, `SRScorer` loads the new weights
   - Logs: `✅ Loaded learned weights for strategy 'standard'`

### Scenario 2: Subsequent Launches (Weights Already Exist)

1. **You launch bot**
   - `SRScorer` initializes
   - Tries to load learned weights → **File exists**
   - **Uses learned weights immediately**
   - Logs: `✅ Loaded learned weights for strategy 'standard'`

2. **Training manager initializes**
   - Checks if weights file exists → **Yes**
   - Checks weights age → If < 7 days, no training needed
   - If > 7 days old, starts retraining in background

3. **Training runs** (if needed)
   - Updates weights file when complete
   - New weights picked up on **next restart**

## The Problem

**Current behavior**: New weights are only picked up on bot restart, not immediately after training completes.

**Your expectation**: When training completes (100%), bot should immediately start using new weights.

## Why This Happens

`SRScorer` loads weights **only once** during initialization:

```python
# In SRScorer.__init__()
def __init__(self, strategy: str = "standard"):
    learned_weights = self._load_learned_weights(strategy)  # Loads once
    if learned_weights:
        self._scoring_weights = {...}  # Sets weights once
    else:
        self._scoring_weights = {...}  # Static weights
```

After initialization, weights are **not reloaded** - they're stored in `self._scoring_weights`.

## Solutions

### Option 1: Current Behavior (Simplest)

**Accept that weights are picked up on restart**
- ✅ Simple, no code changes needed
- ✅ No risk of mid-trade weight changes
- ❌ Need to restart bot to use new weights
- ❌ Delayed benefit from training

### Option 2: Add Weight Reloading (Better UX)

**Add mechanism to reload weights after training completes**

**Changes needed**:

1. **Add reload method to SRScorer**:
```python
def reload_weights(self, strategy: str = None):
    """Reload learned weights from file"""
    strategy = strategy or self._strategy
    learned_weights = self._load_learned_weights(strategy)
    if learned_weights:
        logger.info(f"🔄 Reloaded learned weights for strategy '{strategy}'")
        self._scoring_weights = {
            'proximity': learned_weights.get("proximity", 0.15),
            'touch': learned_weights.get("touch", 0.50),
            # ... etc
        }
```

2. **Notify SRScorer when training completes**:
```python
# In SRWeightTrainingManager._run_training()
self.trainer.save_weights(normalized_weights, strategy=self.strategy, method="elasticnet")

# Notify SRScorer to reload (if accessible)
if hasattr(self, '_notify_scorer'):
    self._notify_scorer(strategy=self.strategy)
```

3. **Register callback in SystemInitializer**:
```python
# When initializing training manager
training_manager = get_global_training_manager(strategy="standard")

# Register scorer for notifications
from core.calculations.support_resistance_calculator import SupportResistanceCalculator
sr_calculator = system_initializer.singleton_systems.get("support_resistance_calculator")
if sr_calculator:
    training_manager.register_scorer_reload_callback(
        lambda s: sr_calculator._scorer.reload_weights(s)
    )
```

**Pros**:
- ✅ New weights used immediately
- ✅ Better UX
- ✅ Faster adaptation

**Cons**:
- ❌ More complex code
- ❌ Risk of mid-trade weight changes
- ❌ Need to handle concurrent access

### Option 3: Hybrid Approach (Recommended)

**Only reload weights at safe times** (e.g., between trades, at strategy change)

- ✅ Safer than Option 2
- ✅ Better than Option 1
- ✅ Can be implemented incrementally

## Recommendation

**For now**: Use Option 1 (current behavior)
- Weights picked up on restart
- Simple and safe
- Works well enough

**Future enhancement**: Implement Option 3 (hybrid)
- Reload weights when safe
- Better UX without risk

## Actual Workflow Summary

**First Launch**:
1. Bot starts → Uses static weights
2. Training starts in background
3. Training completes → Saves weights
4. **Need to restart** → New weights loaded

**Subsequent Launches**:
1. Bot starts → Uses learned weights (from previous training)
2. If weights > 7 days old → Retraining starts
3. Retraining completes → Saves new weights
4. **Need to restart** → New weights loaded

**Key Point**: Weights are loaded at **startup**, not when training completes.
