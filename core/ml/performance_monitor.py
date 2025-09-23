#!/usr/bin/env python3
"""
Model Performance Monitoring System
===================================
Monitors ML model performance, tracks predictions vs actuals, and provides performance metrics
"""

import time
import json
import numpy as np
# import pandas as pd  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger
from collections import defaultdict, deque

@dataclass
class PredictionRecord:
    """Record of a prediction made by the model"""
    timestamp: float
    model_type: str
    model_name: str
    prediction: float
    confidence: float
    features_hash: str
    market_conditions: Dict[str, Any]
    metadata: Dict[str, Any] = None

@dataclass
class ActualOutcome:
    """Record of actual market outcome"""
    timestamp: float
    actual_price: float
    price_change: float
    price_change_pct: float
    market_regime: str
    volatility: float
    volume: float
    metadata: Dict[str, Any] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for a model"""
    model_name: str
    total_predictions: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    mse: float
    mae: float
    r2_score: float
    confidence_correlation: float
    prediction_bias: float
    last_updated: float

class ModelPerformanceMonitor:
    """Monitors and tracks ML model performance"""
    
    def __init__(self, data_path: str = "ml_performance"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        # Prediction tracking
        self.pending_predictions = {}  # timestamp -> PredictionRecord
        self.completed_predictions = deque(maxlen=10000)  # Keep last 10k predictions
        
        # Performance metrics
        self.performance_metrics = {}
        self.model_history = defaultdict(list)
        
        # Dynamic performance thresholds based on market conditions
        self.base_performance_thresholds = {
            "min_accuracy": 0.6,
            "min_confidence_correlation": 0.3,
            "max_prediction_bias": 0.1,
            "min_predictions_for_evaluation": 50
        }
        
        # Load existing data
        self._load_performance_data()
        
        logger.info("📊 Model Performance Monitor initialized")
    
    def get_dynamic_thresholds(self, market_conditions: Dict[str, Any] = None) -> Dict[str, float]:
        """Calculate dynamic performance thresholds based on market conditions"""
        try:
            if not market_conditions:
                return self.base_performance_thresholds.copy()
            
            # Analyze market conditions
            volatility = market_conditions.get("volatility_5m", 0.001)
            trend_strength = market_conditions.get("trend_analysis", {}).get("alignment_score", 0.5)
            volume_ratio = market_conditions.get("hyperliquid_volume", {}).get("volume_ratio", 1.0)
            
            # Adjust thresholds based on market difficulty
            # Higher volatility = lower expected accuracy
            # Stronger trends = higher expected accuracy
            # Higher volume = more reliable data
            
            volatility_adjustment = -volatility * 20  # Higher vol = lower threshold
            trend_adjustment = trend_strength * 0.1   # Stronger trend = higher threshold
            volume_adjustment = min(0.05, (volume_ratio - 1.0) * 0.02)  # Higher volume = higher threshold
            
            # Calculate dynamic thresholds
            dynamic_thresholds = self.base_performance_thresholds.copy()
            dynamic_thresholds["min_accuracy"] = max(0.4, min(0.8, 
                self.base_performance_thresholds["min_accuracy"] + volatility_adjustment + trend_adjustment + volume_adjustment))
            
            dynamic_thresholds["min_confidence_correlation"] = max(0.2, min(0.5,
                self.base_performance_thresholds["min_confidence_correlation"] + trend_adjustment + volume_adjustment))
            
            # Prediction bias should be more lenient in volatile markets
            dynamic_thresholds["max_prediction_bias"] = min(0.2, max(0.05,
                self.base_performance_thresholds["max_prediction_bias"] + volatility * 10))
            
            return dynamic_thresholds
            
        except Exception as e:
            logger.error(f"❌ Dynamic threshold calculation failed: {e}")
            return self.base_performance_thresholds.copy()
    
    def record_prediction(self, model_type: str, model_name: str, prediction: float, 
                         confidence: float, features: np.ndarray, 
                         market_conditions: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Record a prediction for later evaluation"""
        try:
            # Create unique prediction ID
            prediction_id = f"{model_type}_{model_name}_{int(time.time() * 1000)}"
            
            # Hash features for comparison
            features_hash = self._hash_features(features)
            
            # Create prediction record
            prediction_record = PredictionRecord(
                timestamp=time.time(),
                model_type=model_type,
                model_name=model_name,
                prediction=prediction,
                confidence=confidence,
                features_hash=features_hash,
                market_conditions=market_conditions,
                metadata=metadata or {}
            )
            
            # Store pending prediction
            self.pending_predictions[prediction_id] = prediction_record
            
            logger.debug(f"📊 Recorded prediction: {model_name} -> {prediction:.4f} (confidence: {confidence:.3f})")
            
            return prediction_id
            
        except Exception as e:
            logger.error(f"❌ Failed to record prediction: {e}")
            return ""
    
    def record_actual_outcome(self, prediction_id: str, actual_price: float, 
                            initial_price: float, market_conditions: Dict[str, Any] = None) -> bool:
        """Record actual market outcome for a prediction"""
        try:
            if prediction_id not in self.pending_predictions:
                logger.warning(f"⚠️ Prediction ID not found: {prediction_id}")
                return False
            
            prediction_record = self.pending_predictions[prediction_id]
            
            # Calculate price change
            price_change = actual_price - initial_price
            price_change_pct = (price_change / initial_price) * 100
            
            # Create actual outcome record
            actual_outcome = ActualOutcome(
                timestamp=time.time(),
                actual_price=actual_price,
                price_change=price_change,
                price_change_pct=price_change_pct,
                market_regime=market_conditions.get("market_regime", "UNKNOWN") if market_conditions else "UNKNOWN",
                volatility=market_conditions.get("volatility_5m", 0.0) if market_conditions else 0.0,
                volume=market_conditions.get("volume_btc", 0.0) if market_conditions else 0.0,
                metadata=market_conditions or {}
            )
            
            # Move to completed predictions
            self.completed_predictions.append((prediction_record, actual_outcome))
            
            # Remove from pending
            del self.pending_predictions[prediction_id]
            
            # Update performance metrics
            self._update_performance_metrics(prediction_record, actual_outcome)
            
            logger.debug(f"📊 Recorded outcome: {prediction_id} -> {price_change_pct:.2f}% change")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to record actual outcome: {e}")
            return False
    
    def _update_performance_metrics(self, prediction: PredictionRecord, actual: ActualOutcome):
        """Update performance metrics for a model"""
        try:
            model_key = f"{prediction.model_type}_{prediction.model_name}"
            
            # Add to model history
            self.model_history[model_key].append((prediction, actual))
            
            # Keep only recent history (last 1000 predictions per model)
            if len(self.model_history[model_key]) > 1000:
                self.model_history[model_key] = self.model_history[model_key][-1000:]
            
            # Calculate performance metrics
            self._calculate_performance_metrics(model_key)
            
        except Exception as e:
            logger.error(f"❌ Failed to update performance metrics: {e}")
    
    def _calculate_performance_metrics(self, model_key: str):
        """Calculate comprehensive performance metrics for a model"""
        try:
            if model_key not in self.model_history or len(self.model_history[model_key]) < 10:
                return
            
            predictions_data = self.model_history[model_key]
            
            # Extract data
            predictions = [p[0].prediction for p in predictions_data]
            actuals = [p[1].price_change_pct for p in predictions_data]
            confidences = [p[0].confidence for p in predictions_data]
            
            # Convert to numpy arrays
            pred_array = np.array(predictions)
            actual_array = np.array(actuals)
            conf_array = np.array(confidences)
            
            # Calculate regression metrics
            mse = np.mean((pred_array - actual_array) ** 2)
            mae = np.mean(np.abs(pred_array - actual_array))
            
            # R² score
            ss_res = np.sum((actual_array - pred_array) ** 2)
            ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
            r2_score = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Classification metrics (for direction prediction)
            pred_directions = np.sign(pred_array)
            actual_directions = np.sign(actual_array)
            
            # Accuracy (direction prediction)
            accuracy = np.mean(pred_directions == actual_directions)
            
            # Precision, Recall, F1 (for positive predictions)
            true_positives = np.sum((pred_directions == 1) & (actual_directions == 1))
            false_positives = np.sum((pred_directions == 1) & (actual_directions == -1))
            false_negatives = np.sum((pred_directions == -1) & (actual_directions == 1))
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Confidence correlation
            confidence_correlation = np.corrcoef(conf_array, np.abs(actual_array - pred_array))[0, 1]
            if np.isnan(confidence_correlation):
                confidence_correlation = 0.0
            
            # Prediction bias
            prediction_bias = np.mean(pred_array - actual_array)
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                model_name=model_key,
                total_predictions=len(predictions_data),
                accuracy=float(accuracy),
                precision=float(precision),
                recall=float(recall),
                f1_score=float(f1_score),
                mse=float(mse),
                mae=float(mae),
                r2_score=float(r2_score),
                confidence_correlation=float(confidence_correlation),
                prediction_bias=float(prediction_bias),
                last_updated=time.time()
            )
            
            self.performance_metrics[model_key] = metrics
            
            logger.debug(f"📊 Updated metrics for {model_key}: accuracy={accuracy:.3f}, mse={mse:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate performance metrics: {e}")
    
    def get_model_performance(self, model_key: str = None) -> Dict[str, Any]:
        """Get performance metrics for a specific model or all models"""
        try:
            if model_key:
                if model_key in self.performance_metrics:
                    return asdict(self.performance_metrics[model_key])
                else:
                    return {"error": f"Model {model_key} not found"}
            
            # Return all models
            return {
                model_key: asdict(metrics) 
                for model_key, metrics in self.performance_metrics.items()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get model performance: {e}")
            return {"error": str(e)}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        try:
            if not self.performance_metrics:
                return {"error": "No performance data available"}
            
            # Calculate overall statistics
            all_accuracies = [m.accuracy for m in self.performance_metrics.values()]
            all_mses = [m.mse for m in self.performance_metrics.values()]
            all_conf_corrs = [m.confidence_correlation for m in self.performance_metrics.values()]
            
            # Identify best and worst performing models
            best_accuracy_model = max(self.performance_metrics.items(), key=lambda x: x[1].accuracy)
            worst_accuracy_model = min(self.performance_metrics.items(), key=lambda x: x[1].accuracy)
            
            best_mse_model = min(self.performance_metrics.items(), key=lambda x: x[1].mse)
            worst_mse_model = max(self.performance_metrics.items(), key=lambda x: x[1].mse)
            
            return {
                "total_models": len(self.performance_metrics),
                "total_predictions": sum(m.total_predictions for m in self.performance_metrics.values()),
                "overall_accuracy": {
                    "mean": float(np.mean(all_accuracies)),
                    "std": float(np.std(all_accuracies)),
                    "min": float(np.min(all_accuracies)),
                    "max": float(np.max(all_accuracies))
                },
                "overall_mse": {
                    "mean": float(np.mean(all_mses)),
                    "std": float(np.std(all_mses)),
                    "min": float(np.min(all_mses)),
                    "max": float(np.max(all_mses))
                },
                "confidence_correlation": {
                    "mean": float(np.mean(all_conf_corrs)),
                    "std": float(np.std(all_conf_corrs))
                },
                "best_models": {
                    "accuracy": {"model": best_accuracy_model[0], "score": best_accuracy_model[1].accuracy},
                    "mse": {"model": best_mse_model[0], "score": best_mse_model[1].mse}
                },
                "worst_models": {
                    "accuracy": {"model": worst_accuracy_model[0], "score": worst_accuracy_model[1].accuracy},
                    "mse": {"model": worst_mse_model[0], "score": worst_mse_model[1].mse}
                },
                "models_needing_attention": self._identify_problematic_models(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance summary: {e}")
            return {"error": str(e)}
    
    def _identify_problematic_models(self) -> List[Dict[str, Any]]:
        """Identify models that need attention based on performance thresholds"""
        problematic = []
        
        for model_key, metrics in self.performance_metrics.items():
            issues = []
            
            if metrics.accuracy < self.performance_thresholds["min_accuracy"]:
                issues.append(f"Low accuracy: {metrics.accuracy:.3f}")
            
            if abs(metrics.confidence_correlation) < self.performance_thresholds["min_confidence_correlation"]:
                issues.append(f"Poor confidence correlation: {metrics.confidence_correlation:.3f}")
            
            if abs(metrics.prediction_bias) > self.performance_thresholds["max_prediction_bias"]:
                issues.append(f"High prediction bias: {metrics.prediction_bias:.3f}")
            
            if metrics.total_predictions < self.performance_thresholds["min_predictions_for_evaluation"]:
                issues.append(f"Insufficient data: {metrics.total_predictions} predictions")
            
            if issues:
                problematic.append({
                    "model": model_key,
                    "issues": issues,
                    "metrics": asdict(metrics)
                })
        
        return problematic
    
    def _hash_features(self, features: np.ndarray) -> str:
        """Create a hash of features for comparison"""
        try:
            # Round features to reduce noise
            rounded_features = np.round(features, 4)
            return str(hash(rounded_features.tobytes()))
        except Exception:
            return str(hash(str(features)))
    
    def _load_performance_data(self):
        """Load existing performance data from disk"""
        try:
            performance_file = self.data_path / "performance_metrics.json"
            if performance_file.exists():
                with open(performance_file, 'r') as f:
                    data = json.load(f)
                
                # Restore performance metrics
                for model_key, metrics_data in data.get("performance_metrics", {}).items():
                    self.performance_metrics[model_key] = PerformanceMetrics(**metrics_data)
                
                logger.info(f"📂 Loaded performance data for {len(self.performance_metrics)} models")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load performance data: {e}")
    
    def save_performance_data(self):
        """Save performance data to disk"""
        try:
            performance_file = self.data_path / "performance_metrics.json"
            
            data = {
                "performance_metrics": {
                    model_key: asdict(metrics) 
                    for model_key, metrics in self.performance_metrics.items()
                },
                "timestamp": time.time()
            }
            
            with open(performance_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Saved performance data for {len(self.performance_metrics)} models")
            
        except Exception as e:
            logger.error(f"❌ Failed to save performance data: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            "pending_predictions": len(self.pending_predictions),
            "completed_predictions": len(self.completed_predictions),
            "tracked_models": len(self.performance_metrics),
            "model_history_size": {k: len(v) for k, v in self.model_history.items()},
            "performance_thresholds": self.performance_thresholds,
            "timestamp": time.time()
        }

# Global performance monitor instance
global_performance_monitor = ModelPerformanceMonitor()
