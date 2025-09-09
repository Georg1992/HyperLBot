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
    
    def categorize_orderbook_depth(self, total_depth: float, bid_depth: float, ask_depth: float, 
                                 historical_depths: List[float] = None) -> Dict[str, Any]:
        """
        Categorize orderbook depth for liquidity assessment with noise reduction
        
        IMPORTANT: This is ORDERBOOK DEPTH (available liquidity), NOT trading volume!
        Hyperliquid API does not provide actual trading volume data.
        This measures liquidity available in top 5 bid/ask levels.
        """
        try:
            # Apply smoothing to reduce noise from orderbook fluctuations
            smoothed_depth = self._apply_volume_smoothing(total_depth, historical_depths)
            
            # Categorize using Hyperliquid-specific depth thresholds
            if smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_EXTREMELY_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_VERY_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_VERY_HIGH
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_HIGH:
                depth_category = volume_constants.VOLUME_CATEGORY_HIGH
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_ABOVE_AVERAGE:
                depth_category = volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_NORMAL:
                depth_category = volume_constants.VOLUME_CATEGORY_NORMAL
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_BELOW_AVERAGE:
                depth_category = volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_LOW:
                depth_category = volume_constants.VOLUME_CATEGORY_LOW
            elif smoothed_depth >= volume_constants.HYPERLIQUID_DEPTH_VERY_LOW:
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
                "volume_depth": round(smoothed_depth, 2),
                "volume_category": depth_category,
                "bid_depth": round(bid_depth, 2),
                "ask_depth": round(ask_depth, 2),
                "bid_ask_ratio": round(bid_ask_ratio, 3),
                "depth_imbalance": round(depth_imbalance, 4),
                "order_flow": order_flow,
                "depth_analysis": "SUFFICIENT_LIQUIDITY" if smoothed_depth > 10.0 else "LOW_LIQUIDITY",
                "raw_depth": round(total_depth, 2),  # Keep raw for comparison
                "smoothing_applied": historical_depths is not None and len(historical_depths) > 0
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
                "depth_analysis": "ERROR",
                "raw_depth": 0.0,
                "smoothing_applied": False
            }
    
    def _apply_volume_smoothing(self, current_depth: float, historical_depths: List[float] = None) -> float:
        """Apply smoothing to reduce orderbook noise"""
        try:
            if not historical_depths or len(historical_depths) < 2:
                return current_depth  # No smoothing if insufficient data
            
            # Use exponential moving average for responsiveness
            smoothing_period = min(volume_constants.VOLUME_SMOOTHING_PERIOD, len(historical_depths))
            recent_depths = historical_depths[-smoothing_period:] + [current_depth]
            
            # Simple moving average for stability
            smoothed_depth = sum(recent_depths) / len(recent_depths)
            
            # Apply slight exponential weighting to recent values
            alpha = 0.3  # 30% weight to current, 70% to average
            final_depth = (alpha * current_depth) + ((1 - alpha) * smoothed_depth)
            
            return final_depth
            
        except Exception as e:
            logger.warning(f"Volume smoothing failed: {e}")
            return current_depth
    
    def calculate_relative_volume_analysis(self, current_depth: float, historical_depths: List[float], 
                                         current_price: float, historical_prices: List[float] = None) -> Dict[str, Any]:
        """Calculate relative volume analysis with price correlation"""
        try:
            if not historical_depths or len(historical_depths) < 10:
                return {
                    "relative_volume": 1.0,
                    "volume_trend": "UNKNOWN",
                    "price_volume_correlation": 0.0,
                    "volume_quality": "INSUFFICIENT_DATA"
                }
            
            # Calculate relative volume (current vs 24h average)
            avg_24h_depth = sum(historical_depths) / len(historical_depths)
            relative_volume = current_depth / avg_24h_depth if avg_24h_depth > 0 else 1.0
            
            # Calculate volume momentum
            recent_volumes = historical_depths[-volume_constants.VOLUME_MOMENTUM_PERIOD:]
            if len(recent_volumes) >= 3:
                volume_trend = "INCREASING" if recent_volumes[-1] > recent_volumes[0] else "DECREASING"
            else:
                volume_trend = "STABLE"
            
            # Calculate price-volume correlation if price data available
            price_volume_correlation = 0.0
            if historical_prices and len(historical_prices) == len(historical_depths):
                try:
                    import numpy as np
                    # Check for constant values (zero variance) to avoid division by zero
                    prices_array = np.array(historical_prices)
                    depths_array = np.array(historical_depths)
                    
                    # Only calculate correlation if both arrays have variance
                    if np.std(prices_array) > 0 and np.std(depths_array) > 0:
                        correlation = np.corrcoef(prices_array, depths_array)[0, 1]
                        price_volume_correlation = correlation if not np.isnan(correlation) else 0.0
                    else:
                        # No correlation if either array has zero variance
                        price_volume_correlation = 0.0
                except Exception as e:
                    logger.debug(f"Price-volume correlation calculation failed: {e}")
                    price_volume_correlation = 0.0
            
            # Determine volume quality
            volume_quality = "GOOD"
            if relative_volume < 0.5:
                volume_quality = "LOW"
            elif relative_volume > 2.0:
                volume_quality = "SURGE"
            elif abs(price_volume_correlation) < volume_constants.VOLUME_CORRELATION_THRESHOLD:
                volume_quality = "WEAK_CORRELATION"
            
            return {
                "relative_volume": round(relative_volume, 3),
                "volume_trend": volume_trend,
                "price_volume_correlation": round(price_volume_correlation, 3),
                "volume_quality": volume_quality,
                "avg_24h_depth": round(avg_24h_depth, 2)
            }
            
        except Exception as e:
            logger.warning(f"Relative volume analysis failed: {e}")
            return {
                "relative_volume": 1.0,
                "volume_trend": "ERROR",
                "price_volume_correlation": 0.0,
                "volume_quality": "ERROR"
            }
    
    def calculate_trading_volume_from_trades(self, recent_trades: List[Dict], time_window_minutes: int = 5) -> Dict[str, Any]:
        """
        Calculate actual trading volume from recent trades data
        
        Args:
            recent_trades: List of trade data from Hyperliquid API
            time_window_minutes: Time window to aggregate trades (default 5 minutes)
        
        Returns:
            Dict with trading volume analysis
        """
        try:
            if not recent_trades:
                return {
                    "trading_volume_btc": 0.0,
                    "trading_volume_category": "NO_DATA",
                    "trade_count": 0,
                    "avg_trade_size": 0.0,
                    "time_window_minutes": time_window_minutes,
                    "data_source": "hyperliquid_trades"
                }
            
            import time
            current_time = time.time()
            window_start = current_time - (time_window_minutes * 60)
            
            # Filter trades within time window
            recent_trades_in_window = []
            total_volume_btc = 0.0
            
            for trade in recent_trades:
                # Parse trade timestamp (assuming it's in milliseconds)
                trade_time = trade.get('time', 0) / 1000  # Convert to seconds
                
                if trade_time >= window_start:
                    trade_size = float(trade.get('sz', 0))  # Size in BTC
                    total_volume_btc += trade_size
                    recent_trades_in_window.append(trade)
            
            # Calculate statistics
            trade_count = len(recent_trades_in_window)
            avg_trade_size = total_volume_btc / trade_count if trade_count > 0 else 0.0
            
            # Categorize trading volume using realistic Bitcoin trading thresholds
            if total_volume_btc >= 50.0:  # 50+ BTC in 5 minutes = very high
                volume_category = "EXTREMELY_HIGH"
            elif total_volume_btc >= 20.0:  # 20-50 BTC = high
                volume_category = "VERY_HIGH"
            elif total_volume_btc >= 10.0:  # 10-20 BTC = above average
                volume_category = "HIGH"
            elif total_volume_btc >= 5.0:   # 5-10 BTC = normal
                volume_category = "ABOVE_AVERAGE"
            elif total_volume_btc >= 2.0:   # 2-5 BTC = below average
                volume_category = "NORMAL"
            elif total_volume_btc >= 1.0:   # 1-2 BTC = low
                volume_category = "BELOW_AVERAGE"
            elif total_volume_btc >= 0.5:   # 0.5-1 BTC = very low
                volume_category = "LOW"
            else:  # < 0.5 BTC = extremely low
                volume_category = "VERY_LOW"
            
            return {
                "trading_volume_btc": round(total_volume_btc, 3),
                "trading_volume_category": volume_category,
                "trade_count": trade_count,
                "avg_trade_size": round(avg_trade_size, 3),
                "time_window_minutes": time_window_minutes,
                "data_source": "hyperliquid_trades"
            }
            
        except Exception as e:
            logger.warning(f"Trading volume calculation from trades failed: {e}")
            return {
                "trading_volume_btc": 0.0,
                "trading_volume_category": "ERROR",
                "trade_count": 0,
                "avg_trade_size": 0.0,
                "time_window_minutes": time_window_minutes,
                "data_source": "error"
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
        """Categorize Yahoo Finance trading volume (USD) with relative analysis"""
        try:
            # Calculate average volume from recent candles
            if len(volumes) >= 5:
                recent_volumes = volumes[-5:]  # Last 5 candles
                avg_volume = sum(recent_volumes) / len(recent_volumes)
            else:
                avg_volume = current_volume
            
            # Calculate relative volume
            relative_volume = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Categorize volume using Yahoo-specific thresholds (USD)
            if current_volume >= volume_constants.YAHOO_VOLUME_EXTREMELY_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_EXTREMELY_HIGH
            elif current_volume >= volume_constants.YAHOO_VOLUME_VERY_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_VERY_HIGH
            elif current_volume >= volume_constants.YAHOO_VOLUME_HIGH:
                volume_category = volume_constants.VOLUME_CATEGORY_HIGH
            elif current_volume >= volume_constants.YAHOO_VOLUME_ABOVE_AVERAGE:
                volume_category = volume_constants.VOLUME_CATEGORY_ABOVE_AVERAGE
            elif current_volume >= volume_constants.YAHOO_VOLUME_NORMAL:
                volume_category = volume_constants.VOLUME_CATEGORY_NORMAL
            elif current_volume >= volume_constants.YAHOO_VOLUME_BELOW_AVERAGE:
                volume_category = volume_constants.VOLUME_CATEGORY_BELOW_AVERAGE
            elif current_volume >= volume_constants.YAHOO_VOLUME_LOW:
                volume_category = volume_constants.VOLUME_CATEGORY_LOW
            elif current_volume >= volume_constants.YAHOO_VOLUME_VERY_LOW:
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
                "relative_volume": round(relative_volume, 3),
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