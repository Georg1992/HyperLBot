#!/usr/bin/env python3
"""
Master Fusion Engine - Ultimate Intelligence for Bitcoin Trading
Combines ALL available signals, patterns, and factors for maximum accuracy
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import time
from datetime import datetime
from dataclasses import dataclass
from collections import deque
import json

@dataclass
class FusionSignal:
    """Master fusion trading signal with comprehensive analysis"""
    signal: str  # BUY, SELL, HOLD, WAIT
    confidence: float
    position_size: float
    entry_price: float
    target_price: float
    stop_loss: float
    timeframe: str
    reason: str
    supporting_factors: List[str]
    risk_score: float
    profit_potential: float
    fusion_score: float

class MasterFusionEngine:
    """Ultimate trading intelligence combining all available analysis systems"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # Initialize all analysis engines
        self.ml_engine = None
        self.btc_pattern_engine = None
        self.prediction_engine = None
        self.variability_analyzer = None
        self.trade_manager = None
        self.whale_integration = None
        
        # Signal weighting system (based on historical performance)
        self.signal_weights = {
            # Core technical analysis
            "ml_prediction": 0.25,           # ML models
            "btc_patterns": 0.20,            # Bitcoin-specific patterns
            "traditional_prediction": 0.15,  # Classic TA prediction
            "ultimate_pressure": 0.15,       # Real-time pressure indicator
            
            # Market intelligence
            "whale_analytics": 0.10,          # Whale movements
            "blockchain_data": 0.05,          # On-chain metrics
            "global_volume": 0.05,            # Cross-exchange volume
            
            # Risk management
            "variability_analysis": 0.05     # Market conditions
        }
        
        # Confidence thresholds for different signal strength
        self.confidence_thresholds = {
            "ultra_high": 0.90,    # 90%+ - Max position size
            "high": 0.80,          # 80%+ - Large position
            "medium": 0.65,        # 65%+ - Standard position
            "low": 0.50,           # 50%+ - Small position
            "very_low": 0.35       # 35%+ - Minimal position
        }
        
        # Position sizing based on confidence and risk
        self.position_sizing = {
            "ultra_high": {"min": 0.40, "max": 0.60},  # 40-60% of capital
            "high": {"min": 0.25, "max": 0.40},        # 25-40% of capital
            "medium": {"min": 0.15, "max": 0.25},      # 15-25% of capital
            "low": {"min": 0.08, "max": 0.15},         # 8-15% of capital
            "very_low": {"min": 0.03, "max": 0.08}     # 3-8% of capital
        }
        
        # Historical signal tracking for learning
        self.signal_history = deque(maxlen=1000)
        self.performance_tracking = {
            "total_signals": 0,
            "successful_signals": 0,
            "accuracy_by_confidence": {},
            "accuracy_by_source": {}
        }
        
        logger.info("🧠 Master Fusion Engine initialized - Ultimate trading intelligence active")
    
    def initialize_engines(self, engines: Dict[str, Any]):
        """Initialize all analysis engines"""
        self.ml_engine = engines.get("ml_engine")
        self.btc_pattern_engine = engines.get("btc_pattern_engine")
        self.prediction_engine = engines.get("prediction_engine")
        self.variability_analyzer = engines.get("variability_analyzer")
        self.trade_manager = engines.get("trade_manager")
        self.whale_integration = engines.get("whale_integration")
        
        logger.success("🔗 All analysis engines connected to Master Fusion Engine")
    
    def generate_ultimate_signal(self, market_data: Dict[str, Any], current_price: float, 
                                enhanced_analysis: Dict[str, Any]) -> Optional[FusionSignal]:
        """Generate the ultimate trading signal by fusing all available intelligence"""
        try:
            logger.info("🧠 Master Fusion Engine analyzing all available intelligence...")
            
            # 1. COLLECT ALL SIGNALS
            all_signals = self._collect_all_signals(market_data, current_price, enhanced_analysis)
            
            if not all_signals:
                logger.warning("⚠️ No signals available for fusion")
                return None
            
            # 2. ANALYZE SIGNAL QUALITY
            signal_quality = self._analyze_signal_quality(all_signals)
            
            # 3. DETECT SIGNAL CONVERGENCE
            convergence_analysis = self._detect_signal_convergence(all_signals)
            
            # 4. CALCULATE MARKET CONDITIONS
            market_conditions = self._assess_market_conditions(market_data, enhanced_analysis)
            
            # 5. FUSION ALGORITHM - COMBINE ALL INTELLIGENCE
            fusion_result = self._fusion_algorithm(
                all_signals, signal_quality, convergence_analysis, 
                market_conditions, current_price
            )
            
            if not fusion_result:
                logger.info("🤔 Fusion analysis complete - no clear trading opportunity")
                return None
            
            # 6. RISK-ADJUSTED POSITION SIZING
            final_signal = self._calculate_optimal_position(fusion_result, market_conditions)
            
            # 7. LOG AND TRACK
            self._log_fusion_decision(final_signal, all_signals)
            
            logger.success(f"🚀 MASTER FUSION SIGNAL: {final_signal.signal} - {final_signal.confidence:.1%} confidence")
            logger.info(f"   💰 Position Size: {final_signal.position_size:.1%} of capital")
            logger.info(f"   🎯 Target: ${final_signal.target_price:,.2f}")
            logger.info(f"   🛡️ Stop Loss: ${final_signal.stop_loss:,.2f}")
            logger.info(f"   📊 Supporting Factors: {len(final_signal.supporting_factors)}")
            
            return final_signal
            
        except Exception as e:
            logger.error(f"Master Fusion Engine error: {e}")
            return None
    
    def _collect_all_signals(self, market_data: Dict[str, Any], current_price: float, 
                           enhanced_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Collect signals from all available analysis engines"""
        signals = {}
        
        # 1. ML PREDICTION ENGINE
        if self.ml_engine:
            try:
                ml_signal = self.ml_engine.generate_ml_prediction(market_data, current_price)
                if ml_signal.get("has_prediction"):
                    signals["ml_prediction"] = ml_signal
                    logger.info(f"📊 ML Signal: {ml_signal.get('side', 'UNKNOWN')} - {ml_signal.get('confidence', 0):.1%}")
            except Exception as e:
                logger.debug(f"ML engine error: {e}")
        
        # 2. BITCOIN PATTERN ENGINE
        if self.btc_pattern_engine:
            try:
                btc_signal = self.btc_pattern_engine.analyze_bitcoin_patterns(market_data, current_price)
                if btc_signal.get("combined_signal"):
                    signals["btc_patterns"] = btc_signal
                    combined = btc_signal["combined_signal"]
                    logger.info(f"🏗️ BTC Pattern: {combined.get('signal', 'UNKNOWN')} - {combined.get('confidence', 0):.1%}")
            except Exception as e:
                logger.debug(f"BTC pattern engine error: {e}")
        
        # 3. TRADITIONAL PREDICTION ENGINE
        if self.prediction_engine:
            try:
                # This would be the existing prediction engine
                traditional_signal = enhanced_analysis.get("prediction_analysis", {})
                if traditional_signal.get("has_prediction"):
                    signals["traditional_prediction"] = traditional_signal
                    logger.info(f"📈 Traditional: {traditional_signal.get('prediction_type', 'UNKNOWN')}")
            except Exception as e:
                logger.debug(f"Traditional prediction error: {e}")
        
        # 4. ULTIMATE PRESSURE INDICATOR
        try:
            pressure_data = enhanced_analysis.get("ultimate_pressure", {})
            if pressure_data.get("status") == "success":
                signals["ultimate_pressure"] = pressure_data
                direction = pressure_data.get("direction", "UNKNOWN")
                confidence = pressure_data.get("confidence", "0%")
                logger.info(f"⚡ Ultimate Pressure: {direction} - {confidence}")
        except Exception as e:
            logger.debug(f"Ultimate pressure error: {e}")
        
        # 5. WHALE ANALYTICS
        if self.whale_integration:
            try:
                whale_signal = enhanced_analysis.get("whale_analysis", {})
                if whale_signal.get("confidence", 0) > 0.5:
                    signals["whale_analytics"] = whale_signal
                    sentiment = whale_signal.get("overall_sentiment", "UNKNOWN")
                    logger.info(f"🐋 Whale Analytics: {sentiment}")
            except Exception as e:
                logger.debug(f"Whale analytics error: {e}")
        
        # 6. GLOBAL VOLUME ANALYSIS
        try:
            volume_data = enhanced_analysis.get("global_volume", {})
            if volume_data:
                signals["global_volume"] = volume_data
                trend = volume_data.get("trend", "UNKNOWN")
                logger.info(f"🌍 Global Volume: {trend}")
        except Exception as e:
            logger.debug(f"Global volume error: {e}")
        
        # 7. BLOCKCHAIN DATA
        try:
            blockchain_data = enhanced_analysis.get("blockchain_data", {})
            if blockchain_data.get("confidence", 0) > 0.5:
                signals["blockchain_data"] = blockchain_data
                sentiment = blockchain_data.get("overall_sentiment", "UNKNOWN")
                logger.info(f"⛓️ Blockchain: {sentiment}")
        except Exception as e:
            logger.debug(f"Blockchain data error: {e}")
        
        # 8. VARIABILITY ANALYSIS
        if self.variability_analyzer:
            try:
                var_analysis = self.variability_analyzer.get_variability_analysis()
                signals["variability_analysis"] = var_analysis
                recommendation = var_analysis.get("trading_recommendation", "UNKNOWN")
                logger.info(f"📊 Variability: {recommendation}")
            except Exception as e:
                logger.debug(f"Variability analysis error: {e}")
        
        logger.info(f"📡 Collected {len(signals)} signal sources for fusion analysis")
        return signals
    
    def _analyze_signal_quality(self, all_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the quality and reliability of collected signals"""
        quality_scores = {}
        
        for signal_name, signal_data in all_signals.items():
            quality_score = 0.0
            
            # Base confidence
            confidence = 0.0
            if signal_name == "ml_prediction":
                confidence = signal_data.get("confidence", 0)
            elif signal_name == "btc_patterns":
                confidence = signal_data.get("combined_signal", {}).get("confidence", 0)
            elif signal_name == "traditional_prediction":
                confidence = signal_data.get("prediction_confidence", 0)
            elif signal_name == "ultimate_pressure":
                conf_str = signal_data.get("confidence", "0%")
                confidence = int(conf_str.replace('%', '')) / 100 if conf_str != "0%" else 0
            elif signal_name == "whale_analytics":
                confidence = signal_data.get("confidence", 0)
            elif signal_name == "blockchain_data":
                confidence = signal_data.get("confidence", 0)
            else:
                confidence = 0.5  # Default for other signals
            
            quality_score += confidence * 0.6
            
            # Signal freshness (newer = better)
            timestamp = signal_data.get("timestamp", time.time())
            age_minutes = (time.time() - timestamp) / 60
            freshness_score = max(0, 1 - (age_minutes / 30))  # Decay over 30 minutes
            quality_score += freshness_score * 0.2
            
            # Data completeness
            if isinstance(signal_data, dict) and len(signal_data) > 3:
                quality_score += 0.2
            
            quality_scores[signal_name] = min(1.0, quality_score)
        
        return quality_scores
    
    def _detect_signal_convergence(self, all_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Detect convergence/divergence between different signal sources"""
        
        # Extract signal directions
        signal_directions = {}
        
        for signal_name, signal_data in all_signals.items():
            direction = "NEUTRAL"
            
            if signal_name == "ml_prediction":
                side = signal_data.get("side", "")
                direction = "BULLISH" if side == "BUY" else "BEARISH" if side == "SELL" else "NEUTRAL"
            elif signal_name == "btc_patterns":
                combined = signal_data.get("combined_signal", {})
                signal = combined.get("signal", "")
                direction = "BULLISH" if signal == "BUY" else "BEARISH" if signal == "SELL" else "NEUTRAL"
            elif signal_name == "traditional_prediction":
                pred_type = signal_data.get("prediction_type", "")
                direction = "BULLISH" if "BUY" in pred_type else "BEARISH" if "SELL" in pred_type else "NEUTRAL"
            elif signal_name == "ultimate_pressure":
                pressure_dir = signal_data.get("direction", "")
                direction = "BULLISH" if "BUY" in pressure_dir else "BEARISH" if "SELL" in pressure_dir else "NEUTRAL"
            elif signal_name == "whale_analytics":
                sentiment = signal_data.get("overall_sentiment", "")
                direction = "BULLISH" if sentiment == "BULLISH" else "BEARISH" if sentiment == "BEARISH" else "NEUTRAL"
            elif signal_name == "blockchain_data":
                sentiment = signal_data.get("overall_sentiment", "")
                direction = "BULLISH" if sentiment == "BULLISH" else "BEARISH" if sentiment == "BEARISH" else "NEUTRAL"
            
            signal_directions[signal_name] = direction
        
        # Calculate convergence
        bullish_count = sum(1 for d in signal_directions.values() if d == "BULLISH")
        bearish_count = sum(1 for d in signal_directions.values() if d == "BEARISH")
        neutral_count = sum(1 for d in signal_directions.values() if d == "NEUTRAL")
        
        total_signals = len(signal_directions)
        
        convergence_ratio = max(bullish_count, bearish_count) / total_signals if total_signals > 0 else 0
        dominant_direction = "BULLISH" if bullish_count > bearish_count else "BEARISH" if bearish_count > bullish_count else "NEUTRAL"
        
        return {
            "signal_directions": signal_directions,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "convergence_ratio": convergence_ratio,
            "dominant_direction": dominant_direction,
            "consensus_strength": "STRONG" if convergence_ratio > 0.7 else "MODERATE" if convergence_ratio > 0.5 else "WEAK"
        }
    
    def _assess_market_conditions(self, market_data: Dict[str, Any], enhanced_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall market conditions for risk adjustment"""
        
        conditions = {
            "volatility_regime": "NORMAL",
            "volume_regime": "NORMAL",
            "trend_strength": "MODERATE",
            "risk_level": "MEDIUM",
            "market_phase": "NEUTRAL"
        }
        
        # Volatility assessment
        volatility_5m = enhanced_analysis.get("volatility_5m", 0.003)
        if volatility_5m > 0.01:
            conditions["volatility_regime"] = "HIGH"
            conditions["risk_level"] = "HIGH"
        elif volatility_5m > 0.005:
            conditions["volatility_regime"] = "ELEVATED"
        elif volatility_5m < 0.002:
            conditions["volatility_regime"] = "LOW"
        
        # Volume assessment
        volume_category = enhanced_analysis.get("volume_category", "NORMAL")
        conditions["volume_regime"] = volume_category
        
        # Trend strength
        trend_5m = market_data.get("5m", {}).get("trend", {}).get("trend", "UNKNOWN")
        trend_1h = market_data.get("1h", {}).get("trend", {}).get("trend", "UNKNOWN")
        
        if trend_5m in ["STRONG_UP", "STRONG_DOWN"] or trend_1h in ["STRONG_UP", "STRONG_DOWN"]:
            conditions["trend_strength"] = "STRONG"
        elif trend_5m in ["UP", "DOWN"] or trend_1h in ["UP", "DOWN"]:
            conditions["trend_strength"] = "MODERATE"
        else:
            conditions["trend_strength"] = "WEAK"
        
        # Market phase (simplified)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 16:
            conditions["market_phase"] = "ACTIVE"  # US trading hours
        elif 22 <= current_hour or current_hour <= 6:
            conditions["market_phase"] = "QUIET"   # Overnight
        else:
            conditions["market_phase"] = "TRANSITION"
        
        return conditions
    
    def _fusion_algorithm(self, all_signals: Dict[str, Any], signal_quality: Dict[str, Any], 
                         convergence_analysis: Dict[str, Any], market_conditions: Dict[str, Any], 
                         current_price: float) -> Optional[Dict[str, Any]]:
        """Core fusion algorithm - combines all intelligence into trading decision"""
        
        # 1. Calculate weighted signal strength
        bullish_strength = 0.0
        bearish_strength = 0.0
        
        for signal_name, signal_data in all_signals.items():
            weight = self.signal_weights.get(signal_name, 0.05)
            quality = signal_quality.get(signal_name, 0.5)
            direction = convergence_analysis["signal_directions"].get(signal_name, "NEUTRAL")
            
            # Get signal confidence
            confidence = 0.5
            if signal_name == "ml_prediction":
                confidence = signal_data.get("confidence", 0.5)
            elif signal_name == "btc_patterns":
                confidence = signal_data.get("combined_signal", {}).get("confidence", 0.5)
            elif signal_name == "ultimate_pressure":
                conf_str = signal_data.get("confidence", "50%")
                confidence = int(conf_str.replace('%', '')) / 100 if conf_str != "0%" else 0.5
            elif signal_name in ["whale_analytics", "blockchain_data"]:
                confidence = signal_data.get("confidence", 0.5)
            
            # Calculate weighted contribution
            signal_strength = weight * quality * confidence
            
            if direction == "BULLISH":
                bullish_strength += signal_strength
            elif direction == "BEARISH":
                bearish_strength += signal_strength
        
        # 2. Determine signal direction and confidence
        net_strength = bullish_strength - bearish_strength
        total_strength = bullish_strength + bearish_strength
        
        if abs(net_strength) < 0.1 or total_strength < 0.3:
            return None  # No clear signal
        
        signal_direction = "BUY" if net_strength > 0 else "SELL"
        base_confidence = abs(net_strength) / max(total_strength, 0.1)
        
        # 3. Apply convergence boost
        convergence_boost = 0.0
        if convergence_analysis["consensus_strength"] == "STRONG":
            convergence_boost = 0.15
        elif convergence_analysis["consensus_strength"] == "MODERATE":
            convergence_boost = 0.08
        
        # 4. Market condition adjustments
        condition_adjustment = 0.0
        if market_conditions["volatility_regime"] == "HIGH":
            condition_adjustment -= 0.1  # Reduce confidence in high volatility
        elif market_conditions["volatility_regime"] == "LOW" and market_conditions["trend_strength"] == "STRONG":
            condition_adjustment += 0.1  # Boost confidence in stable trending markets
        
        # 5. Final confidence calculation
        final_confidence = min(0.95, max(0.35, base_confidence + convergence_boost + condition_adjustment))
        
        # 6. Generate targets and stops
        target_price, stop_loss = self._calculate_targets(
            signal_direction, current_price, final_confidence, market_conditions
        )
        
        return {
            "signal": signal_direction,
            "confidence": final_confidence,
            "entry_price": current_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "bullish_strength": bullish_strength,
            "bearish_strength": bearish_strength,
            "convergence_boost": convergence_boost,
            "condition_adjustment": condition_adjustment,
            "supporting_signals": len([s for s in convergence_analysis["signal_directions"].values() 
                                     if s == ("BULLISH" if signal_direction == "BUY" else "BEARISH")])
        }
    
    def _calculate_targets(self, signal_direction: str, current_price: float, 
                          confidence: float, market_conditions: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate target price and stop loss based on confidence and market conditions"""
        
        # Base target and stop percentages
        base_target_pct = 0.02  # 2%
        base_stop_pct = 0.015   # 1.5%
        
        # Adjust based on confidence
        confidence_multiplier = 0.5 + (confidence * 1.5)  # 0.5x to 2.0x
        target_pct = base_target_pct * confidence_multiplier
        stop_pct = base_stop_pct / confidence_multiplier  # Tighter stops for higher confidence
        
        # Adjust based on volatility
        volatility_regime = market_conditions.get("volatility_regime", "NORMAL")
        if volatility_regime == "HIGH":
            target_pct *= 1.5
            stop_pct *= 1.3
        elif volatility_regime == "LOW":
            target_pct *= 0.7
            stop_pct *= 0.8
        
        # Calculate actual prices
        if signal_direction == "BUY":
            target_price = current_price * (1 + target_pct)
            stop_loss = current_price * (1 - stop_pct)
        else:  # SELL
            target_price = current_price * (1 - target_pct)
            stop_loss = current_price * (1 + stop_pct)
        
        return target_price, stop_loss
    
    def _calculate_optimal_position(self, fusion_result: Dict[str, Any], 
                                  market_conditions: Dict[str, Any]) -> FusionSignal:
        """Calculate optimal position size based on confidence and risk"""
        
        confidence = fusion_result["confidence"]
        
        # Determine confidence tier
        if confidence >= self.confidence_thresholds["ultra_high"]:
            tier = "ultra_high"
        elif confidence >= self.confidence_thresholds["high"]:
            tier = "high"
        elif confidence >= self.confidence_thresholds["medium"]:
            tier = "medium"
        elif confidence >= self.confidence_thresholds["low"]:
            tier = "low"
        else:
            tier = "very_low"
        
        # Base position size
        pos_range = self.position_sizing[tier]
        base_position = pos_range["min"] + (confidence - self.confidence_thresholds[tier.replace("ultra_", "").replace("very_", "")]) * (pos_range["max"] - pos_range["min"])
        
        # Risk adjustments
        risk_multiplier = 1.0
        
        # Volatility adjustment
        volatility_regime = market_conditions.get("volatility_regime", "NORMAL")
        if volatility_regime == "HIGH":
            risk_multiplier *= 0.7  # Reduce position in high volatility
        elif volatility_regime == "LOW":
            risk_multiplier *= 1.2  # Increase position in low volatility
        
        # Convergence adjustment
        supporting_signals = fusion_result.get("supporting_signals", 1)
        if supporting_signals >= 5:
            risk_multiplier *= 1.1  # Boost for strong convergence
        elif supporting_signals <= 2:
            risk_multiplier *= 0.8  # Reduce for weak convergence
        
        # Final position size
        final_position = min(0.6, max(0.03, base_position * risk_multiplier))
        
        # Calculate risk metrics
        entry_price = fusion_result["entry_price"]
        target_price = fusion_result["target_price"]
        stop_loss = fusion_result["stop_loss"]
        
        profit_potential = abs(target_price - entry_price) / entry_price
        risk_amount = abs(stop_loss - entry_price) / entry_price
        risk_reward = profit_potential / risk_amount if risk_amount > 0 else 0
        
        # Create comprehensive reason
        supporting_factors = []
        if fusion_result.get("convergence_boost", 0) > 0:
            supporting_factors.append("Signal Convergence")
        if fusion_result.get("supporting_signals", 0) >= 3:
            supporting_factors.append("Multiple Confirmations")
        if confidence >= 0.8:
            supporting_factors.append("High Confidence")
        if risk_reward >= 2.0:
            supporting_factors.append("Favorable Risk/Reward")
        
        reason = f"Master Fusion: {confidence:.1%} confidence, {supporting_signals} supporting signals, {tier.replace('_', ' ').title()} tier"
        
        return FusionSignal(
            signal=fusion_result["signal"],
            confidence=confidence,
            position_size=final_position,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            timeframe="5m",
            reason=reason,
            supporting_factors=supporting_factors,
            risk_score=risk_amount,
            profit_potential=profit_potential,
            fusion_score=confidence * final_position * risk_reward
        )
    
    def _log_fusion_decision(self, signal: FusionSignal, all_signals: Dict[str, Any]):
        """Log fusion decision for performance tracking"""
        
        decision_log = {
            "timestamp": time.time(),
            "signal": signal.signal,
            "confidence": signal.confidence,
            "position_size": signal.position_size,
            "fusion_score": signal.fusion_score,
            "supporting_factors": signal.supporting_factors,
            "input_signals": list(all_signals.keys()),
            "signal_count": len(all_signals)
        }
        
        self.signal_history.append(decision_log)
        self.performance_tracking["total_signals"] += 1
        
        logger.info(f"📝 Fusion decision logged - Total signals processed: {self.performance_tracking['total_signals']}")
    
    def get_fusion_performance(self) -> Dict[str, Any]:
        """Get performance statistics for the fusion engine"""
        if not self.signal_history:
            return {"status": "No signals processed yet"}
        
        recent_signals = list(self.signal_history)[-50:]  # Last 50 signals
        
        avg_confidence = np.mean([s["confidence"] for s in recent_signals])
        avg_position_size = np.mean([s["position_size"] for s in recent_signals])
        avg_fusion_score = np.mean([s["fusion_score"] for s in recent_signals])
        
        signal_distribution = {
            "BUY": len([s for s in recent_signals if s["signal"] == "BUY"]),
            "SELL": len([s for s in recent_signals if s["signal"] == "SELL"])
        }
        
        return {
            "total_signals": len(self.signal_history),
            "recent_performance": {
                "avg_confidence": avg_confidence,
                "avg_position_size": avg_position_size,
                "avg_fusion_score": avg_fusion_score,
                "signal_distribution": signal_distribution
            },
            "signal_weights": self.signal_weights,
            "last_update": time.time()
        }