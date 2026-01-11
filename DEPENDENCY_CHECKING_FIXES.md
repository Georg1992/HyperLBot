# Dependency Checking Code Fixes

## Changes Made

### ✅ 1. Added Missing Required Dependencies

Added 4 missing dependencies from `requirements.txt`:
- `eth_account` - Required for Hyperliquid API (Web3/Ethereum)
- `websockets` - Required for WebSocket connections
- `feedparser` - Required for RSS news feed
- `vaderSentiment` - Required for sentiment analysis

### ✅ 2. Fixed Module Name Issues

**Fixed `python-dotenv` import name:**
- Changed from `'python-dotenv'` to `'dotenv'` in required_modules (correct import name)
- Added mapping: `'dotenv': 'python-dotenv'` for pip install (correct package name)

### ✅ 3. Added Module-to-Package Name Mapping

Created `module_to_package` dictionary to handle differences between:
- **Import names** (what Python uses: `import dotenv`, `import flask_socketio`)
- **Package names** (what pip uses: `python-dotenv`, `flask-socketio`)

This ensures proper installation even when names differ.

### ✅ 4. Added Conditional ML Dependency Checking

**ML dependencies are now conditionally checked:**
- Only checks for `scikit-learn` if `ML_TRAINING_ENABLED` environment variable is set to `"true"`
- Default: ML dependencies are **not** checked (since ML training is disabled)
- When enabled: Automatically checks and installs `scikit-learn` if missing

**Usage:**
```bash
# To enable ML dependency checking:
export ML_TRAINING_ENABLED=true
python main.py
```

## Updated Code

```python
def check_and_install_dependencies():
    """Check and automatically install missing dependencies"""
    # Module name -> Package name mapping (for pip install)
    module_to_package = {
        'flask': 'flask',
        'flask_socketio': 'flask-socketio',
        'yfinance': 'yfinance',
        'requests': 'requests',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'loguru': 'loguru',
        'dotenv': 'python-dotenv',  # python-dotenv imports as 'dotenv'
        'httpx': 'httpx',
        'aiohttp': 'aiohttp',
        'eth_account': 'eth_account',
        'websockets': 'websockets',
        'feedparser': 'feedparser',
        'vaderSentiment': 'vaderSentiment',
    }
    
    # Required modules (using import names)
    required_modules = [
        'flask', 'flask_socketio', 'yfinance', 'requests', 'pandas', 
        'numpy', 'loguru', 'dotenv', 'httpx', 'aiohttp',
        'eth_account', 'websockets', 'feedparser', 'vaderSentiment'
    ]
    
    # Conditionally add ML dependencies if ML training is enabled
    ml_training_enabled = os.getenv("ML_TRAINING_ENABLED", "false").lower() == "true"
    if ml_training_enabled:
        required_modules.append('sklearn')  # scikit-learn imports as 'sklearn'
        module_to_package['sklearn'] = 'scikit-learn'
        logger.info("🤖 ML training enabled - scikit-learn will be checked")
    
    # ... rest of checking and installation logic
```

## How It Works

1. **Check Required Modules**: Tries to import each module to see if it's installed
2. **Conditional ML Check**: Only checks for `sklearn` if `ML_TRAINING_ENABLED=true`
3. **Install Missing Modules**: Uses `module_to_package` mapping to get correct pip package name
4. **Proper Installation**: Installs using correct package names (e.g., `flask-socketio`, `python-dotenv`, `scikit-learn`)

## Benefits

✅ **Complete Coverage**: All dependencies from `requirements.txt` are now checked
✅ **Correct Installation**: Uses proper package names for pip install
✅ **Conditional ML**: ML dependencies only checked/installed when needed
✅ **Maintainable**: Clear mapping between import names and package names
✅ **Flexible**: Can enable ML dependencies via environment variable

## When ML Training is Enabled

When you enable ML training in the code (following `ML_TRAINING_ENABLEMENT_ANALYSIS.md`):

1. Set environment variable: `export ML_TRAINING_ENABLED=true`
2. Run bot: `python main.py`
3. Dependency checker will automatically check and install `scikit-learn` if missing
4. Bot starts with ML dependencies available

This ensures ML dependencies are ready when needed, without installing them unnecessarily when ML training is disabled.
