#!/usr/bin/env python3
"""
Support/Resistance Calculator Module
Centralized support and resistance level calculations
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class SupportResistanceCalculator:
    """Centralized support and resistance calculation system"""
    
    def __init__(self):
        logger.info("📊 Support/Resistance Calculator initialized")
    
    def calculate_support_resistance(self, candles: List[Dict], lookback: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels from candle data"""
        try:
            if len(candles) < lookback:
                return {"support": 0.0, "resistance": 0.0}
            
            recent_candles = candles[-lookback:]
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in recent_candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in recent_candles]
            
            # Calculate basic support and resistance
            resistance = max(highs) if highs else 0.0
            support = min(lows) if lows else 0.0
            
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Support/resistance calculation failed: {e}")
            return {"support": 0.0, "resistance": 0.0}
    
    def calculate_pivot_levels(self, candles: List[Dict], periods: int = 10) -> Dict[str, float]:
        """Calculate pivot point levels for advanced support/resistance"""
        try:
            if len(candles) < periods:
                return {"pivot": 0.0, "support1": 0.0, "resistance1": 0.0}
            
            recent_candles = candles[-periods:]
            
            # Calculate pivot point (average of high, low, close)
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in recent_candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in recent_candles]
            closes = [float(candle.get("close", 0)) for candle in recent_candles]
            
            avg_high = sum(highs) / len(highs) if highs else 0.0
            avg_low = sum(lows) / len(lows) if lows else 0.0
            avg_close = sum(closes) / len(closes) if closes else 0.0
            
            pivot = (avg_high + avg_low + avg_close) / 3
            
            # Calculate support and resistance levels
            support1 = 2 * pivot - avg_high
            resistance1 = 2 * pivot - avg_low
            
            return {
                "pivot": round(pivot, 2),
                "support1": round(support1, 2),
                "resistance1": round(resistance1, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Pivot level calculation failed: {e}")
            return {"pivot": 0.0, "support1": 0.0, "resistance1": 0.0}
    
    def identify_key_levels(self, candles: List[Dict], min_touches: int = 2) -> Dict[str, Any]:
        """Identify key support/resistance levels based on price action"""
        try:
            if len(candles) < 10:
                return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
            
            # Extract price levels
            closes = [float(candle.get("close", 0)) for candle in candles]
            highs = [float(candle.get("high", candle.get("close", 0))) for candle in candles]
            lows = [float(candle.get("low", candle.get("close", 0))) for candle in candles]
            
            # Find potential support/resistance levels (PRECISE approach)
            price_range = max(closes) - min(closes)
            level_tolerance = price_range * 0.001  # 0.1% tolerance (much more precise)
            
            # Identify levels where price has bounced multiple times
            key_levels = []
            
            # Get current price for proper support/resistance classification
            current_price = closes[-1] if closes else 0
            
            # SINGLE PRECISE APPROACH: Use clustering for all level detection
            # 1. Find levels from all historical data
            all_precise_levels = self._find_precise_levels(highs, lows, current_price, level_tolerance, min_touches)
            key_levels.extend(all_precise_levels)
            
            # 2. Find levels from recent data (last 20% of candles) for more relevance
            recent_candles_count = max(5, len(candles) // 5)  # Last 20% of candles
            recent_highs = highs[-recent_candles_count:]
            recent_lows = lows[-recent_candles_count:]
            
            recent_precise_levels = self._find_precise_levels(recent_highs, recent_lows, current_price, level_tolerance, min_touches)
            for level in recent_precise_levels:
                level["recent"] = True
            key_levels.extend(recent_precise_levels)
            
            # 3. Remove duplicates and sort by strength (touches)
            key_levels = self._remove_duplicate_levels(key_levels)
            
            # Find strongest levels
            support_levels = [lvl for lvl in key_levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in key_levels if lvl["type"] == "resistance"]
            
            strongest_support = max(support_levels, key=lambda x: x["touches"])["level"] if support_levels else min(lows)
            strongest_resistance = max(resistance_levels, key=lambda x: x["touches"])["level"] if resistance_levels else max(highs)
            
            return {
                "key_levels": key_levels,
                "strongest_support": round(strongest_support, 2),
                "strongest_resistance": round(strongest_resistance, 2),
                "level_count": len(key_levels)
            }
            
        except Exception as e:
            logger.error(f"❌ Key level identification failed: {e}")
            return {"key_levels": [], "strongest_support": 0.0, "strongest_resistance": 0.0}
    
    def _find_precise_levels(self, highs: List[float], lows: List[float], current_price: float, 
                           level_tolerance: float, min_touches: int) -> List[Dict[str, Any]]:
        """Find precise support/resistance levels using clustering approach"""
        try:
            levels = []
            
            # Combine all price points (highs and lows)
            all_prices = highs + lows
            
            # Sort prices for clustering
            all_prices.sort()
            
            # Find clusters of similar prices (precise level detection)
            clusters = []
            current_cluster = [all_prices[0]]
            
            for i in range(1, len(all_prices)):
                if all_prices[i] - current_cluster[-1] <= level_tolerance:
                    current_cluster.append(all_prices[i])
                else:
                    if len(current_cluster) >= min_touches:
                        clusters.append(current_cluster)
                    current_cluster = [all_prices[i]]
            
            # Add the last cluster
            if len(current_cluster) >= min_touches:
                clusters.append(current_cluster)
            
            # Convert clusters to precise levels
            for cluster in clusters:
                # Calculate precise level as median of cluster
                precise_level = statistics.median(cluster)
                
                # Count touches (how many times price hit this level)
                touches = len(cluster)
                
                # Determine if it's support or resistance based on current price
                # More flexible classification: support below current price, resistance above
                if precise_level < current_price:
                    levels.append({
                        "level": round(precise_level, 2),  # Round to nearest cent for precision
                        "type": "support",
                        "touches": touches,
                        "cluster_size": len(cluster),
                        "precision": "high"
                    })
                elif precise_level > current_price:
                    levels.append({
                        "level": round(precise_level, 2),  # Round to nearest cent for precision
                        "type": "resistance", 
                        "touches": touches,
                        "cluster_size": len(cluster),
                        "precision": "high"
                    })
            
            return levels
            
        except Exception as e:
            logger.error(f"❌ Precise level detection failed: {e}")
            return []
    
    def _remove_duplicate_levels(self, levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate levels and merge similar ones"""
        try:
            if not levels:
                return []
            
            # Group levels by type (support/resistance)
            support_levels = [lvl for lvl in levels if lvl["type"] == "support"]
            resistance_levels = [lvl for lvl in levels if lvl["type"] == "resistance"]
            
            # Remove duplicates within each type
            unique_support = self._merge_similar_levels(support_levels)
            unique_resistance = self._merge_similar_levels(resistance_levels)
            
            # Combine and sort by strength (touches)
            all_levels = unique_support + unique_resistance
            all_levels.sort(key=lambda x: x["touches"], reverse=True)
            
            return all_levels
            
        except Exception as e:
            logger.error(f"❌ Duplicate removal failed: {e}")
            return levels
    
    def _merge_similar_levels(self, levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge levels that are very close to each other"""
        try:
            if not levels:
                return []
            
            # Sort by level price
            levels.sort(key=lambda x: x["level"])
            
            merged_levels = []
            current_level = levels[0]
            
            for next_level in levels[1:]:
                # If levels are within 0.1% of each other, merge them
                price_diff = abs(next_level["level"] - current_level["level"])
                if price_diff / current_level["level"] <= 0.001:  # 0.1% tolerance
                    # Merge: use the level with more touches, combine touch counts
                    if next_level["touches"] > current_level["touches"]:
                        current_level = next_level.copy()
                    current_level["touches"] = max(current_level["touches"], next_level["touches"])
                    # Mark as merged if it has recent data
                    if next_level.get("recent", False):
                        current_level["recent"] = True
                else:
                    # Levels are different enough, add current and move to next
                    merged_levels.append(current_level)
                    current_level = next_level
            
            # Add the last level
            merged_levels.append(current_level)
            
            return merged_levels
            
        except Exception as e:
            logger.error(f"❌ Level merging failed: {e}")
            return levels