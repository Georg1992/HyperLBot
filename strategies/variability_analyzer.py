#!/usr/bin/env python3
"""
Variability Theory Analyzer for BTC 5-Minute Trading Strategy
Analyzes market volatility patterns to optimize trading conditions
"""

import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from collections import deque

class VariabilityAnalyzer:
    def __init__(self, lookback_periods: int = 100):
        """
        Initialize variability analyzer
        
        Args:
            lookback_periods: Number of periods to analyze for variability patterns
        """
        self.lookback_periods = lookback_periods
        self.price_history = deque(maxlen=lookback_periods)
        self.volatility_history = deque(maxlen=lookback_periods)
        self.volume_history = deque(maxlen=lookback_periods)
        self.variability_scores = deque(maxlen=lookback_periods)
        
        # Variability thresholds
        self.variability_thresholds = {
            "low_volatility": 0.001,    # 0.1% - choppy market
            "medium_volatility": 0.003,  # 0.3% - normal trading
            "high_volatility": 0.008,    # 0.8% - volatile market
            "extreme_volatility": 0.015  # 1.5% - extreme volatility
        }
        
        # Trading condition scores (adjusted for crypto markets)
        self.condition_scores = {
            "optimal_trading": 0.7,      # 70% score for optimal conditions (lowered)
            "good_trading": 0.5,         # 50% score for good conditions (lowered)
            "poor_trading": 0.2          # 20% score for poor conditions (lowered)
        }
        
    def add_price_data(self, price: float, volume: float = None, timestamp: float = None):
        """Add new price data point"""
        self.price_history.append({
            "price": price,
            "volume": volume,
            "timestamp": timestamp or time.time()
        })
        
        # Calculate volatility if we have enough data
        if len(self.price_history) >= 2:
            volatility = self._calculate_volatility()
            self.volatility_history.append(volatility)
            
            # Calculate variability score
            variability_score = self._calculate_variability_score()
            self.variability_scores.append(variability_score)
    
    def _calculate_volatility(self) -> float:
        """Calculate current volatility based on price changes"""
        if len(self.price_history) < 2:
            return 0.0
        
        prices = [p["price"] for p in self.price_history]
        returns = []
        
        for i in range(1, len(prices)):
            return_pct = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(abs(return_pct))
        
        if not returns:
            return 0.0
        
        # Calculate rolling volatility (standard deviation of returns)
        volatility = np.std(returns) if len(returns) > 1 else returns[0]
        return volatility
    
    def _calculate_variability_score(self) -> float:
        """Calculate variability score based on multiple factors"""
        if len(self.price_history) < 10:
            return 0.0
        
        # 1. Price volatility score (40% weight)
        current_volatility = self._calculate_volatility()
        volatility_score = self._normalize_volatility(current_volatility)
        
        # 2. Price momentum score (30% weight)
        momentum_score = self._calculate_momentum_score()
        
        # 3. Volume variability score (20% weight)
        volume_score = self._calculate_volume_variability()
        
        # 4. Pattern consistency score (10% weight)
        pattern_score = self._calculate_pattern_consistency()
        
        # Weighted average
        total_score = (
            volatility_score * 0.4 +
            momentum_score * 0.3 +
            volume_score * 0.2 +
            pattern_score * 0.1
        )
        
        return total_score
    
    def _normalize_volatility(self, volatility: float) -> float:
        """Normalize volatility to a 0-1 score"""
        if volatility <= self.variability_thresholds["low_volatility"]:
            # Low volatility - poor for trading
            return 0.2
        elif volatility <= self.variability_thresholds["medium_volatility"]:
            # Medium volatility - good for trading
            return 0.7
        elif volatility <= self.variability_thresholds["high_volatility"]:
            # High volatility - optimal for trading
            return 1.0
        elif volatility <= self.variability_thresholds["extreme_volatility"]:
            # Extreme volatility - good but risky
            return 0.8
        else:
            # Too extreme - poor for trading
            return 0.3
    
    def _calculate_momentum_score(self) -> float:
        """Calculate momentum score based on price direction consistency"""
        if len(self.price_history) < 5:
            return 0.5
        
        prices = [p["price"] for p in list(self.price_history)[-5:]]
        directions = []
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                directions.append(1)  # Up
            elif prices[i] < prices[i-1]:
                directions.append(-1)  # Down
            else:
                directions.append(0)  # Sideways
        
        # Calculate direction consistency
        if len(directions) == 0:
            return 0.5
        
        # Count consecutive same directions
        consecutive_count = 1
        max_consecutive = 1
        
        for i in range(1, len(directions)):
            if directions[i] == directions[i-1] and directions[i] != 0:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1
        
        # Normalize to 0-1 score
        momentum_score = min(max_consecutive / len(directions), 1.0)
        return momentum_score
    
    def _calculate_volume_variability(self) -> float:
        """Calculate volume variability score"""
        if len(self.price_history) < 5:
            return 0.5
        
        volumes = [p.get("volume", 1.0) for p in self.price_history if p.get("volume")]
        
        if len(volumes) < 3:
            return 0.5
        
        # Calculate volume coefficient of variation
        mean_volume = np.mean(volumes)
        std_volume = np.std(volumes)
        
        if mean_volume == 0:
            return 0.5
        
        cv = std_volume / mean_volume
        
        # Normalize: moderate volume variability is good for trading
        if cv < 0.3:
            return 0.3  # Too stable
        elif cv < 0.8:
            return 0.8  # Good variability
        elif cv < 1.5:
            return 1.0  # Optimal variability
        else:
            return 0.6  # Too variable
    
    def _calculate_pattern_consistency(self) -> float:
        """Calculate pattern consistency score"""
        if len(self.price_history) < 10:
            return 0.5
        
        prices = [p["price"] for p in self.price_history]
        
        # Look for repeating patterns in recent price movements
        pattern_length = min(5, len(prices) // 2)
        
        if pattern_length < 2:
            return 0.5
        
        # Calculate autocorrelation for pattern detection
        recent_prices = prices[-pattern_length*2:]
        autocorr = self._calculate_autocorrelation(recent_prices, pattern_length)
        
        # Higher autocorrelation means more consistent patterns
        pattern_score = min(abs(autocorr), 1.0)
        return pattern_score
    
    def _calculate_autocorrelation(self, data: List[float], lag: int) -> float:
        """Calculate autocorrelation coefficient"""
        if len(data) < lag * 2:
            return 0.0
        
        # Calculate price changes
        changes = []
        for i in range(1, len(data)):
            changes.append(data[i] - data[i-1])
        
        if len(changes) < lag:
            return 0.0
        
        # Calculate autocorrelation
        mean_change = np.mean(changes)
        variance = np.var(changes)
        
        if variance == 0:
            return 0.0
        
        autocorr = 0.0
        for i in range(lag, len(changes)):
            autocorr += (changes[i] - mean_change) * (changes[i-lag] - mean_change)
        
        autocorr /= (len(changes) - lag) * variance
        return autocorr
    
    def get_variability_analysis(self) -> Dict[str, Any]:
        """Get comprehensive variability analysis"""
        if len(self.price_history) < 10:
            return {
                "insufficient_data": True,
                "message": "Need at least 10 price points for analysis"
            }
        
        current_volatility = self._calculate_volatility()
        current_variability_score = self._calculate_variability_score()
        
        # Determine market condition
        market_condition = self._classify_market_condition(current_volatility, current_variability_score)
        
        # Calculate optimal trading parameters
        optimal_params = self._calculate_optimal_trading_params(current_volatility, current_variability_score, balance=1000.0)
        
        return {
            "insufficient_data": False,
            "current_volatility": current_volatility,
            "current_variability_score": current_variability_score,
            "market_condition": market_condition,
            "optimal_trading_params": optimal_params,
            "volatility_trend": self._analyze_volatility_trend(),
            "trading_recommendation": self._get_trading_recommendation(current_variability_score),
            "risk_level": self._calculate_risk_level(current_volatility),
            "confidence_score": self._calculate_confidence_score()
        }
    
    def _classify_market_condition(self, volatility: float, variability_score: float) -> str:
        """Classify current market condition"""
        if volatility < self.variability_thresholds["low_volatility"]:
            return "LOW_VOLATILITY_CHOPPY"
        elif volatility < self.variability_thresholds["medium_volatility"]:
            if variability_score > self.condition_scores["optimal_trading"]:
                return "MEDIUM_VOLATILITY_OPTIMAL"
            else:
                return "MEDIUM_VOLATILITY_GOOD"
        elif volatility < self.variability_thresholds["high_volatility"]:
            if variability_score > self.condition_scores["good_trading"]:
                return "HIGH_VOLATILITY_OPTIMAL"
            else:
                return "HIGH_VOLATILITY_GOOD"
        elif volatility < self.variability_thresholds["extreme_volatility"]:
            return "EXTREME_VOLATILITY_RISKY"
        else:
            return "EXTREME_VOLATILITY_AVOID"
    
    def _calculate_optimal_trading_params(self, volatility: float, variability_score: float, balance: float = 1000.0) -> Dict[str, Any]:
        """Calculate optimal trading parameters based on variability"""
        # Base parameters - use percentage of balance instead of fixed size
        base_position_size_pct = 0.10  # 10% of balance as base
        base_position_size = (balance * base_position_size_pct) / 114000  # Convert to BTC at current price
        base_leverage = 30
        base_profit_target = 0.003  # 0.3%
        base_stop_loss = 0.0015     # 0.15%
        
        # Adjust based on volatility
        if volatility < self.variability_thresholds["low_volatility"]:
            # Low volatility - reduce position size, increase targets
            position_multiplier = 0.5
            profit_target_multiplier = 1.5
            stop_loss_multiplier = 1.2
            leverage_multiplier = 0.8
        elif volatility < self.variability_thresholds["medium_volatility"]:
            # Medium volatility - standard parameters
            position_multiplier = 1.0
            profit_target_multiplier = 1.0
            stop_loss_multiplier = 1.0
            leverage_multiplier = 1.0
        elif volatility < self.variability_thresholds["high_volatility"]:
            # High volatility - increase position size, reduce targets
            position_multiplier = 1.5
            profit_target_multiplier = 0.8
            stop_loss_multiplier = 0.8
            leverage_multiplier = 1.2
        else:
            # Extreme volatility - reduce position size, increase targets
            position_multiplier = 0.7
            profit_target_multiplier = 1.3
            stop_loss_multiplier = 1.1
            leverage_multiplier = 0.9
        
        # Adjust based on variability score
        if variability_score > self.condition_scores["optimal_trading"]:
            # Optimal conditions - increase position size
            position_multiplier *= 1.2
        elif variability_score < self.condition_scores["poor_trading"]:
            # Poor conditions - reduce position size
            position_multiplier *= 0.7
        
        return {
            "position_size": base_position_size * position_multiplier,
            "leverage": int(base_leverage * leverage_multiplier),
            "profit_target": base_profit_target * profit_target_multiplier,
            "stop_loss": base_stop_loss * stop_loss_multiplier,
            "position_multiplier": position_multiplier,
            "profit_target_multiplier": profit_target_multiplier,
            "stop_loss_multiplier": stop_loss_multiplier,
            "leverage_multiplier": leverage_multiplier
        }
    
    def _analyze_volatility_trend(self) -> Dict[str, Any]:
        """Analyze volatility trend over time"""
        if len(self.volatility_history) < 5:
            return {"trend": "UNKNOWN", "direction": "UNKNOWN", "strength": 0.0}
        
        recent_volatility = list(self.volatility_history)[-5:]
        
        # Calculate trend
        if len(recent_volatility) >= 2:
            trend_slope = (recent_volatility[-1] - recent_volatility[0]) / len(recent_volatility)
            
            if trend_slope > 0.0001:
                direction = "INCREASING"
                strength = min(abs(trend_slope) * 1000, 1.0)
            elif trend_slope < -0.0001:
                direction = "DECREASING"
                strength = min(abs(trend_slope) * 1000, 1.0)
            else:
                direction = "STABLE"
                strength = 0.0
            
            # Classify trend strength
            if strength > 0.7:
                trend = "STRONG"
            elif strength > 0.3:
                trend = "MODERATE"
            else:
                trend = "WEAK"
        else:
            trend = "UNKNOWN"
            direction = "UNKNOWN"
            strength = 0.0
        
        return {
            "trend": trend,
            "direction": direction,
            "strength": strength,
            "recent_volatility": recent_volatility
        }
    
    def _get_trading_recommendation(self, variability_score: float) -> str:
        """Get trading recommendation based on variability score"""
        if variability_score > self.condition_scores["optimal_trading"]:
            return "OPTIMAL_TRADING_CONDITIONS"
        elif variability_score > self.condition_scores["good_trading"]:
            return "GOOD_TRADING_CONDITIONS"
        elif variability_score > self.condition_scores["poor_trading"]:
            return "POOR_TRADING_CONDITIONS"
        else:
            return "AVOID_TRADING"
    
    def _calculate_risk_level(self, volatility: float) -> str:
        """Calculate current risk level"""
        if volatility < self.variability_thresholds["low_volatility"]:
            return "LOW"
        elif volatility < self.variability_thresholds["medium_volatility"]:
            return "MEDIUM"
        elif volatility < self.variability_thresholds["high_volatility"]:
            return "HIGH"
        elif volatility < self.variability_thresholds["extreme_volatility"]:
            return "VERY_HIGH"
        else:
            return "EXTREME"
    
    def _calculate_confidence_score(self) -> float:
        """Calculate confidence score based on data quality"""
        if len(self.price_history) < 20:
            return len(self.price_history) / 20.0
        
        # Check data consistency
        prices = [p["price"] for p in self.price_history]
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        
        # Calculate coefficient of variation of price changes
        mean_change = np.mean(price_changes)
        std_change = np.std(price_changes)
        
        if mean_change == 0:
            return 0.5
        
        cv = std_change / mean_change
        
        # Lower CV means more consistent data (higher confidence)
        confidence = max(0.1, 1.0 - cv)
        return confidence
    
    def should_trade_based_on_variability(self, min_variability_score: float = 0.5) -> Dict[str, Any]:
        """Determine if we should trade based on variability analysis"""
        analysis = self.get_variability_analysis()
        
        if analysis.get("insufficient_data", False):
            # For new bot instances, allow trading even with insufficient data
            # This prevents the bot from being stuck waiting for data
            # Add optimal trading parameters
            optimal_trading_params = {
                "leverage": 30,
                "position_size": 0.001,
                "stop_distance": 0.002,
                "target_distance": 0.005
            }
            
            if len(self.price_history) >= 1:  # At least 1 data point (very lenient)
                return {
                    "should_trade": True,
                    "reason": "Insufficient data but allowing trade (new bot instance)",
                    "analysis": analysis,
                    "optimal_trading_params": optimal_trading_params
                }
            else:
                return {
                    "should_trade": False,
                    "reason": "Insufficient data for variability analysis",
                    "analysis": analysis,
                    "optimal_trading_params": optimal_trading_params
                }
        
        variability_score = analysis["current_variability_score"]
        market_condition = analysis["market_condition"]
        trading_recommendation = analysis.get("trading_recommendation", "UNKNOWN")
        confidence_score = analysis.get("confidence_score", 0.0)
        
        # Check multiple conditions for trading decision
        score_ok = variability_score >= min_variability_score
        recommendation_ok = trading_recommendation in ["OPTIMAL_TRADING_CONDITIONS", "GOOD_TRADING_CONDITIONS"]
        confidence_ok = confidence_score >= 0.1  # Reduced to 10% confidence for more trades
        
        should_trade = score_ok and recommendation_ok and confidence_ok
        
        # Determine reason for decision
        if not score_ok:
            reason = f"Variability score too low: {variability_score:.3f} < {min_variability_score}"
        elif not recommendation_ok:
            reason = f"Poor trading conditions: {trading_recommendation}"
        elif not confidence_ok:
            reason = f"Low confidence: {confidence_score:.3f} < 0.3"
        else:
            reason = f"Good conditions: score={variability_score:.3f}, recommendation={trading_recommendation}, confidence={confidence_score:.3f}"
        
        # Add optimal trading parameters
        optimal_trading_params = {
            "leverage": 30,
            "position_size": 0.001,
            "stop_distance": 0.002,
            "target_distance": 0.005
        }
        
        return {
            "should_trade": should_trade,
            "variability_score": variability_score,
            "market_condition": market_condition,
            "trading_recommendation": trading_recommendation,
            "confidence_score": confidence_score,
            "reason": reason,
            "analysis": analysis,
            "optimal_trading_params": optimal_trading_params
        }

def main():
    """Test variability analyzer"""
    logger.info("🔍 Testing Variability Analyzer")
    
    analyzer = VariabilityAnalyzer(lookback_periods=50)
    
    # Simulate price data
    base_price = 50000
    for i in range(30):
        # Simulate some price movement
        if i < 10:
            # Low volatility period
            price = base_price + np.random.normal(0, 10)
        elif i < 20:
            # Medium volatility period
            price = base_price + np.random.normal(0, 50)
        else:
            # High volatility period
            price = base_price + np.random.normal(0, 100)
        
        analyzer.add_price_data(price, volume=1000 + np.random.normal(0, 200))
    
    # Get analysis
    analysis = analyzer.get_variability_analysis()
    logger.info(f"📊 Variability Analysis: {analysis}")
    
    # Test trading decision
    trading_decision = analyzer.should_trade_based_on_variability(0.5)
    logger.info(f"🎯 Trading Decision: {trading_decision}")

if __name__ == "__main__":
    main()
