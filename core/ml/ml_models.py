#!/usr/bin/env python3
"""
ML Models for Trading Predictions
=================================
Core machine learning models for price prediction, signal confidence, and market regime detection
"""

import time
import pickle
import numpy as np
# import pandas as pd  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from loguru import logger
from pathlib import Path

# ML Libraries
try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
# #     from sklearn.linear_model import LogisticRegression, LinearRegression  # Removed unused import  # Removed unused import
# #     from sklearn.svm import SVC, SVR  # Removed unused import  # Removed unused import
    from sklearn.preprocessing import StandardScaler, LabelEncoder
#     from sklearn.model_selection import train_test_split, cross_val_score  # Removed unused import
#     from sklearn.metrics import accuracy_score, mean_squared_error, classification_report  # Removed unused import
#     import joblib  # Removed unused import
    ML_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Scikit-learn not available. Install with: pip install scikit-learn")
    ML_AVAILABLE = False

@dataclass
class MLPrediction:
    """ML prediction result"""
    prediction: float
    confidence: float
    model_type: str
    features_used: List[str]
    timestamp: float
    metadata: Dict[str, Any] = None

class MLModelManager:
    """Manages all ML models for the trading system"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.label_encoders = {}
        self.model_path = Path("models")
        self.model_path.mkdir(exist_ok=True)
        
        # Initialize models
        self._initialize_models()
        
        logger.info("🤖 ML Model Manager initialized")
    
    def _initialize_models(self):
        """Initialize all ML models"""
        if not ML_AVAILABLE:
            logger.warning("⚠️ ML models not initialized - scikit-learn not available")
            return
        
        # Main trading prediction models (the core of your system)
        self.models['trading_predictions'] = {
            'buy_signal': RandomForestClassifier(n_estimators=200, random_state=42),  # Predict BUY/NO_BUY
            'sell_signal': RandomForestClassifier(n_estimators=200, random_state=42),  # Predict SELL/NO_SELL
            'confidence_predictor': RandomForestRegressor(n_estimators=150, random_state=42),  # Predict confidence (0-1)
            'price_target': RandomForestRegressor(n_estimators=150, random_state=42)  # Predict target price
        }
        
        # Supporting analysis models (for context)
        self.models['market_analysis'] = {
            'market_regime': RandomForestClassifier(n_estimators=100, random_state=42),  # Market condition
            'volatility_forecast': RandomForestRegressor(n_estimators=100, random_state=42)  # Volatility prediction
        }
        
        # Signal confidence models (for individual signal validation)
        self.models['signal_confidence'] = {
            'market_data': RandomForestClassifier(n_estimators=100, random_state=42),  # Market data signal confidence
            'orderbook': RandomForestClassifier(n_estimators=100, random_state=42),  # Order book analysis confidence
            'pattern': RandomForestClassifier(n_estimators=100, random_state=42),  # Pattern recognition confidence
            'technical_analysis': RandomForestClassifier(n_estimators=100, random_state=42),  # Technical analysis confidence
            'volume_analysis': RandomForestClassifier(n_estimators=100, random_state=42),  # Volume analysis confidence
            'volatility_analysis': RandomForestClassifier(n_estimators=100, random_state=42)  # Volatility analysis confidence
        }
        
        # Initialize scalers
        self.scalers['feature_scaler'] = StandardScaler()
        self.scalers['price_scaler'] = StandardScaler()
        
        # Initialize label encoders
        self.label_encoders['regime_encoder'] = LabelEncoder()
        self.label_encoders['signal_encoder'] = LabelEncoder()
        
        logger.info("✅ ML models initialized successfully")
    
    def train_trading_prediction_models(self, features: np.ndarray, 
                                      buy_targets: np.ndarray, 
                                      sell_targets: np.ndarray,
                                      confidence_targets: np.ndarray,
                                      price_targets: np.ndarray) -> Dict[str, Any]:
        """Train the main trading prediction models"""
        if not ML_AVAILABLE:
            return {"error": "ML not available"}
        
        try:
            # Split data
            X_train, X_test, y_buy_train, y_buy_test = train_test_split(
                features, buy_targets, test_size=0.2, random_state=42
            )
            _, _, y_sell_train, y_sell_test = train_test_split(
                features, sell_targets, test_size=0.2, random_state=42
            )
            _, _, y_conf_train, y_conf_test = train_test_split(
                features, confidence_targets, test_size=0.2, random_state=42
            )
            _, _, y_price_train, y_price_test = train_test_split(
                features, price_targets, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scalers['feature_scaler'].fit_transform(X_train)
            X_test_scaled = self.scalers['feature_scaler'].transform(X_test)
            
            results = {}
            
            # Train buy signal model
            buy_model = self.models['trading_predictions']['buy_signal']
            buy_model.fit(X_train_scaled, y_buy_train)
            buy_pred = buy_model.predict(X_test_scaled)
            buy_accuracy = accuracy_score(y_buy_test, buy_pred)
            results['buy_signal'] = {"accuracy": buy_accuracy, "success": True}
            
            # Train sell signal model
            sell_model = self.models['trading_predictions']['sell_signal']
            sell_model.fit(X_train_scaled, y_sell_train)
            sell_pred = sell_model.predict(X_test_scaled)
            sell_accuracy = accuracy_score(y_sell_test, sell_pred)
            results['sell_signal'] = {"accuracy": sell_accuracy, "success": True}
            
            # Train confidence predictor
            conf_model = self.models['trading_predictions']['confidence_predictor']
            conf_model.fit(X_train_scaled, y_conf_train)
            conf_pred = conf_model.predict(X_test_scaled)
            conf_mse = mean_squared_error(y_conf_test, conf_pred)
            results['confidence_predictor'] = {"mse": conf_mse, "success": True}
            
            # Train price target model
            price_model = self.models['trading_predictions']['price_target']
            price_model.fit(X_train_scaled, y_price_train)
            price_pred = price_model.predict(X_test_scaled)
            price_mse = mean_squared_error(y_price_test, price_pred)
            results['price_target'] = {"mse": price_mse, "success": True}
            
            # Save models
            self._save_model('trading_buy_signal', buy_model)
            self._save_model('trading_sell_signal', sell_model)
            self._save_model('trading_confidence', conf_model)
            self._save_model('trading_price_target', price_model)
            
            return {
                "success": True,
                "results": results,
                "model_type": "trading_predictions",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Trading prediction model training failed: {e}")
            return {"error": str(e)}
    
    def train_price_prediction_model(self, features: np.ndarray, targets: np.ndarray, 
                                   timeframe: str = 'short_term') -> Dict[str, Any]:
        """Train price prediction model"""
        if not ML_AVAILABLE:
            return {"error": "ML not available"}
        
        try:
            model = self.models['price_prediction'][timeframe]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scalers['feature_scaler'].fit_transform(X_train)
            X_test_scaled = self.scalers['feature_scaler'].transform(X_test)
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            
            # Feature importance
            feature_importance = model.feature_importances_
            
            # Save model
            self._save_model(f'model_{timeframe}', model)
            
            return {
                "success": True,
                "mse": mse,
                "feature_importance": feature_importance.tolist(),
                "model_type": "price_prediction",
                "timeframe": timeframe
            }
            
        except Exception as e:
            logger.error(f"❌ Price prediction model training failed: {e}")
            return {"error": str(e)}
    
    def train_signal_confidence_model(self, features: np.ndarray, targets: np.ndarray,
                                    signal_type: str = 'market_data') -> Dict[str, Any]:
        """Train signal confidence model"""
        if not ML_AVAILABLE:
            return {"error": "ML not available"}
        
        try:
            model = self.models['signal_confidence'][signal_type]
            
            # Encode targets
            targets_encoded = self.label_encoders['signal_encoder'].fit_transform(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets_encoded, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scalers['feature_scaler'].fit_transform(X_train)
            X_test_scaled = self.scalers['feature_scaler'].transform(X_test)
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Feature importance
            feature_importance = model.feature_importances_
            
            # Save model
            self._save_model(f'signal_confidence_{signal_type}', model)
            
            return {
                "success": True,
                "accuracy": accuracy,
                "feature_importance": feature_importance.tolist(),
                "model_type": "signal_confidence",
                "signal_type": signal_type
            }
            
        except Exception as e:
            logger.error(f"❌ Signal confidence model training failed: {e}")
            return {"error": str(e)}
    
    def predict_trading_signal(self, features: np.ndarray, current_price: float, 
                              market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main trading prediction method - generates complete trading predictions
        
        Returns:
            Dict with complete trading prediction including:
            - signal: "BUY", "SELL", or "HOLD"
            - entry_price: recommended entry price
            - size_btc: position size in BTC
            - size_usd: position size in USD
            - stop_loss: stop loss price
            - take_profit: take profit price
            - confidence: 0.0 to 1.0
            - reasoning: explanation of the prediction
        """
        if not ML_AVAILABLE:
            return {"error": "ML not available"}
        
        try:
            # Check if models are trained
            if not hasattr(self.scalers['feature_scaler'], 'scale_') or self.scalers['feature_scaler'].scale_ is None:
                # Models not trained yet, return fallback prediction
                return self._fallback_trading_prediction(current_price, market_data)
            
            # Scale features
            features_scaled = self.scalers['feature_scaler'].transform(features.reshape(1, -1))
            
            # Get buy signal prediction
            buy_model = self.models['trading_predictions']['buy_signal']
            buy_pred = buy_model.predict(features_scaled)[0]
            buy_proba = buy_model.predict_proba(features_scaled)[0]
            buy_confidence = np.max(buy_proba)
            
            # Get sell signal prediction
            sell_model = self.models['trading_predictions']['sell_signal']
            sell_pred = sell_model.predict(features_scaled)[0]
            sell_proba = sell_model.predict_proba(features_scaled)[0]
            sell_confidence = np.max(sell_proba)
            
            # Get overall confidence
            confidence_model = self.models['trading_predictions']['confidence_predictor']
            overall_confidence = confidence_model.predict(features_scaled)[0]
            overall_confidence = max(0.0, min(1.0, overall_confidence))  # Clamp to 0-1
            
            # Get price target
            price_model = self.models['trading_predictions']['price_target']
            price_target = price_model.predict(features_scaled)[0]
            
            # Determine final signal - optimized for 40x leverage trading
            if buy_confidence > sell_confidence and buy_confidence > 0.15:  # 40x leverage: very aggressive threshold
                signal = "BUY"
                confidence = buy_confidence
                reasoning = f"Buy signal (confidence: {buy_confidence:.3f})"
            elif sell_confidence > buy_confidence and sell_confidence > 0.15:  # 40x leverage: very aggressive threshold
                signal = "SELL"
                confidence = sell_confidence
                reasoning = f"Sell signal (confidence: {sell_confidence:.3f})"
            else:
                signal = "NEUTRAL"
                confidence = max(buy_confidence, sell_confidence)
                reasoning = f"Uncertain signals (buy: {buy_confidence:.3f}, sell: {sell_confidence:.3f})"
            
            # Apply overall confidence threshold - optimized for 40x leverage trading
            if overall_confidence < 0.10:  # 40x leverage: extremely aggressive threshold
                signal = "NEUTRAL"
                reasoning += f" - Low overall confidence ({overall_confidence:.3f})"
            
            # Calculate complete trading parameters
            trading_params = self._calculate_trading_parameters(
                signal, current_price, price_target, confidence, market_data
            )
            
            return {
                "signal": signal,
                "entry_price": trading_params["entry_price"],
                "size_btc": trading_params["size_btc"],
                "size_usd": trading_params["size_usd"],
                "stop_loss": trading_params["stop_loss"],
                "take_profit": trading_params["take_profit"],
                "confidence": float(confidence),
                "overall_confidence": float(overall_confidence),
                "reasoning": reasoning,
                "buy_confidence": float(buy_confidence),
                "sell_confidence": float(sell_confidence),
                "model_type": "trading_prediction",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Trading signal prediction failed: {e}")
            return {
                "signal": "NEUTRAL",
                "entry_price": current_price,
                "size_btc": 0.0,
                "size_usd": 0.0,
                "stop_loss": current_price,
                "take_profit": current_price,
                "confidence": 0.0,
                "overall_confidence": 0.0,
                "reasoning": f"Prediction failed: {str(e)}",
                "error": str(e)
            }
    
    def _fallback_trading_prediction(self, current_price: float, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback trading prediction when models are not trained yet"""
        try:
            # Simple fallback based on basic market indicators
            rsi = market_data.get("rsi", 50.0) if market_data else 50.0
            trend = market_data.get("trend", "NEUTRAL") if market_data else "NEUTRAL"
            
            # Basic signal logic
            if rsi < 30 and trend in ["UPTREND", "STRONG_UPTREND"]:
                signal = "BUY"
                confidence = 0.6
                reasoning = f"Oversold RSI ({rsi:.1f}) with uptrend - fallback prediction"
            elif rsi > 70 and trend in ["DOWNTREND", "STRONG_DOWNTREND"]:
                signal = "SELL"
                confidence = 0.6
                reasoning = f"Overbought RSI ({rsi:.1f}) with downtrend - fallback prediction"
            else:
                signal = "HOLD"
                confidence = 0.3
                reasoning = f"Neutral conditions (RSI: {rsi:.1f}, Trend: {trend}) - fallback prediction"
            
            # Calculate basic trading parameters
            if signal == "BUY":
                entry_price = current_price * 1.001  # Slightly above current price
                stop_loss = current_price * 0.98     # 2% stop loss
                take_profit = current_price * 1.05   # 5% take profit
            elif signal == "SELL":
                entry_price = current_price * 0.999  # Slightly below current price
                stop_loss = current_price * 1.02     # 2% stop loss
                take_profit = current_price * 0.95   # 5% take profit
            else:
                entry_price = current_price
                stop_loss = current_price
                take_profit = current_price
            
            # Basic position sizing (1% of portfolio)
            position_size_usd = 1000.0  # $1000 position
            position_size_btc = position_size_usd / current_price
            
            return {
                "signal": signal,
                "entry_price": entry_price,
                "size_btc": position_size_btc,
                "size_usd": position_size_usd,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": confidence,
                "overall_confidence": confidence,
                "reasoning": reasoning,
                "model_type": "fallback_prediction",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback trading prediction failed: {e}")
            return {
                "signal": "NEUTRAL",
                "entry_price": current_price,
                "size_btc": 0.0,
                "size_usd": 0.0,
                "stop_loss": current_price,
                "take_profit": current_price,
                "confidence": 0.0,
                "overall_confidence": 0.0,
                "reasoning": f"Fallback prediction failed: {str(e)}",
                "error": str(e)
            }
    
    def _calculate_trading_parameters(self, signal: str, current_price: float, 
                                    price_target: float, confidence: float,
                                    market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate complete trading parameters based on signal and market conditions"""
        try:
            market_data = market_data or {}
            
            # Base position size (can be adjusted based on confidence and market conditions)
            # 40x leverage optimized position sizing
            base_size_usd = 2000.0  # $2000 base position (increased for 40x leverage)
            confidence_multiplier = confidence  # Scale position size by confidence
            
            # Adjust position size based on market conditions - 40x leverage optimized
            volatility = market_data.get("volatility_5m", 0.02)
            volume_category = market_data.get("volume_category", "NORMAL")
            
            # 40x leverage: More aggressive position sizing in low volatility (range trading)
            if volatility < 0.01:  # Very low volatility - optimal for 40x leverage
                confidence_multiplier *= 1.5  # Increase size in low volatility
            elif volatility > 0.05:  # High volatility - reduce size
                confidence_multiplier *= 0.3  # More conservative in high volatility
            elif volatility > 0.03:  # Medium volatility
                confidence_multiplier *= 0.6
            
            # 40x leverage: Less penalty for low volume (range trading conditions)
            if volume_category in ["LOW", "VERY_LOW"]:
                confidence_multiplier *= 0.8  # Reduced penalty for low volume
            
            # Calculate position sizes
            size_usd = base_size_usd * confidence_multiplier
            size_btc = size_usd / current_price
            
            # Calculate entry price (current price with small slippage) - 40x leverage optimized
            if signal == "BUY":
                entry_price = current_price * 1.0005  # 0.05% slippage for buy (tighter for 40x)
            elif signal == "SELL":
                entry_price = current_price * 0.9995  # 0.05% slippage for sell (tighter for 40x)
            else:
                entry_price = current_price
            
            # Calculate stop loss and take profit - 40X LEVERAGE OPTIMIZED (much tighter ranges)
            volatility_multiplier = max(0.2, volatility * 20)  # Reduced scaling for 40x leverage
            
            if signal == "BUY":
                # Stop loss: 0.1-0.5% below entry (40x leverage optimized)
                stop_loss_pct = 0.001 + (volatility_multiplier * 0.002)  # 0.1-0.5%
                stop_loss = entry_price * (1 - stop_loss_pct)
                
                # Take profit: 0.2-1.0% above entry (40x leverage optimized)
                take_profit_pct = 0.002 + (confidence * 0.008) + (volatility_multiplier * 0.002)
                take_profit = entry_price * (1 + take_profit_pct)
                
            elif signal == "SELL":
                # Stop loss: 0.1-0.5% above entry (40x leverage optimized)
                stop_loss_pct = 0.001 + (volatility_multiplier * 0.002)  # 0.1-0.5%
                stop_loss = entry_price * (1 + stop_loss_pct)
                
                # Take profit: 0.2-1.0% below entry (40x leverage optimized)
                take_profit_pct = 0.002 + (confidence * 0.008) + (volatility_multiplier * 0.002)
                take_profit = entry_price * (1 - take_profit_pct)
                
            else:  # HOLD
                stop_loss = current_price
                take_profit = current_price
                size_usd = 0.0
                size_btc = 0.0
            
            return {
                "entry_price": round(entry_price, 2),
                "size_btc": round(size_btc, 6),
                "size_usd": round(size_usd, 2),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Trading parameters calculation failed: {e}")
            return {
                "entry_price": current_price,
                "size_btc": 0.0,
                "size_usd": 0.0,
                "stop_loss": current_price,
                "take_profit": current_price
            }
    
    def predict_price_movement(self, features: np.ndarray, timeframe: str = 'short_term') -> MLPrediction:
        """Predict price movement using trained model"""
        if not ML_AVAILABLE:
            return MLPrediction(0.0, 0.0, "error", [], time.time(), {"error": "ML not available"})
        
        try:
            model = self.models['price_prediction'][timeframe]
            
            # Scale features
            features_scaled = self.scalers['feature_scaler'].transform(features.reshape(1, -1))
            
            # Predict
            prediction = model.predict(features_scaled)[0]
            
            # Calculate confidence (based on prediction variance)
            # This is a simplified confidence calculation
            confidence = min(0.95, max(0.1, abs(prediction) * 0.1))
            
            return MLPrediction(
                prediction=prediction,
                confidence=confidence,
                model_type=f"price_prediction_{timeframe}",
                features_used=[f"feature_{i}" for i in range(len(features))],
                timestamp=time.time(),
                metadata={"timeframe": timeframe}
            )
            
        except Exception as e:
            logger.error(f"❌ Price prediction failed: {e}")
            return MLPrediction(0.0, 0.0, "error", [], time.time(), {"error": str(e)})
    
    def predict_signal_confidence(self, features: np.ndarray, signal_type: str = 'market_data') -> MLPrediction:
        """Predict signal confidence using trained model"""
        if not ML_AVAILABLE:
            return MLPrediction(0.0, 0.0, "error", [], time.time(), {"error": "ML not available"})
        
        try:
            # Check if model is trained
            if signal_type not in self.models['signal_confidence']:
                # Return fallback prediction
                return MLPrediction(0.5, 0.3, "fallback", [], time.time(), {"reason": "Model not trained"})
            
            model = self.models['signal_confidence'][signal_type]
            if not hasattr(model, 'predict'):
                # Return fallback prediction
                return MLPrediction(0.5, 0.3, "fallback", [], time.time(), {"reason": "Model not trained"})
            
            # Check if scaler is fitted
            if not hasattr(self.scalers['feature_scaler'], 'scale_') or self.scalers['feature_scaler'].scale_ is None:
                # Return fallback prediction
                return MLPrediction(0.5, 0.3, "fallback", [], time.time(), {"reason": "Scaler not fitted"})
            
            # Scale features
            features_scaled = self.scalers['feature_scaler'].transform(features.reshape(1, -1))
            
            # Predict
            prediction_proba = model.predict_proba(features_scaled)[0]
            prediction = model.predict(features_scaled)[0]
            
            # Confidence is the maximum probability
            confidence = np.max(prediction_proba)
            
            return MLPrediction(
                prediction=float(prediction),
                confidence=float(confidence),
                model_type=f"signal_confidence_{signal_type}",
                features_used=[f"feature_{i}" for i in range(len(features))],
                timestamp=time.time(),
                metadata={"signal_type": signal_type, "probabilities": prediction_proba.tolist()}
            )
            
        except Exception as e:
            logger.error(f"❌ Signal confidence prediction failed: {e}")
            return MLPrediction(0.5, 0.3, "fallback", [], time.time(), {"reason": f"Prediction failed: {str(e)}"})
    
    def predict_market_regime(self, features: np.ndarray) -> MLPrediction:
        """Predict market regime using trained model"""
        if not ML_AVAILABLE:
            return MLPrediction(0.0, 0.0, "error", [], time.time(), {"error": "ML not available"})
        
        try:
            # Check if model is trained
            if 'market_regime' not in self.models or not hasattr(self.models['market_regime'], 'predict'):
                # Return fallback prediction
                return MLPrediction(0.5, 0.3, "NEUTRAL_NORMAL", [], time.time(), {"reason": "Model not trained"})
            model = self.models['market_regime']['regime_classifier']
            
            # Scale features
            features_scaled = self.scalers['feature_scaler'].transform(features.reshape(1, -1))
            
            # Predict
            prediction_proba = model.predict_proba(features_scaled)[0]
            prediction = model.predict(features_scaled)[0]
            
            # Confidence is the maximum probability
            confidence = np.max(prediction_proba)
            
            return MLPrediction(
                prediction=float(prediction),
                confidence=float(confidence),
                model_type="market_regime",
                features_used=[f"feature_{i}" for i in range(len(features))],
                timestamp=time.time(),
                metadata={"probabilities": prediction_proba.tolist()}
            )
            
        except Exception as e:
            logger.error(f"❌ Market regime prediction failed: {e}")
            return MLPrediction(0.0, 0.0, "error", [], time.time(), {"error": str(e)})
    
    def _save_model(self, model_name: str, model):
        """Save trained model to disk"""
        try:
            model_file = self.model_path / f"{model_name}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"💾 Model saved: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to save model {model_name}: {e}")
    
    def _load_model(self, model_name: str):
        """Load trained model from disk"""
        try:
            model_file = self.model_path / f"{model_name}.pkl"
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    model = pickle.load(f)
                logger.info(f"📂 Model loaded: {model_name}")
                return model
            else:
                logger.warning(f"⚠️ Model file not found: {model_name}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_name}: {e}")
            return None
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        status = {
            "ml_available": ML_AVAILABLE,
            "models_initialized": len(self.models) > 0,
            "model_count": sum(len(models) for models in self.models.values()),
            "saved_models": list(self.model_path.glob("*.pkl")),
            "timestamp": time.time()
        }
        return status

# Global ML Manager instance
global_ml_manager = MLModelManager()
