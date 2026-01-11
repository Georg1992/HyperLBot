# Dependency Checking Code Analysis

## Current Implementation

**Location**: `main.py` lines 126-159

**Function**: `check_and_install_dependencies()`

## Issues Found

### ❌ Issue 1: Missing Required Dependencies

The `required_modules` list is **incomplete**. It's missing several dependencies from `requirements.txt`:

**Currently checked:**
```python
required_modules = [
    'flask', 'flask_socketio', 'yfinance', 'requests', 'pandas', 
    'numpy', 'loguru', 'python-dotenv', 'httpx', 'aiohttp'
]
```

**Missing from `requirements.txt`:**
- `eth_account` - Required for Hyperliquid API (Web3/Ethereum)
- `websockets` - Required for WebSocket connections
- `feedparser` - Required for RSS news feed
- `vaderSentiment` - Required for sentiment analysis

### ❌ Issue 2: Module Name vs Package Name Mismatch

The function uses **module import names** instead of **pip package names**:
- `'flask_socketio'` → Should be `'flask-socketio'` for pip install
- `'python-dotenv'` → Should be `'python-dotenv'` (correct) but imported as `'dotenv'`
- `'vaderSentiment'` → Should be `'vaderSentiment'` (correct) but imported as `'vaderSentiment'`

This works by accident because pip can handle some variations, but it's not reliable.

### ⚠️ Issue 3: ML Dependencies Not Included (But Should Be Conditional)

**Current state**: ML dependencies (`scikit-learn`) are **not** in the required list.

**Should ML dependencies be:**
- **Optional** (only installed if ML training is enabled)?
- **Required** (always installed)?

**Recommendation**: **OPTIONAL** - Only install if ML training is enabled, because:
1. ML training is currently disabled
2. Bot works fine without ML dependencies
3. Installing unnecessary packages is wasteful
4. Can be enabled later when ML training is enabled

### ❌ Issue 4: No Version Pinning

The function installs packages without versions (e.g., `pip install flask` instead of `pip install flask>=3.0.0`).

This can lead to:
- Incompatible versions
- Breaking changes in future package updates
- Inconsistent environments

**However**, installing from `requirements.txt` would solve this.

### ⚠️ Issue 5: Using `--break-system-packages` Flag

The code uses `--break-system-packages` flag:
```python
subprocess.check_call([
    sys.executable, "-m", "pip", "install", module, 
    "--break-system-packages", "--quiet"
])
```

**This flag:**
- Only works on Linux/Unix systems
- Can break system Python packages
- Not recommended for production

**Better approach**: Use virtual environments instead.

## Recommended Fixes

### Option 1: Fix Current Approach (Simple)

**Update `required_modules` list:**
```python
required_modules = [
    # Core dependencies
    'flask', 'flask_socketio', 'yfinance', 'requests', 'pandas', 
    'numpy', 'loguru', 'dotenv',  # python-dotenv imports as 'dotenv'
    'httpx', 'aiohttp',
    # Missing dependencies
    'eth_account',  # eth_account package
    'websockets',   # websockets package
    'feedparser',   # feedparser package
    'vaderSentiment',  # vaderSentiment package
]
```

**Add optional ML dependencies check (only if ML enabled):**
```python
# Optional ML dependencies (only if ML training is enabled)
# Check if ML training should be enabled (could be config-based)
ml_training_enabled = os.getenv("ML_TRAINING_ENABLED", "false").lower() == "true"
if ml_training_enabled:
    required_modules.append('sklearn')  # scikit-learn imports as 'sklearn'
```

### Option 2: Install from requirements.txt (Better)

**Instead of hardcoding modules, install from requirements.txt:**
```python
def check_and_install_dependencies():
    """Check and automatically install missing dependencies"""
    requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    
    if not os.path.exists(requirements_file):
        logger.error(f"requirements.txt not found at {requirements_file}")
        return False
    
    try:
        # Check if pip can install from requirements.txt
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file,
            "--quiet"
        ])
        logger.info("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to install dependencies from requirements.txt")
        return False
```

**Pros:**
- Automatically includes all dependencies from requirements.txt
- Respects version constraints
- No hardcoded lists to maintain
- Handles optional dependencies correctly

**Cons:**
- Installs ALL dependencies (including optional ML ones)
- Might want to split requirements.txt into core and optional

### Option 3: Separate Core and Optional Dependencies (Best)

**Split requirements.txt:**
- `requirements-core.txt` - Always required
- `requirements-ml.txt` - Only if ML training enabled

**Update function:**
```python
def check_and_install_dependencies(ml_enabled: bool = False):
    """Check and install dependencies"""
    requirements_file = "requirements-core.txt"
    
    if ml_enabled:
        requirements_file = "requirements.txt"  # Includes ML
    
    # Install from requirements file
    # ...
```

## Current Code Review

### What Works:
✅ Basic dependency checking
✅ Auto-installation of missing packages
✅ Error handling (returns False on failure)
✅ Called at startup (line 94)

### What Needs Fixing:
❌ Missing required dependencies (eth_account, websockets, feedparser, vaderSentiment)
❌ Module name vs package name inconsistencies
❌ No version pinning
❌ ML dependencies not handled conditionally
❌ Uses `--break-system-packages` (not portable/safe)

## Recommendation for ML Dependencies

**When ML training is ENABLED:**

1. **Option A**: Add to `required_modules` conditionally
   ```python
   # Only if ML training is enabled (config-based or env var)
   if ml_training_enabled:
       required_modules.append('sklearn')
   ```

2. **Option B**: Install from full `requirements.txt` (includes ML)
   - Simple but installs ML even if not needed

3. **Option C**: Separate requirements files
   - `requirements-core.txt` (always)
   - `requirements-ml.txt` (only if ML enabled)
   - Most flexible but requires splitting requirements.txt

**Recommendation**: **Option A** - Conditionally add ML dependencies to the list only if ML training is enabled (via config or env var).

## Action Items

1. ✅ Add missing required dependencies to list
2. ✅ Fix module name inconsistencies (dotenv, flask_socketio)
3. ✅ Add conditional ML dependency checking (only if ML enabled)
4. ⚠️ Consider using requirements.txt instead of hardcoded list
5. ⚠️ Remove `--break-system-packages` flag (use virtual environments)
6. ⚠️ Add version pinning or install from requirements.txt
