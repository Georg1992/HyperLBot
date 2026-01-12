#!/usr/bin/env python3
"""
SR Weight Trainer - Data-driven weight learning for S/R scoring

Trains weights using ElasticNet (primary) and optionally XGBoost + SHAP.
Implements walk-forward training on historical BTC data.
"""

import os
import json
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from loguru import logger

try:
    from sklearn.linear_model import ElasticNet
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import xgboost as xgb
    import shap
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


class SRWeightTrainer:
    """
    Trains S/R scoring weights using historical data
    
    Features:
    - touch_count: normalized touch count (0-100)
    - reversal_probability: historical reversal rate (0-100)
    - proximity_atr: distance / ATR (normalized)
    - recency: hours since last touch (normalized)
    - volume_at_touch: normalized volume (0-100)
    
    Target: reversal_magnitude (MAE-MFE based on ATR)
    """
    
    FEATURE_NAMES = ['touch_count', 'reversal_probability', 'proximity_atr', 'recency', 'volume_at_touch']
    
    def __init__(self, db_path: str = "data/candles_5m_btc.db", weights_dir: str = "data/sr_weights"):
        self.db_path = db_path
        self.weights_dir = weights_dir
        os.makedirs(weights_dir, exist_ok=True)
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required for SR weight training")
    
    def extract_features_and_targets(self, start_time: float, end_time: float, 
                                     min_touches: int = 2, lookahead_candles: int = 12) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract features and targets from historical data
        
        Target: reversal_magnitude = (MFE - MAE) / ATR
        - MFE: Maximum favorable excursion (price moved away from level)
        - MAE: Maximum adverse excursion (price moved through level)
        - Normalized by ATR for volatility adjustment
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            min_touches: Minimum touches required
            lookahead_candles: Candles to look ahead for target calculation
            
        Returns:
            (features, targets) as numpy arrays
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM candles_5m
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            """
            cursor.execute(query, (start_time, end_time))
            candles = cursor.fetchall()
            if len(candles) < 100:
                return np.array([]), np.array([])
            
            candles_df = np.array(candles, dtype=[
                ('timestamp', 'f8'), ('open', 'f8'), ('high', 'f8'), 
                ('low', 'f8'), ('close', 'f8'), ('volume', 'f8')
            ])
            
            features_list = []
            targets_list = []
            
            for i in range(len(candles_df) - lookahead_candles - 50):
                candle = candles_df[i]
                current_price = candle['close']
                current_time = candle['timestamp']
                
                lookback_candles = candles_df[max(0, i-200):i+1]
                atr = self._calculate_atr(lookback_candles, period=14)
                if atr <= 0:
                    continue
                
                level_price, level_type, touches, last_touch_time, volume_at_level = \
                    self._find_sr_level(candles_df, i, current_price, atr)
                
                if level_price is None or touches < min_touches:
                    continue
                
                features = self._extract_features(
                    level_price, level_type, touches, last_touch_time, 
                    volume_at_level, current_price, current_time, atr
                )
                
                target = self._calculate_reversal_magnitude(
                    candles_df, i, level_price, level_type, atr, lookahead_candles
                )
                
                if target is not None:
                    features_list.append(features)
                    targets_list.append(target)
            
            return np.array(features_list), np.array(targets_list)
            
        finally:
            conn.close()
    
    def _calculate_atr(self, candles: np.ndarray, period: int = 14) -> float:
        """Calculate ATR from candles array"""
        if len(candles) < period + 1:
            return 0.0
        
        high = candles['high']
        low = candles['low']
        close = candles['close']
        
        tr_list = []
        for i in range(1, len(candles)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return 0.0
        
        atr = np.mean(tr_list[-period:])
        return atr if atr > 0 else 0.0
    
    def _find_sr_level(self, candles: np.ndarray, idx: int, current_price: float, 
                       atr: float) -> Tuple[Optional[float], Optional[str], int, float, float]:
        """Find S/R level at given index"""
        lookback = 100
        start_idx = max(0, idx - lookback)
        window = candles[start_idx:idx+1]
        
        if len(window) < 20:
            return None, None, 0, 0.0, 0.0
        
        highs = window['high']
        lows = window['low']
        closes = window['close']
        volumes = window['volume']
        
        pivot_highs = []
        pivot_lows = []
        
        for i in range(5, len(window) - 5):
            if highs[i] == np.max(highs[i-5:i+6]):
                pivot_highs.append((highs[i], i, volumes[i]))
            if lows[i] == np.min(lows[i-5:i+6]):
                pivot_lows.append((lows[i], i, volumes[i]))
        
        tolerance = atr * 0.5
        level_price = None
        level_type = None
        touches = 0
        last_touch_time = 0.0
        volume_sum = 0.0
        
        for price, pos, vol in pivot_highs + pivot_lows:
            if level_price is None:
                level_price = price
                level_type = 'resistance' if (price, pos, vol) in pivot_highs else 'support'
                touches = 1
                last_touch_time = window[pos]['timestamp']
                volume_sum = vol
            elif abs(price - level_price) < tolerance:
                touches += 1
                if window[pos]['timestamp'] > last_touch_time:
                    last_touch_time = window[pos]['timestamp']
                volume_sum += vol
        
        avg_volume = volume_sum / touches if touches > 0 else 0.0
        
        return level_price, level_type, touches, last_touch_time, avg_volume
    
    def _extract_features(self, level_price: float, level_type: str, touches: int,
                         last_touch_time: float, volume_at_level: float,
                         current_price: float, current_time: float, atr: float) -> np.ndarray:
        """Extract normalized features"""
        touch_count = min(100.0, (touches / 10.0) * 100.0)
        
        reversal_probability = min(100.0, (touches / 5.0) * 100.0)
        
        distance = abs(level_price - current_price)
        proximity_atr = distance / atr if atr > 0 else 10.0
        proximity_atr = min(10.0, proximity_atr)
        
        hours_since_touch = (current_time - last_touch_time) / 3600.0
        recency = max(0.0, 100.0 - (hours_since_touch / 24.0) * 100.0)
        
        volume_at_touch = min(100.0, (volume_at_level / 1000.0) * 100.0)
        
        return np.array([touch_count, reversal_probability, proximity_atr, recency, volume_at_touch])
    
    def _calculate_reversal_magnitude(self, candles: np.ndarray, idx: int, level_price: float,
                                     level_type: str, atr: float, lookahead: int) -> Optional[float]:
        """Calculate reversal magnitude target (MAE-MFE normalized by ATR)"""
        if idx + lookahead >= len(candles):
            return None
        
        future = candles[idx+1:idx+1+lookahead]
        if len(future) == 0:
            return None
        
        current_price = candles[idx]['close']
        
        if level_type == 'support':
            mae = min(future['low']) - level_price
            mfe = max(future['high']) - level_price
        else:
            mae = level_price - max(future['high'])
            mfe = level_price - min(future['low'])
        
        if atr <= 0:
            return None
        
        reversal_magnitude = (mfe - mae) / atr
        return reversal_magnitude
    
    def train_elasticnet(self, features: np.ndarray, targets: np.ndarray,
                        alpha: float = 0.1, l1_ratio: float = 0.5,
                        random_state: int = 42) -> Dict[str, float]:
        """
        Train ElasticNet model and return normalized weights
        
        Args:
            features: Feature matrix (n_samples, n_features)
            targets: Target vector (n_samples,)
            alpha: Regularization strength
            l1_ratio: L1/L2 ratio (1.0 = Lasso, 0.0 = Ridge)
            random_state: Random seed for reproducibility
            
        Returns:
            Normalized weights dict (sum = 1.0)
        """
        if len(features) == 0 or len(targets) == 0:
            raise ValueError("Empty features or targets")
        
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=random_state, max_iter=2000)
        model.fit(features_scaled, targets)
        
        coefficients = model.coef_
        
        abs_coefficients = np.abs(coefficients)
        weights = abs_coefficients / np.sum(abs_coefficients) if np.sum(abs_coefficients) > 0 else np.ones(len(coefficients)) / len(coefficients)
        
        weights_dict = {
            'touch': float(weights[0]),
            'reversal_probability': float(weights[1]),
            'proximity': float(weights[2]),
            'recency': float(weights[3]),
            'volume': float(weights[4])
        }
        
        mae = mean_absolute_error(targets, model.predict(features_scaled))
        r2 = r2_score(targets, model.predict(features_scaled))
        
        logger.info(f"ElasticNet training: MAE={mae:.4f}, R²={r2:.4f}")
        logger.info(f"Learned weights: {weights_dict}")
        
        return weights_dict
    
    def train_xgboost_shap(self, features: np.ndarray, targets: np.ndarray,
                          n_estimators: int = 100, random_state: int = 42) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Train XGBoost model and extract SHAP feature importance
        
        Returns:
            (shap_weights, model_importance) dicts
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not available")
        
        model = xgb.XGBRegressor(n_estimators=n_estimators, random_state=random_state, n_jobs=1)
        model.fit(features, targets)
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(features[:min(100, len(features))])
        
        shap_importance = np.abs(shap_values).mean(axis=0)
        shap_weights = shap_importance / np.sum(shap_importance) if np.sum(shap_importance) > 0 else np.ones(len(shap_importance)) / len(shap_importance)
        
        model_importance = model.feature_importances_
        model_weights = model_importance / np.sum(model_importance) if np.sum(model_importance) > 0 else np.ones(len(model_importance)) / len(model_importance)
        
        shap_dict = {
            'touch': float(shap_weights[0]),
            'reversal_probability': float(shap_weights[1]),
            'proximity': float(shap_weights[2]),
            'recency': float(shap_weights[3]),
            'volume': float(shap_weights[4])
        }
        
        model_dict = {
            'touch': float(model_weights[0]),
            'reversal_probability': float(model_weights[1]),
            'proximity': float(model_weights[2]),
            'recency': float(model_weights[3]),
            'volume': float(model_weights[4])
        }
        
        return shap_dict, model_dict
    
    def walk_forward_train(self, train_months: int = 12, test_months: int = 1,
                          stride_months: int = 1, alpha: float = 0.1,
                          l1_ratio: float = 0.5) -> Dict[str, float]:
        """
        Walk-forward training on historical data
        
        Args:
            train_months: Training window size in months
            test_months: Test window size in months
            stride_months: Stride between windows
            alpha: ElasticNet regularization
            l1_ratio: ElasticNet L1/L2 ratio
            
        Returns:
            Final averaged weights
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM candles_5m")
            min_ts, max_ts = cursor.fetchone()
            
            if min_ts is None or max_ts is None:
                raise ValueError("Database empty")
            
            seconds_per_month = 30 * 24 * 3600
            train_seconds = train_months * seconds_per_month
            test_seconds = test_months * seconds_per_month
            stride_seconds = stride_months * seconds_per_month
            
            all_weights = []
            
            current_start = min_ts
            while current_start + train_seconds + test_seconds <= max_ts:
                train_end = current_start + train_seconds
                test_start = train_end
                test_end = test_start + test_seconds
                
                logger.info(f"Walk-forward: training on [{current_start:.0f}, {train_end:.0f}], testing on [{test_start:.0f}, {test_end:.0f}]")
                
                features_train, targets_train = self.extract_features_and_targets(current_start, train_end)
                
                if len(features_train) < 100:
                    current_start += stride_seconds
                    continue
                
                try:
                    weights = self.train_elasticnet(features_train, targets_train, alpha, l1_ratio)
                    all_weights.append(weights)
                except Exception as e:
                    logger.warning(f"Training failed for window: {e}")
                
                current_start += stride_seconds
            
            if len(all_weights) == 0:
                raise ValueError("No successful training windows")
            
            averaged_weights = {
                key: np.mean([w[key] for w in all_weights])
                for key in all_weights[0].keys()
            }
            
            total = sum(averaged_weights.values())
            normalized_weights = {key: val / total for key, val in averaged_weights.items()}
            
            return normalized_weights
            
        finally:
            conn.close()
    
    def save_weights(self, weights: Dict[str, float], method: str = "elasticnet"):
        """Save weights to JSON file (universal weights - same for all strategies)"""
        filename = f"{method}_weights.json"
        filepath = os.path.join(self.weights_dir, filename)
        
        data = {
            'weights': weights,
            'method': method,
            'timestamp': time.time(),
            'feature_names': self.FEATURE_NAMES,
            'note': 'Universal weights - same for all strategies'
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved weights to {filepath}")
    
    def load_weights(self, method: str = "elasticnet") -> Optional[Dict[str, float]]:
        """Load weights from JSON file (universal weights - same for all strategies)"""
        filename = f"{method}_weights.json"
        filepath = os.path.join(self.weights_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            weights = data.get('weights')
            if weights is None:
                return None
            
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                logger.warning(f"Weights don't sum to 1.0 ({total}), normalizing")
                weights = {key: val / total for key, val in weights.items()}
            
            return weights
            
        except Exception as e:
            logger.error(f"Failed to load weights: {e}")
            return None


def train_sr_weights(use_xgboost: bool = False):
    """
    Main training function - trains universal weights (same for all strategies)
    
    Args:
        use_xgboost: Also train XGBoost + SHAP (optional)
    """
    trainer = SRWeightTrainer()
    
    try:
        logger.info("Starting walk-forward training for universal SR weights...")
        weights = trainer.walk_forward_train(train_months=12, test_months=1, stride_months=1)
        trainer.save_weights(weights, method="elasticnet")
        
        if use_xgboost and XGBOOST_AVAILABLE:
            logger.info("Training XGBoost + SHAP...")
            conn = sqlite3.connect(trainer.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM candles_5m")
            min_ts, max_ts = cursor.fetchone()
            conn.close()
            
            features, targets = trainer.extract_features_and_targets(min_ts, max_ts)
            if len(features) > 100:
                shap_weights, model_weights = trainer.train_xgboost_shap(features, targets)
                trainer.save_weights(shap_weights, method="xgboost_shap")
                trainer.save_weights(model_weights, method="xgboost_model")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise
