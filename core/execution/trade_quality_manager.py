#!/usr/bin/env python3
"""
Trade Manager for Trading Bot
Manages trade execution and position tracking
"""

import time
# import json  # Removed unused import
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger
# from collections import deque  # Removed unused import

# Import core module to setup paths
# import core  # Removed unused import

from config.config import TradingConfig

class TradeManager:
    """Trade management with placement and dynamic stops"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.config = TradingConfig()
        
        # Trade quality thresholds (ADJUSTED FOR REAL TRADING)
        self.QUALITY_THRESHOLDS = {
            "excellent": 0.80,  # Lowered from 85% to 80%
            "good": 0.65,       # Lowered from 70% to 65%
            "acceptable": 0.45, # Lowered from 60% to 45% ← KEY FIX!
            "poor": 0.30        # Lowered from 50% to 30%
        }
        
        # Stop adjustment parameters
        self.STOP_ADJUSTMENT_CONFIG = {
            "min_profit_threshold": 0.003,  # 0.3% profit before adjusting stop
            "trailing_distance": 0.002,     # 0.2% trailing distance
            "max_adjustments": 3,            # Maximum stop adjustments per trade
            "adjustment_cooldown": 300,      # 5 minutes between adjustments
            "condition_change_threshold": 0.2  # 20% change in market conditions
        }
        
        logger.info("🎯 Trade Manager initialized")
    
    def evaluate_trade_quality(self, signal_data: Dict[str, Any], market_analysis: Dict[str, Any], 
                               current_price: float) -> Dict[str, Any]:
        """Comprehensive trade quality evaluation before placement"""
        try:
            # Initialize quality score
            quality_score = 0.0
            quality_factors = {}
            
            # 1. PREDICTION CONFIDENCE (25% weight)
            prediction_confidence = signal_data.get("prediction_confidence", 0.5)
            confidence_score = min(1.0, prediction_confidence / 0.9)  # Normalize to 90% max
            quality_score += confidence_score * 0.25
            quality_factors["prediction_confidence"] = {
                "score": confidence_score,
                "value": prediction_confidence,
                "weight": 0.25
            }
            
            # 2. WIN PROBABILITY (20% weight)
            win_probability = signal_data.get("entry_analysis", {}).get("win_probability", 0.5)
            win_score = min(1.0, win_probability / 0.95)  # Normalize to 95% max
            quality_score += win_score * 0.20
            quality_factors["win_probability"] = {
                "score": win_score,
                "value": win_probability,
                "weight": 0.20
            }
            
            # 3. RISK/REWARD RATIO (20% weight)
            risk_reward = signal_data.get("entry_analysis", {}).get("risk_reward_ratio", 1.0)
            rr_score = min(1.0, risk_reward / 3.0)  # Normalize to 3:1 max
            quality_score += rr_score * 0.20
            quality_factors["risk_reward"] = {
                "score": rr_score,
                "value": risk_reward,
                "weight": 0.20
            }
            
            # 4. MARKET CONDITION ALIGNMENT (15% weight)
            market_condition = market_analysis.get("market_condition", "UNKNOWN")
            prediction_mode = signal_data.get("prediction_analysis", {}).get("prediction_mode", "PREDICTIVE")
            
            alignment_score = 0.5  # Default
            if market_condition == "HIGH_VOLATILITY" and prediction_mode == "REACTIVE":
                alignment_score = 1.0  # Perfect alignment
            elif market_condition in ["LOW_VOLATILITY", "RANGING"] and prediction_mode == "PREDICTIVE":
                alignment_score = 0.9  # Very good alignment
            elif market_condition == "TRENDING" and prediction_mode == "PREDICTIVE":
                alignment_score = 0.8  # Good alignment
            
            quality_score += alignment_score * 0.15
            quality_factors["market_alignment"] = {
                "score": alignment_score,
                "market_condition": market_condition,
                "prediction_mode": prediction_mode,
                "weight": 0.15
            }
            
            # 5. VOLATILITY APPROPRIATENESS (10% weight)
            volatility_5m = signal_data.get("prediction_analysis", {}).get("volatility_5m", 0.003)
            strategy_name = signal_data.get("strategy_name", "standard")
            
            # Use centralized volatility constants for consistency
            from core.constants import VariabilityConstants
            
            volatility_score = 0.5  # Default
            if strategy_name == "high_volatility" and volatility_5m > VariabilityConstants.VOLATILITY_5M_HIGH:
                volatility_score = 1.0  # High vol strategy with high vol
            elif strategy_name == "low_volatility_range" and volatility_5m < VariabilityConstants.VOLATILITY_5M_LOW:
                volatility_score = 1.0  # Low vol strategy with low vol
            elif strategy_name == "standard" and VariabilityConstants.VOLATILITY_5M_LOW <= volatility_5m <= VariabilityConstants.VOLATILITY_5M_HIGH:
                volatility_score = 0.9  # Standard strategy with normal vol
            
            quality_score += volatility_score * 0.10
            quality_factors["volatility_match"] = {
                "score": volatility_score,
                "volatility": volatility_5m,
                "strategy": strategy_name,
                "weight": 0.10
            }
            
            # 6. TREND STRENGTH (10% weight)
            trend_5m = market_analysis.get("trend_5m", {})
            trend_1h = market_analysis.get("trend_1h", {})
            
            trend_alignment = (trend_5m.get("trend") == trend_1h.get("trend"))
            trend_strength_5m = trend_5m.get("strength", 0.5)
            trend_strength_1h = trend_1h.get("strength", 0.5)
            
            trend_score = (trend_strength_5m + trend_strength_1h) / 2
            if trend_alignment:
                trend_score *= 1.2  # Bonus for alignment
            trend_score = min(1.0, trend_score)
            
            quality_score += trend_score * 0.10
            quality_factors["trend_strength"] = {
                "score": trend_score,
                "trend_5m": trend_5m.get("trend"),
                "trend_1h": trend_1h.get("trend"),
                "alignment": trend_alignment,
                "weight": 0.10
            }
            
            # Normalize final score
            quality_score = min(1.0, max(0.0, quality_score))
            
            # Determine quality rating
            if quality_score >= self.QUALITY_THRESHOLDS["excellent"]:
                quality_rating = "EXCELLENT"
            elif quality_score >= self.QUALITY_THRESHOLDS["good"]:
                quality_rating = "GOOD"
            elif quality_score >= self.QUALITY_THRESHOLDS["acceptable"]:
                quality_rating = "ACCEPTABLE"
            else:
                quality_rating = "POOR"
            
            return {
                "quality_score": quality_score,
                "quality_rating": quality_rating,
                "quality_factors": quality_factors,
                "should_trade": quality_score >= self.QUALITY_THRESHOLDS["acceptable"],
                "confidence_level": "HIGH" if quality_score >= 0.8 else "MEDIUM" if quality_score >= 0.6 else "LOW"
            }
            
        except Exception as e:
            logger.error(f"Error evaluating trade quality: {e}")
            return {
                "quality_score": 0.0,
                "quality_rating": "ERROR",
                "should_trade": False,
                "error": str(e)
            }
    
    def should_place_trade(self, signal_data: Dict[str, Any], market_analysis: Dict[str, Any], 
                          current_price: float, open_positions: List[Dict]) -> Dict[str, Any]:
        """Decision making for trade placement"""
        try:
            # 1. Basic signal validation
            if not signal_data.get("should_trade", False):
                return {"should_place": False, "reason": "No valid trading signal"}
            
            # 2. Evaluate trade quality
            quality_eval = self.evaluate_trade_quality(signal_data, market_analysis, current_price)
            
            if not quality_eval["should_trade"]:
                return {
                    "should_place": False, 
                    "reason": f"Trade quality too low: {quality_eval['quality_rating']} ({quality_eval['quality_score']:.2f})",
                    "quality_evaluation": quality_eval
                }
            
            # 3. Check position limits
            max_positions = self.strategy_config.get("max_positions", 3)
            if len(open_positions) >= max_positions:
                return {"should_place": False, "reason": f"Maximum positions reached ({max_positions})"}
            
            # 4. Check for conflicting positions
            side = signal_data.get("side")
            conflicting_positions = [pos for pos in open_positions if pos.get("side") != side]
            
            if conflicting_positions:
                return {
                    "should_place": False, 
                    "reason": f"Conflicting position exists ({len(conflicting_positions)} opposite side positions)"
                }
            
            # 5. Check minimum time between trades
            current_time = time.time()
            min_interval = self.strategy_config.get("min_interval", 300)
            
            if open_positions:
                last_trade_time = max([pos.get("timestamp", 0) for pos in open_positions])
                if current_time - last_trade_time < min_interval:
                    return {
                        "should_place": False, 
                        "reason": f"Too soon since last trade (need {min_interval}s)"
                    }
            
            # 6. Additional quality gates for excellent trades
            if quality_eval["quality_rating"] == "EXCELLENT":
                logger.info("🌟 EXCELLENT trade opportunity detected!")
            elif quality_eval["quality_rating"] == "GOOD":
                logger.info("✅ GOOD trade opportunity detected")
            else:
                logger.info("⚠️ ACCEPTABLE trade opportunity (proceed with caution)")
            
            return {
                "should_place": True,
                "quality_evaluation": quality_eval,
                "recommendation": f"Place {quality_eval['quality_rating']} quality trade"
            }
            
        except Exception as e:
            logger.error(f"Error in trade placement decision: {e}")
            return {"should_place": False, "reason": f"Decision error: {str(e)}"}
    
    def calculate_dynamic_stops(self, position: Dict[str, Any], current_price: float, 
                               current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate dynamic stop loss adjustments based on changing conditions"""
        try:
            original_stop = position.get("stop_loss", 0)
            current_stop = position.get("current_stop_loss", original_stop)
            entry_price = position.get("entry_price", 0)
            side = position.get("side")
            
            # Calculate current P&L
            if side == "BUY":
                current_pnl_pct = (current_price - entry_price) / entry_price
                is_profitable = current_pnl_pct > 0
            else:  # SELL
                current_pnl_pct = (entry_price - current_price) / entry_price
                is_profitable = current_pnl_pct > 0
            
            # Check if we should consider stop adjustment
            min_profit = self.STOP_ADJUSTMENT_CONFIG["min_profit_threshold"]
            if not is_profitable or abs(current_pnl_pct) < min_profit:
                return {
                    "should_adjust": False,
                    "reason": f"Insufficient profit for adjustment (need {min_profit*100:.1f}%, have {current_pnl_pct*100:.1f}%)",
                    "current_stop": current_stop
                }
            
            # Check adjustment cooldown
            last_adjustment = position.get("last_stop_adjustment", 0)
            cooldown = self.STOP_ADJUSTMENT_CONFIG["adjustment_cooldown"]
            if time.time() - last_adjustment < cooldown:
                return {
                    "should_adjust": False,
                    "reason": f"Adjustment cooldown active ({cooldown}s)",
                    "current_stop": current_stop
                }
            
            # Check maximum adjustments
            adjustment_count = position.get("stop_adjustment_count", 0)
            max_adjustments = self.STOP_ADJUSTMENT_CONFIG["max_adjustments"]
            if adjustment_count >= max_adjustments:
                return {
                    "should_adjust": False,
                    "reason": f"Maximum adjustments reached ({max_adjustments})",
                    "current_stop": current_stop
                }
            
            # Analyze market condition changes
            original_analysis = position.get("original_market_analysis", {})
            condition_change = self._analyze_condition_change(original_analysis, current_analysis)
            
            # Determine if conditions favor adjustment
            if not condition_change["favorable"]:
                return {
                    "should_adjust": False,
                    "reason": f"Market conditions not favorable for adjustment: {condition_change['reason']}",
                    "current_stop": current_stop,
                    "condition_analysis": condition_change
                }
            
            # Calculate new stop loss
            trailing_distance = self.STOP_ADJUSTMENT_CONFIG["trailing_distance"]
            
            if side == "BUY":
                # For long positions, move stop up (but never down)
                new_stop = current_price - (current_price * trailing_distance)
                new_stop = max(new_stop, current_stop)  # Never move stop down
                
                # Additional protection: don't move stop too close to entry
                min_stop = entry_price * (1 - self.strategy_config.get("stop_loss", 0.005) * 0.5)
                new_stop = max(new_stop, min_stop)
                
            else:  # SELL
                # For short positions, move stop down (but never up)
                new_stop = current_price + (current_price * trailing_distance)
                new_stop = min(new_stop, current_stop)  # Never move stop up
                
                # Additional protection: don't move stop too close to entry
                max_stop = entry_price * (1 + self.strategy_config.get("stop_loss", 0.005) * 0.5)
                new_stop = min(new_stop, max_stop)
            
            # Check if adjustment is meaningful
            stop_change_pct = abs(new_stop - current_stop) / current_stop
            if stop_change_pct < 0.001:  # Less than 0.1% change
                return {
                    "should_adjust": False,
                    "reason": "Stop adjustment too small to be meaningful",
                    "current_stop": current_stop
                }
            
            return {
                "should_adjust": True,
                "new_stop": new_stop,
                "current_stop": current_stop,
                "stop_improvement": abs(new_stop - original_stop) / original_stop,
                "condition_analysis": condition_change,
                "adjustment_reason": condition_change["reason"],
                "current_pnl": current_pnl_pct
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic stops: {e}")
            return {
                "should_adjust": False,
                "reason": f"Calculation error: {str(e)}",
                "current_stop": position.get("current_stop_loss", position.get("stop_loss", 0))
            }
    
    def _analyze_condition_change(self, original_analysis: Dict[str, Any], 
                                 current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze if market conditions have changed favorably for the trade"""
        try:
            change_threshold = self.STOP_ADJUSTMENT_CONFIG["condition_change_threshold"]
            favorable_changes = []
            unfavorable_changes = []
            
            # 1. Trend strength analysis
            orig_trend_5m = original_analysis.get("trend_5m", {})
            curr_trend_5m = current_analysis.get("trend_5m", {})
            
            orig_strength = orig_trend_5m.get("strength", 0.5)
            curr_strength = curr_trend_5m.get("strength", 0.5)
            
            strength_change = curr_strength - orig_strength
            if abs(strength_change) > change_threshold:
                if strength_change > 0:
                    favorable_changes.append(f"Trend strength improved (+{strength_change:.2f})")
                else:
                    unfavorable_changes.append(f"Trend strength weakened ({strength_change:.2f})")
            
            # 2. Volatility analysis
            orig_volatility = original_analysis.get("volatility_5m", 0.003)
            curr_volatility = current_analysis.get("volatility_5m", 0.003)
            
            volatility_change = (curr_volatility - orig_volatility) / orig_volatility
            if abs(volatility_change) > change_threshold:
                # For reactive strategies, higher volatility is good
                # For predictive strategies, stable volatility is good
                strategy_name = original_analysis.get("strategy_name", "standard")
                
                if strategy_name == "high_volatility":
                    if volatility_change > 0:
                        favorable_changes.append(f"Volatility increased for reactive strategy (+{volatility_change*100:.1f}%)")
                    else:
                        unfavorable_changes.append(f"Volatility decreased for reactive strategy ({volatility_change*100:.1f}%)")
                else:
                    if abs(volatility_change) < change_threshold * 0.5:  # More stable
                        favorable_changes.append(f"Volatility stabilized for predictive strategy")
                    else:
                        unfavorable_changes.append(f"Volatility became unstable ({volatility_change*100:.1f}%)")
            
            # 3. Support/Resistance proximity
            orig_support = original_analysis.get("support_resistance_5m", {}).get("support", 0)
            curr_support = current_analysis.get("support_resistance_5m", {}).get("support", 0)
            orig_resistance = original_analysis.get("support_resistance_5m", {}).get("resistance", 0)
            curr_resistance = current_analysis.get("support_resistance_5m", {}).get("resistance", 0)
            
            if orig_support > 0 and curr_support > 0:
                support_change = (curr_support - orig_support) / orig_support
                if abs(support_change) > change_threshold:
                    if support_change > 0:
                        favorable_changes.append(f"Support level strengthened (+{support_change*100:.1f}%)")
                    else:
                        unfavorable_changes.append(f"Support level weakened ({support_change*100:.1f}%)")
            
            # 4. Overall market condition
            orig_condition = original_analysis.get("market_condition", "UNKNOWN")
            curr_condition = current_analysis.get("market_condition", "UNKNOWN")
            
            if orig_condition != curr_condition:
                favorable_changes.append(f"Market condition changed: {orig_condition} → {curr_condition}")
            
            # Determine overall favorability
            favorable_count = len(favorable_changes)
            unfavorable_count = len(unfavorable_changes)
            
            if favorable_count > unfavorable_count:
                return {
                    "favorable": True,
                    "reason": f"Conditions improved: {'; '.join(favorable_changes)}",
                    "favorable_changes": favorable_changes,
                    "unfavorable_changes": unfavorable_changes,
                    "confidence": min(1.0, favorable_count / max(1, unfavorable_count))
                }
            elif favorable_count == unfavorable_count and favorable_count > 0:
                return {
                    "favorable": True,
                    "reason": f"Mixed conditions with slight improvement",
                    "favorable_changes": favorable_changes,
                    "unfavorable_changes": unfavorable_changes,
                    "confidence": 0.6
                }
            else:
                return {
                    "favorable": False,
                    "reason": f"Conditions deteriorated: {'; '.join(unfavorable_changes) if unfavorable_changes else 'No significant changes'}",
                    "favorable_changes": favorable_changes,
                    "unfavorable_changes": unfavorable_changes,
                    "confidence": 0.3
                }
                
        except Exception as e:
            logger.error(f"Error analyzing condition change: {e}")
            return {
                "favorable": False,
                "reason": f"Analysis error: {str(e)}",
                "favorable_changes": [],
                "unfavorable_changes": [],
                "confidence": 0.0
            }
    
    def update_position_with_adjustment(self, position: Dict[str, Any], 
                                       adjustment_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update position with new stop loss adjustment"""
        try:
            if not adjustment_result.get("should_adjust", False):
                return position
            
            # Update position with new stop
            updated_position = position.copy()
            updated_position["current_stop_loss"] = adjustment_result["new_stop"]
            updated_position["last_stop_adjustment"] = time.time()
            updated_position["stop_adjustment_count"] = position.get("stop_adjustment_count", 0) + 1
            
            # Add adjustment history
            if "stop_adjustments" not in updated_position:
                updated_position["stop_adjustments"] = []
            
            adjustment_record = {
                "timestamp": time.time(),
                "old_stop": adjustment_result["current_stop"],
                "new_stop": adjustment_result["new_stop"],
                "reason": adjustment_result["adjustment_reason"],
                "current_pnl": adjustment_result["current_pnl"],
                "improvement": adjustment_result["stop_improvement"]
            }
            
            updated_position["stop_adjustments"].append(adjustment_record)
            
            logger.info(f"🔧 Stop loss adjusted: ${adjustment_result['current_stop']:,.2f} → ${adjustment_result['new_stop']:,.2f}")
            logger.info(f"   Reason: {adjustment_result['adjustment_reason']}")
            logger.info(f"   Current P&L: {adjustment_result['current_pnl']*100:.2f}%")
            
            return updated_position
            
        except Exception as e:
            logger.error(f"Error updating position with adjustment: {e}")
            return position
    
    def calculate_risk_reward_ratio(self, entry_price: float, target_price: float, stop_price: float) -> float:
        """Calculate risk/reward ratio for a trade"""
        try:
            if entry_price <= 0 or target_price <= 0 or stop_price <= 0:
                return 1.0
            
            # Calculate potential profit and loss
            potential_profit = abs(target_price - entry_price)
            potential_loss = abs(entry_price - stop_price)
            
            if potential_loss == 0:
                return 1.0
            
            return potential_profit / potential_loss
            
        except Exception as e:
            logger.error(f"Error calculating risk/reward ratio: {e}")
            return 1.0
    
    def should_scale_in_position(self, position: Dict[str, Any], current_price: float, 
                                current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if we should scale into an existing position"""
        try:
            entry_price = position.get("entry_price", 0)
            side = position.get("side")
            current_pnl_pct = position.get("current_pnl_pct", 0)
            
            # Only consider scaling in if position is profitable
            if current_pnl_pct <= 0:
                return {"should_scale": False, "reason": "Position not profitable"}
            
            # Check if we have room for more positions
            max_positions = self.strategy_config.get("max_positions", 3)
            if len(self.get_open_positions()) >= max_positions:
                return {"should_scale": False, "reason": "Maximum positions reached"}
            
            # Analyze if conditions have improved since entry
            original_analysis = position.get("original_market_analysis", {})
            condition_improvement = self._analyze_condition_change(original_analysis, current_analysis)
            
            if not condition_improvement["favorable"]:
                return {"should_scale": False, "reason": "Market conditions not favorable for scaling"}
            
            # Calculate optimal scaling entry
            if side == "BUY":
                # For long positions, scale in on pullbacks
                pullback_threshold = entry_price * 0.995  # 0.5% pullback
                if current_price <= pullback_threshold:
                    scale_size = position.get("size", 0) * 0.5  # 50% of original size
                    return {
                        "should_scale": True,
                        "scale_size": scale_size,
                        "scale_price": current_price,
                        "reason": f"Profitable long position pullback - scaling in at ${current_price:,.2f}"
                    }
            else:  # SELL
                # For short positions, scale in on rallies
                rally_threshold = entry_price * 1.005  # 0.5% rally
                if current_price >= rally_threshold:
                    scale_size = position.get("size", 0) * 0.5  # 50% of original size
                    return {
                        "should_scale": True,
                        "scale_size": scale_size,
                        "scale_price": current_price,
                        "reason": f"Profitable short position rally - scaling in at ${current_price:,.2f}"
                    }
            
            return {"should_scale": False, "reason": "No scaling opportunity"}
            
        except Exception as e:
            logger.error(f"Error in scale-in analysis: {e}")
            return {"should_scale": False, "reason": f"Analysis error: {str(e)}"}
    
    def should_partial_close(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Determine if we should partially close a position to lock in profits"""
        try:
            entry_price = position.get("entry_price", 0)
            side = position.get("side")
            size = position.get("size", 0)
            
            # Calculate current P&L
            if side == "BUY":
                current_pnl_pct = (current_price - entry_price) / entry_price
            else:
                current_pnl_pct = (entry_price - current_price) / entry_price
            
            # Partial close thresholds
            partial_close_thresholds = {
                "first_target": 0.01,   # 1% profit - close 25%
                "second_target": 0.02,  # 2% profit - close 50%
                "third_target": 0.03    # 3% profit - close 75%
            }
            
            for target_name, threshold in partial_close_thresholds.items():
                if current_pnl_pct >= threshold:
                    # Check if we've already closed at this level
                    closed_levels = position.get("partial_closes", [])
                    if target_name not in [close.get("level") for close in closed_levels]:
                        
                        # Determine close percentage based on target
                        if target_name == "first_target":
                            close_pct = 0.25
                        elif target_name == "second_target":
                            close_pct = 0.50
                        else:  # third_target
                            close_pct = 0.75
                        
                        close_size = size * close_pct
                        
                        return {
                            "should_partial_close": True,
                            "close_size": close_size,
                            "close_pct": close_pct,
                            "target_level": target_name,
                            "current_pnl": current_pnl_pct,
                            "reason": f"Partial close at {target_name} ({current_pnl_pct*100:.1f}% profit)"
                        }
            
            return {"should_partial_close": False, "reason": "No partial close targets reached"}
            
        except Exception as e:
            logger.error(f"Error in partial close analysis: {e}")
            return {"should_partial_close": False, "reason": f"Analysis error: {str(e)}"}
    
    def calculate_position_heat(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Calculate position 'heat' - how close we are to stop loss"""
        try:
            entry_price = position.get("entry_price", 0)
            current_stop = position.get("current_stop_loss", position.get("stop_loss", 0))
            side = position.get("side")
            
            if entry_price <= 0 or current_stop <= 0:
                return {"heat_level": "UNKNOWN", "heat_pct": 0.0}
            
            # Calculate distance to stop loss
            if side == "BUY":
                distance_to_stop = (current_price - current_stop) / current_price
                max_distance = (entry_price - current_stop) / entry_price
            else:  # SELL
                distance_to_stop = (current_stop - current_price) / current_price
                max_distance = (current_stop - entry_price) / entry_price
            
            if max_distance <= 0:
                return {"heat_level": "UNKNOWN", "heat_pct": 0.0}
            
            # Calculate heat percentage (0% = far from stop, 100% = at stop)
            heat_pct = max(0.0, min(1.0, 1.0 - (distance_to_stop / max_distance)))
            
            # Determine heat level
            if heat_pct >= 0.9:
                heat_level = "CRITICAL"
            elif heat_pct >= 0.7:
                heat_level = "HIGH"
            elif heat_pct >= 0.5:
                heat_level = "MEDIUM"
            elif heat_pct >= 0.3:
                heat_level = "LOW"
            else:
                heat_level = "SAFE"
            
            return {
                "heat_level": heat_level,
                "heat_pct": heat_pct,
                "distance_to_stop": distance_to_stop,
                "max_distance": max_distance
            }
            
        except Exception as e:
            logger.error(f"Error calculating position heat: {e}")
            return {"heat_level": "ERROR", "heat_pct": 0.0}
    
    def should_emergency_close(self, position: Dict[str, Any], current_price: float, 
                              current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if we should emergency close a position due to adverse conditions"""
        try:
            # Check position heat
            heat_analysis = self.calculate_position_heat(position, current_price)
            
            # Emergency close if heat is critical and conditions are deteriorating
            if heat_analysis["heat_level"] == "CRITICAL":
                original_analysis = position.get("original_market_analysis", {})
                condition_change = self._analyze_condition_change(original_analysis, current_analysis)
                
                if not condition_change["favorable"] and condition_change["confidence"] > 0.7:
                    return {
                        "should_emergency_close": True,
                        "reason": f"Critical heat ({heat_analysis['heat_pct']*100:.1f}%) + deteriorating conditions",
                        "heat_analysis": heat_analysis,
                        "condition_analysis": condition_change
                    }
            
            # Check for extreme market conditions
            market_condition = current_analysis.get("market_condition", "UNKNOWN")
            if market_condition in ["EXTREME_VOLATILITY_AVOID", "MARKET_CRASH"]:
                return {
                    "should_emergency_close": True,
                    "reason": f"Extreme market conditions: {market_condition}",
                    "market_condition": market_condition
                }
            
            # Check for prolonged losing position
            entry_time = position.get("entry_time", 0)
            position_age = time.time() - entry_time
            max_hold_time = self.strategy_config.get("max_hold_time", 3600)  # 1 hour default
            
            if position_age > max_hold_time:
                current_pnl_pct = position.get("current_pnl_pct", 0)
                if current_pnl_pct < -0.01:  # Losing more than 1%
                    return {
                        "should_emergency_close": True,
                        "reason": f"Prolonged losing position ({position_age/60:.1f} minutes, {current_pnl_pct*100:.1f}% loss)",
                        "position_age": position_age,
                        "current_pnl": current_pnl_pct
                    }
            
            return {"should_emergency_close": False, "reason": "No emergency close conditions met"}
            
        except Exception as e:
            logger.error(f"Error in emergency close analysis: {e}")
            return {"should_emergency_close": False, "reason": f"Analysis error: {str(e)}"}
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of open positions (to be implemented by main bot)"""
        # This will be overridden by the main bot to provide actual positions
        return []
    
    def calculate_portfolio_risk(self, positions: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics"""
        try:
            if not positions:
                return {
                    "total_risk": 0.0,
                    "max_drawdown": 0.0,
                    "correlation_risk": 0.0,
                    "concentration_risk": 0.0,
                    "risk_level": "LOW"
                }
            
            total_exposure = 0.0
            total_pnl = 0.0
            position_sizes = []
            sides = []
            
            for position in positions:
                size = position.get("size", 0)
                entry_price = position.get("entry_price", 0)
                side = position.get("side")
                
                if side == "BUY":
                    pnl = (current_price - entry_price) / entry_price
                else:
                    pnl = (entry_price - current_price) / entry_price
                
                exposure = size * entry_price
                total_exposure += exposure
                total_pnl += pnl * exposure
                position_sizes.append(exposure)
                sides.append(side)
            
            # Calculate risk metrics
            avg_position_size = total_exposure / len(positions) if positions else 0
            concentration_risk = max(position_sizes) / total_exposure if total_exposure > 0 else 0
            
            # Calculate correlation risk (all positions same direction = high risk)
            unique_sides = set(sides)
            correlation_risk = 1.0 if len(unique_sides) == 1 else 0.5
            
            # Calculate maximum potential loss
            max_loss = 0.0
            for position in positions:
                size = position.get("size", 0)
                entry_price = position.get("entry_price", 0)
                stop_price = position.get("current_stop_loss", position.get("stop_loss", 0))
                
                if stop_price > 0:
                    if position.get("side") == "BUY":
                        potential_loss = (entry_price - stop_price) / entry_price
                    else:
                        potential_loss = (stop_price - entry_price) / entry_price
                    
                    max_loss += potential_loss * size * entry_price
            
            total_risk = max_loss / total_exposure if total_exposure > 0 else 0
            
            # Determine risk level
            if total_risk > 0.05:  # 5% max loss
                risk_level = "HIGH"
            elif total_risk > 0.03:  # 3% max loss
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                "total_risk": total_risk,
                "max_drawdown": max_loss,
                "correlation_risk": correlation_risk,
                "concentration_risk": concentration_risk,
                "total_exposure": total_exposure,
                "total_pnl": total_pnl,
                "avg_position_size": avg_position_size,
                "risk_level": risk_level
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {
                "total_risk": 0.0,
                "max_drawdown": 0.0,
                "correlation_risk": 0.0,
                "concentration_risk": 0.0,
                "risk_level": "ERROR"
            }
