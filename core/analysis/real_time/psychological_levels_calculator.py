#!/usr/bin/env python3
"""
Psychological Levels Calculator Module
Detects and analyzes psychological price levels for Bitcoin trading
"""

import math
from typing import Dict, List, Any, Tuple
from loguru import logger


class PsychologicalLevelsCalculator:
    """
    Calculates psychological price levels that traders focus on
    These are key levels that create support/resistance zones
    """
    
    def __init__(self):
        # Bitcoin psychological level patterns
        self.psychological_patterns = {
            # Round numbers (most important)
            "round_thousands": [1000, 2000, 3000, 5000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000, 130000, 140000, 150000],
            "round_hundreds": [100, 200, 300, 400, 500, 600, 700, 800, 900],
            "round_fifties": [50, 150, 250, 350, 450, 550, 650, 750, 850, 950],
            "round_twenty_fives": [25, 75, 125, 175, 225, 275, 325, 375, 425, 475, 525, 575, 625, 675, 725, 775, 825, 875, 925, 975],
            
            # Fibonacci levels (common in crypto)
            "fibonacci": [0.236, 0.382, 0.5, 0.618, 0.786],
            
            # Historical significant levels
            "historical_ath": [69000, 65000, 60000, 50000, 40000, 30000, 20000],
            "historical_atl": [3000, 5000, 10000, 15000, 20000],
            
            # Psychological half-levels
            "half_levels": [500, 1500, 2500, 3500, 4500, 5500, 6500, 7500, 8500, 9500, 105000, 115000, 125000, 135000, 145000]
        }
        
        logger.info("🧠 Psychological Levels Calculator initialized")
    
    def calculate_psychological_levels(self, current_price: float, price_range: float = 5000) -> Dict[str, Any]:
        """
        Calculate psychological levels around current price
        
        Args:
            current_price: Current Bitcoin price
            price_range: Range to look for levels (default 5000 = $5000 above/below)
        
        Returns:
            Dict with psychological levels and their significance
        """
        try:
            # Find relevant psychological levels around current price
            relevant_levels = self._find_relevant_levels(current_price, price_range)
            
            # Categorize levels by type and strength
            categorized_levels = self._categorize_levels(relevant_levels, current_price)
            
            # Calculate level significance scores
            significance_scores = self._calculate_significance_scores(categorized_levels, current_price)
            
            # Find nearest levels for trading decisions
            nearest_levels = self._find_nearest_levels(categorized_levels, current_price)
            
            # Calculate level attraction probability
            attraction_probability = self._calculate_attraction_probability(nearest_levels, current_price)
            
            return {
                "current_price": current_price,
                "relevant_levels": relevant_levels,
                "categorized_levels": categorized_levels,
                "significance_scores": significance_scores,
                "nearest_levels": nearest_levels,
                "attraction_probability": attraction_probability,
                "trading_implications": self._analyze_trading_implications(nearest_levels, current_price)
            }
            
        except Exception as e:
            logger.error(f"❌ Psychological levels calculation failed: {e}")
            return self._get_default_psychological_levels(current_price)
    
    def _find_relevant_levels(self, current_price: float, price_range: float) -> List[Dict[str, Any]]:
        """Find psychological levels within the specified price range"""
        relevant_levels = []
        
        # Check all psychological patterns
        for pattern_name, levels in self.psychological_patterns.items():
            for level in levels:
                # Check if level is within range
                if abs(level - current_price) <= price_range:
                    # Calculate distance and direction
                    distance = abs(level - current_price)
                    direction = "above" if level > current_price else "below"
                    
                    # Calculate strength based on pattern type
                    strength = self._calculate_pattern_strength(pattern_name, level)
                    
                    relevant_levels.append({
                        "level": level,
                        "pattern": pattern_name,
                        "distance": distance,
                        "direction": direction,
                        "strength": strength,
                        "significance": self._calculate_level_significance(level, pattern_name)
                    })
        
        # Sort by distance (closest first)
        relevant_levels.sort(key=lambda x: x["distance"])
        
        return relevant_levels
    
    def _categorize_levels(self, levels: List[Dict], current_price: float) -> Dict[str, List[Dict]]:
        """Categorize levels by type and strength"""
        categorized = {
            "strong_support": [],
            "strong_resistance": [],
            "moderate_support": [],
            "moderate_resistance": [],
            "weak_support": [],
            "weak_resistance": []
        }
        
        for level_data in levels:
            level = level_data["level"]
            strength = level_data["strength"]
            significance = level_data["significance"]
            
            # Determine if it's support or resistance
            if level < current_price:
                # Below current price = potential support
                if strength >= 0.8 and significance >= 0.8:
                    categorized["strong_support"].append(level_data)
                elif strength >= 0.6 and significance >= 0.6:
                    categorized["moderate_support"].append(level_data)
                else:
                    categorized["weak_support"].append(level_data)
            else:
                # Above current price = potential resistance
                if strength >= 0.8 and significance >= 0.8:
                    categorized["strong_resistance"].append(level_data)
                elif strength >= 0.6 and significance >= 0.6:
                    categorized["moderate_resistance"].append(level_data)
                else:
                    categorized["weak_resistance"].append(level_data)
        
        return categorized
    
    def _calculate_pattern_strength(self, pattern_name: str, level: float) -> float:
        """Calculate strength of psychological pattern"""
        strength_map = {
            "round_thousands": 1.0,      # Strongest - round thousands
            "round_hundreds": 0.9,       # Very strong - round hundreds
            "historical_ath": 0.8,       # Strong - historical ATH
            "round_fifties": 0.7,        # Moderate-strong - round fifties
            "half_levels": 0.6,          # Moderate - half levels
            "round_twenty_fives": 0.5,   # Weak-moderate - round 25s
            "fibonacci": 0.4,            # Weak - Fibonacci (less common in crypto)
            "historical_atl": 0.3        # Weakest - historical ATL
        }
        
        return strength_map.get(pattern_name, 0.5)
    
    def _calculate_level_significance(self, level: float, pattern_name: str) -> float:
        """Calculate significance of a specific level"""
        # Round thousands are most significant
        if level % 1000 == 0:
            return 1.0
        # Round hundreds are very significant
        elif level % 100 == 0:
            return 0.9
        # Round fifties are moderately significant
        elif level % 50 == 0:
            return 0.7
        # Round twenty-fives are less significant
        elif level % 25 == 0:
            return 0.5
        # Other levels
        else:
            return 0.3
    
    def _calculate_significance_scores(self, categorized_levels: Dict, current_price: float) -> Dict[str, float]:
        """Calculate overall significance scores for each category"""
        scores = {}
        
        for category, levels in categorized_levels.items():
            if not levels:
                scores[category] = 0.0
                continue
            
            # Calculate weighted average significance
            total_weight = 0
            weighted_sum = 0
            
            for level_data in levels:
                # Weight by inverse distance (closer = more important)
                weight = 1.0 / (1.0 + level_data["distance"] / 1000)  # Normalize distance
                weighted_sum += level_data["significance"] * weight
                total_weight += weight
            
            scores[category] = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return scores
    
    def _find_nearest_levels(self, categorized_levels: Dict, current_price: float) -> Dict[str, Any]:
        """Find the nearest levels in each category"""
        nearest = {}
        
        for category, levels in categorized_levels.items():
            if not levels:
                nearest[category] = None
                continue
            
            # Find closest level in this category
            closest = min(levels, key=lambda x: x["distance"])
            nearest[category] = closest
        
        return nearest
    
    def _calculate_attraction_probability(self, nearest_levels: Dict, current_price: float) -> Dict[str, float]:
        """Calculate probability of price being attracted to each level"""
        attraction = {}
        
        for category, level_data in nearest_levels.items():
            if not level_data:
                attraction[category] = 0.0
                continue
            
            level = level_data["level"]
            distance = level_data["distance"]
            strength = level_data["strength"]
            significance = level_data["significance"]
            
            # Calculate attraction probability based on:
            # 1. Inverse distance (closer = higher probability)
            # 2. Pattern strength
            # 3. Level significance
            
            distance_factor = 1.0 / (1.0 + distance / 500)  # Normalize distance
            attraction_prob = (strength * 0.4 + significance * 0.4 + distance_factor * 0.2)
            
            attraction[category] = min(1.0, attraction_prob)
        
        return attraction
    
    def _analyze_trading_implications(self, nearest_levels: Dict, current_price: float) -> Dict[str, Any]:
        """Analyze trading implications of psychological levels"""
        implications = {
            "primary_direction": "NEUTRAL",
            "confidence": 0.5,
            "target_levels": [],
            "risk_levels": [],
            "trading_bias": "NEUTRAL"
        }
        
        # Find strongest support and resistance
        strongest_support = nearest_levels.get("strong_support")
        strongest_resistance = nearest_levels.get("strong_resistance")
        
        # Also check moderate levels for better signal generation
        moderate_support = nearest_levels.get("moderate_support")
        moderate_resistance = nearest_levels.get("moderate_resistance")
        
        # Use strongest levels first, then moderate if no strong levels
        support_level = strongest_support or moderate_support
        resistance_level = strongest_resistance or moderate_resistance
        
        if support_level and resistance_level:
            support_distance = support_level["distance"]
            resistance_distance = resistance_level["distance"]
            
            # Determine primary direction based on relative distances and proximity
            distance_ratio = support_distance / resistance_distance if resistance_distance > 0 else 1.0
            
            # More aggressive direction determination
            if distance_ratio < 0.7:  # Support is significantly closer
                implications["primary_direction"] = "DOWN"
                implications["confidence"] = min(0.9, support_level["strength"] + 0.2)  # Boost confidence
                implications["target_levels"].append(support_level["level"])
                implications["trading_bias"] = "BEARISH"
            elif distance_ratio > 1.4:  # Resistance is significantly closer
                implications["primary_direction"] = "UP"
                implications["confidence"] = min(0.9, resistance_level["strength"] + 0.2)  # Boost confidence
                implications["target_levels"].append(resistance_level["level"])
                implications["trading_bias"] = "BULLISH"
            else:
                # Close distances - use level strength to determine bias
                if support_level["strength"] > resistance_level["strength"]:
                    implications["primary_direction"] = "DOWN"
                    implications["confidence"] = support_level["strength"]
                    implications["target_levels"].append(support_level["level"])
                    implications["trading_bias"] = "BEARISH"
                elif resistance_level["strength"] > support_level["strength"]:
                    implications["primary_direction"] = "UP"
                    implications["confidence"] = resistance_level["strength"]
                    implications["target_levels"].append(resistance_level["level"])
                    implications["trading_bias"] = "BULLISH"
        
        # Add risk levels (levels that could cause reversals)
        for category in ["strong_support", "strong_resistance", "moderate_support", "moderate_resistance"]:
            level_data = nearest_levels.get(category)
            if level_data and level_data["distance"] < 2000:  # Within $2000 (increased range)
                implications["risk_levels"].append(level_data["level"])
        
        return implications
    
    def _get_default_psychological_levels(self, current_price: float) -> Dict[str, Any]:
        """Return default psychological levels when calculation fails"""
        return {
            "current_price": current_price,
            "relevant_levels": [],
            "categorized_levels": {
                "strong_support": [],
                "strong_resistance": [],
                "moderate_support": [],
                "moderate_resistance": [],
                "weak_support": [],
                "weak_resistance": []
            },
            "significance_scores": {},
            "nearest_levels": {},
            "attraction_probability": {},
            "trading_implications": {
                "primary_direction": "NEUTRAL",
                "confidence": 0.5,
                "target_levels": [],
                "risk_levels": [],
                "trading_bias": "NEUTRAL"
            }
        }
    
    def get_psychological_level_signal(self, current_price: float, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signal based on psychological levels
        
        Args:
            current_price: Current Bitcoin price
            market_data: Additional market data (RSI, trend, etc.)
        
        Returns:
            Trading signal with psychological level analysis
        """
        try:
            # Calculate psychological levels
            psychological_analysis = self.calculate_psychological_levels(current_price)
            
            # Get trading implications
            implications = psychological_analysis["trading_implications"]
            
            # Combine with market data for enhanced signal
            rsi = market_data.get("rsi", 50)
            trend = market_data.get("trend", "NEUTRAL")
            
            # Determine signal strength
            signal_strength = self._calculate_signal_strength(implications, rsi, trend)
            
            # Generate signal
            signal = {
                "type": "PSYCHOLOGICAL_LEVEL",
                "direction": implications["primary_direction"],
                "confidence": signal_strength,
                "target_level": implications["target_levels"][0] if implications["target_levels"] else None,
                "risk_levels": implications["risk_levels"],
                "trading_bias": implications["trading_bias"],
                "psychological_analysis": psychological_analysis,
                "reasoning": self._generate_signal_reasoning(implications, rsi, trend)
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Psychological level signal generation failed: {e}")
            return {
                "type": "PSYCHOLOGICAL_LEVEL",
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "target_level": None,
                "risk_levels": [],
                "trading_bias": "NEUTRAL",
                "psychological_analysis": self._get_default_psychological_levels(current_price),
                "reasoning": "Psychological level analysis failed"
            }
    
    def _calculate_signal_strength(self, implications: Dict, rsi: float, trend: str) -> float:
        """Calculate signal strength based on psychological levels and market data"""
        base_confidence = implications["confidence"]
        
        # Adjust based on RSI
        rsi_factor = 1.0
        if implications["primary_direction"] == "UP" and rsi < 30:
            rsi_factor = 1.2  # Oversold + psychological support = stronger signal
        elif implications["primary_direction"] == "DOWN" and rsi > 70:
            rsi_factor = 1.2  # Overbought + psychological resistance = stronger signal
        elif implications["primary_direction"] == "UP" and rsi > 70:
            rsi_factor = 0.8  # Overbought + psychological support = weaker signal
        elif implications["primary_direction"] == "DOWN" and rsi < 30:
            rsi_factor = 0.8  # Oversold + psychological resistance = weaker signal
        
        # Adjust based on trend
        trend_factor = 1.0
        if implications["trading_bias"] == "BULLISH" and "UP" in trend:
            trend_factor = 1.1  # Trend aligns with psychological bias
        elif implications["trading_bias"] == "BEARISH" and "DOWN" in trend:
            trend_factor = 1.1  # Trend aligns with psychological bias
        elif implications["trading_bias"] == "BULLISH" and "DOWN" in trend:
            trend_factor = 0.9  # Trend contradicts psychological bias
        elif implications["trading_bias"] == "BEARISH" and "UP" in trend:
            trend_factor = 0.9  # Trend contradicts psychological bias
        
        final_confidence = base_confidence * rsi_factor * trend_factor
        return min(1.0, max(0.0, final_confidence))
    
    def _generate_signal_reasoning(self, implications: Dict, rsi: float, trend: str) -> str:
        """Generate human-readable reasoning for the signal"""
        direction = implications["primary_direction"]
        bias = implications["trading_bias"]
        confidence = implications["confidence"]
        
        reasoning_parts = []
        
        # Add psychological level reasoning
        if direction != "NEUTRAL":
            reasoning_parts.append(f"Psychological {direction.lower()} bias ({confidence:.1%} confidence)")
        
        # Add RSI reasoning
        if rsi < 30:
            reasoning_parts.append("RSI oversold")
        elif rsi > 70:
            reasoning_parts.append("RSI overbought")
        
        # Add trend reasoning
        if trend != "NEUTRAL":
            reasoning_parts.append(f"Trend: {trend}")
        
        # Add target level
        if implications["target_levels"]:
            target = implications["target_levels"][0]
            reasoning_parts.append(f"Target: ${target:,.0f}")
        
        return " | ".join(reasoning_parts) if reasoning_parts else "No clear psychological level signal"


# Global instance for easy access
global_psychological_levels_calculator = PsychologicalLevelsCalculator()
