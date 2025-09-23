#!/usr/bin/env python3
"""
Continuous Learning System
==========================
Implements continuous learning for ML models with automatic retraining and adaptation
"""

import time
import threading
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from loguru import logger
# from pathlib import Path  # Removed unused import

from .performance_monitor import global_performance_monitor
from .model_training import global_model_trainer
# from .ml_models import global_ml_manager  # Removed unused import

@dataclass
class LearningTrigger:
    """Defines when to trigger model retraining"""
    trigger_type: str  # "performance", "time", "data_size", "manual"
    threshold: float
    last_triggered: float = 0.0
    enabled: bool = True

@dataclass
class LearningConfig:
    """Configuration for continuous learning"""
    retrain_interval_hours: float = 24.0  # Retrain every 24 hours
    min_data_points: int = 100  # Minimum data points for retraining
    performance_threshold: float = 0.6  # Retrain if accuracy drops below this
    confidence_threshold: float = 0.3  # Retrain if confidence correlation drops below this
    max_retrain_frequency_hours: float = 4.0  # Maximum retrain frequency
    enable_automatic_retraining: bool = True
    enable_performance_monitoring: bool = True
    enable_feature_adaptation: bool = True

class ContinuousLearningSystem:
    """Manages continuous learning for ML models"""
    
    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        
        # Learning triggers
        self.learning_triggers = {
            "performance": LearningTrigger("performance", self.config.performance_threshold),
            "time": LearningTrigger("time", self.config.retrain_interval_hours),
            "data_size": LearningTrigger("data_size", self.config.min_data_points),
            "confidence": LearningTrigger("confidence", self.config.confidence_threshold)
        }
        
        # Learning state
        self.is_learning = False
        self.last_retrain_time = 0.0
        self.retrain_count = 0
        self.learning_thread = None
        self.stop_learning = False
        
        # Model performance tracking
        self.model_performance_history = {}
        self.feature_importance_history = {}
        
        # Learning callbacks
        self.learning_callbacks = []
        
        logger.info("🔄 Continuous Learning System initialized")
    
    def start_continuous_learning(self):
        """Start the continuous learning system"""
        if self.learning_thread and self.learning_thread.is_alive():
            logger.debug("🔄 Continuous learning already running - skipping duplicate start")
            return
        
        self.stop_learning = False
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.learning_thread.start()
        
        logger.info("🔄 Continuous learning system started")
    
    def stop_continuous_learning(self):
        """Stop the continuous learning system"""
        self.stop_learning = True
        if self.learning_thread:
            self.learning_thread.join(timeout=5.0)
        
        logger.info("🔄 Continuous learning system stopped")
    
    def _learning_loop(self):
        """Main learning loop that runs in background"""
        while not self.stop_learning:
            try:
                # Check if learning is needed
                if self._should_retrain():
                    self._perform_retraining()
                
                # Update performance tracking
                if self.config.enable_performance_monitoring:
                    self._update_performance_tracking()
                
                # Adapt features if needed
                if self.config.enable_feature_adaptation:
                    self._adapt_features()
                
                # Sleep for 5 minutes before next check
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Error in learning loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _should_retrain(self) -> bool:
        """Determine if models should be retrained"""
        try:
            # Check if automatic retraining is enabled
            if not self.config.enable_automatic_retraining:
                return False
            
            # Check minimum retrain frequency
            time_since_last_retrain = time.time() - self.last_retrain_time
            if time_since_last_retrain < self.config.max_retrain_frequency_hours * 3600:
                return False
            
            # Check data size trigger
            training_status = global_model_trainer.get_training_status()
            data_points = training_status.get("training_data", {}).get("data_points", 0)
            
            if data_points < self.config.min_data_points:
                logger.debug(f"🔄 Not enough data for retraining: {data_points} < {self.config.min_data_points}")
                return False
            
            # Check performance trigger
            performance_summary = global_performance_monitor.get_performance_summary()
            if "error" not in performance_summary:
                overall_accuracy = performance_summary.get("overall_accuracy", {}).get("mean", 1.0)
                if overall_accuracy < self.config.performance_threshold:
                    logger.info(f"🔄 Performance trigger: accuracy {overall_accuracy:.3f} < {self.config.performance_threshold}")
                    return True
            
            # Check time trigger
            if time_since_last_retrain > self.config.retrain_interval_hours * 3600:
                logger.info(f"🔄 Time trigger: {time_since_last_retrain/3600:.1f}h since last retrain")
                return True
            
            # Check confidence correlation trigger
            if "error" not in performance_summary:
                conf_correlation = performance_summary.get("confidence_correlation", {}).get("mean", 1.0)
                if conf_correlation < self.config.confidence_threshold:
                    logger.info(f"🔄 Confidence trigger: correlation {conf_correlation:.3f} < {self.config.confidence_threshold}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking retrain conditions: {e}")
            return False
    
    def _perform_retraining(self):
        """Perform model retraining"""
        try:
            if self.is_learning:
                logger.warning("⚠️ Retraining already in progress")
                return
            
            self.is_learning = True
            logger.info("🔄 Starting model retraining...")
            
            # Get training data
            training_status = global_model_trainer.get_training_status()
            data_points = training_status.get("training_data", {}).get("data_points", 0)
            
            if data_points < self.config.min_data_points:
                logger.warning(f"⚠️ Insufficient data for retraining: {data_points} < {self.config.min_data_points}")
                self.is_learning = False
                return
            
            # Retrain main trading prediction models
            logger.info("🔄 Retraining trading prediction models...")
            trading_results = {}
            try:
                result = global_model_trainer.train_trading_prediction_models()
                trading_results["main"] = result
                if result.get("success"):
                    logger.info("✅ Trading prediction models retrained successfully")
                else:
                    logger.warning(f"⚠️ Trading prediction model retraining failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Trading prediction model retraining error: {e}")
                trading_results["main"] = {"error": str(e)}
            
            # Retrain signal confidence models
            logger.info("🔄 Retraining signal confidence models...")
            signal_results = {}
            for signal_type in ["market_data", "orderbook", "pattern"]:
                try:
                    result = global_model_trainer.train_signal_confidence_model(signal_type)
                    signal_results[signal_type] = result
                    if result.get("success"):
                        logger.info(f"✅ {signal_type} signal model retrained successfully")
                    else:
                        logger.warning(f"⚠️ {signal_type} signal model retraining failed: {result.get('error')}")
                except Exception as e:
                    logger.error(f"❌ {signal_type} signal model retraining error: {e}")
                    signal_results[signal_type] = {"error": str(e)}
            
            # Update retrain tracking
            self.last_retrain_time = time.time()
            self.retrain_count += 1
            
            # Save training data
            global_model_trainer.save_training_data(f"retrain_{int(self.last_retrain_time)}.json")
            
            # Notify callbacks
            self._notify_learning_callbacks({
                "event": "retraining_completed",
                "retrain_count": self.retrain_count,
                "trading_results": trading_results,
                "signal_results": signal_results,
                "timestamp": self.last_retrain_time
            })
            
            logger.info(f"✅ Model retraining completed (retrain #{self.retrain_count})")
            
        except Exception as e:
            logger.error(f"❌ Model retraining failed: {e}")
        finally:
            self.is_learning = False
    
    def _update_performance_tracking(self):
        """Update performance tracking and history"""
        try:
            # Get current performance summary
            performance_summary = global_performance_monitor.get_performance_summary()
            
            if "error" not in performance_summary:
                # Store performance history
                timestamp = time.time()
                self.model_performance_history[timestamp] = performance_summary
                
                # Keep only recent history (last 100 entries)
                if len(self.model_performance_history) > 100:
                    oldest_timestamp = min(self.model_performance_history.keys())
                    del self.model_performance_history[oldest_timestamp]
                
                # Check for performance degradation
                self._check_performance_degradation()
            
        except Exception as e:
            logger.error(f"❌ Performance tracking update failed: {e}")
    
    def _check_performance_degradation(self):
        """Check for significant performance degradation"""
        try:
            if len(self.model_performance_history) < 2:
                return
            
            # Get recent performance data
            recent_timestamps = sorted(self.model_performance_history.keys())[-5:]  # Last 5 entries
            recent_performances = [self.model_performance_history[ts] for ts in recent_timestamps]
            
            # Calculate performance trend
            accuracies = [p["overall_accuracy"]["mean"] for p in recent_performances]
            if len(accuracies) >= 3:
                # Simple trend analysis
                recent_avg = np.mean(accuracies[-2:])
                older_avg = np.mean(accuracies[:-2])
                
                performance_change = recent_avg - older_avg
                
                if performance_change < -0.05:  # 5% degradation
                    logger.warning(f"⚠️ Performance degradation detected: {performance_change:.3f}")
                    self._notify_learning_callbacks({
                        "event": "performance_degradation",
                        "performance_change": performance_change,
                        "recent_accuracy": recent_avg,
                        "older_accuracy": older_avg,
                        "timestamp": time.time()
                    })
        
        except Exception as e:
            logger.error(f"❌ Performance degradation check failed: {e}")
    
    def _adapt_features(self):
        """Adapt feature engineering based on performance"""
        try:
            # Get feature importance from recent models
            # This is a placeholder for future feature adaptation logic
            pass
            
        except Exception as e:
            logger.error(f"❌ Feature adaptation failed: {e}")
    
    def add_learning_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback function to be called during learning events"""
        self.learning_callbacks.append(callback)
    
    def _notify_learning_callbacks(self, event_data: Dict[str, Any]):
        """Notify all registered callbacks of learning events"""
        for callback in self.learning_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"❌ Learning callback error: {e}")
    
    def force_retrain(self, reason: str = "manual") -> Dict[str, Any]:
        """Force immediate model retraining"""
        try:
            if self.is_learning:
                return {"error": "Retraining already in progress"}
            
            logger.info(f"🔄 Force retraining triggered: {reason}")
            
            # Temporarily disable automatic retraining to avoid conflicts
            original_config = self.config.enable_automatic_retraining
            self.config.enable_automatic_retraining = False
            
            # Perform retraining
            self._perform_retraining()
            
            # Restore original config
            self.config.enable_automatic_retraining = original_config
            
            return {
                "success": True,
                "reason": reason,
                "retrain_count": self.retrain_count,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Force retraining failed: {e}")
            return {"error": str(e)}
    
    def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning system status"""
        try:
            training_status = global_model_trainer.get_training_status()
            performance_summary = global_performance_monitor.get_performance_summary()
            
            return {
                "is_learning": self.is_learning,
                "is_running": self.learning_thread and self.learning_thread.is_alive(),
                "retrain_count": self.retrain_count,
                "last_retrain_time": self.last_retrain_time,
                "time_since_last_retrain": time.time() - self.last_retrain_time,
                "config": {
                    "retrain_interval_hours": self.config.retrain_interval_hours,
                    "min_data_points": self.config.min_data_points,
                    "performance_threshold": self.config.performance_threshold,
                    "confidence_threshold": self.config.confidence_threshold,
                    "enable_automatic_retraining": self.config.enable_automatic_retraining
                },
                "training_data": training_status.get("training_data", {}),
                "performance_summary": performance_summary,
                "performance_history_size": len(self.model_performance_history),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get learning status: {e}")
            return {"error": str(e)}
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update learning configuration"""
        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"🔄 Updated learning config: {key} = {value}")
            
            # Update trigger thresholds
            if "performance_threshold" in new_config:
                self.learning_triggers["performance"].threshold = new_config["performance_threshold"]
            
            if "confidence_threshold" in new_config:
                self.learning_triggers["confidence"].threshold = new_config["confidence_threshold"]
            
            if "min_data_points" in new_config:
                self.learning_triggers["data_size"].threshold = new_config["min_data_points"]
            
            if "retrain_interval_hours" in new_config:
                self.learning_triggers["time"].threshold = new_config["retrain_interval_hours"]
            
        except Exception as e:
            logger.error(f"❌ Failed to update learning config: {e}")

# Global continuous learning system instance
global_continuous_learning = ContinuousLearningSystem()
