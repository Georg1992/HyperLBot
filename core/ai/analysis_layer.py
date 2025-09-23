#!/usr/bin/env python3
"""
AI Analysis Layer
================
Analyzes the data that we receive, chooses strategy, and generates predictions/reactions.
This layer contains all the intelligence and decision-making logic.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass

@dataclass
class AnalysisResult:
    """Result of market analysis"""
    strategy: str
    strategy_confidence: float
    prediction: Optional[Dict[str, Any]]
    reactive_trade: Optional[Dict[str, Any]]
    market_regime: str
    analysis_confidence: float
    reasoning: str
    timestamp: float

@dataclass
class StrategyDecision:
    """Strategy selection decision"""
    strategy: str
    confidence: float
    reasoning: str
    market_conditions: Dict[str, Any]
    alternative_strategies: List[str]

class AnalysisLayer:
    """
    Analysis Layer - Strategy Selection and Prediction Generation
    
    Responsibilities:
    1. Analyze market data and conditions
    2. Select optimal trading strategy
    3. Generate predictions based on strategy
    4. Generate reactive trades for urgent conditions
    5. Provide reasoning for all decisions
    """
    
    def __init__(self):
        # Import required components
        try:
            from core.ml.strategy_selector import global_ml_strategy_selector
            from core.ml.prediction_manager import global_prediction_manager
            from core.signals import global_signal_aggregator
            
            self.strategy_selector = global_ml_strategy_selector
            self.prediction_manager = global_prediction_manager
            self.signal_aggregator = global_signal_aggregator
            self.reactive_engine = None  # Reactive functionality integrated into execution layer
            
            # Import adaptive AI engine
            from core.ai.adaptive_ai_engine import global_adaptive_ai
            self.adaptive_ai = global_adaptive_ai
            
            self.analysis_history = []
            self.max_history = 50
            
            logger.info("🧠 AI Analysis Layer initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Analysis Layer: {e}")
            raise
    
    def analyze_market_and_generate_decisions(self, current_price: float, market_data: Dict[str, Any]) -> AnalysisResult:
        """
        Main analysis method - analyzes market and generates trading decisions
        
        Args:
            current_price: Current market price
            market_data: Comprehensive market data
            
        Returns:
            AnalysisResult with strategy, predictions, and reasoning
        """
        try:
            logger.debug(f"🧠 Analyzing market at ${current_price:.2f}")
            
            # Step 1: Analyze market conditions and select strategy
            strategy_decision = self._select_optimal_strategy(current_price, market_data)
            
            # Step 2: Generate comprehensive signals
            signals = self._generate_market_signals(current_price, market_data)
            
            # Step 3: Check for reactive trading opportunities first
            reactive_trade = self._check_reactive_opportunities(current_price, market_data)
            
            # Step 4: Generate strategy-specific prediction (if no reactive trade)
            prediction = None
            if not reactive_trade:
                prediction = self._generate_strategy_prediction(
                    strategy_decision.strategy, 
                    current_price, 
                    market_data, 
                    signals
                )
            
            # Step 5: Determine market regime
            market_regime = self._determine_market_regime(market_data)
            
            # Step 6: Calculate overall analysis confidence
            analysis_confidence = self._calculate_analysis_confidence(
                strategy_decision, prediction, reactive_trade, market_data
            )
            
            # Step 7: Generate comprehensive reasoning
            reasoning = self._generate_analysis_reasoning(
                strategy_decision, prediction, reactive_trade, market_regime
            )
            
            # Create analysis result
            result = AnalysisResult(
                strategy=strategy_decision.strategy,
                strategy_confidence=strategy_decision.confidence,
                prediction=prediction,
                reactive_trade=reactive_trade,
                market_regime=market_regime,
                analysis_confidence=analysis_confidence,
                reasoning=reasoning,
                timestamp=time.time()
            )
            
            # Store in history
            self._store_analysis_result(result)
            
            logger.info(f"🧠 Analysis complete: {strategy_decision.strategy} strategy, "
                       f"confidence: {analysis_confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Market analysis failed: {e}")
            return AnalysisResult(
                strategy="error",
                strategy_confidence=0.0,
                prediction=None,
                reactive_trade=None,
                market_regime="unknown",
                analysis_confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                timestamp=time.time()
            )
    
    def adaptive_analysis(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform adaptive analysis that continuously adjusts predictions and trades
        """
        try:
            # Use adaptive AI engine for continuous analysis
            adaptive_results = self.adaptive_ai.analyze_and_adapt_predictions(current_price, market_data)
            
            # Convert adaptive predictions to standard format
            adapted_predictions = []
            for prediction in adaptive_results.get("new_predictions", []):
                # TradingPrediction already has all needed fields
                adapted_predictions.append({
                    "direction": prediction.direction,
                    "entry_price": prediction.entry_price,
                    "target_price": prediction.target_price,
                    "stop_loss": prediction.stop_loss,
                    "confidence": prediction.confidence,
                    "strategy": "adaptive",  # Set strategy as adaptive
                    "reasoning": prediction.reasoning,
                    "adaptive": True
                })
            
            # Add adapted predictions to results
            adaptive_results["adapted_predictions"] = adapted_predictions
            
            return adaptive_results
            
        except Exception as e:
            logger.error(f"❌ Adaptive analysis failed: {e}")
            return {"error": str(e)}
    
    def _select_optimal_strategy(self, current_price: float, market_data: Dict[str, Any]) -> StrategyDecision:
        """Select optimal trading strategy based on market conditions"""
        try:
            # Use strategy selector to choose optimal strategy
            strategy_result = self.strategy_selector.select_strategy(market_data)
            
            strategy = strategy_result.strategy
            confidence = strategy_result.confidence
            reasoning = strategy_result.reasoning
            market_conditions = strategy_result.market_conditions
            alternative_strategies = strategy_result.alternative_strategies
            
            return StrategyDecision(
                strategy=strategy,
                confidence=confidence,
                reasoning=reasoning,
                market_conditions=market_conditions,
                alternative_strategies=alternative_strategies
            )
            
        except Exception as e:
            logger.error(f"❌ Strategy selection failed: {e}")
            return StrategyDecision(
                strategy="standard",
                confidence=0.0,
                reasoning=f"Strategy selection failed: {str(e)}",
                market_conditions={},
                alternative_strategies=[]
            )
    
    def _generate_market_signals(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive market signals"""
        try:
            return self.signal_aggregator.generate_primary_signals(current_price, market_data)
        except Exception as e:
            logger.error(f"❌ Signal generation failed: {e}")
            return {}
    
    def _check_reactive_opportunities(self, current_price: float, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for reactive trading opportunities"""
        try:
            # Check for extreme market conditions that require reactive trading
            volatility = market_data.get("volatility_5m", 0.001)
            rsi = market_data.get("rsi", 50)
            
            # Check for volatility changes first (most important for reactive trading)
            volatility_change = market_data.get("volatility_change", {})
            is_volatility_spike = volatility_change.get("change_direction") in ["SPIKE_UP", "EXTREME_SPIKE"]
            is_high_urgency = volatility_change.get("urgency") in ["HIGH", "CRITICAL"]
            
            # Detect extreme conditions that need immediate action
            is_extreme_volatility = volatility > 0.01  # >1% volatility
            is_extreme_rsi = rsi < 20 or rsi > 80
            
            if is_volatility_spike or is_high_urgency or is_extreme_volatility or is_extreme_rsi:
                # Generate reactive trade for extreme conditions
                direction = "BUY" if rsi < 20 else "SELL" if rsi > 80 else "BUY"
                
                # Determine urgency based on volatility change
                if is_volatility_spike and is_high_urgency:
                    urgency = "CRITICAL"
                elif is_volatility_spike or is_high_urgency:
                    urgency = "HIGH"
                else:
                    urgency = "MEDIUM"
                
                # Build detailed reasoning
                reasoning_parts = []
                if is_volatility_spike:
                    change_direction = volatility_change.get("change_direction", "UNKNOWN")
                    change_magnitude = volatility_change.get("change_magnitude", 0) * 100
                    reasoning_parts.append(f"Volatility {change_direction} ({change_magnitude:.1f}%)")
                if is_extreme_volatility:
                    reasoning_parts.append(f"Extreme volatility ({volatility*100:.2f}%)")
                if is_extreme_rsi:
                    reasoning_parts.append(f"Extreme RSI ({rsi:.1f})")
                
                reasoning = " | ".join(reasoning_parts) if reasoning_parts else f"Market conditions: volatility={volatility:.3f}, RSI={rsi:.1f}"
                
                reactive_signal = {
                    "direction": direction,
                    "urgency": urgency,
                    "confidence": 0.8,
                    "reasoning": reasoning
                }
                
                return self._generate_reactive_trade(current_price, reactive_signal)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Reactive opportunity check failed: {e}")
            return None
    
    def _generate_reactive_trade(self, current_price: float, reactive_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Generate reactive trade parameters"""
        try:
            direction = reactive_signal.get("direction", "BUY")
            urgency = reactive_signal.get("urgency", "HIGH")
            confidence = reactive_signal.get("confidence", 0.8)
            
            # Calculate reactive trade size (smaller for urgent trades)
            # Get account balance from market data or use default
            account_balance = market_data.get("account_balance", 455.0)
            size_usd = account_balance * 0.02  # 2% for reactive trades
            size_btc = size_usd / current_price
            
            # Calculate reactive stop loss and target
            if urgency == "CRITICAL":
                stop_percent = 0.015  # 1.5% stop loss
                target_percent = 0.06  # 6% target
            else:
                stop_percent = 0.02   # 2% stop loss
                target_percent = 0.04  # 4% target
            
            if direction == "BUY":
                stop_loss = current_price * (1 - stop_percent)
                target_price = current_price * (1 + target_percent)
            else:
                stop_loss = current_price * (1 + stop_percent)
                target_price = current_price * (1 - target_percent)
            
            return {
                "trade_id": f"reactive_{int(time.time())}",
                "direction": direction,
                "entry_price": current_price,
                "size_btc": size_btc,
                "size_usd": size_usd,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "confidence": confidence,
                "urgency": urgency,
                "timestamp": time.time(),
                "reasoning": reactive_signal.get("reasoning", "Reactive trade opportunity"),
                "execution_type": "market",
                "reactive_signal": reactive_signal,
                "is_reactive": True
            }
            
        except Exception as e:
            logger.error(f"❌ Reactive trade generation failed: {e}")
            return None
    
    def _generate_strategy_prediction(self, strategy: str, current_price: float, 
                                    market_data: Dict[str, Any], signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate strategy-specific prediction"""
        try:
            # Generate prediction using prediction manager with strategy
            prediction = self.prediction_manager.generate_prediction(
                current_price, 
                market_data, 
                signals,
                strategy=strategy
            )
            
            if prediction:
                # Convert to dictionary and add strategy info
                prediction_dict = prediction.to_dict()
                prediction_dict["strategy"] = strategy
                return prediction_dict
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Strategy prediction generation failed: {e}")
            return None
    
    def _determine_market_regime(self, market_data: Dict[str, Any]) -> str:
        """Determine current market regime"""
        try:
            volatility = market_data.get("volatility_5m", 0.001)
            trend_analysis = market_data.get("trend_analysis", {})
            trend = trend_analysis.get("overall_trend", "NEUTRAL")
            
            if volatility > 0.005:  # High volatility
                if trend == "BULLISH":
                    return "HIGH_VOL_BULL"
                elif trend == "BEARISH":
                    return "HIGH_VOL_BEAR"
                else:
                    return "HIGH_VOL_SIDEWAYS"
            elif volatility > 0.002:  # Medium volatility
                if trend == "BULLISH":
                    return "MED_VOL_BULL"
                elif trend == "BEARISH":
                    return "MED_VOL_BEAR"
                else:
                    return "MED_VOL_SIDEWAYS"
            else:  # Low volatility
                if trend == "BULLISH":
                    return "LOW_VOL_BULL"
                elif trend == "BEARISH":
                    return "LOW_VOL_BEAR"
                else:
                    return "LOW_VOL_SIDEWAYS"
                    
        except Exception as e:
            logger.error(f"❌ Market regime determination failed: {e}")
            return "UNKNOWN"
    
    def _calculate_analysis_confidence(self, strategy_decision: StrategyDecision, 
                                     prediction: Optional[Dict[str, Any]], 
                                     reactive_trade: Optional[Dict[str, Any]], 
                                     market_data: Dict[str, Any]) -> float:
        """Calculate overall analysis confidence"""
        try:
            base_confidence = strategy_decision.confidence
            
            # Boost confidence if we have a clear prediction or reactive trade
            if reactive_trade:
                base_confidence = max(base_confidence, reactive_trade.get("confidence", 0.8))
            elif prediction:
                base_confidence = max(base_confidence, prediction.get("confidence", 0.5))
            
            # Adjust based on market data quality
            data_quality = self._assess_data_quality(market_data)
            quality_adjustment = (data_quality - 0.5) * 0.2  # ±10% adjustment
            
            final_confidence = min(1.0, max(0.0, base_confidence + quality_adjustment))
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"❌ Confidence calculation failed: {e}")
            return 0.0
    
    def _assess_data_quality(self, market_data: Dict[str, Any]) -> float:
        """Assess quality of market data"""
        try:
            quality_score = 0.0
            total_checks = 0
            
            # Check price data
            if market_data.get("current_price", 0) > 0:
                quality_score += 1.0
            total_checks += 1
            
            # Check RSI
            rsi = market_data.get("rsi", 0)
            if 0 <= rsi <= 100:
                quality_score += 1.0
            total_checks += 1
            
            # Check volatility
            if market_data.get("volatility_5m", 0) > 0:
                quality_score += 1.0
            total_checks += 1
            
            # Check S/R levels
            sr_data = market_data.get("support_resistance", {})
            if sr_data and sr_data.get("key_levels"):
                quality_score += 1.0
            total_checks += 1
            
            return quality_score / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Data quality assessment failed: {e}")
            return 0.0
    
    def _generate_analysis_reasoning(self, strategy_decision: StrategyDecision, 
                                   prediction: Optional[Dict[str, Any]], 
                                   reactive_trade: Optional[Dict[str, Any]], 
                                   market_regime: str) -> str:
        """Generate comprehensive reasoning for the analysis"""
        try:
            reasoning_parts = []
            
            # Strategy reasoning
            reasoning_parts.append(f"Strategy: {strategy_decision.strategy} (confidence: {strategy_decision.confidence:.2f})")
            reasoning_parts.append(f"Market Regime: {market_regime}")
            
            # Decision reasoning
            if reactive_trade:
                reasoning_parts.append(f"Reactive Trade: {reactive_trade['direction']} (urgency: {reactive_trade['urgency']})")
                reasoning_parts.append(f"Reason: {reactive_trade.get('reasoning', 'Urgent market conditions')}")
            elif prediction:
                reasoning_parts.append(f"Prediction: {prediction['direction']} (confidence: {prediction['confidence']:.2f})")
                reasoning_parts.append(f"Entry: ${prediction['entry_price']:.2f}, Target: ${prediction['target_price']:.2f}")
            else:
                reasoning_parts.append("No trading opportunity identified")
            
            # Strategy-specific reasoning
            reasoning_parts.append(f"Strategy Reasoning: {strategy_decision.reasoning}")
            
            return " | ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"❌ Reasoning generation failed: {e}")
            return f"Analysis completed with {strategy_decision.strategy} strategy"
    
    def _store_analysis_result(self, result: AnalysisResult):
        """Store analysis result in history"""
        try:
            self.analysis_history.append(result)
            if len(self.analysis_history) > self.max_history:
                self.analysis_history = self.analysis_history[-self.max_history:]
        except Exception as e:
            logger.error(f"❌ Failed to store analysis result: {e}")
    
    def get_analysis_history(self, limit: int = 10) -> List[AnalysisResult]:
        """Get recent analysis history"""
        try:
            return self.analysis_history[-limit:] if self.analysis_history else []
        except Exception as e:
            logger.error(f"❌ Failed to get analysis history: {e}")
            return []
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get performance statistics by strategy"""
        try:
            strategy_stats = {}
            
            for result in self.analysis_history:
                strategy = result.strategy
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        "count": 0,
                        "avg_confidence": 0.0,
                        "total_confidence": 0.0
                    }
                
                strategy_stats[strategy]["count"] += 1
                strategy_stats[strategy]["total_confidence"] += result.analysis_confidence
            
            # Calculate averages
            for strategy in strategy_stats:
                count = strategy_stats[strategy]["count"]
                strategy_stats[strategy]["avg_confidence"] = strategy_stats[strategy]["total_confidence"] / count
            
            return strategy_stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get strategy performance: {e}")
            return {}

# Global instance
global_analysis_layer = AnalysisLayer()
