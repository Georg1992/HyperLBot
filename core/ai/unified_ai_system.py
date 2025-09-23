#!/usr/bin/env python3
"""
Unified AI System
================
Orchestrates all three AI layers: Initialization, Analysis, and Execution.
This is the main interface for the AI trading system.
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger

from core.ai.initialization_layer import global_initialization_layer, SystemReadiness
from core.ai.analysis_layer import global_analysis_layer, AnalysisResult
from core.ai.execution_layer import global_execution_layer, Order, Trade

class UnifiedAISystem:
    """
    Unified AI System - Orchestrates all AI layers
    
    This is the main interface that coordinates:
    1. Initialization Layer - Data validation and system readiness
    2. Analysis Layer - Strategy selection and prediction generation
    3. Execution Layer - Order management and trade lifecycle
    """
    
    def __init__(self):
        self.initialization_layer = global_initialization_layer
        self.analysis_layer = global_analysis_layer
        self.execution_layer = global_execution_layer
        
        self.is_initialized = False
        self.last_analysis_time = 0
        self.analysis_interval = 5  # Analyze every 5 seconds
        
        logger.info("🤖 Unified AI System initialized")
    
    def initialize_system(self, market_data: Dict[str, Any] = None) -> SystemReadiness:
        """
        Initialize and validate the AI system
        
        Args:
            market_data: Initial market data for validation
            
        Returns:
            SystemReadiness object with initialization status
        """
        try:
            # Skip if already initialized
            if self.is_initialized and hasattr(self, '_last_readiness_check'):
                logger.debug("🔧 AI system already initialized, returning cached status")
                return self._last_readiness_check
            
            logger.info("🔧 Initializing AI system...")
            
            # Check system readiness
            readiness = self.initialization_layer.check_system_readiness(market_data)
            
            if readiness.is_ready:
                self.is_initialized = True
                self._last_readiness_check = readiness  # Cache the readiness check
                logger.success("✅ AI system initialized and ready")
            else:
                logger.warning(f"⚠️ AI system not ready: {len(readiness.errors)} errors")
                for error in readiness.errors:
                    logger.warning(f"   - {error}")
            
            return readiness
            
        except Exception as e:
            logger.error(f"❌ AI system initialization failed: {e}")
            return SystemReadiness(
                is_ready=False,
                data_sources=[],
                critical_components=[],
                warnings=[],
                errors=[f"Initialization failed: {str(e)}"]
            )
    
    def analyze_and_trade(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main AI method - analyzes market and executes trades
        
        Args:
            current_price: Current market price
            market_data: Comprehensive market data
            
        Returns:
            Dictionary with analysis results and execution status
        """
        try:
            if not self.is_initialized:
                logger.warning("⚠️ AI system not initialized - attempting auto-initialization")
                # Try to auto-initialize the system
                readiness = self.initialize_system(market_data)
                if not readiness.is_ready:
                    logger.error(f"❌ Auto-initialization failed: {len(readiness.errors)} errors")
                    return {"error": "System initialization failed"}
                logger.success("✅ AI system auto-initialized successfully")
            
            # Check if enough time has passed since last analysis
            current_time = time.time()
            if current_time - self.last_analysis_time < self.analysis_interval:
                return {"status": "waiting", "next_analysis_in": self.analysis_interval - (current_time - self.last_analysis_time)}
            
            logger.debug(f"🤖 AI analyzing market at ${current_price:.2f}")
            
            # Step 1: Analyze market and generate decisions
            analysis_result = self.analysis_layer.analyze_market_and_generate_decisions(current_price, market_data)
            
            # Step 1.5: Perform adaptive analysis for continuous adjustment
            adaptive_results = self.analysis_layer.adaptive_analysis(current_price, market_data)
            
            # Step 2: Execute decisions
            execution_results = self._execute_analysis_decisions(analysis_result, current_price, market_data)
            
            # Step 2.5: Execute adaptive predictions
            adaptive_execution_results = self._execute_adaptive_predictions(adaptive_results, current_price, market_data)
            
            # Step 3: Monitor existing trades
            self.execution_layer.monitor_trades(current_price, market_data)
            
            # Update last analysis time
            self.last_analysis_time = current_time
            
            # Store current prediction for dashboard display (even if discarded)
            current_prediction = None
            if analysis_result.prediction:
                # analysis_result.prediction is already a dict, just add metadata
                current_prediction = analysis_result.prediction.copy()
                current_prediction.update({
                    "strategy": analysis_result.strategy,
                    "is_discarded": execution_results.get("predictions_discarded", 0) > 0
                })
            
            # Compile results
            results = {
                "analysis": {
                    "strategy": analysis_result.strategy,
                    "strategy_confidence": analysis_result.strategy_confidence,
                    "market_regime": analysis_result.market_regime,
                    "analysis_confidence": analysis_result.analysis_confidence,
                    "reasoning": analysis_result.reasoning,
                    "timestamp": analysis_result.timestamp,
                    "prediction": current_prediction  # Add current prediction for dashboard
                },
                "adaptive_analysis": adaptive_results,
                "execution": execution_results,
                "adaptive_execution": adaptive_execution_results,
                "system_status": {
                    "initialized": self.is_initialized,
                    "last_analysis": self.last_analysis_time,
                    "next_analysis_in": self.analysis_interval
                }
            }
            
            logger.info(f"🤖 AI cycle complete: {analysis_result.strategy} strategy, "
                       f"confidence: {analysis_result.analysis_confidence:.2f}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ AI analysis and trading failed: {e}")
            return {"error": str(e)}
    
    def _execute_analysis_decisions(self, analysis_result: AnalysisResult, current_price: float, 
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute decisions from analysis layer"""
        try:
            execution_results = {
                "orders_placed": 0,
                "trades_opened": 0,
                "reactive_trades": 0,
                "predictions_executed": 0,
                "predictions_discarded": 0
            }
            
            # Execute reactive trade if available (highest priority)
            if analysis_result.reactive_trade:
                order = self.execution_layer.execute_reactive_trade(analysis_result.reactive_trade, current_price)
                if order:
                    execution_results["reactive_trades"] += 1
                    execution_results["orders_placed"] += 1
                    logger.info(f"⚡ Reactive trade executed: {order.direction}")
            
            # Execute prediction if available and no reactive trade
            elif analysis_result.prediction:
                # Filter out bad predictions
                valid_predictions = self.execution_layer.discard_bad_predictions(
                    [analysis_result.prediction], current_price, market_data
                )
                
                if valid_predictions:
                    order = self.execution_layer.execute_prediction(valid_predictions[0], current_price, market_data)
                    if order:
                        execution_results["predictions_executed"] += 1
                        execution_results["orders_placed"] += 1
                        logger.info(f"⚡ Prediction executed: {order.direction}")
                else:
                    execution_results["predictions_discarded"] += 1
                    logger.debug("🗑️ Prediction discarded as invalid")
            
            return execution_results
            
        except Exception as e:
            logger.error(f"❌ Decision execution failed: {e}")
            return {"error": str(e)}
    
    def _execute_adaptive_predictions(self, adaptive_results: Dict[str, Any], current_price: float, 
                                    market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute adaptive predictions with high confidence"""
        try:
            executed_orders = []
            rejected_predictions = []
            
            # Execute new adaptive predictions
            for prediction in adaptive_results.get("new_predictions", []):
                # Handle both AdaptivePrediction objects and dictionaries
                if hasattr(prediction, 'confidence'):
                    confidence = prediction.confidence
                else:
                    confidence = prediction.get("confidence", 0.0)
                
                if confidence >= 0.6:  # 60% confidence threshold
                    order = self.execution_layer.execute_prediction(
                        prediction, current_price, market_data
                    )
                    if order:
                        executed_orders.append(order)
                        direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                        entry_price = prediction.entry_price if hasattr(prediction, 'entry_price') else prediction.get('entry_price', 0)
                        logger.info(f"🎯 Adaptive prediction executed: {direction} at ${entry_price:.2f}")
                    else:
                        rejected_predictions.append(prediction)
                        direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                        logger.warning(f"⚠️ Adaptive prediction rejected: {direction} (confidence: {confidence:.2f})")
                else:
                    rejected_predictions.append(prediction)
                    direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                    logger.debug(f"📊 Adaptive prediction below threshold: {direction} (confidence: {confidence:.2f})")
            
            # Execute adapted predictions
            for prediction in adaptive_results.get("adapted_predictions", []):
                # Handle both AdaptivePrediction objects and dictionaries
                if hasattr(prediction, 'confidence'):
                    confidence = prediction.confidence
                else:
                    confidence = prediction.get("confidence", 0.0)
                
                if confidence >= 0.6:  # 60% confidence threshold
                    order = self.execution_layer.execute_prediction(
                        prediction, current_price, market_data
                    )
                    if order:
                        executed_orders.append(order)
                        direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                        entry_price = prediction.entry_price if hasattr(prediction, 'entry_price') else prediction.get('entry_price', 0)
                        logger.info(f"🔄 Adapted prediction executed: {direction} at ${entry_price:.2f}")
                    else:
                        rejected_predictions.append(prediction)
                        direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                        logger.warning(f"⚠️ Adapted prediction rejected: {direction} (confidence: {confidence:.2f})")
                else:
                    rejected_predictions.append(prediction)
                    direction = prediction.direction if hasattr(prediction, 'direction') else prediction.get('direction', 'UNKNOWN')
                    logger.debug(f"📊 Adapted prediction below threshold: {direction} (confidence: {confidence:.2f})")
            
            return {
                "executed_orders": executed_orders,
                "rejected_predictions": rejected_predictions,
                "total_predictions": len(adaptive_results.get("new_predictions", [])) + len(adaptive_results.get("adapted_predictions", [])),
                "executed_count": len(executed_orders),
                "rejected_count": len(rejected_predictions)
            }
            
        except Exception as e:
            logger.error(f"❌ Adaptive prediction execution failed: {e}")
            return {"error": str(e)}
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics from the execution layer"""
        try:
            return self.execution_layer.get_execution_stats()
        except Exception as e:
            logger.error(f"❌ Failed to get execution stats: {e}")
            return {
                "active_orders": 0,
                "active_trades": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "daily_pnl": 0.0,
                "max_concurrent_trades": 3
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get initialization status (use cached status if available)
            if hasattr(self, '_last_readiness_check') and self._last_readiness_check:
                readiness = self._last_readiness_check
            else:
                readiness = self.initialization_layer.check_system_readiness()
                self._last_readiness_check = readiness
            
            # Get execution stats
            execution_stats = self.get_execution_stats()
            
            # Get analysis history
            analysis_history = self.analysis_layer.get_analysis_history(5)
            
            # Get strategy performance
            strategy_performance = self.analysis_layer.get_strategy_performance()
            
            return {
                "initialization": {
                    "is_ready": readiness.is_ready,
                    "data_sources": len(readiness.data_sources),
                    "available_sources": len([ds for ds in readiness.data_sources if ds.is_available]),
                    "errors": len(readiness.errors),
                    "warnings": len(readiness.warnings)
                },
                "execution": execution_stats,
                "analysis": {
                    "recent_analyses": len(analysis_history),
                    "strategy_performance": strategy_performance
                },
                "system": {
                    "initialized": self.is_initialized,
                    "last_analysis": self.last_analysis_time,
                    "analysis_interval": self.analysis_interval
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {"error": str(e)}
    
    def get_active_trades(self) -> List[Dict[str, Any]]:
        """Get all active trades"""
        try:
            trades = []
            for trade in self.execution_layer.active_trades.values():
                trades.append({
                    "trade_id": trade.trade_id,
                    "direction": trade.direction,
                    "entry_price": trade.entry_price,
                    "size_btc": trade.size_btc,
                    "stop_loss": trade.stop_loss,
                    "target_price": trade.target_price,
                    "strategy": trade.strategy,
                    "entry_time": trade.entry_time,
                    "leverage": trade.leverage
                })
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to get active trades: {e}")
            return []
    
    def get_recent_analysis(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent analysis results"""
        try:
            analysis_history = self.analysis_layer.get_analysis_history(limit)
            results = []
            
            for analysis in analysis_history:
                results.append({
                    "strategy": analysis.strategy,
                    "strategy_confidence": analysis.strategy_confidence,
                    "market_regime": analysis.market_regime,
                    "analysis_confidence": analysis.analysis_confidence,
                    "reasoning": analysis.reasoning,
                    "timestamp": analysis.timestamp,
                    "had_prediction": analysis.prediction is not None,
                    "had_reactive_trade": analysis.reactive_trade is not None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent analysis: {e}")
            return []
    
    def force_analysis(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Force immediate analysis (bypass interval)"""
        try:
            # Temporarily set last analysis time to force immediate analysis
            original_time = self.last_analysis_time
            self.last_analysis_time = 0
            
            # Run analysis
            result = self.analyze_and_trade(current_price, market_data)
            
            # Restore original time
            self.last_analysis_time = original_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Forced analysis failed: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """Shutdown the AI system gracefully"""
        try:
            logger.info("🛑 Shutting down AI system...")
            
            # Close all active trades
            for trade_id in list(self.execution_layer.active_trades.keys()):
                self.execution_layer._close_trade(trade_id, 0, "system_shutdown")
            
            # Cancel all pending orders
            for order_id in list(self.execution_layer.active_orders.keys()):
                order = self.execution_layer.active_orders[order_id]
                order.status = order.status.CANCELLED
                logger.info(f"⚡ Order cancelled: {order_id}")
            
            self.is_initialized = False
            logger.info("✅ AI system shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ AI system shutdown failed: {e}")

# Global instance
global_unified_ai_system = UnifiedAISystem()
