#!/usr/bin/env python3
"""
ML-Enhanced Prediction Engine
Combines traditional technical analysis with machine learning for maximum profitability
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import time
from collections import deque
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import joblib
import os

class MLPredictionEngine:
    """Machine Learning enhanced prediction engine for maximum profitability"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # ML Models
        self.price_model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
        self.volatility_model = GradientBoostingRegressor(n_estimators=100, max_depth=8, random_state=42)
        self.direction_model = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42)
        
        # Feature scalers
        self.price_scaler = StandardScaler()
        self.volatility_scaler = StandardScaler()
        self.direction_scaler = StandardScaler()
        
        # Training data storage
        self.feature_history = deque(maxlen=10000)  # Store last 10k data points
        self.model_accuracy = {"price": 0.0, "volatility": 0.0, "direction": 0.0}
        self.last_training = 0
        self.training_interval = 3600  # Retrain every hour
        
        # Pattern recognition
        self.pattern_library = {
            "bullish_engulfing": self._detect_bullish_engulfing,
            "bearish_engulfing": self._detect_bearish_engulfing,
            "hammer": self._detect_hammer,
            "shooting_star": self._detect_shooting_star,
            "ascending_triangle": self._detect_ascending_triangle,
            "descending_triangle": self._detect_descending_triangle,
            "cup_and_handle": self._detect_cup_and_handle,
            "head_shoulders": self._detect_head_shoulders
        }
        
        logger.info("🤖 ML-Enhanced Prediction Engine initialized")
    
    def generate_ml_prediction(self, market_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Generate ML-enhanced predictions combining multiple models"""
        try:
            # Extract features
            features = self._extract_features(market_data, current_price)
            
            if len(features) < 50:  # Not enough features
                return {"has_prediction": False, "reason": "Insufficient feature data"}
            
            # Get ML predictions
            price_pred = self._predict_price_movement(features)
            vol_pred = self._predict_volatility(features)
            direction_pred = self._predict_direction(features)
            
            # Pattern recognition
            patterns = self._recognize_patterns(market_data)
            
            # Combine predictions
            combined_prediction = self._combine_predictions(
                price_pred, vol_pred, direction_pred, patterns, current_price
            )
            
            # Add ML confidence metrics
            combined_prediction["ml_accuracy"] = self.model_accuracy
            combined_prediction["feature_count"] = len(features)
            combined_prediction["patterns_detected"] = patterns
            
            return combined_prediction
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return {"has_prediction": False, "reason": f"ML error: {str(e)}"}
    
    def _extract_features(self, market_data: Dict[str, Any], current_price: float) -> np.ndarray:
        """Extract comprehensive feature set for ML models"""
        features = []
        
        # Price-based features
        candles_5m = market_data.get("candles_5m", [])
        candles_1h = market_data.get("candles_1h", [])
        
        if len(candles_5m) >= 20 and len(candles_1h) >= 20:
            # Price momentum features
            prices_5m = [c["close"] for c in candles_5m[-20:]]
            prices_1h = [c["close"] for c in candles_1h[-20:]]
            volumes_5m = [c["volume"] for c in candles_5m[-20:]]
            
            # Technical indicators
            features.extend([
                self._calculate_rsi(prices_5m, 14),
                self._calculate_rsi(prices_1h, 14),
                self._calculate_macd(prices_5m)[0],  # MACD line
                self._calculate_bollinger_position(prices_5m, current_price),
                self._calculate_stochastic(candles_5m[-14:]),
                self._calculate_williams_r(candles_5m[-14:])
            ])
            
            # Price action features
            features.extend([
                (current_price - prices_5m[0]) / prices_5m[0],  # 5m price change
                (current_price - prices_1h[0]) / prices_1h[0],  # 1h price change
                np.std(prices_5m) / np.mean(prices_5m),  # 5m volatility
                np.std(prices_1h) / np.mean(prices_1h),  # 1h volatility
                max(prices_5m) / min(prices_5m),  # 5m high/low ratio
                sum(volumes_5m[-5:]) / sum(volumes_5m[:-5])  # Volume trend
            ])
            
            # Market microstructure
            orderbook_data = market_data.get("orderbook_data", {})
            if orderbook_data:
                features.extend([
                    orderbook_data.get("bid_ask_spread", 0),
                    orderbook_data.get("depth_imbalance", 0),
                    orderbook_data.get("total_depth", 0) / current_price,
                    orderbook_data.get("bid_depth", 0) / orderbook_data.get("ask_depth", 1)
                ])
            else:
                features.extend([0, 0, 0, 1])
            
            # Volatility regime features
            vol_5m = market_data.get("volatility_5m", 0)
            vol_1h = market_data.get("volatility_1h", 0)
            features.extend([
                vol_5m,
                vol_1h,
                vol_5m / vol_1h if vol_1h > 0 else 1,
                1 if vol_5m > 0.005 else 0  # High volatility flag
            ])
            
            # Time-based features
            current_hour = time.localtime().tm_hour
            features.extend([
                np.sin(2 * np.pi * current_hour / 24),  # Hour cyclical
                np.cos(2 * np.pi * current_hour / 24),
                1 if 9 <= current_hour <= 16 else 0,  # Trading hours
                1 if current_hour in [0, 8, 16] else 0  # High activity hours
            ])
            
        return np.array(features) if features else np.array([])
    
    def _predict_price_movement(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict price movement using trained model"""
        if not hasattr(self.price_model, 'feature_importances_'):
            # Model not trained yet
            return {"predicted_change": 0.0, "confidence": 0.0, "trained": False}
        
        try:
            # Reshape for prediction
            features_scaled = self.price_scaler.transform([features])
            
            # Predict price change percentage
            predicted_change = self.price_model.predict(features_scaled)[0]
            
            # Calculate confidence based on feature importance and model accuracy
            confidence = min(0.9, self.model_accuracy["price"] * 1.2)
            
            return {
                "predicted_change": predicted_change,
                "confidence": confidence,
                "trained": True,
                "model_accuracy": self.model_accuracy["price"]
            }
            
        except Exception as e:
            logger.error(f"Price prediction error: {e}")
            return {"predicted_change": 0.0, "confidence": 0.0, "trained": False}
    
    def _predict_volatility(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict volatility using trained model"""
        if not hasattr(self.volatility_model, 'feature_importances_'):
            return {"predicted_volatility": 0.002, "confidence": 0.0, "trained": False}
        
        try:
            features_scaled = self.volatility_scaler.transform([features])
            predicted_vol = self.volatility_model.predict(features_scaled)[0]
            confidence = min(0.9, self.model_accuracy["volatility"] * 1.2)
            
            return {
                "predicted_volatility": max(0.0001, predicted_vol),
                "confidence": confidence,
                "trained": True
            }
        except Exception as e:
            logger.error(f"Volatility prediction error: {e}")
            return {"predicted_volatility": 0.002, "confidence": 0.0, "trained": False}
    
    def _predict_direction(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict price direction (up/down) with confidence"""
        if not hasattr(self.direction_model, 'feature_importances_'):
            return {"direction": "UNKNOWN", "confidence": 0.0, "trained": False}
        
        try:
            features_scaled = self.direction_scaler.transform([features])
            direction_score = self.direction_model.predict(features_scaled)[0]
            
            # Convert to direction
            if direction_score > 0.02:
                direction = "UP"
                confidence = min(0.9, abs(direction_score) * 10)
            elif direction_score < -0.02:
                direction = "DOWN" 
                confidence = min(0.9, abs(direction_score) * 10)
            else:
                direction = "SIDEWAYS"
                confidence = 0.3
            
            return {
                "direction": direction,
                "confidence": confidence,
                "direction_score": direction_score,
                "trained": True
            }
        except Exception as e:
            logger.error(f"Direction prediction error: {e}")
            return {"direction": "UNKNOWN", "confidence": 0.0, "trained": False}
    
    def _recognize_patterns(self, market_data: Dict[str, Any]) -> List[str]:
        """Recognize trading patterns using pattern library"""
        patterns_found = []
        candles = market_data.get("candles_5m", [])
        
        if len(candles) >= 20:
            for pattern_name, pattern_func in self.pattern_library.items():
                try:
                    if pattern_func(candles[-20:]):
                        patterns_found.append(pattern_name)
                        logger.info(f"📈 Pattern detected: {pattern_name}")
                except Exception as e:
                    logger.debug(f"Pattern detection error for {pattern_name}: {e}")
        
        return patterns_found
    
    def _combine_predictions(self, price_pred: Dict, vol_pred: Dict, direction_pred: Dict, 
                           patterns: List[str], current_price: float) -> Dict[str, Any]:
        """Combine all ML predictions into final trading signal"""
        
        # Calculate overall confidence
        confidences = [
            price_pred.get("confidence", 0),
            vol_pred.get("confidence", 0), 
            direction_pred.get("confidence", 0)
        ]
        overall_confidence = np.mean(confidences) * 0.8  # Conservative
        
        # Pattern boost
        if patterns:
            pattern_boost = min(0.15, len(patterns) * 0.05)
            overall_confidence += pattern_boost
            logger.info(f"🎯 Pattern boost: +{pattern_boost:.2f} from {len(patterns)} patterns")
        
        # Determine trade signal
        predicted_change = price_pred.get("predicted_change", 0)
        direction = direction_pred.get("direction", "UNKNOWN")
        predicted_vol = vol_pred.get("predicted_volatility", 0.002)
        
        # Generate trading signal
        if overall_confidence > 0.65 and abs(predicted_change) > 0.003:
            if predicted_change > 0 and direction in ["UP"]:
                side = "BUY"
                entry_price = current_price * (1 - predicted_vol * 0.5)  # Enter below current
                target_price = current_price * (1 + abs(predicted_change) * 0.8)
            elif predicted_change < 0 and direction in ["DOWN"]:
                side = "SELL"
                entry_price = current_price * (1 + predicted_vol * 0.5)  # Enter above current
                target_price = current_price * (1 - abs(predicted_change) * 0.8)
            else:
                return {"has_prediction": False, "reason": "Direction mismatch"}
            
            # Calculate position size based on confidence and volatility
            base_position = 0.15  # 15% base
            confidence_multiplier = overall_confidence / 0.7  # Scale based on confidence
            volatility_multiplier = min(1.5, 0.002 / predicted_vol)  # Larger positions in low vol
            
            position_size = base_position * confidence_multiplier * volatility_multiplier
            position_size = min(0.4, max(0.05, position_size))  # 5% to 40% range
            
            return {
                "has_prediction": True,
                "type": "ML_ENHANCED",
                "side": side,
                "entry_price": entry_price,
                "target_price": target_price,
                "confidence": overall_confidence,
                "position_size": position_size,
                "timeframe": max(5, int(20 / predicted_vol)),  # Dynamic timeframe
                "reason": f"ML prediction: {direction} {predicted_change*100:.2f}% (vol: {predicted_vol*100:.1f}%)",
                "ml_details": {
                    "predicted_change": predicted_change,
                    "predicted_volatility": predicted_vol,
                    "direction": direction,
                    "patterns": patterns,
                    "model_accuracies": self.model_accuracy
                },
                "stop_loss": current_price * (1 - 0.015 if side == "BUY" else 1 + 0.015)
            }
        
        return {"has_prediction": False, "reason": f"Low confidence: {overall_confidence:.2f}"}
    
    def train_models(self, historical_data: List[Dict]) -> Dict[str, float]:
        """Train ML models with historical data"""
        if len(historical_data) < 200:
            logger.warning("Not enough data to train ML models")
            return self.model_accuracy
        
        try:
            # Prepare training data
            X_features = []
            y_price = []
            y_volatility = []
            y_direction = []
            
            for i in range(50, len(historical_data) - 10):  # Leave room for features and targets
                # Extract features for this point
                market_data = historical_data[i]
                current_price = market_data.get("price", 0)
                
                if current_price > 0:
                    features = self._extract_features(market_data, current_price)
                    if len(features) > 0:
                        # Future price change (10 candles ahead)
                        future_price = historical_data[i + 10].get("price", current_price)
                        price_change = (future_price - current_price) / current_price
                        
                        # Future volatility 
                        future_prices = [historical_data[j].get("price", current_price) for j in range(i+1, i+11)]
                        future_volatility = np.std(future_prices) / np.mean(future_prices) if future_prices else 0.002
                        
                        X_features.append(features)
                        y_price.append(price_change)
                        y_volatility.append(future_volatility)
                        y_direction.append(price_change)  # Same as price change for direction
            
            if len(X_features) < 100:
                logger.warning("Insufficient feature data for training")
                return self.model_accuracy
            
            X = np.array(X_features)
            y_p = np.array(y_price)
            y_v = np.array(y_volatility)
            y_d = np.array(y_direction)
            
            # Split training data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_p_train, y_p_test = y_p[:split_idx], y_p[split_idx:]
            y_v_train, y_v_test = y_v[:split_idx], y_v[split_idx:]
            y_d_train, y_d_test = y_d[:split_idx], y_d[split_idx:]
            
            # Scale features
            X_train_scaled = self.price_scaler.fit_transform(X_train)
            X_test_scaled = self.price_scaler.transform(X_test)
            
            # Train models
            logger.info("🤖 Training ML models...")
            
            # Price model
            self.price_model.fit(X_train_scaled, y_p_train)
            price_pred = self.price_model.predict(X_test_scaled)
            price_accuracy = 1 - np.mean(np.abs(price_pred - y_p_test)) / np.std(y_p_test)
            self.model_accuracy["price"] = max(0, min(1, price_accuracy))
            
            # Volatility model  
            self.volatility_scaler.fit(X_train)
            X_train_vol = self.volatility_scaler.transform(X_train)
            X_test_vol = self.volatility_scaler.transform(X_test)
            self.volatility_model.fit(X_train_vol, y_v_train)
            vol_pred = self.volatility_model.predict(X_test_vol)
            vol_accuracy = 1 - np.mean(np.abs(vol_pred - y_v_test)) / np.std(y_v_test)
            self.model_accuracy["volatility"] = max(0, min(1, vol_accuracy))
            
            # Direction model
            self.direction_scaler.fit(X_train)
            X_train_dir = self.direction_scaler.transform(X_train)
            X_test_dir = self.direction_scaler.transform(X_test)
            self.direction_model.fit(X_train_dir, y_d_train)
            dir_pred = self.direction_model.predict(X_test_dir)
            
            # Direction accuracy (correct sign prediction)
            correct_directions = sum(1 for p, a in zip(dir_pred, y_d_test) if np.sign(p) == np.sign(a))
            self.model_accuracy["direction"] = correct_directions / len(y_d_test)
            
            self.last_training = time.time()
            
            logger.success("🤖 ML models trained successfully!")
            logger.info(f"   Price Accuracy: {self.model_accuracy['price']:.3f}")
            logger.info(f"   Volatility Accuracy: {self.model_accuracy['volatility']:.3f}")
            logger.info(f"   Direction Accuracy: {self.model_accuracy['direction']:.3f}")
            
            return self.model_accuracy
            
        except Exception as e:
            logger.error(f"ML training error: {e}")
            return self.model_accuracy
    
    # Technical indicator helper methods
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD"""
        if len(prices) < 26:
            return 0.0, 0.0, 0.0
        
        prices_array = np.array(prices)
        ema_12 = self._ema(prices_array, 12)
        ema_26 = self._ema(prices_array, 26)
        macd_line = ema_12 - ema_26
        signal_line = self._ema(np.array([macd_line]), 9)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) == 0:
            return 0.0
        multiplier = 2.0 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _calculate_bollinger_position(self, prices: List[float], current_price: float) -> float:
        """Calculate position within Bollinger Bands"""
        if len(prices) < 20:
            return 0.5
        
        sma = np.mean(prices[-20:])
        std = np.std(prices[-20:])
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        
        if upper_band == lower_band:
            return 0.5
        
        return (current_price - lower_band) / (upper_band - lower_band)
    
    def _calculate_stochastic(self, candles: List[Dict]) -> float:
        """Calculate Stochastic %K"""
        if len(candles) < 14:
            return 50.0
        
        highs = [c["high"] for c in candles[-14:]]
        lows = [c["low"] for c in candles[-14:]]
        current_close = candles[-1]["close"]
        
        highest_high = max(highs)
        lowest_low = min(lows)
        
        if highest_high == lowest_low:
            return 50.0
        
        return ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
    
    def _calculate_williams_r(self, candles: List[Dict]) -> float:
        """Calculate Williams %R"""
        if len(candles) < 14:
            return -50.0
        
        highs = [c["high"] for c in candles[-14:]]
        lows = [c["low"] for c in candles[-14:]]
        current_close = candles[-1]["close"]
        
        highest_high = max(highs)
        lowest_low = min(lows)
        
        if highest_high == lowest_low:
            return -50.0
        
        return ((highest_high - current_close) / (highest_high - lowest_low)) * -100
    
    # Pattern recognition methods
    def _detect_bullish_engulfing(self, candles: List[Dict]) -> bool:
        """Detect bullish engulfing pattern"""
        if len(candles) < 2:
            return False
        
        prev_candle = candles[-2]
        curr_candle = candles[-1]
        
        # Previous candle is bearish
        prev_bearish = prev_candle["close"] < prev_candle["open"]
        # Current candle is bullish
        curr_bullish = curr_candle["close"] > curr_candle["open"]
        # Current engulfs previous
        engulfs = (curr_candle["open"] <= prev_candle["close"] and 
                  curr_candle["close"] >= prev_candle["open"])
        
        return prev_bearish and curr_bullish and engulfs
    
    def _detect_bearish_engulfing(self, candles: List[Dict]) -> bool:
        """Detect bearish engulfing pattern"""
        if len(candles) < 2:
            return False
        
        prev_candle = candles[-2]
        curr_candle = candles[-1]
        
        # Previous candle is bullish
        prev_bullish = prev_candle["close"] > prev_candle["open"]
        # Current candle is bearish
        curr_bearish = curr_candle["close"] < curr_candle["open"]
        # Current engulfs previous
        engulfs = (curr_candle["open"] >= prev_candle["close"] and 
                  curr_candle["close"] <= prev_candle["open"])
        
        return prev_bullish and curr_bearish and engulfs
    
    def _detect_hammer(self, candles: List[Dict]) -> bool:
        """Detect hammer pattern"""
        if len(candles) < 1:
            return False
        
        candle = candles[-1]
        body = abs(candle["close"] - candle["open"])
        lower_shadow = min(candle["open"], candle["close"]) - candle["low"]
        upper_shadow = candle["high"] - max(candle["open"], candle["close"])
        
        # Long lower shadow, short upper shadow, small body
        return (lower_shadow > body * 2 and 
                upper_shadow < body * 0.5 and
                body > 0)
    
    def _detect_shooting_star(self, candles: List[Dict]) -> bool:
        """Detect shooting star pattern"""
        if len(candles) < 1:
            return False
        
        candle = candles[-1]
        body = abs(candle["close"] - candle["open"])
        lower_shadow = min(candle["open"], candle["close"]) - candle["low"]
        upper_shadow = candle["high"] - max(candle["open"], candle["close"])
        
        # Long upper shadow, short lower shadow, small body
        return (upper_shadow > body * 2 and 
                lower_shadow < body * 0.5 and
                body > 0)
    
    def _detect_ascending_triangle(self, candles: List[Dict]) -> bool:
        """Detect ascending triangle pattern"""
        if len(candles) < 10:
            return False
        
        highs = [c["high"] for c in candles[-10:]]
        lows = [c["low"] for c in candles[-10:]]
        
        # Check if highs are relatively flat (resistance)
        high_variance = np.var(highs[-5:]) / np.mean(highs[-5:])
        # Check if lows are ascending
        low_trend = np.polyfit(range(5), lows[-5:], 1)[0]
        
        return high_variance < 0.001 and low_trend > 0
    
    def _detect_descending_triangle(self, candles: List[Dict]) -> bool:
        """Detect descending triangle pattern"""
        if len(candles) < 10:
            return False
        
        highs = [c["high"] for c in candles[-10:]]
        lows = [c["low"] for c in candles[-10:]]
        
        # Check if lows are relatively flat (support)
        low_variance = np.var(lows[-5:]) / np.mean(lows[-5:])
        # Check if highs are descending
        high_trend = np.polyfit(range(5), highs[-5:], 1)[0]
        
        return low_variance < 0.001 and high_trend < 0
    
    def _detect_cup_and_handle(self, candles: List[Dict]) -> bool:
        """Detect cup and handle pattern"""
        if len(candles) < 20:
            return False
        
        closes = [c["close"] for c in candles[-20:]]
        
        # Simple cup detection - U-shaped price movement
        first_third = closes[:7]
        middle_third = closes[7:14]
        last_third = closes[14:]
        
        # Cup: high -> low -> high
        cup_condition = (np.mean(first_third) > np.mean(middle_third) and
                        np.mean(last_third) > np.mean(middle_third) and
                        abs(np.mean(first_third) - np.mean(last_third)) < np.mean(first_third) * 0.02)
        
        return cup_condition
    
    def _detect_head_shoulders(self, candles: List[Dict]) -> bool:
        """Detect head and shoulders pattern"""
        if len(candles) < 15:
            return False
        
        highs = [c["high"] for c in candles[-15:]]
        
        # Find peaks
        peaks = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                peaks.append((i, highs[i]))
        
        if len(peaks) >= 3:
            # Sort by height
            peaks.sort(key=lambda x: x[1], reverse=True)
            # Check if middle peak is highest (head)
            head = peaks[0]
            shoulders = [p for p in peaks[1:3]]
            
            # Head should be in middle chronologically
            shoulder_heights = [s[1] for s in shoulders]
            head_height = head[1]
            
            return (head_height > max(shoulder_heights) * 1.02 and
                    min(shoulders, key=lambda x: x[0])[0] < head[0] < max(shoulders, key=lambda x: x[0])[0])
        
        return False
    
    def save_models(self, path: str = "ml_models/"):
        """Save trained models to disk"""
        try:
            os.makedirs(path, exist_ok=True)
            
            joblib.dump(self.price_model, f"{path}/price_model.pkl")
            joblib.dump(self.volatility_model, f"{path}/volatility_model.pkl") 
            joblib.dump(self.direction_model, f"{path}/direction_model.pkl")
            
            joblib.dump(self.price_scaler, f"{path}/price_scaler.pkl")
            joblib.dump(self.volatility_scaler, f"{path}/volatility_scaler.pkl")
            joblib.dump(self.direction_scaler, f"{path}/direction_scaler.pkl")
            
            logger.success(f"✅ ML models saved to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def load_models(self, path: str = "ml_models/") -> bool:
        """Load trained models from disk"""
        try:
            if not os.path.exists(f"{path}/price_model.pkl"):
                logger.warning("No saved models found")
                return False
            
            self.price_model = joblib.load(f"{path}/price_model.pkl")
            self.volatility_model = joblib.load(f"{path}/volatility_model.pkl")
            self.direction_model = joblib.load(f"{path}/direction_model.pkl")
            
            self.price_scaler = joblib.load(f"{path}/price_scaler.pkl")
            self.volatility_scaler = joblib.load(f"{path}/volatility_scaler.pkl")
            self.direction_scaler = joblib.load(f"{path}/direction_scaler.pkl")
            
            logger.success("✅ ML models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False