#!/usr/bin/env python3
"""
Intelligent Win-Back Engine
Places smarter, more aggressive trades after losses to recover quickly
Prevents emotional revenge trading while maximizing recovery opportunities
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import deque

class WinBackEngine:
    """Intelligent loss recovery system with disciplined aggression"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        
        # Win-back configuration
        self.WIN_BACK_CONFIG = {
            "trigger_loss_threshold": 0.005,    # 0.5% - only trigger on real losses
            "max_recovery_attempts": 2,         # Max 2 recovery attempts per loss
            "recovery_timeout": 1800,           # 30 minutes - no revenge after this
            "min_confidence_boost": 0.15,       # Require +15% higher confidence
            "position_multipliers": {
                "first_attempt": 1.8,           # 1.8x normal position size
                "second_attempt": 1.5,          # 1.5x normal position size (more conservative)
                "max_position": 0.50            # Never exceed 50% of balance
            },
            "required_edge_boost": 0.10,        # Need +10% better setup than normal
            "cooldown_between_attempts": 300    # 5 minutes between recovery attempts
        }
        
        # Loss tracking
        self.recent_losses = deque(maxlen=10)  # Track last 10 losses
        self.recovery_attempts = {}            # Track recovery attempts per loss
        self.win_back_active = False
        self.last_loss_time = 0
        self.total_recovery_pnl = 0.0
        
        # Performance tracking
        self.win_back_stats = {
            "attempts": 0,
            "successes": 0,
            "failures": 0, 
            "total_recovered": 0.0,
            "biggest_recovery": 0.0,
            "success_rate": 0.0
        }
        
        logger.info("🔥 Intelligent Win-Back Engine initialized - Smart revenge trading")
    
    def register_loss(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a loss and determine if win-back is appropriate"""
        
        loss_amount = abs(trade_data.get("net_profit_loss", 0))
        loss_pct = abs(trade_data.get("profit_loss_pct", 0))
        trade_id = trade_data.get("trade_id", "unknown")
        
        # Only register significant losses
        if loss_pct < self.WIN_BACK_CONFIG["trigger_loss_threshold"]:
            logger.info(f"💸 Minor loss registered: {loss_pct*100:.2f}% - No win-back needed")
            return {"should_attempt_winback": False, "reason": "Loss too small"}
        
        # Create loss record
        loss_record = {
            "trade_id": trade_id,
            "loss_amount": loss_amount,
            "loss_pct": loss_pct,
            "timestamp": time.time(),
            "balance_after_loss": trade_data.get("balance_after", 0),
            "recovery_attempts": 0,
            "recovered": False
        }
        
        self.recent_losses.append(loss_record)
        self.last_loss_time = time.time()
        
        logger.warning(f"💸 SIGNIFICANT LOSS REGISTERED: {loss_pct*100:.2f}% (${loss_amount:.2f})")
        logger.warning(f"   Trade ID: {trade_id}")
        logger.warning(f"   Evaluating win-back opportunity...")
        
        # Evaluate if win-back is appropriate
        win_back_analysis = self._evaluate_win_back_opportunity(loss_record)
        
        if win_back_analysis["should_attempt_winback"]:
            self.win_back_active = True
            self.recovery_attempts[trade_id] = {
                "loss_record": loss_record,
                "attempts_made": 0,
                "start_time": time.time(),
                "target_recovery": loss_amount * 1.2  # Aim to recover 120% of loss
            }
            
            logger.success(f"🎯 WIN-BACK ACTIVATED: Targeting ${loss_amount * 1.2:.2f} recovery")
            logger.info(f"   Strategy: {win_back_analysis['strategy']}")
            logger.info(f"   Position multiplier: {win_back_analysis['position_multiplier']:.1f}x")
            logger.info(f"   Required confidence: {win_back_analysis['min_confidence']:.1%}")
        
        return win_back_analysis
    
    def _evaluate_win_back_opportunity(self, loss_record: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if conditions are right for win-back attempt"""
        
        loss_pct = loss_record["loss_pct"]
        loss_time = loss_record["timestamp"]
        current_time = time.time()
        
        # Check timeout
        if current_time - loss_time > self.WIN_BACK_CONFIG["recovery_timeout"]:
            return {
                "should_attempt_winback": False,
                "reason": "Recovery timeout exceeded (30 minutes)"
            }
        
        # Check recent loss pattern
        recent_losses_count = len([l for l in self.recent_losses 
                                 if current_time - l["timestamp"] < 3600])  # Last hour
        
        if recent_losses_count >= 3:
            return {
                "should_attempt_winback": False,
                "reason": "Too many recent losses - entering defensive mode"
            }
        
        # Check if we're in a losing streak
        last_3_trades = list(self.recent_losses)[-3:]
        if len(last_3_trades) == 3:
            total_recent_loss = sum(l["loss_pct"] for l in last_3_trades)
            if total_recent_loss > 0.02:  # 2% total loss in recent trades
                return {
                    "should_attempt_winback": False,
                    "reason": "Losing streak detected - need defensive strategy"
                }
        
        # Determine recovery strategy based on loss magnitude
        if loss_pct > 0.015:  # >1.5% loss
            strategy = "conservative_recovery"
            position_multiplier = 1.3
            min_confidence = 0.80
        elif loss_pct > 0.010:  # >1.0% loss  
            strategy = "moderate_recovery"
            position_multiplier = 1.6
            min_confidence = 0.75
        else:  # 0.5-1.0% loss
            strategy = "aggressive_recovery"
            position_multiplier = 1.8
            min_confidence = 0.70
        
        return {
            "should_attempt_winback": True,
            "strategy": strategy,
            "position_multiplier": position_multiplier,
            "min_confidence": min_confidence,
            "target_recovery": loss_record["loss_amount"] * 1.2,
            "time_limit": self.WIN_BACK_CONFIG["recovery_timeout"]
        }
    
    def enhance_signal_for_winback(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Enhance a trading signal for win-back purposes"""
        
        if not self.win_back_active:
            return signal  # No enhancement needed
        
        # Get active recovery attempt
        active_recovery = None
        for trade_id, recovery_data in self.recovery_attempts.items():
            if recovery_data["attempts_made"] < self.WIN_BACK_CONFIG["max_recovery_attempts"]:
                active_recovery = recovery_data
                break
        
        if not active_recovery:
            self.win_back_active = False
            return signal
        
        # Check if signal meets win-back requirements
        current_confidence = signal.get("confidence", 0)
        required_confidence = self._get_required_winback_confidence(active_recovery)
        
        if current_confidence < required_confidence:
            logger.info(f"⏳ Win-back waiting: Need {required_confidence:.1%} confidence, have {current_confidence:.1%}")
            return signal  # Don't enhance - not good enough
        
        # Enhance the signal for win-back
        enhanced_signal = signal.copy()
        
        # Calculate enhanced position size
        original_position = signal.get("position_size", 0.10)
        loss_data = active_recovery["loss_record"]
        
        # Determine multiplier based on loss magnitude and attempt number
        attempt_number = active_recovery["attempts_made"] + 1
        base_multiplier = self._get_position_multiplier(loss_data, attempt_number)
        
        # Confidence bonus multiplier (higher confidence = more aggressive)
        confidence_bonus = (current_confidence - required_confidence) / 0.2  # Scale over 20%
        confidence_multiplier = 1.0 + (confidence_bonus * 0.3)  # Up to 30% bonus
        
        total_multiplier = base_multiplier * confidence_multiplier
        enhanced_position = original_position * total_multiplier
        
        # Apply absolute limits
        max_position = self.WIN_BACK_CONFIG["position_multipliers"]["max_position"]
        enhanced_position = min(enhanced_position, max_position)
        
        # Update signal
        enhanced_signal["position_size"] = enhanced_position
        enhanced_signal["is_winback_trade"] = True
        enhanced_signal["winback_data"] = {
            "original_loss": loss_data["loss_amount"],
            "target_recovery": active_recovery["target_recovery"],
            "attempt_number": attempt_number,
            "position_multiplier": total_multiplier,
            "required_confidence": required_confidence,
            "strategy": self._get_recovery_strategy(loss_data)
        }
        
        # Enhance stop-loss for win-back (tighter for aggressive trades)
        if "stop_loss" in enhanced_signal:
            # Tighter stop for win-back trades (reduce risk despite larger position)
            stop_adjustment = 0.8  # 20% tighter stop
            if enhanced_signal["side"] == "BUY":
                enhanced_signal["stop_loss"] = current_price * (1 - (current_price - enhanced_signal["stop_loss"]) / current_price * stop_adjustment)
            else:
                enhanced_signal["stop_loss"] = current_price * (1 + (enhanced_signal["stop_loss"] - current_price) / current_price * stop_adjustment)
        
        # Update attempt counter
        active_recovery["attempts_made"] += 1
        
        logger.success(f"🔥 WIN-BACK SIGNAL ENHANCED!")
        logger.info(f"   Original Position: {original_position*100:.1f}%")
        logger.info(f"   Enhanced Position: {enhanced_position*100:.1f}%")
        logger.info(f"   Multiplier: {total_multiplier:.1f}x")
        logger.info(f"   Target Recovery: ${active_recovery['target_recovery']:.2f}")
        logger.info(f"   Attempt: {attempt_number}/{self.WIN_BACK_CONFIG['max_recovery_attempts']}")
        
        return enhanced_signal
    
    def register_winback_result(self, trade_result: Dict[str, Any]):
        """Register the result of a win-back trade"""
        
        if not trade_result.get("is_winback_trade", False):
            return  # Not a win-back trade
        
        trade_id = trade_result.get("trade_id", "unknown")
        net_pnl = trade_result.get("net_profit_loss", 0)
        was_profitable = net_pnl > 0
        
        # Update win-back stats
        self.win_back_stats["attempts"] += 1
        
        if was_profitable:
            self.win_back_stats["successes"] += 1
            self.win_back_stats["total_recovered"] += net_pnl
            self.win_back_stats["biggest_recovery"] = max(self.win_back_stats["biggest_recovery"], net_pnl)
            
            # Mark original loss as recovered
            winback_data = trade_result.get("winback_data", {})
            original_loss = winback_data.get("original_loss", 0)
            
            if net_pnl >= original_loss:
                logger.success(f"🎯 FULL RECOVERY ACHIEVED: ${net_pnl:.2f} recovered ${original_loss:.2f} loss")
                self.win_back_active = False  # Deactivate win-back mode
                self._cleanup_recovery_attempts()
            else:
                logger.info(f"📈 PARTIAL RECOVERY: ${net_pnl:.2f} of ${original_loss:.2f} target")
        else:
            self.win_back_stats["failures"] += 1
            logger.warning(f"💸 WIN-BACK FAILED: Additional ${abs(net_pnl):.2f} loss")
            
            # Check if we should continue or stop
            attempt_number = trade_result.get("winback_data", {}).get("attempt_number", 1)
            if attempt_number >= self.WIN_BACK_CONFIG["max_recovery_attempts"]:
                logger.warning("🛑 MAX RECOVERY ATTEMPTS REACHED - Entering defensive mode")
                self.win_back_active = False
                self._cleanup_recovery_attempts()
        
        # Update success rate
        if self.win_back_stats["attempts"] > 0:
            self.win_back_stats["success_rate"] = self.win_back_stats["successes"] / self.win_back_stats["attempts"]
        
        logger.info(f"📊 Win-Back Stats: {self.win_back_stats['successes']}/{self.win_back_stats['attempts']} ({self.win_back_stats['success_rate']*100:.1f}% success)")
    
    def _get_required_winback_confidence(self, recovery_data: Dict[str, Any]) -> float:
        """Get required confidence for win-back trade based on loss magnitude"""
        
        loss_pct = recovery_data["loss_record"]["loss_pct"]
        attempt_number = recovery_data["attempts_made"] + 1
        
        # Base requirement increases with loss magnitude
        if loss_pct > 0.015:      # >1.5% loss
            base_requirement = 0.85   # Very high confidence needed
        elif loss_pct > 0.010:    # >1.0% loss
            base_requirement = 0.80   # High confidence needed
        else:                     # 0.5-1.0% loss
            base_requirement = 0.75   # Moderate-high confidence needed
        
        # Increase requirement for subsequent attempts
        attempt_penalty = (attempt_number - 1) * 0.05  # +5% per additional attempt
        
        final_requirement = min(0.95, base_requirement + attempt_penalty)
        return final_requirement
    
    def _get_position_multiplier(self, loss_data: Dict[str, Any], attempt_number: int) -> float:
        """Calculate position size multiplier for recovery attempt"""
        
        if attempt_number == 1:
            base_multiplier = self.WIN_BACK_CONFIG["position_multipliers"]["first_attempt"]
        else:
            base_multiplier = self.WIN_BACK_CONFIG["position_multipliers"]["second_attempt"]
        
        # Adjust based on loss magnitude
        loss_pct = loss_data["loss_pct"]
        
        if loss_pct > 0.020:      # >2% loss - be more aggressive to recover
            magnitude_multiplier = 1.2
        elif loss_pct > 0.015:    # >1.5% loss
            magnitude_multiplier = 1.1  
        elif loss_pct > 0.010:    # >1% loss
            magnitude_multiplier = 1.0
        else:                     # 0.5-1% loss
            magnitude_multiplier = 0.9  # Less aggressive for smaller losses
        
        return base_multiplier * magnitude_multiplier
    
    def _get_recovery_strategy(self, loss_data: Dict[str, Any]) -> str:
        """Determine recovery strategy based on loss characteristics"""
        
        loss_pct = loss_data["loss_pct"]
        
        if loss_pct > 0.020:
            return "HIGH_AGGRESSION"     # Big loss = aggressive recovery
        elif loss_pct > 0.015:
            return "MODERATE_AGGRESSION" # Medium loss = moderate recovery
        elif loss_pct > 0.010:
            return "CONTROLLED_RECOVERY" # Small loss = controlled recovery
        else:
            return "CONSERVATIVE_RECOVERY" # Tiny loss = conservative
    
    def should_enter_defensive_mode(self) -> Dict[str, Any]:
        """Check if bot should enter defensive mode due to multiple losses"""
        
        current_time = time.time()
        
        # Count recent losses (last 2 hours)
        recent_losses = [l for l in self.recent_losses 
                        if current_time - l["timestamp"] < 7200]
        
        # Count failed recovery attempts
        failed_recoveries = sum(1 for l in recent_losses if l.get("recovery_failed", False))
        
        # Calculate total recent loss
        total_recent_loss_pct = sum(l["loss_pct"] for l in recent_losses)
        
        # Defensive mode triggers
        should_defend = False
        reason = ""
        
        if len(recent_losses) >= 4:
            should_defend = True
            reason = f"Too many losses: {len(recent_losses)} in 2 hours"
        elif failed_recoveries >= 2:
            should_defend = True
            reason = f"Multiple failed recoveries: {failed_recoveries}"
        elif total_recent_loss_pct > 0.05:  # >5% total loss
            should_defend = True
            reason = f"High cumulative loss: {total_recent_loss_pct*100:.1f}%"
        
        if should_defend:
            logger.warning(f"🛡️ ENTERING DEFENSIVE MODE: {reason}")
            self.win_back_active = False
            self._cleanup_recovery_attempts()
        
        return {
            "should_defend": should_defend,
            "reason": reason,
            "recent_losses": len(recent_losses),
            "failed_recoveries": failed_recoveries,
            "total_loss_pct": total_recent_loss_pct,
            "defensive_duration": 3600  # 1 hour defensive mode
        }
    
    def get_winback_signal_requirements(self) -> Dict[str, Any]:
        """Get current requirements for win-back signals"""
        
        if not self.win_back_active:
            return {"active": False}
        
        # Find active recovery
        active_recovery = None
        for trade_id, recovery_data in self.recovery_attempts.items():
            if recovery_data["attempts_made"] < self.WIN_BACK_CONFIG["max_recovery_attempts"]:
                current_time = time.time()
                if current_time - recovery_data["start_time"] < self.WIN_BACK_CONFIG["recovery_timeout"]:
                    active_recovery = recovery_data
                    break
        
        if not active_recovery:
            self.win_back_active = False
            return {"active": False}
        
        loss_data = active_recovery["loss_record"]
        attempt_number = active_recovery["attempts_made"] + 1
        
        return {
            "active": True,
            "target_recovery": active_recovery["target_recovery"],
            "required_confidence": self._get_required_winback_confidence(active_recovery),
            "position_multiplier": self._get_position_multiplier(loss_data, attempt_number),
            "max_position": self.WIN_BACK_CONFIG["position_multipliers"]["max_position"],
            "attempt_number": attempt_number,
            "time_remaining": self.WIN_BACK_CONFIG["recovery_timeout"] - (time.time() - active_recovery["start_time"]),
            "strategy": self._get_recovery_strategy(loss_data),
            "original_loss": loss_data["loss_amount"]
        }
    
    def _cleanup_recovery_attempts(self):
        """Clean up completed or expired recovery attempts"""
        current_time = time.time()
        timeout = self.WIN_BACK_CONFIG["recovery_timeout"]
        
        expired_attempts = []
        for trade_id, recovery_data in self.recovery_attempts.items():
            if (current_time - recovery_data["start_time"] > timeout or 
                recovery_data["attempts_made"] >= self.WIN_BACK_CONFIG["max_recovery_attempts"]):
                expired_attempts.append(trade_id)
        
        for trade_id in expired_attempts:
            del self.recovery_attempts[trade_id]
        
        if not self.recovery_attempts:
            self.win_back_active = False
    
    def get_winback_status(self) -> Dict[str, Any]:
        """Get current win-back engine status"""
        
        return {
            "active": self.win_back_active,
            "recent_losses": len(self.recent_losses),
            "active_recoveries": len(self.recovery_attempts),
            "stats": self.win_back_stats.copy(),
            "last_loss_time": self.last_loss_time,
            "total_recovery_pnl": self.total_recovery_pnl
        }
    
    def apply_winback_enhancements(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply win-back enhancements to trading signal"""
        
        requirements = self.get_winback_signal_requirements()
        if not requirements.get("active", False):
            return signal
        
        # Check if current signal meets requirements
        current_confidence = signal.get("confidence", 0)
        required_confidence = requirements["required_confidence"]
        
        if current_confidence < required_confidence:
            # Signal not good enough for win-back
            signal["winback_status"] = "WAITING_FOR_BETTER_SETUP"
            signal["winback_requirements"] = requirements
            return signal
        
        # Enhance signal for win-back
        enhanced_signal = signal.copy()
        
        # Apply position multiplier
        original_position = signal.get("position_size", 0.10)
        multiplier = requirements["position_multiplier"] 
        enhanced_position = min(requirements["max_position"], original_position * multiplier)
        
        enhanced_signal["position_size"] = enhanced_position
        enhanced_signal["is_winback_trade"] = True
        enhanced_signal["winback_data"] = requirements
        
        # Enhance confidence (psychological boost for aggressive trades)
        confidence_boost = min(0.05, (current_confidence - required_confidence))
        enhanced_signal["confidence"] = min(0.95, current_confidence + confidence_boost)
        
        # Add win-back specific metadata
        enhanced_signal["reason"] += f" [WIN-BACK: Attempt {requirements['attempt_number']}, Target: ${requirements['target_recovery']:.2f}]"
        
        logger.success(f"🔥 WIN-BACK SIGNAL ACTIVATED!")
        logger.info(f"   Position Enhanced: {original_position*100:.1f}% → {enhanced_position*100:.1f}% ({multiplier:.1f}x)")
        logger.info(f"   Confidence: {current_confidence:.1%} → {enhanced_signal['confidence']:.1%}")
        logger.info(f"   Strategy: {requirements['strategy']}")
        logger.info(f"   Target Recovery: ${requirements['target_recovery']:.2f}")
        
        return enhanced_signal


class LossPatternAnalyzer:
    """Analyzes loss patterns to prevent destructive revenge trading"""
    
    def __init__(self):
        self.loss_patterns = deque(maxlen=50)  # Track patterns over time
        
        # Pattern thresholds
        self.DANGEROUS_PATTERNS = {
            "streak_threshold": 3,           # 3 consecutive losses = dangerous
            "frequency_threshold": 0.6,      # >60% loss rate = dangerous
            "magnitude_threshold": 0.03,     # >3% cumulative loss = dangerous
            "time_window": 7200              # 2-hour analysis window
        }
        
        logger.info("📊 Loss Pattern Analyzer initialized")
    
    def analyze_loss_risk(self, recent_trades: List[Dict]) -> Dict[str, Any]:
        """Analyze if current loss pattern is dangerous"""
        
        if len(recent_trades) < 3:
            return {"risk_level": "LOW", "safe_for_winback": True}
        
        # Analyze recent performance
        recent_losses = [t for t in recent_trades if t.get("net_profit_loss", 0) < 0]
        win_rate = 1 - (len(recent_losses) / len(recent_trades))
        
        # Check for losing streaks
        consecutive_losses = 0
        for trade in reversed(recent_trades):
            if trade.get("net_profit_loss", 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        # Calculate cumulative loss
        total_loss = sum(abs(t.get("net_profit_loss", 0)) for t in recent_losses)
        
        # Determine risk level
        risk_factors = []
        
        if consecutive_losses >= self.DANGEROUS_PATTERNS["streak_threshold"]:
            risk_factors.append(f"Losing streak: {consecutive_losses} trades")
        
        if win_rate < (1 - self.DANGEROUS_PATTERNS["frequency_threshold"]):
            risk_factors.append(f"Low win rate: {win_rate*100:.1f}%")
        
        if total_loss > self.DANGEROUS_PATTERNS["magnitude_threshold"]:
            risk_factors.append(f"High cumulative loss: {total_loss*100:.1f}%")
        
        # Determine overall risk
        if len(risk_factors) >= 2:
            risk_level = "HIGH"
            safe_for_winback = False
        elif len(risk_factors) == 1:
            risk_level = "MEDIUM"
            safe_for_winback = consecutive_losses < 3  # Allow if not a streak
        else:
            risk_level = "LOW"
            safe_for_winback = True
        
        return {
            "risk_level": risk_level,
            "safe_for_winback": safe_for_winback,
            "consecutive_losses": consecutive_losses,
            "win_rate": win_rate,
            "total_recent_loss": total_loss,
            "risk_factors": risk_factors,
            "recommendation": self._get_risk_recommendation(risk_level, safe_for_winback)
        }
    
    def _get_risk_recommendation(self, risk_level: str, safe_for_winback: bool) -> str:
        """Get trading recommendation based on risk analysis"""
        
        if risk_level == "HIGH":
            return "DEFENSIVE_MODE: Reduce position sizes, focus on high-confidence setups only"
        elif risk_level == "MEDIUM":
            return "CAUTIOUS_MODE: Standard positions, avoid risky setups" if not safe_for_winback else "CONTROLLED_WINBACK: Single attempt only"
        else:
            return "NORMAL_MODE: Standard win-back procedures allowed"