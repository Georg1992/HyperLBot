#!/usr/bin/env python3
"""
Prediction Ensemble System
==========================
Combines multiple ML models for robust predictions
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from loguru import logger

@dataclass
class EnsemblePrediction:
    """Ensemble prediction result"""
    prediction: float
    confidence: float
    individual_predictions: List[Dict[str, Any]]
    ensemble_method: str
    timestamp: float
    metadata: Dict[str, Any] = None

class ModelEnsemble:
    """Combines multiple models for ensemble predictions"""
    
    def __init__(self):
        self.models = {}
        self.weights = {}
        self.ensemble_methods = ["weighted_average", "majority_vote", "confidence_weighted"]
        
        logger.info("🎯 Model Ensemble initialized")
    
    def add_model(self, model_name: str, model, weight: float = 1.0) -> None:
        """Add a model to the ensemble"""
        self.models[model_name] = model
        self.weights[model_name] = weight
        logger.info(f"➕ Added model to ensemble: {model_name} (weight: {weight})")
    
    def remove_model(self, model_name: str) -> None:
        """Remove a model from the ensemble"""
        if model_name in self.models:
            del self.models[model_name]
            del self.weights[model_name]
            logger.info(f"➖ Removed model from ensemble: {model_name}")
    
    def predict_ensemble(self, features: np.ndarray, method: str = "weighted_average") -> EnsemblePrediction:
        """Make ensemble prediction using specified method"""
        try:
            if not self.models:
                return EnsemblePrediction(0.0, 0.0, [], method, time.time(), {"error": "No models in ensemble"})
            
            individual_predictions = []
            
            # Get predictions from all models
            for model_name, model in self.models.items():
                try:
                    if hasattr(model, 'predict'):
                        prediction = model.predict(features.reshape(1, -1))[0]
                        confidence = 0.8  # Default confidence
                        
                        # Try to get confidence if available
                        if hasattr(model, 'predict_proba'):
                            proba = model.predict_proba(features.reshape(1, -1))[0]
                            confidence = np.max(proba)
                        
                        individual_predictions.append({
                            "model_name": model_name,
                            "prediction": float(prediction),
                            "confidence": float(confidence),
                            "weight": self.weights[model_name]
                        })
                        
                except Exception as e:
                    logger.warning(f"⚠️ Model {model_name} prediction failed: {e}")
                    continue
            
            if not individual_predictions:
                return EnsemblePrediction(0.0, 0.0, [], method, time.time(), {"error": "All model predictions failed"})
            
            # Combine predictions using specified method
            if method == "weighted_average":
                final_prediction, final_confidence = self._weighted_average(individual_predictions)
            elif method == "majority_vote":
                final_prediction, final_confidence = self._majority_vote(individual_predictions)
            elif method == "confidence_weighted":
                final_prediction, final_confidence = self._confidence_weighted(individual_predictions)
            else:
                return EnsemblePrediction(0.0, 0.0, individual_predictions, method, time.time(), {"error": f"Unknown method: {method}"})
            
            return EnsemblePrediction(
                prediction=final_prediction,
                confidence=final_confidence,
                individual_predictions=individual_predictions,
                ensemble_method=method,
                timestamp=time.time(),
                metadata={"model_count": len(individual_predictions)}
            )
            
        except Exception as e:
            logger.error(f"❌ Ensemble prediction failed: {e}")
            return EnsemblePrediction(0.0, 0.0, [], method, time.time(), {"error": str(e)})
    
    def _weighted_average(self, predictions: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate weighted average of predictions"""
        total_weight = sum(p["weight"] for p in predictions)
        if total_weight == 0:
            return 0.0, 0.0
        
        weighted_sum = sum(p["prediction"] * p["weight"] for p in predictions)
        weighted_confidence = sum(p["confidence"] * p["weight"] for p in predictions)
        
        final_prediction = weighted_sum / total_weight
        final_confidence = weighted_confidence / total_weight
        
        return final_prediction, final_confidence
    
    def _majority_vote(self, predictions: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate majority vote of predictions"""
        # For regression, use median
        predictions_values = [p["prediction"] for p in predictions]
        final_prediction = np.median(predictions_values)
        
        # Confidence based on agreement
        agreement = sum(1 for p in predictions_values if abs(p - final_prediction) < 0.1) / len(predictions_values)
        final_confidence = agreement
        
        return final_prediction, final_confidence
    
    def _confidence_weighted(self, predictions: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate confidence-weighted average"""
        total_confidence = sum(p["confidence"] for p in predictions)
        if total_confidence == 0:
            return 0.0, 0.0
        
        confidence_weighted_sum = sum(p["prediction"] * p["confidence"] for p in predictions)
        final_prediction = confidence_weighted_sum / total_confidence
        final_confidence = total_confidence / len(predictions)
        
        return final_prediction, final_confidence
    
    def get_ensemble_status(self) -> Dict[str, Any]:
        """Get ensemble status"""
        return {
            "model_count": len(self.models),
            "models": list(self.models.keys()),
            "weights": self.weights.copy(),
            "available_methods": self.ensemble_methods,
            "timestamp": time.time()
        }

class PredictionEnsemble:
    """Main prediction ensemble system for the trading bot"""
    
    def __init__(self):
        self.price_ensemble = ModelEnsemble()
        self.signal_ensemble = ModelEnsemble()
        self.regime_ensemble = ModelEnsemble()
        
        logger.info("🎯 Prediction Ensemble system initialized")
    
    def add_price_model(self, model_name: str, model, weight: float = 1.0) -> None:
        """Add model to price prediction ensemble"""
        self.price_ensemble.add_model(model_name, model, weight)
    
    def add_signal_model(self, model_name: str, model, weight: float = 1.0) -> None:
        """Add model to signal confidence ensemble"""
        self.signal_ensemble.add_model(model_name, model, weight)
    
    def add_regime_model(self, model_name: str, model, weight: float = 1.0) -> None:
        """Add model to market regime ensemble"""
        self.regime_ensemble.add_model(model_name, model, weight)
    
    def predict_price_movement(self, features: np.ndarray, method: str = "weighted_average") -> EnsemblePrediction:
        """Predict price movement using ensemble"""
        return self.price_ensemble.predict_ensemble(features, method)
    
    def predict_signal_confidence(self, features: np.ndarray, method: str = "confidence_weighted") -> EnsemblePrediction:
        """Predict signal confidence using ensemble"""
        return self.signal_ensemble.predict_ensemble(features, method)
    
    def predict_market_regime(self, features: np.ndarray, method: str = "majority_vote") -> EnsemblePrediction:
        """Predict market regime using ensemble"""
        return self.regime_ensemble.predict_ensemble(features, method)
    
    def get_comprehensive_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Get comprehensive prediction from all ensembles"""
        try:
            price_pred = self.predict_price_movement(features)
            signal_pred = self.predict_signal_confidence(features)
            regime_pred = self.predict_market_regime(features)
            
            return {
                "price_prediction": {
                    "prediction": price_pred.prediction,
                    "confidence": price_pred.confidence,
                    "method": price_pred.ensemble_method
                },
                "signal_confidence": {
                    "prediction": signal_pred.prediction,
                    "confidence": signal_pred.confidence,
                    "method": signal_pred.ensemble_method
                },
                "market_regime": {
                    "prediction": regime_pred.prediction,
                    "confidence": regime_pred.confidence,
                    "method": regime_pred.ensemble_method
                },
                "overall_confidence": (price_pred.confidence + signal_pred.confidence + regime_pred.confidence) / 3,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive prediction failed: {e}")
            return {"error": str(e)}
    
    def get_ensemble_status(self) -> Dict[str, Any]:
        """Get status of all ensembles"""
        return {
            "price_ensemble": self.price_ensemble.get_ensemble_status(),
            "signal_ensemble": self.signal_ensemble.get_ensemble_status(),
            "regime_ensemble": self.regime_ensemble.get_ensemble_status(),
            "timestamp": time.time()
        }

# Global prediction ensemble instance
global_prediction_ensemble = PredictionEnsemble()
