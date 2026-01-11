# How to Train SR Weights

## Step-by-Step Instructions

### 1. Install Dependencies

```bash
pip install scikit-learn
```

### 2. Ensure Database Has Data

The bot will create the database automatically. You need at least 12+ months of historical data for walk-forward training.

If the database is empty, run the bot once to populate it:
```bash
python main.py
```

The bot will automatically:
- Create `data/candles_5m_btc.db`
- Download 5 years of historical data (on first run)

Wait for initialization to complete, then stop the bot (Ctrl+C).

### 3. Train Weights

Run the training script:
```bash
python scripts/train_sr_weights.py --strategy standard
```

This will:
- Extract features from historical data
- Train ElasticNet model using walk-forward validation
- Save weights to `data/sr_weights/standard_elasticnet_weights.json`

**Note**: Training time depends on database size:
- **5 years of data**: ~1-3 hours (49 training windows)
- **3 years of data**: ~30-90 minutes (25 training windows)
- **1 year of data**: ~15-30 minutes (1 training window)

The bottleneck is feature extraction (S/R level detection), not ElasticNet training.

### 4. Verify Weights Were Saved

Check the weights file was created:
```bash
# Windows PowerShell
ls data\sr_weights\

# Or check if file exists
Test-Path data\sr_weights\standard_elasticnet_weights.json
```

### 5. Use Learned Weights

**No additional steps needed!** The `SRScorer` automatically loads learned weights when it initializes:

- ✅ If weights file exists → Uses learned weights
- ✅ If weights file missing → Falls back to static weights (from config)

Just run your bot normally:
```bash
python main.py
```

Check logs for: `✅ Loaded learned weights for strategy 'standard'`

---

## Optional: XGBoost + SHAP Training

For research/analysis, you can also train XGBoost models:

```bash
# Install XGBoost and SHAP
pip install xgboost shap

# Train with XGBoost
python scripts/train_sr_weights.py --strategy standard --xgboost
```

This creates additional weight files:
- `standard_xgboost_shap_weights.json` (SHAP importance)
- `standard_xgboost_model_weights.json` (XGBoost feature importance)

**Note**: Only ElasticNet weights are used in production. XGBoost is for research only.

---

## Troubleshooting

**"No module named 'sklearn'"**
→ Install: `pip install scikit-learn`

**"Database is empty"**
→ Run the bot once to populate the database, then train

**"Not enough data for walk-forward training"**
→ Need at least 12+ months of historical data. Let the bot populate more data.

**Weights file not created**
→ Check training logs for errors. Ensure database has sufficient data.

**Weights not loading (no log message)**
→ This is normal - falls back to static weights silently if file is missing or invalid.
