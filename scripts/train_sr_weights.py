#!/usr/bin/env python3
"""
Train SR weights using historical data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loguru import logger
from core.calculations.sr_weight_trainer import train_sr_weights


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train universal S/R scoring weights (same for all strategies)")
    parser.add_argument("--xgboost", action="store_true", help="Also train XGBoost + SHAP")
    
    args = parser.parse_args()
    
    try:
        logger.info("Training universal SR weights (used by all strategies)...")
        train_sr_weights(use_xgboost=args.xgboost)
        logger.info("✅ Training completed successfully")
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        sys.exit(1)
