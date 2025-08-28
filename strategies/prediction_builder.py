#!/usr/bin/env python3
"""
Prediction Builder Module
Handles building reactive and predictive trading predictions
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.analysis.real_time.volatility_calculator import VolatilityCalculator
from strategies.prediction_confidence import PredictionConfidence
from strategies.prediction_analysis import PredictionAnalysis

class PredictionBuilder:
    """Handles building different types of trading predictions"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # Prediction types
        self.PREDICTION_TYPES = {
            "BREAKOUT_ABOVE": "BUY",
            "BREAKOUT_BELOW": "SELL", 
            "REVERSION_FROM_RESISTANCE": "SELL",
            "REVERSION_FROM_SUPPORT": "BUY",
            "MOMENTUM_UP": "BUY",
            "MOMENTUM_DOWN": "SELL"
        }
        
        # Reactive types for high volatility
        self.REACTIVE_TYPES = {
            "FAST_BREAKOUT": "BUY/SELL",
            "MOMENTUM_SURGE": "BUY/SELL",
            "VOLATILITY_SPIKE": "BUY/SELL",
            "PRICE_ACCELERATION": "BUY/SELL"
        }
        
        # Initialize sub-modules
        self.confidence = PredictionConfidence()
        self.analysis = PredictionAnalysis()
        self.volatility_calculator = VolatilityCalculator()
        
        logger.info("🔨 Prediction Builder initialized")
    
    def build_price_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float, strategy_name: str = "standard") -> Dict[str, Any]:
        """Build price prediction based on strategy"""
        if strategy_name == "reactive":
            prediction = self._build_reactive_prediction(yahoo_analysis, current_price)
        else:
            prediction = self._build_predictive_prediction(yahoo_analysis, current_price)
        
        # Return the prediction in the expected format with best_prediction key
        return {
            "has_prediction": prediction.get("has_prediction", False),
            "best_prediction": prediction,
            "prediction_mode": prediction.get("prediction_mode", "PREDICTIVE"),
            "reason": prediction.get("reason", "No prediction available"),
            "confidence": prediction.get("confidence", 0.0),
            "volatility_5m": prediction.get("volatility_5m", 0.0),
            "range_size": prediction.get("range_size", 0.0)
        }
    
    def _build_reactive_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build reactive prediction based on current market conditions"""
        try:
            # Extract market data
            trend_5m = yahoo_analysis.get("trend_5m", {})
            trend_1h = yahoo_analysis.get("trend_1h", {})
            support_resistance_5m = yahoo_analysis.get("support_resistance_5m", {})
            volatility_5m = yahoo_analysis.get("volatility_5m", 0.0)
            current_rsi = yahoo_analysis.get("current_rsi", 50.0)
            
            support_5m = support_resistance_5m.get("support", 0)
            resistance_5m = support_resistance_5m.get("resistance", 0)
            
            # Calculate range size
            range_size = resistance_5m - support_5m if resistance_5m > support_5m > 0 else 0
            
            # Generate basic predictions
            predictions = self._generate_basic_predictions(
                current_price, support_5m, resistance_5m, trend_5m, trend_1h, 
                volatility_5m, current_rsi
            )
            
            if not predictions:
                return {
                    "has_prediction": False,
                    "reason": "No valid reactive predictions found",
                    "prediction_mode": "REACTIVE"
                }
            
            # Find best prediction
            best_prediction = max(predictions, key=lambda x: x.get("confidence", 0))
            
            # Add metadata
            best_prediction = self._add_prediction_metadata(
                best_prediction, current_price, support_5m, resistance_5m,
                yahoo_analysis.get("candles_5m", []), yahoo_analysis.get("market_condition", "UNKNOWN"),
                trend_1h, trend_5m, volatility_5m, current_rsi
            )
            
            return {
                "has_prediction": True,
                "prediction": best_prediction,
                "prediction_mode": "REACTIVE",
                "reason": f"Reactive prediction: {best_prediction.get('type', 'UNKNOWN')}",
                "confidence": best_prediction.get("confidence", 0.0),
                "volatility_5m": volatility_5m,
                "range_size": range_size
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to build reactive prediction: {e}")
            return {
                "has_prediction": False,
                "reason": f"Reactive prediction failed: {str(e)}",
                "prediction_mode": "REACTIVE"
            }
    
    def _build_predictive_prediction(self, yahoo_analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Build predictive prediction based on technical analysis"""
        try:
            # Extract market data
            trend_5m = yahoo_analysis.get("trend_5m", {})
            trend_1h = yahoo_analysis.get("trend_1h", {})
            support_resistance_5m = yahoo_analysis.get("support_resistance_5m", {})
            volatility_5m = yahoo_analysis.get("volatility_5m", 0.0)
            current_rsi = yahoo_analysis.get("current_rsi", 50.0)
            candles_5m = yahoo_analysis.get("candles_5m", [])
            
            support_5m = support_resistance_5m.get("support", 0)
            resistance_5m = support_resistance_5m.get("resistance", 0)
            
            # Calculate range size
            range_size = resistance_5m - support_5m if resistance_5m > support_5m > 0 else 0
            
            # Generate basic predictions
            predictions = self._generate_basic_predictions(
                current_price, support_5m, resistance_5m, trend_5m, trend_1h, 
                volatility_5m, current_rsi
            )
            
            if not predictions:
                return {
                    "has_prediction": False,
                    "reason": "No valid predictive predictions found",
                    "prediction_mode": "PREDICTIVE"
                }
            
            # Find best prediction
            best_prediction = max(predictions, key=lambda x: x.get("confidence", 0))
            
            # Add metadata
            best_prediction = self._add_prediction_metadata(
                best_prediction, current_price, support_5m, resistance_5m,
                candles_5m, yahoo_analysis.get("market_condition", "UNKNOWN"),
                trend_1h, trend_5m, volatility_5m, current_rsi
            )
            
            return {
                "has_prediction": True,
                "prediction": best_prediction,
                "prediction_mode": "PREDICTIVE",
                "reason": f"Predictive prediction: {best_prediction.get('type', 'UNKNOWN')}",
                "confidence": best_prediction.get("confidence", 0.0),
                "volatility_5m": volatility_5m,
                "range_size": range_size
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to build predictive prediction: {e}")
            return {
                "has_prediction": False,
                "reason": f"Predictive prediction failed: {str(e)}",
                "prediction_mode": "PREDICTIVE"
            }
    
    def _generate_basic_predictions(self, current_price: float, support: float, resistance: float, 
                                  trend_5m: Dict, trend_1h: Dict, volatility: float, 
                                  current_rsi: float = 50.0, total_depth: float = 0, 
                                  depth_imbalance: float = 0) -> List[Dict[str, Any]]:
        """Generate basic predictions based on market conditions"""
        predictions = []
        
        try:
            # Breakout predictions
            if resistance > support > 0:
                range_size = resistance - support
                
                # Breakout above resistance
                breakout_above_prob = self._analyze_breakout_probability(trend_1h, trend_5m, volatility, range_size, current_price)
                if breakout_above_prob > 0.3:
                    predictions.append({
                        "type": "BREAKOUT_ABOVE",
                        "side": "BUY",
                        "entry_price": resistance * 1.001,  # Slightly above resistance
                        "target_price": resistance + (range_size * 0.5),
                        "stop_loss": resistance - (range_size * 0.2),
                        "confidence": breakout_above_prob,
                        "timeframe": self._calculate_breakout_timeframe(volatility, range_size),
                        "reason": f"Breakout above resistance ${resistance:,.2f} (prob: {breakout_above_prob:.1%})"
                    })
                
                # Breakdown below support
                breakdown_prob = self._analyze_breakdown_probability(trend_1h, trend_5m, volatility, range_size, current_price)
                if breakdown_prob > 0.3:
                    predictions.append({
                        "type": "BREAKOUT_BELOW",
                        "side": "SELL",
                        "entry_price": support * 0.999,  # Slightly below support
                        "target_price": support - (range_size * 0.5),
                        "stop_loss": support + (range_size * 0.2),
                        "confidence": breakdown_prob,
                        "timeframe": self._calculate_breakout_timeframe(volatility, range_size),
                        "reason": f"Breakdown below support ${support:,.2f} (prob: {breakdown_prob:.1%})"
                    })
            
            # Reversion predictions
            if current_price > resistance * 0.99:
                # Price near resistance - potential reversion
                reversion_prob = 0.6  # Base probability
                if trend_5m.get("direction", 0) < 0:
                    reversion_prob += 0.2
                if current_rsi > 70:
                    reversion_prob += 0.1
                
                if reversion_prob > 0.4:
                    predictions.append({
                        "type": "REVERSION_FROM_RESISTANCE",
                        "side": "SELL",
                        "entry_price": current_price,
                        "target_price": support,
                        "stop_loss": resistance * 1.01,
                        "confidence": reversion_prob,
                        "timeframe": self._calculate_reversion_timeframe(volatility),
                        "reason": f"Reversion from resistance ${resistance:,.2f} (prob: {reversion_prob:.1%})"
                    })
            
            elif current_price < support * 1.01:
                # Price near support - potential bounce
                bounce_prob = 0.6  # Base probability
                if trend_5m.get("direction", 0) > 0:
                    bounce_prob += 0.2
                if current_rsi < 30:
                    bounce_prob += 0.1
                
                if bounce_prob > 0.4:
                    predictions.append({
                        "type": "REVERSION_FROM_SUPPORT",
                        "side": "BUY",
                        "entry_price": current_price,
                        "target_price": resistance,
                        "stop_loss": support * 0.99,
                        "confidence": bounce_prob,
                        "timeframe": self._calculate_reversion_timeframe(volatility),
                        "reason": f"Bounce from support ${support:,.2f} (prob: {bounce_prob:.1%})"
                    })
            
            # Momentum predictions
            momentum_strength = self._analyze_momentum_strength(trend_1h, trend_5m, volatility)
            if momentum_strength > 0.5:
                if trend_5m.get("direction", 0) > 0:
                    predictions.append({
                        "type": "MOMENTUM_UP",
                        "side": "BUY",
                        "entry_price": current_price,
                        "target_price": current_price * 1.02,  # 2% target
                        "stop_loss": current_price * 0.98,  # 2% stop
                        "confidence": momentum_strength,
                        "timeframe": self._calculate_momentum_timeframe(volatility),
                        "reason": f"Upward momentum (strength: {momentum_strength:.1%})"
                    })
                elif trend_5m.get("direction", 0) < 0:
                    predictions.append({
                        "type": "MOMENTUM_DOWN",
                        "side": "SELL",
                        "entry_price": current_price,
                        "target_price": current_price * 0.98,  # 2% target
                        "stop_loss": current_price * 1.02,  # 2% stop
                        "confidence": momentum_strength,
                        "timeframe": self._calculate_momentum_timeframe(volatility),
                        "reason": f"Downward momentum (strength: {momentum_strength:.1%})"
                    })
            
        except Exception as e:
            logger.error(f"❌ Failed to generate basic predictions: {e}")
        
        return predictions
    
    def _add_prediction_metadata(self, prediction: Dict[str, Any], current_price: float, 
                                support_5m: float = 0, resistance_5m: float = 0, 
                                candles_5m: List = None, market_condition: str = "UNKNOWN", 
                                trend_1h: Dict = None, trend_5m: Dict = None, 
                                volatility_5m: float = 0, current_rsi: float = 50.0, 
                                total_depth: float = 0, depth_imbalance: float = 0, 
                                trend_1d: Dict = None, volume_data: Dict = None) -> Dict[str, Any]:
        """Add standard metadata to all predictions including RSI context"""
        prediction["current_price"] = current_price
        prediction["prediction_timestamp"] = time.time()
        prediction["prediction_datetime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Add RSI context for dashboard display
        prediction["rsi_context"] = current_rsi
        
        # Add volume data for dashboard display
        if volume_data:
            prediction["volume_data"] = volume_data
        
        # Add other context data if available
        if support_5m > 0:
            prediction["support"] = support_5m
        if resistance_5m > 0:
            prediction["resistance"] = resistance_5m
        if total_depth > 0:
            prediction["orderbook_depth"] = total_depth
        if depth_imbalance != 0:
            prediction["orderbook_imbalance"] = depth_imbalance
            
        return prediction
    
    def _calculate_breakout_timeframe(self, volatility: float, range_size: float) -> int:
        """Calculate expected timeframe for breakout"""
        if volatility > 0.01:  # High volatility
            return 5  # 5 minutes
        elif volatility > 0.005:  # Medium volatility
            return 15  # 15 minutes
        else:  # Low volatility
            return 30  # 30 minutes
    
    def _calculate_reversion_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for reversion"""
        if volatility > 0.01:  # High volatility
            return 10  # 10 minutes
        elif volatility > 0.005:  # Medium volatility
            return 20  # 20 minutes
        else:  # Low volatility
            return 45  # 45 minutes
    
    def _calculate_momentum_timeframe(self, volatility: float) -> int:
        """Calculate expected timeframe for momentum"""
        if volatility > 0.01:  # High volatility
            return 15  # 15 minutes
        elif volatility > 0.005:  # Medium volatility
            return 30  # 30 minutes
        else:  # Low volatility
            return 60  # 60 minutes
    
    def _analyze_breakout_probability(self, trend_1h: Dict, trend_5m: Dict, volatility: float, range_size: float, current_price: float) -> float:
        """Analyze probability of breakout above resistance"""
        try:
            # Base probability
            prob = 0.3
            
            # Trend alignment
            if trend_1h.get("direction", 0) > 0 and trend_5m.get("direction", 0) > 0:
                prob += 0.2  # Both trends up
            
            # Volatility factor
            if volatility > 0.01:
                prob += 0.1  # High volatility favors breakouts
            
            # Range size factor
            if range_size > current_price * 0.02:  # Range > 2% of price
                prob += 0.1  # Large range increases breakout probability
            
            return min(prob, 0.9)  # Cap at 90%
            
        except Exception as e:
            logger.error(f"Breakout probability analysis failed: {e}")
            return 0.3
    
    def _analyze_breakdown_probability(self, trend_1h: Dict, trend_5m: Dict, volatility: float, range_size: float, current_price: float) -> float:
        """Analyze probability of breakdown below support"""
        try:
            # Base probability
            prob = 0.3
            
            # Trend alignment
            if trend_1h.get("direction", 0) < 0 and trend_5m.get("direction", 0) < 0:
                prob += 0.2  # Both trends down
            
            # Volatility factor
            if volatility > 0.01:
                prob += 0.1  # High volatility favors breakdowns
            
            # Range size factor
            if range_size > current_price * 0.02:  # Range > 2% of price
                prob += 0.1  # Large range increases breakdown probability
            
            return min(prob, 0.9)  # Cap at 90%
            
        except Exception as e:
            logger.error(f"Breakdown probability analysis failed: {e}")
            return 0.3
    
    def _analyze_momentum_strength(self, trend_1h: Dict, trend_5m: Dict, volatility: float) -> float:
        """Analyze momentum strength"""
        try:
            # Base strength
            strength = 0.3
            
            # Trend alignment
            if trend_1h.get("direction", 0) == trend_5m.get("direction", 0):
                strength += 0.2  # Aligned trends
            
            # Volatility factor
            if volatility > 0.005:
                strength += 0.1  # Some volatility needed for momentum
            
            # Trend strength
            trend_5m_strength = trend_5m.get("strength", 0)
            if trend_5m_strength > 0.01:
                strength += min(trend_5m_strength * 10, 0.3)  # Scale trend strength
            
            return min(strength, 0.9)  # Cap at 90%
            
        except Exception as e:
            logger.error(f"Momentum strength analysis failed: {e}")
            return 0.3
