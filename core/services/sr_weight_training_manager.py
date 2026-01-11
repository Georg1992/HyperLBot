#!/usr/bin/env python3
"""
SR Weight Training Manager - Automatic training scheduler and status tracker

Manages automatic SR weight training:
- Checks if retraining is needed
- Runs training in background thread
- Tracks training status
- Updates dashboard with training info
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    from core.calculations.sr_weight_trainer import SRWeightTrainer
    TRAINING_AVAILABLE = True
except ImportError:
    TRAINING_AVAILABLE = False


class SRWeightTrainingManager:
    """
    Manages automatic SR weight training and status tracking
    """
    
    def __init__(self, retrain_interval_days: int = 7, strategy: str = "standard"):
        """
        Initialize training manager
        
        Args:
            retrain_interval_days: Days between retraining (default: 7)
            strategy: Strategy name (default: "standard")
        """
        self.retrain_interval_days = retrain_interval_days
        self.strategy = strategy
        
        if not TRAINING_AVAILABLE:
            logger.warning("⚠️ SR weight training not available - scikit-learn required")
            self.trainer = None
        else:
            self.trainer = SRWeightTrainer()
        
        self._training_thread = None
        self._training_lock = threading.Lock()
        self._status = {
            "status": "idle",  # idle, training, completed, error
            "last_training_time": None,
            "next_training_time": None,
            "training_progress": 0,  # 0-100
            "training_window": None,
            "total_windows": None,
            "weights_loaded": False,
            "weights_age_days": None,
            "error_message": None
        }
        
        self._update_training_schedule()
    
    def _update_training_schedule(self):
        """Update next training time based on last training"""
        try:
            if not self.trainer:
                return
            
            weights = self.trainer.load_weights(strategy=self.strategy, method="elasticnet")
            if weights:
                weights_file = os.path.join(
                    self.trainer.weights_dir,
                    f"{self.strategy}_elasticnet_weights.json"
                )
                if os.path.exists(weights_file):
                    file_time = os.path.getmtime(weights_file)
                    self._status["last_training_time"] = file_time
                    self._status["weights_loaded"] = True
                    self._status["weights_age_days"] = (time.time() - file_time) / 86400.0
                    self._status["next_training_time"] = file_time + (self.retrain_interval_days * 86400)
                    logger.debug(f"📊 Weights loaded: {self._status['weights_age_days']:.1f} days old")
        except Exception as e:
            logger.debug(f"Could not load weights info: {e}")
    
    def check_and_train_if_needed(self, force: bool = False) -> bool:
        """
        Check if training is needed and start if so (NON-BLOCKING - runs in background thread)
        
        Args:
            force: Force training even if not needed
            
        Returns:
            True if training started, False otherwise
        """
        if not self.trainer:
            return False
        
        # Quick check without lock first to avoid blocking
        if self._status["status"] == "training":
            return False
        
        with self._training_lock:
            if self._status["status"] == "training":
                return False
            
            if not force:
                if self._status["next_training_time"] and time.time() < self._status["next_training_time"]:
                    return False
            
            # Start training in background thread (NON-BLOCKING)
            self._start_training()
            return True
    
    def _start_training(self):
        """Start training in background thread"""
        if not self.trainer:
            return
        
        self._status["status"] = "training"
        self._status["training_progress"] = 0
        self._status["error_message"] = None
        self._status["training_window"] = 0
        self._status["total_windows"] = None
        
        self._training_thread = threading.Thread(target=self._run_training, daemon=True)
        self._training_thread.start()
        logger.info("🤖 Starting SR weight training in background...")
    
    def _run_training(self):
        """Run training (called in background thread)"""
        try:
            if not self.trainer:
                self._status["status"] = "error"
                self._status["error_message"] = "Training not available"
                return
            
            logger.info("🤖 Training SR weights...")
            
            conn = __import__('sqlite3').connect(self.trainer.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM candles_5m")
            min_ts, max_ts = cursor.fetchone()
            conn.close()
            
            if min_ts is None or max_ts is None:
                raise ValueError("Database empty")
            
            seconds_per_month = 30 * 24 * 3600
            train_seconds = 12 * seconds_per_month
            test_seconds = 1 * seconds_per_month
            stride_seconds = 1 * seconds_per_month
            
            current_start = min_ts
            windows = []
            total_windows = 0
            while current_start + train_seconds + test_seconds <= max_ts:
                total_windows += 1
                current_start += stride_seconds
            
            self._status["total_windows"] = total_windows
            
            current_start = min_ts
            window_num = 0
            all_weights = []
            
            while current_start + train_seconds + test_seconds <= max_ts:
                window_num += 1
                self._status["training_window"] = window_num
                self._status["training_progress"] = int((window_num / total_windows) * 100)
                
                train_end = current_start + train_seconds
                
                try:
                    features_train, targets_train = self.trainer.extract_features_and_targets(current_start, train_end)
                    
                    if len(features_train) >= 100:
                        weights = self.trainer.train_elasticnet(features_train, targets_train, alpha=0.1, l1_ratio=0.5)
                        all_weights.append(weights)
                except Exception as e:
                    logger.warning(f"Training failed for window {window_num}: {e}")
                
                current_start += stride_seconds
            
            if len(all_weights) == 0:
                raise ValueError("No successful training windows")
            
            import numpy as np
            averaged_weights = {
                key: np.mean([w[key] for w in all_weights])
                for key in all_weights[0].keys()
            }
            
            total = sum(averaged_weights.values())
            normalized_weights = {key: val / total for key, val in averaged_weights.items()}
            
            self.trainer.save_weights(normalized_weights, strategy=self.strategy, method="elasticnet")
            
            self._status["status"] = "completed"
            self._status["training_progress"] = 100
            self._status["last_training_time"] = time.time()
            self._status["next_training_time"] = time.time() + (self.retrain_interval_days * 86400)
            self._status["weights_loaded"] = True
            self._status["weights_age_days"] = 0
            
            logger.info("✅ SR weight training completed successfully")
            
        except Exception as e:
            logger.error(f"❌ SR weight training failed: {e}")
            self._status["status"] = "error"
            self._status["error_message"] = str(e)
        finally:
            with self._training_lock:
                self._training_thread = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current training status"""
        with self._training_lock:
            return self._status.copy()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get training data formatted for dashboard ML panel"""
        status = self.get_status()
        
        status_text = status["status"].upper()
        if status["status"] == "training":
            progress = status.get("training_progress", 0)
            window = status.get("training_window", 0)
            total = status.get("total_windows", 0)
            status_text = f"Training ({progress}% - {window}/{total})"
        elif status["status"] == "completed":
            status_text = "Completed"
        elif status["status"] == "error":
            status_text = "Error"
        
        next_train = "N/A"
        if status.get("next_training_time"):
            days = (status["next_training_time"] - time.time()) / 86400.0
            if days > 0:
                next_train = f"{days:.1f} days"
            else:
                next_train = "Due"
        
        age_days = status.get("weights_age_days")
        age_text = f"{age_days:.1f} days" if age_days is not None else "N/A"
        
        return {
            "analysis_type": "SR Weight Learning",
            "analysis_type_detail": "ElasticNet Regression",
            "training_data_points": status.get("total_windows", 0),
            "accuracy": None,
            "confidence_correlation": None,
            "retrain_status": status_text,
            "learning_status": "Active" if status.get("weights_loaded") else "No weights",
            "weights_age_days": age_days,
            "next_training": next_train,
            "training_in_progress": status["status"] == "training",
            "error_message": status.get("error_message")
        }


# Global instance
_global_training_manager = None

def get_global_training_manager(strategy: str = "standard") -> Optional[SRWeightTrainingManager]:
    """Get global training manager instance"""
    global _global_training_manager
    if _global_training_manager is None:
        _global_training_manager = SRWeightTrainingManager(strategy=strategy)
    return _global_training_manager
