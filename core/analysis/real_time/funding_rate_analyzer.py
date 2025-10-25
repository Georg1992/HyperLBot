#!/usr/bin/env python3
"""
Funding Rate Analyzer Module
Analyzes funding rates for market sentiment and trend insights
"""

import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from loguru import logger

# Factory function for dependency injection
def create_funding_rate_analyzer() -> 'FundingRateAnalyzer':
    """
    Factory function to create FundingRateAnalyzer with dependency injection
    
    Returns:
        Configured FundingRateAnalyzer instance
    """
    return FundingRateAnalyzer()

# Global instance for backward compatibility (DEPRECATED - use create_funding_rate_analyzer)
_global_funding_rate_analyzer = None

def get_global_funding_rate_analyzer() -> 'FundingRateAnalyzer':
    """Get the global FundingRateAnalyzer singleton instance (DEPRECATED)"""
    global _global_funding_rate_analyzer
    if _global_funding_rate_analyzer is None:
        _global_funding_rate_analyzer = create_funding_rate_analyzer()
    return _global_funding_rate_analyzer

class FundingRateAnalyzer:
    """Analyzes funding rates for market sentiment and trend insights"""
    
    def __init__(self):
        # Store funding rate history for trend analysis
        self._funding_rate_history = []
        self._max_history = 100  # Keep last 100 funding rate readings
        
        logger.info("📊 Funding Rate Analyzer initialized")
    
    def analyze_funding_rate(self, funding_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze funding rate data for market insights
        
        Args:
            funding_data: Raw funding rate data from Hyperliquid API
            
        Returns:
            Dictionary with funding rate analysis
        """
        try:
            if not funding_data:
                raise Exception("No funding rate data provided")
            
            # Extract funding rate
            funding_rate = funding_data.get('funding_rate', 0.0)
            funding_rate_pct = funding_data.get('funding_rate_percentage', 0.0)
            
            # Update history
            self._update_funding_history(funding_rate, funding_data)
            
            # Calculate analysis metrics
            analysis = {
                "current_funding_rate": funding_rate,
                "current_funding_rate_pct": funding_rate_pct,
                "funding_trend": self._calculate_funding_trend(),
                "funding_sentiment": self._analyze_funding_sentiment(funding_rate),
                "extreme_funding_detection": self._detect_extreme_funding(funding_rate),
                "funding_volatility": self._calculate_funding_volatility(),
                "next_funding_time": funding_data.get('next_funding_time', 0),
                "data_source": funding_data.get('data_source', 'unknown'),
                "timestamp": time.time()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Funding rate analysis failed: {e}")
            raise Exception(f"Funding rate analysis failed: {e}")
    
    def _update_funding_history(self, funding_rate: float, funding_data: Dict[str, Any]):
        """Update funding rate history for trend analysis"""
        try:
            current_time = time.time()
            
            # Add to history
            self._funding_rate_history.append({
                "timestamp": current_time,
                "funding_rate": funding_rate,
                "data_source": funding_data.get('data_source', 'unknown')
            })
            
            # Keep only recent history
            if len(self._funding_rate_history) > self._max_history:
                self._funding_rate_history = self._funding_rate_history[-self._max_history:]
                
        except Exception as e:
            logger.error(f"❌ Failed to update funding history: {e}")
    
    def _calculate_funding_trend(self) -> Dict[str, Any]:
        """Calculate funding rate trend over time"""
        try:
            if len(self._funding_rate_history) < 3:
                return {"trend": "INSUFFICIENT_DATA", "direction": "NEUTRAL", "strength": 0.0}
            
            # Get recent funding rates (last 10 readings)
            recent_rates = [entry["funding_rate"] for entry in self._funding_rate_history[-10:]]
            
            # Calculate trend direction
            first_rate = recent_rates[0]
            last_rate = recent_rates[-1]
            rate_change = last_rate - first_rate
            
            # Calculate trend strength
            rate_volatility = max(recent_rates) - min(recent_rates)
            if rate_volatility == 0:
                strength = 0.0
            else:
                strength = abs(rate_change) / rate_volatility
            
            # Determine trend direction
            if rate_change > 0.0001:  # 0.01% increase
                direction = "INCREASING"
            elif rate_change < -0.0001:  # 0.01% decrease
                direction = "DECREASING"
            else:
                direction = "STABLE"
            
            # Determine trend strength category
            if strength > 0.7:
                trend_strength = "STRONG"
            elif strength > 0.4:
                trend_strength = "MODERATE"
            elif strength > 0.1:
                trend_strength = "WEAK"
            else:
                trend_strength = "MINIMAL"
            
            return {
                "trend": f"{direction}_{trend_strength}",
                "direction": direction,
                "strength": round(strength, 3),
                "rate_change": round(rate_change, 6),
                "rate_change_pct": round(rate_change * 100, 4),
                "volatility": round(rate_volatility, 6),
                "data_points": len(recent_rates)
            }
            
        except Exception as e:
            logger.error(f"❌ Funding trend calculation failed: {e}")
            return {"trend": "ERROR", "direction": "UNKNOWN", "strength": 0.0}
    
    def _analyze_funding_sentiment(self, funding_rate: float) -> Dict[str, Any]:
        """Analyze market sentiment based on funding rate using dynamic thresholds"""
        try:
            # Calculate dynamic thresholds based on historical funding rate data
            thresholds = self._calculate_dynamic_thresholds()
            
            # Categorize funding rate using dynamic thresholds
            if funding_rate > thresholds['extreme_positive']:
                sentiment = "EXTREME_BULLISH"
                description = f"Very high funding ({funding_rate*100:.3f}%) - extreme bullish sentiment"
                risk_level = "HIGH"
            elif funding_rate > thresholds['high_positive']:
                sentiment = "BULLISH"
                description = f"High funding ({funding_rate*100:.3f}%) - bullish sentiment"
                risk_level = "MEDIUM"
            elif funding_rate > thresholds['low_positive']:
                sentiment = "SLIGHTLY_BULLISH"
                description = f"Positive funding ({funding_rate*100:.3f}%) - slightly bullish"
                risk_level = "LOW"
            elif funding_rate > thresholds['low_negative']:
                sentiment = "NEUTRAL"
                description = f"Neutral funding ({funding_rate*100:.3f}%) - balanced sentiment"
                risk_level = "LOW"
            elif funding_rate > thresholds['high_negative']:
                sentiment = "SLIGHTLY_BEARISH"
                description = f"Negative funding ({funding_rate*100:.3f}%) - slightly bearish"
                risk_level = "LOW"
            elif funding_rate > thresholds['extreme_negative']:
                sentiment = "BEARISH"
                description = f"Low funding ({funding_rate*100:.3f}%) - bearish sentiment"
                risk_level = "MEDIUM"
            else:  # Below extreme negative threshold
                sentiment = "EXTREME_BEARISH"
                description = f"Very low funding ({funding_rate*100:.3f}%) - extreme bearish sentiment"
                risk_level = "HIGH"
            
            return {
                "sentiment": sentiment,
                "description": description,
                "risk_level": risk_level,
                "funding_rate_pct": round(funding_rate * 100, 4),
                "thresholds_used": thresholds
            }
            
        except Exception as e:
            logger.error(f"❌ Funding sentiment analysis failed: {e}")
            return {"sentiment": "ERROR", "description": "Analysis failed", "risk_level": "UNKNOWN"}
    
    def _detect_extreme_funding(self, funding_rate: float) -> Dict[str, Any]:
        """Detect extreme funding rate conditions"""
        try:
            # Define extreme thresholds
            extreme_positive = 0.001  # 0.1%
            extreme_negative = -0.001  # -0.1%
            
            is_extreme = False
            extreme_type = "NORMAL"
            extreme_description = "Funding rate within normal range"
            
            if funding_rate > extreme_positive:
                is_extreme = True
                extreme_type = "EXTREME_POSITIVE"
                extreme_description = f"Extreme positive funding: {funding_rate*100:.3f}%"
            elif funding_rate < extreme_negative:
                is_extreme = True
                extreme_type = "EXTREME_NEGATIVE"
                extreme_description = f"Extreme negative funding: {funding_rate*100:.3f}%"
            
            # Check for reversal potential
            reversal_potential = "NONE"
            if is_extreme:
                if extreme_type == "EXTREME_POSITIVE":
                    reversal_potential = "BEARISH_REVERSAL"
                elif extreme_type == "EXTREME_NEGATIVE":
                    reversal_potential = "BULLISH_REVERSAL"
            
            return {
                "is_extreme": is_extreme,
                "extreme_type": extreme_type,
                "description": extreme_description,
                "reversal_potential": reversal_potential,
                "threshold_breach": abs(funding_rate) - abs(extreme_positive if funding_rate > 0 else extreme_negative)
            }
            
        except Exception as e:
            logger.error(f"❌ Extreme funding detection failed: {e}")
            return {"is_extreme": False, "extreme_type": "ERROR", "description": "Detection failed"}
    
    def _calculate_funding_volatility(self) -> Dict[str, Any]:
        """Calculate funding rate volatility"""
        try:
            if len(self._funding_rate_history) < 5:
                return {"volatility": 0.0, "category": "INSUFFICIENT_DATA"}
            
            # Get recent funding rates
            recent_rates = [entry["funding_rate"] for entry in self._funding_rate_history[-20:]]
            
            # Calculate standard deviation
            mean_rate = sum(recent_rates) / len(recent_rates)
            variance = sum((rate - mean_rate) ** 2 for rate in recent_rates) / len(recent_rates)
            volatility = variance ** 0.5
            
            # Categorize volatility
            if volatility > 0.0005:  # > 0.05%
                category = "HIGH"
            elif volatility > 0.0002:  # > 0.02%
                category = "MEDIUM"
            elif volatility > 0.0001:  # > 0.01%
                category = "LOW"
            else:
                category = "VERY_LOW"
            
            return {
                "volatility": round(volatility, 6),
                "volatility_pct": round(volatility * 100, 4),
                "category": category,
                "mean_rate": round(mean_rate, 6),
                "data_points": len(recent_rates)
            }
            
        except Exception as e:
            logger.error(f"❌ Funding volatility calculation failed: {e}")
            return {"volatility": 0.0, "category": "ERROR"}
    
    def _calculate_dynamic_thresholds(self) -> Dict[str, float]:
        """Calculate dynamic thresholds based on historical funding rate data"""
        try:
            if len(self._funding_rate_history) < 10:
                # Use industry-standard thresholds if insufficient data
                return {
                    'extreme_positive': 0.001,   # 0.1%
                    'high_positive': 0.0005,     # 0.05%
                    'low_positive': 0.0001,     # 0.01%
                    'low_negative': -0.0001,     # -0.01%
                    'high_negative': -0.0005,    # -0.05%
                    'extreme_negative': -0.001,  # -0.1%
                    'data_source': 'industry_standard'
                }
            
            # Get recent funding rates for analysis
            recent_rates = [entry["funding_rate"] for entry in self._funding_rate_history[-50:]]
            
            # Calculate percentiles for dynamic thresholds
            sorted_rates = sorted(recent_rates)
            n = len(sorted_rates)
            
            # Calculate percentiles (90th, 75th, 25th, 10th percentiles)
            extreme_positive = sorted_rates[int(n * 0.9)] if n > 0 else 0.001
            high_positive = sorted_rates[int(n * 0.75)] if n > 0 else 0.0005
            low_positive = sorted_rates[int(n * 0.6)] if n > 0 else 0.0001
            low_negative = sorted_rates[int(n * 0.4)] if n > 0 else -0.0001
            high_negative = sorted_rates[int(n * 0.25)] if n > 0 else -0.0005
            extreme_negative = sorted_rates[int(n * 0.1)] if n > 0 else -0.001
            
            return {
                'extreme_positive': max(0.0005, extreme_positive),  # Minimum 0.05%
                'high_positive': max(0.0002, high_positive),       # Minimum 0.02%
                'low_positive': max(0.00005, low_positive),         # Minimum 0.005%
                'low_negative': min(-0.00005, low_negative),        # Maximum -0.005%
                'high_negative': min(-0.0002, high_negative),       # Maximum -0.02%
                'extreme_negative': min(-0.0005, extreme_negative), # Maximum -0.05%
                'data_source': 'historical_analysis',
                'data_points': n
            }
            
        except Exception as e:
            logger.error(f"❌ Dynamic threshold calculation failed: {e}")
            # Fallback to industry standards
            return {
                'extreme_positive': 0.001,
                'high_positive': 0.0005,
                'low_positive': 0.0001,
                'low_negative': -0.0001,
                'high_negative': -0.0005,
                'extreme_negative': -0.001,
                'data_source': 'fallback_industry_standard'
            }
    
