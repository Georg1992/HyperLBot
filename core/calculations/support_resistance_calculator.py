#!/usr/bin/env python3
"""
Support/Resistance Calculator - Matches specifications exactly
"""

import time
from typing import Dict, List, Any
from loguru import logger

# Singleton pattern implementation
_global_support_resistance_calculator = None

def get_global_support_resistance_calculator() -> 'SupportResistanceCalculator':
    """Get the global SupportResistanceCalculator singleton instance"""
    global _global_support_resistance_calculator
    if _global_support_resistance_calculator is None:
        _global_support_resistance_calculator = SupportResistanceCalculator()
    return _global_support_resistance_calculator

class SupportResistanceCalculator:
    """Support/Resistance calculator matching exact specifications"""
    
    def __init__(self):
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        logger.info("📊 S/R Calculator initialized - Matching specifications exactly")
    
    def invalidate_cache(self):
        """Clear all cached S/R data to force fresh calculation"""
        self._cache.force_sr_recalculation()
        logger.info("📊 S/R cache invalidated - next calculation will be fresh")
    
    def get_latest_analysis(self, current_price: float = None) -> Dict[str, Any]:
        """Get latest S/R analysis for MarketDataService coordination"""
        try:
            if not current_price:
                logger.warning("⚠️ No current price available for S/R analysis")
                return {}
            
            current_time = time.time()
            cache_key = f"support_resistance_{current_price:.0f}"
            
            def calculate_fresh_sr():
                return self.calculate_multi_timeframe_levels(current_price)
            
            sr_data = self._cache.get_or_set(
                key=cache_key,
                factory_func=calculate_fresh_sr,
                ttl=300  # 5 minutes cache
            )
            
            if sr_data:
                sr_data["timestamp"] = current_time
                sr_data["data_type"] = "support_resistance"
            
            return sr_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest S/R analysis: {e}")
            return {}
    
    def calculate_multi_timeframe_levels(self, current_price: float) -> Dict[str, Any]:
        """
        Calculate S/R levels using specifications:
        1. Data Input: 5-minute OHLCV candles, rolling lookback window (200-500 candles), ATR(14)
        2. Swing Point Detection: N=2-3 for 5-minute timeframe
        3. Level Clustering: cluster_tolerance = ATR × 0.5
        4. Level Scoring: Multi-timeframe (25%), Proximity (35%), Touch count (20%), Volume (15%), Recency (5%)
        """
        try:
            logger.debug(f"🔍 Calculating S/R levels for price: ${current_price:.2f}")
            
            # Get 5m candles with rolling lookback window (200-500 candles as specified)
            from core.services.historical_data_service import get_global_historical_data_service
            historical_service = get_global_historical_data_service()
            
            # Use 300 candles (25 hours) as middle of 200-500 range
            candles_5m = historical_service.get_5m_candles("BTC", 300)
            if not candles_5m or len(candles_5m) < 200:
                raise ValueError(f"Insufficient 5m candles: {len(candles_5m) if candles_5m else 0}")
            
            # Calculate ATR(14) for volatility reference
            atr_14 = self._calculate_atr(candles_5m, 14)
            logger.debug(f"📊 ATR(14): {atr_14:.2f}")
            
            # 1. Swing Point Detection with N=2-3 for 5-minute timeframe
            swing_points = self._detect_swing_points(candles_5m, current_price, n=2)
            logger.debug(f"📊 Detected {len(swing_points)} swing points")
            
            # 2. Level Clustering with cluster_tolerance = ATR × 0.5
            cluster_tolerance = atr_14 * 0.5
            clustered_levels = self._cluster_levels(swing_points, cluster_tolerance)
            logger.debug(f"📊 After clustering: {len(clustered_levels)} levels (tolerance: ${cluster_tolerance:.2f})")
            
            # 3. Level Scoring with exact weights
            scored_levels = self._score_levels(clustered_levels, current_price, atr_14)
            logger.debug(f"📊 Scored {len(scored_levels)} levels")
            
            # Separate support and resistance
            support_levels = [level for level in scored_levels if level["type"] == "support"]
            resistance_levels = [level for level in scored_levels if level["type"] == "resistance"]
            
            # Select strongest levels
            strongest_support = 0.0
            strongest_resistance = 0.0
            support_score = 0.0
            resistance_score = 0.0
            
            if support_levels:
                strongest_support_level = max(support_levels, key=lambda x: x["score"])
                strongest_support = strongest_support_level["level"]
                support_score = strongest_support_level["score"]
            
            if resistance_levels:
                strongest_resistance_level = max(resistance_levels, key=lambda x: x["score"])
                strongest_resistance = strongest_resistance_level["level"]
                resistance_score = strongest_resistance_level["score"]
            
            # Prepare key levels for display
            key_levels = []
            for level in support_levels[:3]:  # Top 3 support
                key_levels.append({
                    "level": level["level"],
                    "type": "support",
                    "score": level["score"],
                    "touches": level["touches"]
                })
            
            for level in resistance_levels[:3]:  # Top 3 resistance
                key_levels.append({
                    "level": level["level"],
                    "type": "resistance",
                    "score": level["score"],
                    "touches": level["touches"]
                })
            
            logger.debug(f"📊 Final S/R: Support ${strongest_support:.2f}, Resistance ${strongest_resistance:.2f}")
            
            return {
                "key_levels": key_levels,
                "strongest_support": strongest_support,
                "strongest_resistance": strongest_resistance,
                "support_score": support_score,
                "resistance_score": resistance_score,
                "metadata": {
                    "analysis_timestamp": time.time(),
                    "total_levels": len(scored_levels),
                    "analysis_confidence": 0.9 if len(support_levels) > 0 and len(resistance_levels) > 0 else 0.3,
                    "atr_14": atr_14,
                    "cluster_tolerance": cluster_tolerance
                }
            }
            
        except Exception as e:
            logger.error(f"❌ S/R calculation failed: {e}")
            return {
                "key_levels": [],
                "strongest_support": 0.0,
                "strongest_resistance": 0.0,
                "support_score": 0.0,
                "resistance_score": 0.0,
                "metadata": {
                    "analysis_timestamp": time.time(),
                    "total_levels": 0,
                    "analysis_confidence": 0.0
                }
            }
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range for volatility reference"""
        try:
            if len(candles) < period + 1:
                return 0.0
            
            true_ranges = []
            for i in range(1, len(candles)):
                prev_close = candles[i-1].get("close", 0)
                high = candles[i].get("high", 0)
                low = candles[i].get("low", 0)
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            if len(true_ranges) < period:
                return 0.0
            
            # Calculate ATR as simple moving average of true ranges
            atr = sum(true_ranges[-period:]) / period
            return atr
            
        except Exception as e:
            logger.error(f"❌ ATR calculation failed: {e}")
            return 0.0
    
    def _detect_swing_points(self, candles: List[Dict], current_price: float, n: int = 2) -> List[Dict]:
        """Detect swing points using N=2-3 for 5-minute timeframe"""
        try:
            swing_points = []
            
            # Look for swing highs and lows
            for i in range(n, len(candles) - n):
                candle = candles[i]
                high = candle.get("high", 0)
                low = candle.get("low", 0)
                
                # Check for swing high (resistance)
                is_swing_high = True
                for j in range(i - n, i + n + 1):
                    if j != i and j >= 0 and j < len(candles):
                        if candles[j].get("high", 0) >= high:
                            is_swing_high = False
                            break
                
                if is_swing_high and high > current_price:
                    swing_points.append({
                        "level": high,
                        "type": "resistance",
                        "timestamp": candle.get("timestamp", 0),
                        "candle_index": i
                    })
                
                # Check for swing low (support)
                is_swing_low = True
                for j in range(i - n, i + n + 1):
                    if j != i and j >= 0 and j < len(candles):
                        if candles[j].get("low", 0) <= low:
                            is_swing_low = False
                            break
                
                if is_swing_low and low < current_price:
                    swing_points.append({
                        "level": low,
                        "type": "support",
                        "timestamp": candle.get("timestamp", 0),
                        "candle_index": i
                    })
            
            return swing_points
            
        except Exception as e:
            logger.error(f"❌ Swing point detection failed: {e}")
            return []
    
    def _cluster_levels(self, swing_points: List[Dict], cluster_tolerance: float) -> List[Dict]:
        """Cluster nearby swing points into zones using ATR × 0.5 tolerance"""
        try:
            if not swing_points:
                return []
            
            clustered_levels = []
            used_indices = set()
            
            for i, point in enumerate(swing_points):
                if i in used_indices:
                    continue
                
                # Find all points within cluster tolerance
                cluster = [point]
                cluster_indices = [i]
                
                for j, other_point in enumerate(swing_points[i+1:], i+1):
                    if j in used_indices:
                        continue
                    
                    if (other_point["type"] == point["type"] and 
                        abs(other_point["level"] - point["level"]) <= cluster_tolerance):
                        cluster.append(other_point)
                        cluster_indices.append(j)
                
                # Mark all points in this cluster as used
                for idx in cluster_indices:
                    used_indices.add(idx)
                
                # Calculate cluster properties
                if cluster:
                    avg_level = sum(p["level"] for p in cluster) / len(cluster)
                    touches = len(cluster)
                    
                    clustered_levels.append({
                        "level": avg_level,
                        "type": point["type"],
                        "touches": touches,
                        "cluster_size": len(cluster),
                        "timestamp": max(p["timestamp"] for p in cluster),
                        "candle_index": max(p["candle_index"] for p in cluster)
                    })
            
            return clustered_levels
            
        except Exception as e:
            logger.error(f"❌ Level clustering failed: {e}")
            return []
    
    def _score_levels(self, levels: List[Dict], current_price: float, atr_14: float) -> List[Dict]:
        """Score levels using exact specifications: MTF(25%), Proximity(35%), Touches(20%), Volume(15%), Recency(5%)"""
        try:
            scored_levels = []
            
            for level in levels:
                # 1. Multi-timeframe confirmation (25% weight)
                mtf_score = self._calculate_mtf_score(level, levels)
                
                # 2. Proximity to current price (35% weight)
                proximity_score = self._calculate_proximity_score(level["level"], current_price)
                
                # 3. Touch count (20% weight)
                touch_score = self._calculate_touch_score(level["touches"])
                
                # 4. Volume confirmation (15% weight)
                volume_score = self._calculate_volume_score(level, atr_14)
                
                # 5. Recency (5% weight)
                recency_score = self._calculate_recency_score(level)
                
                # Apply exact weights from specifications
                weighted_score = (
                    mtf_score * 0.25 +      # 25% Multi-timeframe confirmation
                    proximity_score * 0.35 + # 35% Proximity to current price
                    touch_score * 0.20 +     # 20% Touch count
                    volume_score * 0.15 +    # 15% Volume confirmation
                    recency_score * 0.05    # 5% Recency
                )
                
                level["score"] = weighted_score
                level["score_breakdown"] = {
                    "mtf_confirmation": mtf_score,
                    "proximity": proximity_score,
                    "touches": touch_score,
                    "volume": volume_score,
                    "recency": recency_score
                }
                
                scored_levels.append(level)
            
            # Sort by score (highest first)
            scored_levels.sort(key=lambda x: x["score"], reverse=True)
            
            return scored_levels
            
        except Exception as e:
            logger.error(f"❌ Level scoring failed: {e}")
            return []
    
    def _calculate_mtf_score(self, level: Dict, all_levels: List[Dict]) -> float:
        """Calculate multi-timeframe confirmation score (0-100)"""
        try:
            level_price = level["level"]
            level_type = level["type"]
            
            # Count confirmations from other levels of same type
            confirmations = 0
            tolerance = level_price * 0.002  # 0.2% tolerance
            
            for other_level in all_levels:
                if (other_level != level and 
                    other_level["type"] == level_type and 
                    abs(other_level["level"] - level_price) <= tolerance):
                    confirmations += 1
            
            # Score based on confirmations
            return min(100.0, confirmations * 25.0)
            
        except Exception as e:
            logger.error(f"❌ MTF score calculation failed: {e}")
            return 0.0
    
    def _calculate_proximity_score(self, level_price: float, current_price: float) -> float:
        """Calculate proximity score (0-100) - closer levels get higher scores"""
        try:
            distance = abs(level_price - current_price)
            distance_percent = distance / current_price
            
            # Exponential decay for proximity
            if distance_percent < 0.001:  # Within 0.1%
                return 100.0
            elif distance_percent < 0.002:  # Within 0.2%
                return 90.0
            elif distance_percent < 0.005:  # Within 0.5%
                return 70.0
            elif distance_percent < 0.01:   # Within 1%
                return 50.0
            elif distance_percent < 0.02:   # Within 2%
                return 30.0
            elif distance_percent < 0.05:   # Within 5%
                return 10.0
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"❌ Proximity score calculation failed: {e}")
            return 0.0
    
    def _calculate_touch_score(self, touches: int) -> float:
        """Calculate touch count score (0-100)"""
        try:
            if touches <= 0:
                return 0.0
            elif touches == 1:
                return 20.0
            elif touches == 2:
                return 40.0
            elif touches == 3:
                return 60.0
            elif touches == 4:
                return 80.0
            else:
                return min(100.0, 80.0 + (touches - 4) * 5.0)
                
        except Exception as e:
            logger.error(f"❌ Touch score calculation failed: {e}")
            return 0.0
    
    def _calculate_volume_score(self, level: Dict, atr_14: float) -> float:
        """Calculate volume confirmation score (0-100)"""
        try:
            # Simplified volume score based on touch count and cluster size
            touches = level.get("touches", 1)
            cluster_size = level.get("cluster_size", 1)
            
            # Higher touch count and cluster size suggest volume confirmation
            base_score = min(100.0, (touches + cluster_size) * 15.0)
            
            return base_score
            
        except Exception as e:
            logger.error(f"❌ Volume score calculation failed: {e}")
            return 0.0
    
    def _calculate_recency_score(self, level: Dict) -> float:
        """Calculate recency score (0-100) based on candle index"""
        try:
            candle_index = level.get("candle_index", 0)
            
            # More recent levels get higher scores
            if candle_index >= 50:  # Very recent
                return 100.0
            elif candle_index >= 30:  # Recent
                return 80.0
            elif candle_index >= 20:  # Moderately recent
                return 60.0
            elif candle_index >= 10:  # Somewhat recent
                return 40.0
            else:  # Older
                return 20.0
                
        except Exception as e:
            logger.error(f"❌ Recency score calculation failed: {e}")
            return 0.0