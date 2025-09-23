#!/usr/bin/env python3
"""
Model Training Pipeline
=======================
Handles training data collection, model training, and validation
"""

import time
import json
import numpy as np
# import pandas as pd  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from pathlib import Path
from loguru import logger
from dataclasses import dataclass

@dataclass
class TrainingDataPoint:
    """Single training data point"""
    features: np.ndarray
    target: float
    timestamp: float
    metadata: Dict[str, Any]

class TrainingDataCollector:
    """Collects and manages training data for ML models"""
    
    def __init__(self, data_path: str = "training_data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        self.training_data = []
        self.max_data_points = 10000  # Maximum data points to keep in memory
        
        logger.info("📊 Training Data Collector initialized")
    
    def add_data_point(self, features: np.ndarray, target: float, 
                      metadata: Dict[str, Any] = None) -> None:
        """Add a new training data point"""
        try:
            data_point = TrainingDataPoint(
                features=features.copy(),
                target=target,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            
            self.training_data.append(data_point)
            
            # Keep only recent data points
            if len(self.training_data) > self.max_data_points:
                self.training_data = self.training_data[-self.max_data_points:]
            
            logger.debug(f"📊 Added training data point: target={target:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add training data point: {e}")
    
    def get_training_data(self, min_data_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """Get training data as numpy arrays"""
        if len(self.training_data) < min_data_points:
            logger.warning(f"⚠️ Not enough training data: {len(self.training_data)} < {min_data_points}")
            return np.array([]), np.array([])
        
        try:
            features = np.array([dp.features for dp in self.training_data])
            targets = np.array([dp.target for dp in self.training_data])
            
            logger.info(f"📊 Retrieved {len(features)} training data points")
            return features, targets
            
        except Exception as e:
            logger.error(f"❌ Failed to get training data: {e}")
            return np.array([]), np.array([])
    
    def save_training_data(self, filename: str = None) -> bool:
        """Save training data to disk"""
        try:
            if not filename:
                filename = f"training_data_{int(time.time())}.json"
            
            file_path = self.data_path / filename
            
            # Convert to serializable format
            data_to_save = []
            for dp in self.training_data:
                data_to_save.append({
                    "features": dp.features.tolist(),
                    "target": dp.target,
                    "timestamp": dp.timestamp,
                    "metadata": dp.metadata
                })
            
            with open(file_path, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            
            logger.info(f"💾 Training data saved: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save training data: {e}")
            return False
    
    def load_training_data(self, filename: str) -> bool:
        """Load training data from disk"""
        try:
            file_path = self.data_path / filename
            
            if not file_path.exists():
                logger.error(f"❌ Training data file not found: {filename}")
                return False
            
            with open(file_path, 'r') as f:
                data_loaded = json.load(f)
            
            # Convert back to TrainingDataPoint objects
            self.training_data = []
            for item in data_loaded:
                dp = TrainingDataPoint(
                    features=np.array(item["features"]),
                    target=item["target"],
                    timestamp=item["timestamp"],
                    metadata=item["metadata"]
                )
                self.training_data.append(dp)
            
            logger.info(f"📂 Training data loaded: {len(self.training_data)} points")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load training data: {e}")
            return False
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """Get statistics about collected training data"""
        if not self.training_data:
            return {"error": "No training data available"}
        
        try:
            targets = [dp.target for dp in self.training_data]
            timestamps = [dp.timestamp for dp in self.training_data]
            
            return {
                "data_points": len(self.training_data),
                "target_mean": np.mean(targets),
                "target_std": np.std(targets),
                "target_min": np.min(targets),
                "target_max": np.max(targets),
                "time_span_hours": (max(timestamps) - min(timestamps)) / 3600,
                "feature_dimensions": len(self.training_data[0].features) if self.training_data else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get data statistics: {e}")
            return {"error": str(e)}

class ModelValidator:
    """Validates trained models and provides performance metrics"""
    
    def __init__(self):
        logger.info("✅ Model Validator initialized")
    
    def validate_model(self, model, X_test: np.ndarray, y_test: np.ndarray, 
                      model_type: str = "regression") -> Dict[str, Any]:
        """Validate a trained model"""
        try:
            if model_type == "regression":
                return self._validate_regression_model(model, X_test, y_test)
            elif model_type == "classification":
                return self._validate_classification_model(model, X_test, y_test)
            else:
                return {"error": f"Unknown model type: {model_type}"}
                
        except Exception as e:
            logger.error(f"❌ Model validation failed: {e}")
            return {"error": str(e)}
    
    def _validate_regression_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Validate regression model"""
        try:
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            
            y_pred = model.predict(X_test)
            
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            return {
                "model_type": "regression",
                "mse": mse,
                "mae": mae,
                "r2_score": r2,
                "rmse": np.sqrt(mse),
                "predictions_count": len(y_pred)
            }
            
        except Exception as e:
            return {"error": f"Regression validation failed: {e}"}
    
    def _validate_classification_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Validate classification model"""
        try:
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            y_pred = model.predict(X_test)
            
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            return {
                "model_type": "classification",
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "predictions_count": len(y_pred)
            }
            
        except Exception as e:
            return {"error": f"Classification validation failed: {e}"}

class ModelTrainer:
    """Main model training orchestrator"""
    
    def __init__(self):
        self.data_collector = TrainingDataCollector()
        self.validator = ModelValidator()
        
        logger.info("🎓 Model Trainer initialized")
    
    def collect_training_data_from_signals(self, signals: Dict[str, Any], 
                                         market_data: Dict[str, Any],
                                         actual_outcome: float = None) -> None:
        """Collect training data from current signals and market data"""
        try:
            from core.ml.feature_engineering import global_feature_engineer
            
            # Extract features
            features = global_feature_engineer.extract_ml_features(market_data, signals)
            
            if len(features) == 0:
                logger.warning("⚠️ No features extracted for training data")
                return
            
            # Use signal consensus as target if no actual outcome provided
            if actual_outcome is None:
                actual_outcome = signals.get("signal_consensus", 0.0)
            
            # Add to training data
            self.data_collector.add_data_point(
                features=features,
                target=actual_outcome,
                metadata={
                    "signal_count": signals.get("signal_count", 0),
                    "dominant_direction": signals.get("dominant_direction", "NEUTRAL"),
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to collect training data: {e}")
    
    def train_trading_prediction_models(self) -> Dict[str, Any]:
        """Train the main trading prediction models"""
        try:
            from core.ml.ml_models import global_ml_manager
            
            # Get training data
            features, targets = self.data_collector.get_training_data(min_data_points=10)
            
            if len(features) == 0:
                return {"error": "No training data available"}
            
            # Convert targets to trading prediction format
            # This is a simplified conversion - in practice, you'd have actual trading outcomes
            buy_targets = np.where(targets > 0.1, 1, 0)  # Positive targets = BUY
            sell_targets = np.where(targets < -0.1, 1, 0)  # Negative targets = SELL
            confidence_targets = np.abs(targets)  # Absolute value as confidence
            price_targets = targets * 1000  # Scale for price targets (simplified)
            
            # Train models
            result = global_ml_manager.train_trading_prediction_models(
                features, buy_targets, sell_targets, confidence_targets, price_targets
            )
            
            if result.get("success"):
                logger.info("✅ Trading prediction models trained successfully")
            else:
                logger.error(f"❌ Trading prediction model training failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Trading prediction training failed: {e}")
            return {"error": str(e)}
    
    def train_price_prediction_model(self, timeframe: str = "short_term") -> Dict[str, Any]:
        """Train price prediction model"""
        try:
            from core.ml.ml_models import global_ml_manager
            
            # Get training data
            features, targets = self.data_collector.get_training_data(min_data_points=10)
            
            if len(features) == 0:
                return {"error": "No training data available"}
            
            # Train model
            result = global_ml_manager.train_price_prediction_model(features, targets, timeframe)
            
            if result.get("success"):
                logger.info(f"✅ Price prediction model trained: {timeframe}")
            else:
                logger.error(f"❌ Price prediction model training failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Price prediction training failed: {e}")
            return {"error": str(e)}
    
    def train_signal_confidence_model(self, signal_type: str = "market_data") -> Dict[str, Any]:
        """Train signal confidence model"""
        try:
            from core.ml.ml_models import global_ml_manager
            
            # Get training data
            features, targets = self.data_collector.get_training_data(min_data_points=10)
            
            if len(features) == 0:
                return {"error": "No training data available"}
            
            # Convert targets to confidence categories
            confidence_targets = self._convert_to_confidence_categories(targets)
            
            # Train model
            result = global_ml_manager.train_signal_confidence_model(features, confidence_targets, signal_type)
            
            if result.get("success"):
                logger.info(f"✅ Signal confidence model trained: {signal_type}")
            else:
                logger.error(f"❌ Signal confidence model training failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Signal confidence training failed: {e}")
            return {"error": str(e)}
    
    def _convert_to_confidence_categories(self, targets: np.ndarray) -> np.ndarray:
        """Convert continuous targets to confidence categories"""
        # Convert to confidence levels: LOW, MEDIUM, HIGH
        categories = []
        for target in targets:
            if target < 0.3:
                categories.append("LOW")
            elif target < 0.7:
                categories.append("MEDIUM")
            else:
                categories.append("HIGH")
        
        return np.array(categories)
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get training status and statistics"""
        try:
            data_stats = self.data_collector.get_data_statistics()
            
            return {
                "training_data": data_stats,
                "data_collector_ready": len(self.data_collector.training_data) > 0,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get training status: {e}")
            return {"error": str(e)}
    

# Global model trainer instance
global_model_trainer = ModelTrainer()
