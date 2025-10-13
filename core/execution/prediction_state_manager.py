#!/usr/bin/env python3
"""
Prediction State Management System
==================================
Manages prediction states during order lifecycle to prevent conflicting predictions
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from loguru import logger
from enum import Enum

class PredictionState(Enum):
    """Prediction states during order lifecycle"""
    GENERATED = "GENERATED"           # Prediction created but no order placed
    ORDER_PENDING = "ORDER_PENDING"   # Order placed, waiting for fill
    POSITION_ACTIVE = "POSITION_ACTIVE"  # Order filled, position open
    COMPLETED = "COMPLETED"           # Position closed, prediction complete
    CANCELLED = "CANCELLED"           # Prediction cancelled before execution
    EXPIRED = "EXPIRED"               # Prediction expired without execution

@dataclass
class PredictionRecord:
    """Complete prediction record with lifecycle tracking"""
    prediction_id: str
    timestamp: float
    side: str  # BUY or SELL
    entry_price: float
    confidence: float
    expected_value: float
    strategy: str
    state: PredictionState
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    created_at: float = 0.0
    order_placed_at: Optional[float] = None
    position_opened_at: Optional[float] = None
    completed_at: Optional[float] = None
    final_pnl: Optional[float] = None
    exit_reason: Optional[str] = None
    metadata: Dict[str, Any] = None

class PredictionStateManager:
    """Manages prediction states and prevents conflicting predictions"""
    
    def __init__(self):
        # Prediction tracking
        self.predictions: Dict[str, PredictionRecord] = {}
        self.active_predictions: Set[str] = set()  # Predictions with orders/positions
        self.completed_predictions: List[PredictionRecord] = []
        
        # State tracking
        self.current_direction: Optional[str] = None  # Current active direction
        self.last_prediction_time: float = 0.0
        self.prediction_count = 0
        
        # Configuration
        self.min_prediction_interval = 5.0  # Minimum seconds between predictions (reduced for faster trading)
        self.max_concurrent_predictions = 1  # Max predictions with active orders/positions
        
        logger.info("🧠 Prediction State Manager initialized")
    
    def create_prediction(self, prediction_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new prediction record
        
        Args:
            prediction_data: Prediction data from ML engine
            
        Returns:
            prediction_id: Unique identifier for the prediction
        """
        try:
            # Generate unique prediction ID
            prediction_id = f"pred_{uuid.uuid4().hex[:8]}"
            
            # Extract prediction parameters
            side = prediction_data.get("side", "BUY")
            entry_price = prediction_data.get("entry_price", 0.0)
            confidence = prediction_data.get("calibrated_confidence", 0.0)
            expected_value = prediction_data.get("expected_value", 0.0)
            strategy = prediction_data.get("strategy", "standard")
            
            # Check if we can create this prediction
            if not self._can_create_prediction(side):
                logger.warning(f"🚫 Cannot create {side} prediction: conflicting active predictions")
                return None
            
            # Create prediction record
            prediction = PredictionRecord(
                prediction_id=prediction_id,
                timestamp=time.time(),
                side=side,
                entry_price=entry_price,
                confidence=confidence,
                expected_value=expected_value,
                strategy=strategy,
                state=PredictionState.GENERATED,
                created_at=time.time(),
                metadata=prediction_data.copy()
            )
            
            # Store prediction
            self.predictions[prediction_id] = prediction
            self.prediction_count += 1
            self.last_prediction_time = time.time()
            
            logger.info(f"🧠 PREDICTION CREATED: {side} @ ${entry_price:,.2f}")
            logger.info(f"   Prediction ID: {prediction_id}")
            logger.info(f"   Confidence: {confidence:.1%}")
            logger.info(f"   Strategy: {strategy}")
            logger.info(f"   Expected Value: {expected_value:+.2%}")
            
            return prediction_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create prediction: {e}")
            return None
    
    def _can_create_prediction(self, side: str) -> bool:
        """Check if we can create a new prediction in the given direction"""
        try:
            # Check minimum interval
            if time.time() - self.last_prediction_time < self.min_prediction_interval:
                logger.debug(f"⏰ Too soon since last prediction ({self.min_prediction_interval}s interval)")
                return False
            
            # Check for conflicting active predictions (allow override if stale)
            for pred_id in self.active_predictions:
                if pred_id in self.predictions:
                    pred = self.predictions[pred_id]
                    if pred.side != side:
                        # Check if the conflicting prediction is stale (older than 60 seconds)
                        if time.time() - pred.timestamp > 60.0:
                            logger.debug(f"🔄 Clearing stale {pred.side} prediction (ID: {pred_id})")
                            self._clear_prediction(pred_id)
                        else:
                            logger.debug(f"🚫 Conflicting {pred.side} prediction active (ID: {pred_id})")
                            return False
            
            # Check max concurrent predictions
            if len(self.active_predictions) >= self.max_concurrent_predictions:
                logger.debug(f"🚫 Max concurrent predictions reached ({self.max_concurrent_predictions})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking prediction creation: {e}")
            return False
    
    def place_order(self, prediction_id: str, order_id: str) -> bool:
        """
        Mark prediction as having an order placed
        
        Args:
            prediction_id: Prediction identifier
            order_id: Order identifier
            
        Returns:
            success: Whether the operation succeeded
        """
        try:
            if prediction_id not in self.predictions:
                logger.warning(f"⚠️ Prediction {prediction_id} not found")
                return False
            
            prediction = self.predictions[prediction_id]
            
            # Update prediction state
            prediction.state = PredictionState.ORDER_PENDING
            prediction.order_id = order_id
            prediction.order_placed_at = time.time()
            
            # Add to active predictions
            self.active_predictions.add(prediction_id)
            self.current_direction = prediction.side
            
            logger.info(f"📋 ORDER PLACED for prediction {prediction_id}")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Direction: {prediction.side}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to place order for prediction {prediction_id}: {e}")
            return False
    
    def fill_order(self, prediction_id: str, position_id: str) -> bool:
        """
        Mark prediction as having position opened
        
        Args:
            prediction_id: Prediction identifier
            position_id: Position identifier
            
        Returns:
            success: Whether the operation succeeded
        """
        try:
            if prediction_id not in self.predictions:
                logger.warning(f"⚠️ Prediction {prediction_id} not found")
                return False
            
            prediction = self.predictions[prediction_id]
            
            # Update prediction state
            prediction.state = PredictionState.POSITION_ACTIVE
            prediction.position_id = position_id
            prediction.position_opened_at = time.time()
            
            logger.info(f"📈 POSITION OPENED for prediction {prediction_id}")
            logger.info(f"   Position ID: {position_id}")
            logger.info(f"   Entry Price: ${prediction.entry_price:,.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fill order for prediction {prediction_id}: {e}")
            return False
    
    def complete_prediction(self, prediction_id: str, final_pnl: float, exit_reason: str) -> bool:
        """
        Mark prediction as completed
        
        Args:
            prediction_id: Prediction identifier
            final_pnl: Final P&L of the trade
            exit_reason: Reason for exit (STOP_LOSS, TAKE_PROFIT, etc.)
            
        Returns:
            success: Whether the operation succeeded
        """
        try:
            if prediction_id not in self.predictions:
                logger.warning(f"⚠️ Prediction {prediction_id} not found")
                return False
            
            prediction = self.predictions[prediction_id]
            
            # Update prediction state
            prediction.state = PredictionState.COMPLETED
            prediction.completed_at = time.time()
            prediction.final_pnl = final_pnl
            prediction.exit_reason = exit_reason
            
            # Move to completed predictions
            self.completed_predictions.append(prediction)
            
            # Remove from active predictions
            if prediction_id in self.active_predictions:
                self.active_predictions.remove(prediction_id)
            
            # Clear current direction if no active predictions
            if not self.active_predictions:
                self.current_direction = None
            
            logger.info(f"🏁 PREDICTION COMPLETED: {prediction_id}")
            logger.info(f"   Final P&L: ${final_pnl:,.2f}")
            logger.info(f"   Exit Reason: {exit_reason}")
            logger.info(f"   Duration: {(prediction.completed_at - prediction.created_at) / 60:.1f} minutes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to complete prediction {prediction_id}: {e}")
            return False
    
    def cancel_prediction(self, prediction_id: str, reason: str = "MANUAL") -> bool:
        """
        Cancel a prediction
        
        Args:
            prediction_id: Prediction identifier
            reason: Reason for cancellation
            
        Returns:
            success: Whether the operation succeeded
        """
        try:
            if prediction_id not in self.predictions:
                logger.warning(f"⚠️ Prediction {prediction_id} not found")
                return False
            
            prediction = self.predictions[prediction_id]
            
            # Update prediction state
            prediction.state = PredictionState.CANCELLED
            prediction.completed_at = time.time()
            prediction.exit_reason = reason
            
            # Remove from active predictions
            if prediction_id in self.active_predictions:
                self.active_predictions.remove(prediction_id)
            
            # Clear current direction if no active predictions
            if not self.active_predictions:
                self.current_direction = None
            
            logger.info(f"❌ PREDICTION CANCELLED: {prediction_id}")
            logger.info(f"   Reason: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel prediction {prediction_id}: {e}")
            return False
    
    def expire_prediction(self, prediction_id: str) -> bool:
        """
        Expire a prediction (order timeout)
        
        Args:
            prediction_id: Prediction identifier
            
        Returns:
            success: Whether the operation succeeded
        """
        try:
            if prediction_id not in self.predictions:
                logger.warning(f"⚠️ Prediction {prediction_id} not found")
                return False
            
            prediction = self.predictions[prediction_id]
            
            # Update prediction state
            prediction.state = PredictionState.EXPIRED
            prediction.completed_at = time.time()
            prediction.exit_reason = "TIMEOUT"
            
            # Remove from active predictions
            if prediction_id in self.active_predictions:
                self.active_predictions.remove(prediction_id)
            
            # Clear current direction if no active predictions
            if not self.active_predictions:
                self.current_direction = None
            
            logger.warning(f"⏰ PREDICTION EXPIRED: {prediction_id}")
            logger.warning(f"   Reason: Order timeout")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to expire prediction {prediction_id}: {e}")
            return False
    
    def can_generate_prediction(self, side: str) -> bool:
        """
        Check if we can generate a new prediction in the given direction
        
        Args:
            side: BUY or SELL
            
        Returns:
            can_generate: Whether we can generate the prediction
        """
        try:
            # Check if we have conflicting active predictions
            for pred_id in self.active_predictions:
                if pred_id in self.predictions:
                    pred = self.predictions[pred_id]
                    if pred.side != side:
                        logger.debug(f"🚫 Cannot generate {side} prediction: conflicting {pred.side} prediction active")
                        return False
            
            # Check minimum interval
            if time.time() - self.last_prediction_time < self.min_prediction_interval:
                logger.debug(f"⏰ Too soon since last prediction")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking prediction generation: {e}")
            return False
    
    def get_active_direction(self) -> Optional[str]:
        """Get the current active trading direction"""
        return self.current_direction
    
    def get_prediction_by_order_id(self, order_id: str) -> Optional[PredictionRecord]:
        """Get prediction record by order ID"""
        try:
            for prediction in self.predictions.values():
                if prediction.order_id == order_id:
                    return prediction
            return None
        except Exception as e:
            logger.error(f"❌ Error finding prediction by order ID: {e}")
            return None
    
    def get_prediction_by_position_id(self, position_id: str) -> Optional[PredictionRecord]:
        """Get prediction record by position ID"""
        try:
            for prediction in self.predictions.values():
                if prediction.position_id == position_id:
                    return prediction
            return None
        except Exception as e:
            logger.error(f"❌ Error finding prediction by position ID: {e}")
            return None
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current state for dashboard display"""
        try:
            # Get active predictions
            active_preds = []
            for pred_id in self.active_predictions:
                if pred_id in self.predictions:
                    pred = self.predictions[pred_id]
                    active_preds.append(asdict(pred))
            
            # Get recent completed predictions
            recent_completed = [asdict(pred) for pred in self.completed_predictions[-10:]]
            
            return {
                "active_predictions": active_preds,
                "completed_predictions": recent_completed,
                "current_direction": self.current_direction,
                "statistics": {
                    "total_predictions": self.prediction_count,
                    "active_predictions_count": len(self.active_predictions),
                    "completed_predictions_count": len(self.completed_predictions),
                    "last_prediction_time": self.last_prediction_time
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard data: {e}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for ML learning"""
        try:
            if not self.completed_predictions:
                return {"message": "No completed predictions yet"}
            
            # Calculate metrics
            total_predictions = len(self.completed_predictions)
            successful_predictions = len([p for p in self.completed_predictions if p.final_pnl and p.final_pnl > 0])
            failed_predictions = len([p for p in self.completed_predictions if p.final_pnl and p.final_pnl < 0])
            
            total_pnl = sum(p.final_pnl for p in self.completed_predictions if p.final_pnl)
            avg_pnl = total_pnl / total_predictions if total_predictions > 0 else 0
            
            success_rate = successful_predictions / total_predictions if total_predictions > 0 else 0
            
            # Strategy performance
            strategy_performance = {}
            for pred in self.completed_predictions:
                strategy = pred.strategy
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {"count": 0, "total_pnl": 0, "successful": 0}
                
                strategy_performance[strategy]["count"] += 1
                if pred.final_pnl:
                    strategy_performance[strategy]["total_pnl"] += pred.final_pnl
                    if pred.final_pnl > 0:
                        strategy_performance[strategy]["successful"] += 1
            
            return {
                "total_predictions": total_predictions,
                "successful_predictions": successful_predictions,
                "failed_predictions": failed_predictions,
                "success_rate": success_rate,
                "total_pnl": total_pnl,
                "avg_pnl": avg_pnl,
                "strategy_performance": strategy_performance
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance metrics: {e}")
            return {}

# Global instance
_global_prediction_state_manager = None

def get_global_prediction_state_manager() -> PredictionStateManager:
    """Get global PredictionStateManager instance"""
    global _global_prediction_state_manager
    if _global_prediction_state_manager is None:
        _global_prediction_state_manager = PredictionStateManager()
    return _global_prediction_state_manager
