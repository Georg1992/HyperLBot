#!/usr/bin/env python3
"""
Volume Calculator Module
Centralized volume calculations and analysis for trading decisions
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from core.constants import MagicNumbers, volume_constants


class VolumeCalculator:
    """Centralized volume calculation and analysis system"""
    
    def __init__(self):
        logger.info("📊 Volume Calculator initialized")
    
    def calculate_relative_volume(self, current_volume: float, historical_volumes: List[float]) -> float:
        """Calculate relative volume (current vs historical average)"""
        try:
            if not historical_volumes or len(historical_volumes) < 5:
                return 1.0  # Default neutral relative volume
            
            historical_avg = sum(historical_volumes) / len(historical_volumes)
            if historical_avg == 0:
                return 1.0
                
            relative_volume = current_volume / historical_avg
            return round(relative_volume, 3)
            
        except Exception as e:
            logger.warning(f"Relative volume calculation failed: {e}")
            return 1.0
    
    def calculate_volume_momentum(self, volumes: List[float]) -> Dict[str, Any]:
        """Calculate volume momentum and acceleration"""
        try:
            if len(volumes) < 6:
                return {
                    "momentum": 0.0,
                    "acceleration": 0.0,
                    "trend": "UNKNOWN"
                }
            
            # Recent vs older volume comparison
            recent_volumes = volumes[-3:]  # Last 3 periods
            older_volumes = volumes[-6:-3]  # Previous 3 periods
            
            recent_avg = sum(recent_volumes) / len(recent_volumes)
            older_avg = sum(older_volumes) / len(older_volumes)
            
            # Calculate momentum (rate of change)
            if older_avg > 0:
                momentum = (recent_avg - older_avg) / older_avg
            else:
                momentum = 0.0
            
            # Calculate acceleration (change in momentum)
            if len(volumes) >= 9:
                earlier_volumes = volumes[-9:-6]
                earlier_avg = sum(earlier_volumes) / len(earlier_volumes)
                
                if earlier_avg > 0:
                    previous_momentum = (older_avg - earlier_avg) / earlier_avg
                    acceleration = momentum - previous_momentum
                else:
                    acceleration = 0.0
            else:
                acceleration = 0.0
            
            # Determine trend
            if momentum > 0.15:  # 15% increase
                trend = "ACCELERATING"
            elif momentum > 0.05:  # 5% increase
                trend = "INCREASING"
            elif momentum < -0.15:  # 15% decrease
                trend = "DECLINING"
            elif momentum < -0.05:  # 5% decrease
                trend = "DECREASING"
            else:
                trend = "STABLE"
            
            return {
                "momentum": round(momentum, 4),
                "acceleration": round(acceleration, 4),
                "trend": trend
            }
            
        except Exception as e:
            logger.warning(f"Volume momentum calculation failed: {e}")
            return {
                "momentum": 0.0,
                "acceleration": 0.0,
                "trend": "ERROR"
            }
    
    def categorize_orderbook_depth(self, total_depth: float, bid_depth: float, ask_depth: float) -> Dict[str, Any]:
        """Categorize orderbook depth for liquidity assessment"""
        try:
            # Categorize total depth (BTC)
            if total_depth > MagicNumbers.ORDERBOOK_DEPTH_EXTREMELY_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_VERY_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_VERY_HIGH
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_HIGH
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_ABOVE_AVERAGE:
                depth_category = volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_NORMAL:
                depth_category = volume_constants.VOLUME_CATEGORY_NORMAL
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_BELOW_AVERAGE:
                depth_category = volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
            elif total_depth > MagicNumbers.ORDERBOOK_DEPTH_LOW:
                depth_category = volume_constants.VOLUME_CATEGORY_LOW
            elif total_depth > 5.0:
                depth_category = volume_constants.VOLUME_CATEGORY_VERY_LOW
            else:
                depth_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_LOW
            
            # Calculate bid/ask ratio and imbalance
            bid_ask_ratio = bid_depth / ask_depth if ask_depth > 0 else 1.0
            depth_imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0.0
            
            # Determine order flow direction
            if depth_imbalance > 0.15:  # Bid-heavy
                order_flow = "BUY_PRESSURE"
            elif depth_imbalance < -0.15:  # Ask-heavy
                order_flow = "SELL_PRESSURE"
            else:
                order_flow = "NEUTRAL"
            
            return {
                "volume_depth": round(total_depth, 2),
                "volume_category": depth_category,
                "bid_depth": round(bid_depth, 2),
                "ask_depth": round(ask_depth, 2),
                "bid_ask_ratio": round(bid_ask_ratio, 3),
                "depth_imbalance": round(depth_imbalance, 4),
                "order_flow": order_flow,
                "depth_analysis": "SUFFICIENT_LIQUIDITY" if total_depth > 10.0 else "LOW_LIQUIDITY"
            }
            
        except Exception as e:
            logger.warning(f"Orderbook depth categorization failed: {e}")
            return {
                "volume_depth": 0.0,
                "volume_category": "ERROR",
                "bid_depth": 0.0,
                "ask_depth": 0.0,
                "bid_ask_ratio": 1.0,
                "depth_imbalance": 0.0,
                "order_flow": "NEUTRAL",
                "depth_analysis": "ERROR"
            }
    
    def detect_volume_spikes(self, current_volume: float, historical_volumes: List[float], 
                           spike_threshold: float = 2.0) -> Dict[str, Any]:
        """Detect unusual volume activity (spikes)"""
        try:
            if not historical_volumes or len(historical_volumes) < 10:
                return {
                    "has_spike": False,
                    "spike_magnitude": 1.0,
                    "spike_type": "NORMAL"
                }
            
            # Calculate statistical thresholds
            avg_volume = statistics.mean(historical_volumes)
            std_volume = statistics.stdev(historical_volumes) if len(historical_volumes) > 1 else 0
            
            # Detect spike
            relative_volume = current_volume / avg_volume if avg_volume > 0 else 1.0
            z_score = (current_volume - avg_volume) / std_volume if std_volume > 0 else 0
            
            # Categorize spike
            if relative_volume > spike_threshold * 2:  # 4x normal
                spike_type = "EXTREME_SPIKE"
                has_spike = True
            elif relative_volume > spike_threshold:  # 2x normal
                spike_type = "VOLUME_SPIKE"
                has_spike = True
            elif relative_volume > 1.5:  # 1.5x normal
                spike_type = "ELEVATED"
                has_spike = False
            else:
                spike_type = "NORMAL"
                has_spike = False
            
            return {
                "has_spike": has_spike,
                "spike_magnitude": round(relative_volume, 2),
                "spike_type": spike_type,
                "z_score": round(z_score, 2)
            }
            
        except Exception as e:
            logger.warning(f"Volume spike detection failed: {e}")
            return {
                "has_spike": False,
                "spike_magnitude": 1.0,
                "spike_type": "ERROR",
                "z_score": 0.0
            }
    
    def categorize_yahoo_volume(self, current_volume: float, volumes: List[float]) -> Dict[str, Any]:
        """Categorize Yahoo Finance trading volume (USD)"""
        try:
            # Calculate average volume from recent candles
            if len(volumes) >= 5:
                recent_volumes = volumes[-5:]  # Last 5 candles
                avg_volume = sum(recent_volumes) / len(recent_volumes)
            else:
                avg_volume = current_volume
            
            # Categorize volume using standardized thresholds
            if current_volume >= volume_constants.TRADING_VOLUME_EXTREMELY_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
            elif current_volume >= volume_constants.TRADING_VOLUME_VERY_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_VERY_HIGH
            elif current_volume >= volume_constants.TRADING_VOLUME_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_HIGH
            elif current_volume >= volume_constants.TRADING_VOLUME_ABOVE_AVERAGE:
                volume_category = volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
            elif current_volume >= volume_constants.TRADING_VOLUME_NORMAL:
                volume_category = volume_constants.VOLUME_CATEGORY_NORMAL
            elif current_volume >= volume_constants.TRADING_VOLUME_BELOW_AVERAGE:
                volume_category = volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
            elif current_volume >= volume_constants.TRADING_VOLUME_LOW:
                volume_category = volume_constants.VOLUME_CATEGORY_LOW
            elif current_volume >= volume_constants.TRADING_VOLUME_VERY_LOW:
                volume_category = volume_constants.VOLUME_CATEGORY_VERY_LOW
            else:
                volume_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_LOW
            
            # Determine volume trend
            if len(volumes) >= 6:
                recent_avg = sum(volumes[-3:]) / 3
                older_avg = sum(volumes[-6:-3]) / 3
                
                if recent_avg > older_avg * 1.1:
                    volume_trend = "INCREASING"
                elif recent_avg < older_avg * 0.9:
                    volume_trend = "DECREASING"
                else:
                    volume_trend = "STABLE"
            else:
                volume_trend = "UNKNOWN"
            
            return {
                "current_volume": current_volume,
                "volume_category": volume_category,
                "avg_volume": avg_volume,
                "volume_trend": volume_trend,
                "data_source": "yahoo_finance"
            }
            
        except Exception as e:
            logger.warning(f"Yahoo volume categorization failed: {e}")
            return {
                "current_volume": 0,
                "volume_category": "ERROR",
                "avg_volume": 0,
                "volume_trend": "ERROR",
                "data_source": "error"
            }