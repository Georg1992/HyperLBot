#!/usr/bin/env python3
"""
Active Position Manager - Intelligent Trade Monitoring & Management
Actively monitors open trades and makes dynamic decisions for optimization
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

class PositionAction(Enum):
    """Actions that can be taken on a position"""
    HOLD = "hold"
    ADJUST_STOP_LOSS = "adjust_stop_loss"
    TRAILING_STOP = "trailing_stop"
    EXIT_EARLY = "exit_early"
    ADD_LIMIT_ORDER = "add_limit_order"
    CANCEL_ORDERS = "cancel_orders"
    REDUCE_SIZE = "reduce_size"
    EMERGENCY_EXIT = "emergency_exit"

@dataclass
class PositionAction_Data:
    """Data for position actions"""
    action: PositionAction
    position_id: str
    reason: str
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    parameters: Dict[str, Any]
    confidence: float
    timestamp: float

@dataclass
class TradingSignal:
    """Trading signal for exit decisions"""
    signal_type: str
    direction: str  # EXIT_LONG, EXIT_SHORT, HOLD
    strength: float  # 0-1
    confidence: float  # 0-1
    reason: str
    timestamp: float

class ActivePositionManager:
    """Intelligent position monitoring and management system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Core components will be injected
        self.pnl_tracker = None
        self.hyperliquid_api = None
        self.prediction_engines = {}
        
        # Position monitoring
        self.monitoring_active = False
        self.last_check_time = 0
        self.check_interval = 10  # seconds
        
        # Risk management parameters
        self.risk_params = {
            "max_loss_per_trade": 0.05,        # 5% max loss per trade
            "trailing_stop_distance": 0.02,    # 2% trailing stop
            "volatility_stop_multiplier": 2.5, # Stop based on volatility
            "time_based_exit_hours": 24,       # Max holding time
            "profit_taking_levels": [0.03, 0.06, 0.10],  # 3%, 6%, 10%
            "emergency_exit_threshold": -0.08,  # -8% emergency exit
            "max_drawdown_per_position": 0.15,  # 15% max drawdown
        }
        
        # Action history
        self.action_history = []
        self.decision_cache = {}
        
        # Performance tracking
        self.management_stats = {
            "total_adjustments": 0,
            "successful_exits": 0,
            "prevented_losses": 0,
            "profit_optimizations": 0,
            "emergency_exits": 0
        }
        
        logger.info("🤖 Active Position Manager initialized - Intelligent trade monitoring active")
    
    def inject_dependencies(self, pnl_tracker=None, hyperliquid_api=None, prediction_engines=None):
        """Inject required dependencies"""
        self.pnl_tracker = pnl_tracker
        self.hyperliquid_api = hyperliquid_api
        self.prediction_engines = prediction_engines or {}
        
        if all([self.pnl_tracker, self.hyperliquid_api]):
            logger.success("🔗 Active Position Manager dependencies connected")
        else:
            logger.warning("⚠️ Some dependencies missing for Active Position Manager")
    
    def start_monitoring(self):
        """Start active position monitoring"""
        self.monitoring_active = True
        logger.info("👁️ Position monitoring started - Watching all open trades")
    
    def stop_monitoring(self):
        """Stop active position monitoring"""
        self.monitoring_active = False
        logger.info("⏹️ Position monitoring stopped")
    
    def analyze_open_positions(self, current_prices: Dict[str, float]) -> List[PositionAction_Data]:
        """Analyze all open positions and return recommended actions"""
        if not self.pnl_tracker or not self.monitoring_active:
            return []
        
        actions = []
        
        try:
            # Get current position data
            position_summaries = self.pnl_tracker.get_position_summary(current_prices)
            
            for position_data in position_summaries:
                position_actions = self._analyze_single_position(position_data, current_prices)
                actions.extend(position_actions)
            
            # Sort by urgency and confidence
            actions.sort(key=lambda x: (
                {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[x.urgency],
                x.confidence
            ), reverse=True)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error analyzing positions: {e}")
            return []
    
    def _analyze_single_position(self, position_data: Dict[str, Any], current_prices: Dict[str, float]) -> List[PositionAction_Data]:
        """Analyze a single position and determine actions"""
        actions = []
        position_id = position_data["position_id"]
        
        try:
            # 1. Emergency Exit Check
            emergency_action = self._check_emergency_exit(position_data)
            if emergency_action:
                actions.append(emergency_action)
                return actions  # Emergency takes priority
            
            # 2. Profit Taking Opportunities
            profit_action = self._check_profit_taking(position_data)
            if profit_action:
                actions.append(profit_action)
            
            # 3. Dynamic Stop Loss Adjustment
            stop_action = self._check_stop_loss_adjustment(position_data)
            if stop_action:
                actions.append(stop_action)
            
            # 4. Trailing Stop Management
            trailing_action = self._check_trailing_stop(position_data)
            if trailing_action:
                actions.append(trailing_action)
            
            # 5. Exit Signal Analysis
            exit_action = self._check_exit_signals(position_data, current_prices)
            if exit_action:
                actions.append(exit_action)
            
            # 6. Time-Based Exit
            time_action = self._check_time_based_exit(position_data)
            if time_action:
                actions.append(time_action)
            
            # 7. Volatility-Based Adjustments
            volatility_action = self._check_volatility_adjustments(position_data)
            if volatility_action:
                actions.append(volatility_action)
            
        except Exception as e:
            logger.error(f"Error analyzing position {position_id}: {e}")
        
        return actions
    
    def _check_emergency_exit(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check for emergency exit conditions"""
        unrealized_pct = position_data.get("unrealized_pct", 0)
        position_id = position_data["position_id"]
        
        # Emergency exit if loss exceeds threshold
        if unrealized_pct <= (self.risk_params["emergency_exit_threshold"] * 100):
            return PositionAction_Data(
                action=PositionAction.EMERGENCY_EXIT,
                position_id=position_id,
                reason=f"Emergency exit: Loss {unrealized_pct:.1f}% exceeds {self.risk_params['emergency_exit_threshold']*100:.1f}% threshold",
                urgency="CRITICAL",
                parameters={"exit_type": "market", "reason": "emergency_loss"},
                confidence=0.95,
                timestamp=time.time()
            )
        
        # Check for extreme volatility or market crash indicators
        if self._detect_market_crash(position_data):
            return PositionAction_Data(
                action=PositionAction.EMERGENCY_EXIT,
                position_id=position_id,
                reason="Emergency exit: Market crash detected",
                urgency="CRITICAL",
                parameters={"exit_type": "market", "reason": "market_crash"},
                confidence=0.90,
                timestamp=time.time()
            )
        
        return None
    
    def _check_profit_taking(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check for profit taking opportunities"""
        unrealized_pct = position_data.get("unrealized_pct", 0)
        position_id = position_data["position_id"]
        
        if unrealized_pct <= 0:
            return None  # No profit to take
        
        # Check profit taking levels
        for level in self.risk_params["profit_taking_levels"]:
            level_pct = level * 100
            
            if unrealized_pct >= level_pct:
                # Calculate partial exit size
                if unrealized_pct >= 10:  # 10%+ profit
                    exit_percentage = 0.50  # Take 50% profit
                elif unrealized_pct >= 6:   # 6%+ profit
                    exit_percentage = 0.30  # Take 30% profit
                else:  # 3%+ profit
                    exit_percentage = 0.20  # Take 20% profit
                
                return PositionAction_Data(
                    action=PositionAction.REDUCE_SIZE,
                    position_id=position_id,
                    reason=f"Profit taking: {unrealized_pct:.1f}% profit, taking {exit_percentage*100:.0f}%",
                    urgency="MEDIUM",
                    parameters={
                        "exit_percentage": exit_percentage,
                        "exit_type": "limit",
                        "reason": "profit_taking"
                    },
                    confidence=0.85,
                    timestamp=time.time()
                )
        
        return None
    
    def _check_stop_loss_adjustment(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check if stop loss needs adjustment"""
        current_price = position_data.get("current_price", 0)
        entry_price = position_data.get("entry_price", 0)
        stop_loss = position_data.get("stop_loss")
        side = position_data.get("side", "")
        position_id = position_data["position_id"]
        unrealized_pct = position_data.get("unrealized_pct", 0)
        
        if not stop_loss or not current_price or not entry_price:
            return None
        
        # Calculate optimal stop loss based on volatility
        optimal_stop = self._calculate_optimal_stop_loss(position_data)
        
        if not optimal_stop:
            return None
        
        # Check if adjustment is needed
        current_stop_distance = abs(stop_loss - current_price) / current_price
        optimal_stop_distance = abs(optimal_stop - current_price) / current_price
        
        # Adjust if optimal stop is significantly different
        if abs(current_stop_distance - optimal_stop_distance) > 0.01:  # 1% difference
            return PositionAction_Data(
                action=PositionAction.ADJUST_STOP_LOSS,
                position_id=position_id,
                reason=f"Optimizing stop loss: Current {current_stop_distance:.1%} → Optimal {optimal_stop_distance:.1%}",
                urgency="MEDIUM",
                parameters={
                    "new_stop_loss": optimal_stop,
                    "reason": "volatility_optimization"
                },
                confidence=0.75,
                timestamp=time.time()
            )
        
        return None
    
    def _check_trailing_stop(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check for trailing stop opportunities"""
        unrealized_pct = position_data.get("unrealized_pct", 0)
        position_id = position_data["position_id"]
        current_price = position_data.get("current_price", 0)
        side = position_data.get("side", "")
        
        # Only apply trailing stop when in profit
        if unrealized_pct <= 2:  # Only when 2%+ profit
            return None
        
        # Calculate trailing stop price
        trailing_distance = self.risk_params["trailing_stop_distance"]
        
        if side == "BUY":
            trailing_stop = current_price * (1 - trailing_distance)
        else:  # SELL
            trailing_stop = current_price * (1 + trailing_distance)
        
        return PositionAction_Data(
            action=PositionAction.TRAILING_STOP,
            position_id=position_id,
            reason=f"Trailing stop: Protecting {unrealized_pct:.1f}% profit with {trailing_distance:.1%} trail",
            urgency="MEDIUM",
            parameters={
                "trailing_stop_price": trailing_stop,
                "trailing_distance": trailing_distance,
                "reason": "profit_protection"
            },
            confidence=0.80,
            timestamp=time.time()
        )
    
    def _check_exit_signals(self, position_data: Dict[str, Any], current_prices: Dict[str, float]) -> Optional[PositionAction_Data]:
        """Check for exit signals from prediction engines"""
        position_id = position_data["position_id"]
        symbol = position_data.get("symbol", "BTC")
        side = position_data.get("side", "")
        
        try:
            # Get current market signals
            exit_signals = self._get_exit_signals(symbol, current_prices)
            
            # Analyze signals for this position
            strongest_signal = self._analyze_exit_signals(exit_signals, side)
            
            if strongest_signal and strongest_signal.strength > 0.7:  # Strong signal
                urgency = "HIGH" if strongest_signal.strength > 0.85 else "MEDIUM"
                
                return PositionAction_Data(
                    action=PositionAction.EXIT_EARLY,
                    position_id=position_id,
                    reason=f"Exit signal: {strongest_signal.reason} (Strength: {strongest_signal.strength:.1%})",
                    urgency=urgency,
                    parameters={
                        "exit_type": "market",
                        "signal_strength": strongest_signal.strength,
                        "signal_reason": strongest_signal.reason,
                        "reason": "signal_exit"
                    },
                    confidence=strongest_signal.confidence,
                    timestamp=time.time()
                )
            
        except Exception as e:
            logger.debug(f"Error checking exit signals for {position_id}: {e}")
        
        return None
    
    def _check_time_based_exit(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check for time-based exit conditions"""
        position_id = position_data["position_id"]
        entry_time = position_data.get("entry_time", time.time())
        duration_hours = position_data.get("duration_hours", 0)
        unrealized_pct = position_data.get("unrealized_pct", 0)
        
        max_holding_hours = self.risk_params["time_based_exit_hours"]
        
        # Check if position has been open too long
        if duration_hours > max_holding_hours:
            # More urgent if losing money
            urgency = "HIGH" if unrealized_pct < 0 else "MEDIUM"
            
            return PositionAction_Data(
                action=PositionAction.EXIT_EARLY,
                position_id=position_id,
                reason=f"Time-based exit: Position open {duration_hours:.1f}h (max: {max_holding_hours}h)",
                urgency=urgency,
                parameters={
                    "exit_type": "limit",
                    "reason": "time_limit",
                    "duration_hours": duration_hours
                },
                confidence=0.70,
                timestamp=time.time()
            )
        
        return None
    
    def _check_volatility_adjustments(self, position_data: Dict[str, Any]) -> Optional[PositionAction_Data]:
        """Check for volatility-based position adjustments"""
        position_id = position_data["position_id"]
        
        # This would analyze recent price volatility and suggest adjustments
        # Placeholder for now - would integrate with volatility calculation
        
        return None
    
    def _calculate_optimal_stop_loss(self, position_data: Dict[str, Any]) -> Optional[float]:
        """Calculate optimal stop loss based on volatility and risk parameters"""
        current_price = position_data.get("current_price", 0)
        entry_price = position_data.get("entry_price", 0)
        side = position_data.get("side", "")
        
        if not current_price or not entry_price:
            return None
        
        # Simple volatility-based stop (would be enhanced with real volatility data)
        volatility_estimate = 0.02  # 2% estimated daily volatility
        stop_distance = volatility_estimate * self.risk_params["volatility_stop_multiplier"]
        
        if side == "BUY":
            optimal_stop = current_price * (1 - stop_distance)
        else:  # SELL
            optimal_stop = current_price * (1 + stop_distance)
        
        return optimal_stop
    
    def _get_exit_signals(self, symbol: str, current_prices: Dict[str, float]) -> List[TradingSignal]:
        """Get exit signals from prediction engines"""
        signals = []
        
        # This would integrate with prediction engines to get current signals
        # For now, return placeholder signals
        
        return signals
    
    def _analyze_exit_signals(self, signals: List[TradingSignal], position_side: str) -> Optional[TradingSignal]:
        """Analyze exit signals and return the strongest one"""
        if not signals:
            return None
        
        # Filter signals relevant to position side
        relevant_signals = []
        for signal in signals:
            if position_side == "BUY" and signal.direction == "EXIT_LONG":
                relevant_signals.append(signal)
            elif position_side == "SELL" and signal.direction == "EXIT_SHORT":
                relevant_signals.append(signal)
        
        if not relevant_signals:
            return None
        
        # Return strongest signal
        return max(relevant_signals, key=lambda s: s.strength * s.confidence)
    
    def _detect_market_crash(self, position_data: Dict[str, Any]) -> bool:
        """Detect market crash conditions"""
        # Placeholder for market crash detection
        # Would analyze rapid price movements, volume spikes, etc.
        return False
    
    def execute_action(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute a position action"""
        try:
            logger.info(f"🎯 Executing {action.action.value}: {action.reason}")
            
            result = {"success": False, "action": action.action.value}
            
            if action.action == PositionAction.EMERGENCY_EXIT:
                result = self._execute_emergency_exit(action)
            elif action.action == PositionAction.ADJUST_STOP_LOSS:
                result = self._execute_stop_loss_adjustment(action)
            elif action.action == PositionAction.TRAILING_STOP:
                result = self._execute_trailing_stop(action)
            elif action.action == PositionAction.EXIT_EARLY:
                result = self._execute_early_exit(action)
            elif action.action == PositionAction.REDUCE_SIZE:
                result = self._execute_size_reduction(action)
            elif action.action == PositionAction.ADD_LIMIT_ORDER:
                result = self._execute_limit_order(action)
            
            # Record action
            self.action_history.append({
                "timestamp": time.time(),
                "action": asdict(action),
                "result": result
            })
            
            # Update stats
            if result.get("success"):
                self.management_stats["total_adjustments"] += 1
                if action.action == PositionAction.EMERGENCY_EXIT:
                    self.management_stats["emergency_exits"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing action {action.action.value}: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_emergency_exit(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute emergency exit"""
        # Would integrate with trading API to close position immediately
        logger.warning(f"🚨 EMERGENCY EXIT: {action.reason}")
        return {"success": True, "exit_type": "emergency"}
    
    def _execute_stop_loss_adjustment(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute stop loss adjustment"""
        new_stop = action.parameters.get("new_stop_loss")
        logger.info(f"🛡️ Adjusting stop loss to ${new_stop:.2f}")
        return {"success": True, "new_stop_loss": new_stop}
    
    def _execute_trailing_stop(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute trailing stop"""
        trailing_price = action.parameters.get("trailing_stop_price")
        logger.info(f"📈 Setting trailing stop at ${trailing_price:.2f}")
        return {"success": True, "trailing_stop": trailing_price}
    
    def _execute_early_exit(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute early exit"""
        exit_type = action.parameters.get("exit_type", "market")
        logger.info(f"🚪 Early exit via {exit_type} order")
        return {"success": True, "exit_type": exit_type}
    
    def _execute_size_reduction(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute position size reduction"""
        exit_percentage = action.parameters.get("exit_percentage", 0.3)
        logger.info(f"📉 Reducing position size by {exit_percentage:.1%}")
        return {"success": True, "size_reduction": exit_percentage}
    
    def _execute_limit_order(self, action: PositionAction_Data) -> Dict[str, Any]:
        """Execute limit order placement"""
        logger.info("📋 Adding limit order")
        return {"success": True, "order_type": "limit"}
    
    def get_management_report(self) -> Dict[str, Any]:
        """Get position management report"""
        return {
            "monitoring_active": self.monitoring_active,
            "total_actions": len(self.action_history),
            "recent_actions": self.action_history[-10:],  # Last 10 actions
            "management_stats": self.management_stats,
            "risk_parameters": self.risk_params,
            "last_check": self.last_check_time
        }
    
    def update_risk_parameters(self, new_params: Dict[str, Any]):
        """Update risk management parameters"""
        self.risk_params.update(new_params)
        logger.info("⚙️ Risk parameters updated")
    
    def get_position_recommendations(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get all position recommendations"""
        actions = self.analyze_open_positions(current_prices)
        
        recommendations = []
        for action in actions:
            recommendations.append({
                "position_id": action.position_id,
                "action": action.action.value,
                "reason": action.reason,
                "urgency": action.urgency,
                "confidence": f"{action.confidence:.1%}",
                "parameters": action.parameters
            })
        
        return recommendations