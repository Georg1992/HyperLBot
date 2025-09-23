#!/usr/bin/env python3
"""
Adaptive AI Engine
Continuously adjusts predictions, confidence, and trade parameters based on real-time market analysis
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

# Use existing TradingPrediction from prediction_manager
from core.ml.prediction_manager import TradingPrediction

@dataclass
class TradeAdjustment:
    """Trade parameter adjustment based on market analysis"""
    trade_id: str
    new_stop_loss: Optional[float] = None
    new_take_profit: Optional[float] = None
    new_confidence: Optional[float] = None
    adjustment_reason: str = ""
    urgency: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

class AdaptiveAIEngine:
    """
    Adaptive AI Engine that continuously adjusts predictions and trades
    """
    
    def __init__(self):
        self.active_predictions: Dict[str, TradingPrediction] = {}
        self.prediction_history: List[TradingPrediction] = []
        self.trade_adjustments: List[TradeAdjustment] = []
        
        # Strategy-specific adaptation parameters
        self.strategy_adapters = {
            "scalping": ScalpingAdapter(),
            "trend_following": TrendFollowingAdapter(),
            "range_trading": RangeTradingAdapter(),
            "liquidation_hunting": LiquidationHuntingAdapter()
        }
        
        logger.info("🧠 Adaptive AI Engine initialized")
    
    def analyze_and_adapt_predictions(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market conditions and adapt existing predictions or create new ones
        """
        try:
            # Get current market conditions
            market_conditions = self._analyze_market_conditions(market_data)
            
            # Check if we need new predictions
            new_predictions = self._generate_new_predictions(current_price, market_conditions)
            
            # Adapt existing predictions
            adapted_predictions = self._adapt_existing_predictions(current_price, market_conditions)
            
            # Check for trade adjustments
            trade_adjustments = self._check_trade_adjustments(current_price, market_conditions)
            
            return {
                "new_predictions": new_predictions,
                "adapted_predictions": adapted_predictions,
                "trade_adjustments": trade_adjustments,
                "market_conditions": market_conditions,
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Adaptive analysis failed: {e}")
            return {"error": str(e)}
    
    def _analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market conditions for adaptation"""
        try:
            # Extract key market indicators
            volatility = market_data.get("volatility_5m", 0.0)
            volatility_category = market_data.get("volatility_5m_category", "LOW")
            rsi = market_data.get("rsi", 50.0)
            trend = market_data.get("trend_5m", {})
            volume = market_data.get("trading_volume_btc", 0.0)
            
            # Analyze market regime
            market_regime = self._determine_market_regime(volatility, rsi, trend)
            
            # Calculate adaptation factors
            adaptation_factors = {
                "volatility_factor": self._calculate_volatility_factor(volatility, volatility_category),
                "momentum_factor": self._calculate_momentum_factor(rsi, trend),
                "volume_factor": self._calculate_volume_factor(volume),
                "trend_strength": trend.get("strength", 0.5),
                "market_regime": market_regime
            }
            
            return adaptation_factors
            
        except Exception as e:
            logger.error(f"❌ Market condition analysis failed: {e}")
            return {}
    
    def _generate_new_predictions(self, current_price: float, market_conditions: Dict[str, Any]) -> List[TradingPrediction]:
        """Generate new predictions based on current market conditions"""
        try:
            new_predictions = []
            
            # Check if we need new predictions (max 3 active predictions)
            if len(self.active_predictions) >= 3:
                return new_predictions
            
            # Determine if conditions are favorable for new predictions
            volatility_factor = market_conditions.get("volatility_factor", 0.5)
            momentum_factor = market_conditions.get("momentum_factor", 0.5)
            volume_factor = market_conditions.get("volume_factor", 0.5)
            
            # Calculate overall market favorability
            market_favorability = (volatility_factor + momentum_factor + volume_factor) / 3
            
            # Only create new predictions if market is favorable
            if market_favorability > 0.6:  # 60% favorability threshold
                prediction = self._create_adaptive_prediction(current_price, market_conditions)
                if prediction:
                    self.active_predictions[prediction.prediction_id] = prediction
                    new_predictions.append(prediction)
                    logger.info(f"🎯 New adaptive prediction created: {prediction.direction} at ${prediction.entry_price:.2f} (confidence: {prediction.confidence:.2f})")
            
            return new_predictions
            
        except Exception as e:
            logger.error(f"❌ New prediction generation failed: {e}")
            return []
    
    def _adapt_existing_predictions(self, current_price: float, market_conditions: Dict[str, Any]) -> List[TradingPrediction]:
        """Adapt existing predictions based on new market conditions"""
        try:
            adapted_predictions = []
            
            for prediction_id, prediction in self.active_predictions.items():
                # Check if prediction needs adaptation
                adaptation_needed = self._should_adapt_prediction(prediction, current_price, market_conditions)
                
                if adaptation_needed:
                    # Adapt the prediction
                    adapted_prediction = self._adapt_prediction(prediction, current_price, market_conditions)
                    if adapted_prediction:
                        self.active_predictions[prediction_id] = adapted_prediction
                        adapted_predictions.append(adapted_prediction)
                        logger.info(f"🔄 Prediction adapted: {prediction_id} - {adapted_prediction.reasoning}")
            
            return adapted_predictions
            
        except Exception as e:
            logger.error(f"❌ Prediction adaptation failed: {e}")
            return []
    
    def _check_trade_adjustments(self, current_price: float, market_conditions: Dict[str, Any]) -> List[TradeAdjustment]:
        """Check if active trades need parameter adjustments"""
        try:
            adjustments = []
            
            # This would integrate with the execution layer to check active trades
            # For now, return empty list as trade management is handled by execution layer
            
            return adjustments
            
        except Exception as e:
            logger.error(f"❌ Trade adjustment check failed: {e}")
            return []
    
    def _create_adaptive_prediction(self, current_price: float, market_conditions: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Create a new adaptive prediction"""
        try:
            # Determine direction based on market conditions
            momentum_factor = market_conditions.get("momentum_factor", 0.5)
            volatility_factor = market_conditions.get("volatility_factor", 0.5)
            
            # Calculate confidence based on market favorability
            base_confidence = (momentum_factor + volatility_factor) / 2
            
            # Determine direction
            if momentum_factor > 0.6:
                direction = "BUY"
            elif momentum_factor < 0.4:
                direction = "SELL"
            else:
                # Neutral conditions - don't create prediction
                return None
            
            # Calculate entry price (slightly better than current price)
            if direction == "BUY":
                entry_price = current_price * 0.999  # 0.1% below current price
                target_price = current_price * 1.002  # 0.2% above current price
                stop_loss = current_price * 0.998  # 0.2% below current price
            else:
                entry_price = current_price * 1.001  # 0.1% above current price
                target_price = current_price * 0.998  # 0.2% below current price
                stop_loss = current_price * 1.002  # 0.2% above current price
            
            prediction = TradingPrediction(
                prediction_id=str(uuid.uuid4()),
                direction=direction,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                confidence=base_confidence,
                size_btc=0.001,  # Default size
                size_usd=entry_price * 0.001,  # Calculate USD size
                reasoning=f"Adaptive prediction based on momentum={momentum_factor:.2f}, volatility={volatility_factor:.2f}",
                timestamp=time.time(),
                signal_strength={"volatility": volatility_factor, "momentum": momentum_factor}
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Adaptive prediction creation failed: {e}")
            return None
    
    def _should_adapt_prediction(self, prediction: TradingPrediction, current_price: float, market_conditions: Dict[str, Any]) -> bool:
        """Check if a prediction should be adapted"""
        try:
            # Adapt if price has moved significantly from entry
            price_change = abs(current_price - prediction.entry_price) / prediction.entry_price
            if price_change > 0.01:  # 1% price change
                return True
            
            # Adapt if prediction is old (5 minutes)
            if time.time() - prediction.timestamp > 300:
                return True
            
            # Check if market conditions suggest adaptation
            volatility_factor = market_conditions.get("volatility_factor", 0.5)
            momentum_factor = market_conditions.get("momentum_factor", 0.5)
            
            # Adapt if conditions are significantly different from neutral
            if abs(volatility_factor - 0.5) > 0.3 or abs(momentum_factor - 0.5) > 0.3:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Prediction adaptation check failed: {e}")
            return False
    
    def _adapt_prediction(self, prediction: TradingPrediction, current_price: float, market_conditions: Dict[str, Any]) -> Optional[TradingPrediction]:
        """Adapt an existing prediction"""
        try:
            # Recalculate confidence based on new conditions
            volatility_factor = market_conditions.get("volatility_factor", 0.5)
            momentum_factor = market_conditions.get("momentum_factor", 0.5)
            new_confidence = (volatility_factor + momentum_factor) / 2
            
            # Update confidence (weighted average with previous confidence)
            prediction.confidence = (prediction.confidence * 0.7) + (new_confidence * 0.3)
            
            # Adjust stop loss and take profit based on volatility
            volatility_factor = market_conditions.get("volatility_factor", 0.5)
            if volatility_factor > 0.7:  # High volatility - wider stops
                if prediction.direction == "BUY":
                    prediction.stop_loss = current_price * 0.995  # 0.5% stop loss
                    prediction.target_price = current_price * 1.005  # 0.5% target
                else:
                    prediction.stop_loss = current_price * 1.005  # 0.5% stop loss
                    prediction.target_price = current_price * 0.995  # 0.5% target
            else:  # Low volatility - tighter stops
                if prediction.direction == "BUY":
                    prediction.stop_loss = current_price * 0.998  # 0.2% stop loss
                    prediction.target_price = current_price * 1.002  # 0.2% target
                else:
                    prediction.stop_loss = current_price * 1.002  # 0.2% stop loss
                    prediction.target_price = current_price * 0.998  # 0.2% target
            
            prediction.reasoning = f"Adapted based on volatility={volatility_factor:.2f}, momentum={momentum_factor:.2f}, confidence={prediction.confidence:.2f}"
            prediction.timestamp = time.time()  # Update timestamp
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction adaptation failed: {e}")
            return None
    
    def _determine_market_regime(self, volatility: float, rsi: float, trend: Dict[str, Any]) -> str:
        """Determine current market regime"""
        try:
            if volatility > 0.01:  # High volatility
                return "HIGH_VOLATILITY"
            elif volatility < 0.002:  # Low volatility
                return "LOW_VOLATILITY"
            elif rsi > 70:  # Overbought
                return "OVERBOUGHT"
            elif rsi < 30:  # Oversold
                return "OVERSOLD"
            else:
                return "NORMAL"
                
        except Exception as e:
            logger.error(f"❌ Market regime determination failed: {e}")
            return "UNKNOWN"
    
    def _calculate_volatility_factor(self, volatility: float, category: str) -> float:
        """Calculate volatility adaptation factor"""
        try:
            if category == "EXTREME":
                return 0.9
            elif category == "HIGH":
                return 0.7
            elif category == "MODERATE":
                return 0.5
            elif category == "LOW":
                return 0.3
            else:
                return 0.1
                
        except Exception as e:
            logger.error(f"❌ Volatility factor calculation failed: {e}")
            return 0.5
    
    def _calculate_momentum_factor(self, rsi: float, trend: Dict[str, Any]) -> float:
        """Calculate momentum adaptation factor"""
        try:
            # RSI-based momentum
            rsi_factor = 1.0 - abs(rsi - 50) / 50  # Closer to 50 = higher factor
            
            # Trend-based momentum
            trend_strength = trend.get("strength", 0.5)
            trend_direction = trend.get("trend", "NEUTRAL")
            
            if trend_direction == "BULLISH":
                trend_factor = 0.5 + (trend_strength * 0.5)
            elif trend_direction == "BEARISH":
                trend_factor = 0.5 - (trend_strength * 0.5)
            else:
                trend_factor = 0.5
            
            return (rsi_factor + trend_factor) / 2
            
        except Exception as e:
            logger.error(f"❌ Momentum factor calculation failed: {e}")
            return 0.5
    
    def _calculate_volume_factor(self, volume: float) -> float:
        """Calculate volume adaptation factor"""
        try:
            # Normalize volume (this would need to be calibrated based on historical data)
            if volume > 1000:  # High volume
                return 0.8
            elif volume > 500:  # Medium volume
                return 0.6
            elif volume > 100:  # Low volume
                return 0.4
            else:  # Very low volume
                return 0.2
                
        except Exception as e:
            logger.error(f"❌ Volume factor calculation failed: {e}")
            return 0.5

# Strategy-specific adapters
class ScalpingAdapter:
    """Scalping strategy adapter"""
    
    def adapt_prediction(self, prediction: TradingPrediction, market_conditions: Dict[str, Any]) -> TradingPrediction:
        """Adapt prediction for scalping strategy"""
        # Scalping needs tight stops and quick targets
        volatility_factor = market_conditions.get("volatility_factor", 0.5)
        
        if volatility_factor > 0.7:  # High volatility - wider stops for scalping
            prediction.stop_loss = prediction.entry_price * 0.998  # 0.2% stop
            prediction.target_price = prediction.entry_price * 1.002  # 0.2% target
        else:  # Low volatility - very tight stops
            prediction.stop_loss = prediction.entry_price * 0.999  # 0.1% stop
            prediction.target_price = prediction.entry_price * 1.001  # 0.1% target
        
        return prediction

class TrendFollowingAdapter:
    """Trend following strategy adapter"""
    
    def adapt_prediction(self, prediction: TradingPrediction, market_conditions: Dict[str, Any]) -> TradingPrediction:
        """Adapt prediction for trend following strategy"""
        # Trend following needs wider stops and targets
        trend_strength = market_conditions.get("trend_strength", 0.5)
        
        if trend_strength > 0.7:  # Strong trend - wider stops
            prediction.stop_loss = prediction.entry_price * 0.99  # 1% stop
            prediction.target_price = prediction.entry_price * 1.01  # 1% target
        else:  # Weak trend - tighter stops
            prediction.stop_loss = prediction.entry_price * 0.995  # 0.5% stop
            prediction.target_price = prediction.entry_price * 1.005  # 0.5% target
        
        return prediction

class RangeTradingAdapter:
    """Range trading strategy adapter"""
    
    def adapt_prediction(self, prediction: TradingPrediction, market_conditions: Dict[str, Any]) -> TradingPrediction:
        """Adapt prediction for range trading strategy"""
        # Range trading needs to respect support/resistance levels
        # This would integrate with support/resistance analysis
        return prediction

class LiquidationHuntingAdapter:
    """Liquidation hunting strategy adapter"""
    
    def adapt_prediction(self, prediction: TradingPrediction, market_conditions: Dict[str, Any]) -> TradingPrediction:
        """Adapt prediction for liquidation hunting strategy"""
        # Liquidation hunting needs to target specific price levels
        # This would integrate with liquidation level analysis
        return prediction

# Global instance
global_adaptive_ai = AdaptiveAIEngine()
