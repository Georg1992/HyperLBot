#!/usr/bin/env python3
"""
Clean Prediction Engine
Generates trading predictions based on signal analysis
Simplified, focused, and ready for future modeling integration
"""

import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from core.signals import global_signal_aggregator, SignalType
from core.analysis.real_time.psychological_levels_calculator import global_psychological_levels_calculator
from core.market_data_manager import global_rsi_calculator
from core.constants import MagicNumbers


@dataclass
class PredictionResult:
    """Result of a prediction generation"""
    direction: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasoning: str
    signal_analysis: Dict[str, Any]
    timestamp: float
    strategy_used: str


class PredictionEngine:
    """
    Clean Signal-Based Prediction Engine
    
    Purpose:
    - Generate trading predictions based on signal analysis
    - Calculate entry prices, stop losses, and take profits
    - Provide position sizing based on confidence and strategy
    - Ready for future modeling integration
    """
    
    def __init__(self):
        self.signal_aggregator = global_signal_aggregator
        
        # Simple tracking
        self.last_prediction = None
        self.last_update_time = 0
        self.prediction_cooldown = 10  # 10 seconds between predictions
        
        # Quality thresholds
        self.min_confidence_threshold = 0.3  # 30% minimum confidence
        
        logger.info("🎯 Clean Prediction Engine initialized - Ready for future modeling")
    
    def generate_prediction(self, current_price: float, market_data: Dict[str, Any] = None, 
                          strategy_name: str = "standard") -> Optional[Dict[str, Any]]:
        """
        Generate a trading prediction based on signal analysis
        
        Args:
            current_price: Current market price
            market_data: Additional market data
            strategy_name: Trading strategy to use
            
        Returns:
            Dict with prediction data if high-quality prediction found, None otherwise
        """
        try:
            # Check cooldown period
            if self._is_in_cooldown():
                return None
            
            market_data = market_data or {}
            
            # Step 1: Generate signals
            signals = self.signal_aggregator.generate_primary_signals(current_price, market_data)
            aggregated_signal = self.signal_aggregator.aggregate_signals(signals)
            
            # Step 2: Check if we have a valid directional signal
            overall_direction = aggregated_signal.get("overall_direction", "NEUTRAL")
            overall_confidence = aggregated_signal.get("overall_confidence", 0.0)
            
            if overall_direction == "NEUTRAL" or overall_confidence < self.min_confidence_threshold:
                logger.debug(f"📊 No valid directional signal (direction: {overall_direction}, confidence: {overall_confidence:.1%})")
                return None
            
            # Step 3: Generate prediction
            prediction = self._create_prediction(
                aggregated_signal, current_price, market_data, strategy_name
            )
            
            if prediction:
                # Update tracking
                self.last_prediction = prediction
                self.last_update_time = time.time()
                
                logger.info(f"🎯 PREDICTION: {prediction['direction']} at ${prediction['entry_price']:,.2f} ({prediction['confidence']:.1%} confidence)")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction generation failed: {e}")
            return None
    
    def _create_prediction(self, aggregated_signal: Dict[str, Any], current_price: float, 
                          market_data: Dict[str, Any], strategy_name: str) -> Optional[Dict[str, Any]]:
        """Create prediction from aggregated signal"""
        try:
            overall_direction = aggregated_signal.get("overall_direction", "NEUTRAL")
            overall_confidence = aggregated_signal.get("overall_confidence", 0.0)
            signal_components = aggregated_signal.get("signal_components", {})
            
            # Calculate prediction parameters
            entry_price = self._calculate_entry_price(overall_direction, current_price, strategy_name)
            stop_loss, take_profit = self._calculate_risk_levels(
                overall_direction, entry_price, current_price, strategy_name, market_data
            )
            position_size = self._calculate_position_size(overall_confidence, strategy_name, market_data)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(aggregated_signal, overall_direction, overall_confidence)
            
            # Get market context
            rsi_5m = market_data.get("rsi_5m", market_data.get("rsi", 50))
            trend_direction = market_data.get("trend", market_data.get("trend_5m", {}).get("direction", "NEUTRAL"))
            volatility_category = market_data.get("volatility_category", "MODERATE")
            
            # Create prediction result
            prediction = {
                "direction": overall_direction,
                "confidence": overall_confidence,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_size,
                "reasoning": reasoning,
                "rsi": rsi_5m,
                "trend": trend_direction,
                "volatility_category": volatility_category,
                "signal_analysis": {
                    "quality_rating": aggregated_signal.get("quality_rating", "UNKNOWN"),
                    "quality_score": aggregated_signal.get("quality_score", 0.0),
                    "signal_components": signal_components,
                    "overall_reasoning": aggregated_signal.get("overall_reasoning", "")
                },
                "timestamp": time.time(),
                "strategy_used": strategy_name,
                "prediction_type": "SIGNAL_BASED"
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction creation failed: {e}")
            return None
    
    def _calculate_entry_price(self, direction: str, current_price: float, strategy_name: str) -> float:
        """Calculate optimal entry price based on direction and strategy"""
        try:
            if direction == "BUY":
                # For buy orders, entry should be at or below current price
                if strategy_name == "low_volatility_range":
                    # Range trading: slightly below current price for better fill
                    return current_price * 0.999
                else:
                    # Standard: slightly below current price
                    return current_price * 0.999
            else:  # SELL
                # For sell orders, entry should be at or above current price
                if strategy_name == "low_volatility_range":
                    # Range trading: slightly above current price for better fill
                    return current_price * 1.001
                else:
                    # Standard: slightly above current price
                    return current_price * 1.001
            
        except Exception as e:
            logger.error(f"❌ Entry price calculation failed: {e}")
            return current_price
    
    def _calculate_risk_levels(self, direction: str, entry_price: float, current_price: float, 
                             strategy_name: str, market_data: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        try:
            # Get market conditions
            volatility_category = market_data.get("volatility_category", "MODERATE")
            
            # Calculate volatility-based multipliers
            if volatility_category == "VERY_LOW":
                volatility_multiplier = 0.5
                target_multiplier = 0.8
            elif volatility_category == "LOW":
                volatility_multiplier = 0.7
                target_multiplier = 0.9
            elif volatility_category == "MODERATE":
                volatility_multiplier = 1.0
                target_multiplier = 1.0
            elif volatility_category == "HIGH":
                volatility_multiplier = 1.5
                target_multiplier = 1.2
            else:  # EXTREME
                volatility_multiplier = 2.0
                target_multiplier = 1.5
            
            if direction == "BUY":
                # Calculate stop loss (below entry)
                base_stop_pct = 0.008  # 0.8% base stop loss
                stop_loss = entry_price * (1 - base_stop_pct * volatility_multiplier)
                
                # Calculate take profit (above entry)
                base_target_pct = 0.015  # 1.5% base take profit
                take_profit = entry_price * (1 + base_target_pct * target_multiplier)
                    
            else:  # SELL
                # Calculate stop loss (above entry)
                base_stop_pct = 0.008  # 0.8% base stop loss
                stop_loss = entry_price * (1 + base_stop_pct * volatility_multiplier)
                
                # Calculate take profit (below entry)
                base_target_pct = 0.015  # 1.5% base take profit
                take_profit = entry_price * (1 - base_target_pct * target_multiplier)
            
            # Ensure minimum risk/reward ratio of 1:1.5
            if direction == "BUY":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
                if reward < risk * 1.5:
                    take_profit = entry_price + (risk * 1.5)
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
                if reward < risk * 1.5:
                    take_profit = entry_price - (risk * 1.5)
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"❌ Risk level calculation failed: {e}")
            # Fallback to simple percentage-based levels
            if direction == "BUY":
                return entry_price * 0.98, entry_price * 1.02
            else:
                return entry_price * 1.02, entry_price * 0.98
    
    def _calculate_position_size(self, confidence: float, strategy_name: str, market_data: Dict[str, Any] = None) -> float:
        """Calculate position size based on confidence and strategy"""
        try:
            market_data = market_data or {}
            
            # Get available balance
            try:
                from core.session.session_manager import session_manager
                session_data = session_manager.get_current_session_data()
                available_balance = session_data.get("current_balance", 100.0)
            except Exception:
                available_balance = 100.0
            
            # Get current price
            current_price = market_data.get("current_price", 112000)
            
            # Get strategy-specific base position size
            from config.config import TradingConfig
            config = TradingConfig()
            strategy_config = config.STRATEGY_CONFIGS.get(strategy_name, config.STRATEGY_CONFIGS["standard"])
            base_capital_pct = strategy_config.get("position_size", 0.1)  # Default 10%
            
            # Confidence multiplier
            if confidence >= 0.8:
                confidence_multiplier = 1.2
            elif confidence >= 0.6:
                confidence_multiplier = 1.0
            elif confidence >= 0.4:
                confidence_multiplier = 0.8
            else:
                confidence_multiplier = 0.6
            
            # Calculate position size
            base_capital_usd = available_balance * base_capital_pct * confidence_multiplier
            position_size = base_capital_usd / current_price
            
            # Apply limits
            min_size = 0.0001
            max_size = (available_balance * 0.08) / current_price
            position_size = max(min_size, min(position_size, max_size))
            
            return round(position_size, 6)
            
        except Exception as e:
            logger.error(f"❌ Position size calculation failed: {e}")
            return 0.001
    
    def _generate_reasoning(self, aggregated_signal: Dict[str, Any], direction: str, confidence: float) -> str:
        """Generate reasoning for the prediction"""
        try:
            reasoning_parts = []
            
            # Overall signal analysis
            quality_rating = aggregated_signal.get("quality_rating", "UNKNOWN")
            signal_strength = aggregated_signal.get("signal_strength", "UNKNOWN")
            reasoning_parts.append(f"📊 Signal Quality: {quality_rating} | Strength: {signal_strength}")
            
            # Confidence analysis
            if confidence >= 0.8:
                confidence_level = "High"
            elif confidence >= 0.6:
                confidence_level = "Good"
            elif confidence >= 0.4:
                confidence_level = "Moderate"
            else:
                confidence_level = "Low"
            
            reasoning_parts.append(f"🎯 Confidence: {confidence_level} ({confidence:.1%})")
            
            # Signal breakdown
            signal_components = aggregated_signal.get("signal_components", {})
            if signal_components:
                reasoning_parts.append("🔍 Signal Analysis:")
                for signal_type, component in signal_components.items():
                    signal_direction = component.get("direction", "NEUTRAL")
                    signal_confidence = component.get("confidence", 0)
                    reasoning_parts.append(f"  • {signal_type}: {signal_direction} ({signal_confidence:.1%})")
            
            # Final decision
            reasoning_parts.append(f"🎯 Final Decision: {direction}")
            
            return "\n".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Reasoning generation failed: {e}")
            return f"Signal-based {direction} prediction ({confidence:.1%} confidence)"
    
    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period between predictions"""
        if not self.last_prediction:
            return False
        
        time_since_last = time.time() - self.last_update_time
        return time_since_last < self.prediction_cooldown
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of prediction engine status"""
        return {
            "engine_status": "ACTIVE",
            "last_prediction": self.last_prediction is not None,
            "last_prediction_time": self.last_update_time,
            "cooldown_active": self._is_in_cooldown(),
            "min_confidence_threshold": self.min_confidence_threshold,
            "prediction_cooldown": self.prediction_cooldown
        }


# Global instance for easy access
global_prediction_engine = PredictionEngine()
