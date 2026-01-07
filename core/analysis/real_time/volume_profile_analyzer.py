#!/usr/bin/env python3
"""
Volume Profile Analyzer Module
Analyzes trade size distribution and flow patterns for market insights
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger

# Factory function for dependency injection
def create_volume_profile_analyzer() -> 'VolumeProfileAnalyzer':
    """
    Factory function to create VolumeProfileAnalyzer with dependency injection
    
    Returns:
        Configured VolumeProfileAnalyzer instance
    """
    return VolumeProfileAnalyzer()

# Deprecated global instance functions removed - use create_volume_profile_analyzer() instead

class VolumeProfileAnalyzer:
    """Analyzes trade size distribution and flow patterns for market insights"""
    
    def __init__(self):
        # Store trade history for analysis
        self._trade_history = []
        self._max_history = 500  # Keep last 500 trades
        
        logger.info("📊 Volume Profile Analyzer initialized")
    
    def analyze_volume_profile(self, trades_data: List[Dict[str, Any]], current_price: float) -> Dict[str, Any]:
        """
        Analyze trade size distribution and flow patterns
        
        Args:
            trades_data: Raw trades data from Hyperliquid API
            current_price: Current market price for reference
            
        Returns:
            Dictionary with volume profile analysis
        """
        try:
            if not trades_data or len(trades_data) == 0:
                raise Exception("No trades data provided")
            
            # Update trade history
            self._update_trade_history(trades_data)
            
            # Analyze trade patterns
            analysis = {
                "trade_size_distribution": self._analyze_trade_size_distribution(),
                "trade_flow_analysis": self._analyze_trade_flow(),
                "volume_weighted_price": self._calculate_volume_weighted_price(),
                "large_trade_detection": self._detect_large_trades(),
                "trade_frequency_analysis": self._analyze_trade_frequency(),
                "market_microstructure": self._analyze_market_microstructure(),
                "timestamp": time.time(),
                "data_source": "hyperliquid_trades"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Volume profile analysis failed: {e}")
            raise Exception(f"Volume profile analysis failed: {e}")
    
    def _update_trade_history(self, trades_data: List[Dict[str, Any]]):
        """Update trade history for analysis"""
        try:
            current_time = time.time()
            
            for trade in trades_data:
                # Parse trade data
                trade_info = {
                    "timestamp": current_time,
                    "price": float(trade.get('px', 0)),
                    "size": float(trade.get('sz', 0)),
                    "side": trade.get('side', 'unknown'),  # 'buy' or 'sell'
                    "trade_id": trade.get('tid', 'unknown')
                }
                
                # Only add if we have valid data
                if trade_info["price"] > 0 and trade_info["size"] > 0:
                    self._trade_history.append(trade_info)
            
            # Keep only recent history
            if len(self._trade_history) > self._max_history:
                self._trade_history = self._trade_history[-self._max_history:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update trade history: {e}")
    
    def _analyze_trade_size_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of trade sizes"""
        try:
            if len(self._trade_history) < 5:
                return {"distribution": "INSUFFICIENT_DATA", "categories": {}}
            
            # Get recent trades (last 100)
            recent_trades = self._trade_history[-100:]
            trade_sizes = [trade["size"] for trade in recent_trades]
            
            if not trade_sizes:
                return {"distribution": "NO_DATA", "categories": {}}
            
            # Calculate size statistics
            min_size = min(trade_sizes)
            max_size = max(trade_sizes)
            avg_size = sum(trade_sizes) / len(trade_sizes)
            median_size = sorted(trade_sizes)[len(trade_sizes) // 2]
            
            # Categorize trade sizes
            small_trades = [s for s in trade_sizes if s < avg_size * 0.5]
            medium_trades = [s for s in trade_sizes if avg_size * 0.5 <= s < avg_size * 2]
            large_trades = [s for s in trade_sizes if s >= avg_size * 2]
            
            # Calculate percentages
            total_trades = len(trade_sizes)
            small_pct = len(small_trades) / total_trades * 100
            medium_pct = len(medium_trades) / total_trades * 100
            large_pct = len(large_trades) / total_trades * 100
            
            # Determine dominant size category
            if large_pct > 30:
                dominant_category = "LARGE_TRADES"
            elif medium_pct > 50:
                dominant_category = "MEDIUM_TRADES"
            else:
                dominant_category = "SMALL_TRADES"
            
            return {
                "distribution": dominant_category,
                "categories": {
                    "small_trades": {"count": len(small_trades), "percentage": round(small_pct, 1)},
                    "medium_trades": {"count": len(medium_trades), "percentage": round(medium_pct, 1)},
                    "large_trades": {"count": len(large_trades), "percentage": round(large_pct, 1)}
                },
                "statistics": {
                    "min_size": round(min_size, 4),
                    "max_size": round(max_size, 4),
                    "avg_size": round(avg_size, 4),
                    "median_size": round(median_size, 4),
                    "total_trades": total_trades
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Trade size distribution analysis failed: {e}")
            return {"distribution": "ERROR", "categories": {}}
    
    def _analyze_trade_flow(self) -> Dict[str, Any]:
        """Analyze buying vs selling flow"""
        try:
            if len(self._trade_history) < 5:
                return {"flow": "INSUFFICIENT_DATA", "direction": "NEUTRAL", "strength": 0.0}
            
            # Get recent trades
            recent_trades = self._trade_history[-50:]
            
            # Separate buy and sell trades
            buy_trades = [t for t in recent_trades if t["side"] == "buy"]
            sell_trades = [t for t in recent_trades if t["side"] == "sell"]
            
            # Calculate total volume for each side
            buy_volume = sum(t["size"] for t in buy_trades)
            sell_volume = sum(t["size"] for t in sell_trades)
            total_volume = buy_volume + sell_volume
            
            if total_volume == 0:
                return {"flow": "NO_DATA", "direction": "NEUTRAL", "strength": 0.0}
            
            # Calculate flow ratio
            buy_ratio = buy_volume / total_volume
            sell_ratio = sell_volume / total_volume
            
            # Determine flow direction and strength
            if buy_ratio > 0.6:
                direction = "BUYING"
                strength = "STRONG" if buy_ratio > 0.75 else "MODERATE"
            elif sell_ratio > 0.6:
                direction = "SELLING"
                strength = "STRONG" if sell_ratio > 0.75 else "MODERATE"
            else:
                direction = "BALANCED"
                strength = "WEAK"
            
            return {
                "flow": f"{direction}_{strength}",
                "direction": direction,
                "strength": strength,
                "buy_volume": round(buy_volume, 4),
                "sell_volume": round(sell_volume, 4),
                "buy_ratio": round(buy_ratio, 3),
                "sell_ratio": round(sell_ratio, 3),
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades)
            }
            
        except Exception as e:
            logger.error(f"❌ Trade flow analysis failed: {e}")
            return {"flow": "ERROR", "direction": "UNKNOWN", "strength": "WEAK"}
    
    def _calculate_volume_weighted_price(self) -> Dict[str, Any]:
        """Calculate volume weighted average price (VWAP)"""
        try:
            if len(self._trade_history) < 5:
                return {"vwap": 0.0, "deviation": 0.0, "category": "INSUFFICIENT_DATA"}
            
            # Get recent trades
            recent_trades = self._trade_history[-100:]
            
            # Calculate VWAP
            total_volume = sum(t["size"] for t in recent_trades)
            if total_volume == 0:
                return {"vwap": 0.0, "deviation": 0.0, "category": "NO_VOLUME"}
            
            weighted_price = sum(t["price"] * t["size"] for t in recent_trades) / total_volume
            
            # Calculate current price deviation from VWAP
            current_price = recent_trades[-1]["price"] if recent_trades else 0
            if current_price == 0:
                deviation = 0.0
            else:
                deviation = (current_price - weighted_price) / weighted_price
            
            # Categorize deviation
            if abs(deviation) > 0.01:  # > 1%
                category = "HIGH_DEVIATION"
            elif abs(deviation) > 0.005:  # > 0.5%
                category = "MEDIUM_DEVIATION"
            else:
                category = "LOW_DEVIATION"
            
            return {
                "vwap": round(weighted_price, 2),
                "current_price": round(current_price, 2),
                "deviation": round(deviation, 4),
                "deviation_pct": round(deviation * 100, 2),
                "category": category,
                "total_volume": round(total_volume, 4)
            }
            
        except Exception as e:
            logger.error(f"❌ VWAP calculation failed: {e}")
            return {"vwap": 0.0, "deviation": 0.0, "category": "ERROR"}
    
    def _detect_large_trades(self) -> Dict[str, Any]:
        """Detect and analyze large trades"""
        try:
            if len(self._trade_history) < 10:
                return {"large_trades": [], "count": 0, "impact": "INSUFFICIENT_DATA"}
            
            # Get recent trades
            recent_trades = self._trade_history[-100:]
            trade_sizes = [t["size"] for t in recent_trades]
            
            if not trade_sizes:
                return {"large_trades": [], "count": 0, "impact": "NO_DATA"}
            
            # Calculate threshold for large trades (top 10% by size)
            sorted_sizes = sorted(trade_sizes, reverse=True)
            threshold_index = max(1, len(sorted_sizes) // 10)  # Top 10%
            large_trade_threshold = sorted_sizes[threshold_index]
            
            # Find large trades
            large_trades = [t for t in recent_trades if t["size"] >= large_trade_threshold]
            
            # Analyze large trade impact
            if len(large_trades) == 0:
                impact = "NO_LARGE_TRADES"
            elif len(large_trades) > 5:
                impact = "HIGH_LARGE_TRADE_ACTIVITY"
            elif len(large_trades) > 2:
                impact = "MODERATE_LARGE_TRADE_ACTIVITY"
            else:
                impact = "LOW_LARGE_TRADE_ACTIVITY"
            
            # Calculate large trade statistics
            large_trade_sizes = [t["size"] for t in large_trades]
            avg_large_size = sum(large_trade_sizes) / len(large_trade_sizes) if large_trade_sizes else 0
            
            return {
                "large_trades": [
                    {
                        "size": round(t["size"], 4),
                        "price": round(t["price"], 2),
                        "side": t["side"],
                        "timestamp": t["timestamp"]
                    } for t in large_trades[-5:]  # Last 5 large trades
                ],
                "count": len(large_trades),
                "threshold": round(large_trade_threshold, 4),
                "avg_large_size": round(avg_large_size, 4),
                "impact": impact,
                "percentage_of_trades": round(len(large_trades) / len(recent_trades) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"❌ Large trade detection failed: {e}")
            return {"large_trades": [], "count": 0, "impact": "ERROR"}
    
    def _analyze_trade_frequency(self) -> Dict[str, Any]:
        """Analyze trade frequency patterns"""
        try:
            if len(self._trade_history) < 10:
                return {"frequency": "INSUFFICIENT_DATA", "pattern": "UNKNOWN"}
            
            # Get recent trades (last 5 minutes)
            current_time = time.time()
            recent_trades = [t for t in self._trade_history if current_time - t["timestamp"] < 300]  # 5 minutes
            
            if len(recent_trades) < 5:
                return {"frequency": "LOW", "pattern": "SPARSE"}
            
            # Calculate trades per minute
            trades_per_minute = len(recent_trades) / 5
            
            # Categorize frequency
            if trades_per_minute > 20:
                frequency = "VERY_HIGH"
            elif trades_per_minute > 10:
                frequency = "HIGH"
            elif trades_per_minute > 5:
                frequency = "MEDIUM"
            elif trades_per_minute > 2:
                frequency = "LOW"
            else:
                frequency = "VERY_LOW"
            
            # Analyze pattern (burst vs steady)
            if len(recent_trades) > 20:
                # Check for burst patterns
                time_gaps = []
                for i in range(1, len(recent_trades)):
                    gap = recent_trades[i]["timestamp"] - recent_trades[i-1]["timestamp"]
                    time_gaps.append(gap)
                
                avg_gap = sum(time_gaps) / len(time_gaps)
                gap_variance = sum((gap - avg_gap) ** 2 for gap in time_gaps) / len(time_gaps)
                
                if gap_variance > avg_gap * 2:
                    pattern = "BURSTY"
                else:
                    pattern = "STEADY"
            else:
                pattern = "INSUFFICIENT_DATA"
            
            return {
                "frequency": frequency,
                "pattern": pattern,
                "trades_per_minute": round(trades_per_minute, 1),
                "total_recent_trades": len(recent_trades),
                "time_window_minutes": 5
            }
            
        except Exception as e:
            logger.error(f"❌ Trade frequency analysis failed: {e}")
            return {"frequency": "ERROR", "pattern": "UNKNOWN"}
    
    def _analyze_market_microstructure(self) -> Dict[str, Any]:
        """Analyze market microstructure patterns"""
        try:
            if len(self._trade_history) < 20:
                return {"microstructure": "INSUFFICIENT_DATA", "characteristics": []}
            
            # Get recent trades
            recent_trades = self._trade_history[-50:]
            
            characteristics = []
            
            # 1. Check for price clustering
            prices = [t["price"] for t in recent_trades]
            price_rounding = sum(1 for p in prices if p % 1 == 0) / len(prices)
            if price_rounding > 0.3:
                characteristics.append("PRICE_CLUSTERING")
            
            # 2. Check for size clustering
            sizes = [t["size"] for t in recent_trades]
            size_rounding = sum(1 for s in sizes if s % 0.1 == 0) / len(sizes)
            if size_rounding > 0.4:
                characteristics.append("SIZE_CLUSTERING")
            
            # 3. Check for alternating buy/sell patterns
            sides = [t["side"] for t in recent_trades]
            alternations = sum(1 for i in range(1, len(sides)) if sides[i] != sides[i-1])
            alternation_ratio = alternations / (len(sides) - 1) if len(sides) > 1 else 0
            if alternation_ratio > 0.7:
                characteristics.append("HIGH_ALTERNATION")
            
            # 4. Check for momentum patterns
            buy_sequences = []
            sell_sequences = []
            current_sequence = 1
            for i in range(1, len(sides)):
                if sides[i] == sides[i-1]:
                    current_sequence += 1
                else:
                    if sides[i-1] == "buy":
                        buy_sequences.append(current_sequence)
                    else:
                        sell_sequences.append(current_sequence)
                    current_sequence = 1
            
            # Add the last sequence
            if sides:
                if sides[-1] == "buy":
                    buy_sequences.append(current_sequence)
                else:
                    sell_sequences.append(current_sequence)
            
            max_buy_sequence = max(buy_sequences) if buy_sequences else 0
            max_sell_sequence = max(sell_sequences) if sell_sequences else 0
            
            if max_buy_sequence > 5 or max_sell_sequence > 5:
                characteristics.append("MOMENTUM_PATTERNS")
            
            # Determine overall microstructure type
            if len(characteristics) >= 3:
                microstructure = "COMPLEX"
            elif len(characteristics) >= 2:
                microstructure = "MODERATE"
            elif len(characteristics) >= 1:
                microstructure = "SIMPLE"
            else:
                microstructure = "RANDOM"
            
            return {
                "microstructure": microstructure,
                "characteristics": characteristics,
                "price_clustering": round(price_rounding, 3),
                "size_clustering": round(size_rounding, 3),
                "alternation_ratio": round(alternation_ratio, 3),
                "max_buy_sequence": max_buy_sequence,
                "max_sell_sequence": max_sell_sequence
            }
            
        except Exception as e:
            logger.error(f"❌ Market microstructure analysis failed: {e}")
            return {"microstructure": "ERROR", "characteristics": []}
    
