#!/usr/bin/env python3
"""
Liquidation Hunting Strategy
============================
Advanced strategy that leverages global exchange opening times to hunt liquidations
and capitalize on high-volume price movements during market transitions.

STRATEGY CONCEPT:
- Major exchanges open at different times globally
- Opening times create massive liquidity influxes
- High leverage positions get liquidated during these transitions
- We can predict and profit from these liquidation cascades

EXCHANGE OPENING TIMES (UTC):
- Asian Markets: 00:00 UTC (Tokyo, Seoul, Hong Kong)
- European Markets: 08:00 UTC (London, Frankfurt, Paris)
- US Markets: 14:30 UTC (New York, Chicago)
- Crypto Markets: 24/7 but follow traditional market patterns
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import pytz

@dataclass
class ExchangeOpening:
    """Represents a major exchange opening time"""
    name: str
    timezone: str
    open_time_utc: str  # HH:MM format
    close_time_utc: str  # HH:MM format
    importance: int  # 1-5 (5 = most important)
    liquidation_risk: float  # 0.0-1.0 (higher = more liquidations expected)
    volume_multiplier: float  # Expected volume increase during opening

@dataclass
class LiquidationOpportunity:
    """Represents a potential liquidation hunting opportunity"""
    exchange: str
    time_until_opening: int  # seconds
    confidence: float  # 0.0-1.0
    expected_volume_spike: float
    liquidation_risk: float
    recommended_position_size: float
    entry_window: int  # seconds before opening to enter
    exit_window: int  # seconds after opening to exit

class LiquidationHunter:
    """
    Advanced liquidation hunting system that monitors global exchange openings
    and identifies high-probability liquidation opportunities
    """
    
    def __init__(self):
        self.name = "LiquidationHunter"
        self.is_active = False
        self.monitoring_thread = None
        self.current_opportunities = []
        
        # Define major exchange opening times
        self.exchanges = [
            ExchangeOpening(
                name="Tokyo Stock Exchange",
                timezone="Asia/Tokyo",
                open_time_utc="00:00",
                close_time_utc="06:00",
                importance=5,
                liquidation_risk=0.8,
                volume_multiplier=2.5
            ),
            ExchangeOpening(
                name="Hong Kong Stock Exchange",
                timezone="Asia/Hong_Kong",
                open_time_utc="01:30",
                close_time_utc="08:00",
                importance=4,
                liquidation_risk=0.7,
                volume_multiplier=2.2
            ),
            ExchangeOpening(
                name="London Stock Exchange",
                timezone="Europe/London",
                open_time_utc="08:00",
                close_time_utc="16:30",
                importance=5,
                liquidation_risk=0.9,
                volume_multiplier=3.0
            ),
            ExchangeOpening(
                name="Frankfurt Stock Exchange",
                timezone="Europe/Berlin",
                open_time_utc="08:00",
                close_time_utc="16:30",
                importance=4,
                liquidation_risk=0.8,
                volume_multiplier=2.8
            ),
            ExchangeOpening(
                name="New York Stock Exchange",
                timezone="America/New_York",
                open_time_utc="14:30",
                close_time_utc="21:00",
                importance=5,
                liquidation_risk=0.95,
                volume_multiplier=3.5
            ),
            ExchangeOpening(
                name="Chicago Mercantile Exchange",
                timezone="America/Chicago",
                open_time_utc="14:30",
                close_time_utc="21:00",
                importance=4,
                liquidation_risk=0.85,
                volume_multiplier=3.2
            )
        ]
        
        # Liquidation hunting parameters
        self.entry_window_minutes = 15  # Enter 15 minutes before opening
        self.exit_window_minutes = 30   # Exit 30 minutes after opening
        self.min_confidence_threshold = 0.7
        self.max_position_size = 0.1  # 10% of portfolio max
        
        logger.info("🎯 Liquidation Hunter initialized - Global exchange timing analysis")
    
    def start_monitoring(self):
        """Start monitoring for liquidation opportunities"""
        if self.is_active:
            logger.warning("⚠️ Liquidation hunting already active")
            return
        
        self.is_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_exchange_openings, daemon=True)
        self.monitoring_thread.start()
        logger.info("🚀 Liquidation hunting monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for liquidation opportunities"""
        self.is_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("🛑 Liquidation hunting monitoring stopped")
    
    def _monitor_exchange_openings(self):
        """Main monitoring loop for exchange openings"""
        while self.is_active:
            try:
                current_utc = datetime.utcnow()
                opportunities = self._identify_liquidation_opportunities(current_utc)
                
                if opportunities:
                    self.current_opportunities = opportunities
                    self._log_opportunities(opportunities)
                else:
                    self.current_opportunities = []
                
                # Check every 60 seconds
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in liquidation monitoring: {e}")
                time.sleep(30)
    
    def _identify_liquidation_opportunities(self, current_time: datetime) -> List[LiquidationOpportunity]:
        """Identify current liquidation hunting opportunities"""
        opportunities = []
        
        for exchange in self.exchanges:
            # Calculate next opening time
            next_opening = self._get_next_opening_time(exchange, current_time)
            if not next_opening:
                continue
            
            time_until_opening = (next_opening - current_time).total_seconds()
            
            # Only consider opportunities within our entry window
            if time_until_opening <= self.entry_window_minutes * 60:
                # Calculate opportunity confidence
                confidence = self._calculate_opportunity_confidence(exchange, time_until_opening)
                
                if confidence >= self.min_confidence_threshold:
                    opportunity = LiquidationOpportunity(
                        exchange=exchange.name,
                        time_until_opening=int(time_until_opening),
                        confidence=confidence,
                        expected_volume_spike=exchange.volume_multiplier,
                        liquidation_risk=exchange.liquidation_risk,
                        recommended_position_size=self._calculate_position_size(exchange, confidence),
                        entry_window=self.entry_window_minutes * 60,
                        exit_window=self.exit_window_minutes * 60
                    )
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _get_next_opening_time(self, exchange: ExchangeOpening, current_time: datetime) -> Optional[datetime]:
        """Get the next opening time for an exchange"""
        try:
            # Parse opening time
            open_hour, open_minute = map(int, exchange.open_time_utc.split(':'))
            
            # Create opening time for today
            today_opening = current_time.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
            
            # If opening time has passed today, get tomorrow's opening
            if today_opening <= current_time:
                tomorrow_opening = today_opening + timedelta(days=1)
                return tomorrow_opening
            else:
                return today_opening
                
        except Exception as e:
            logger.error(f"❌ Error calculating opening time for {exchange.name}: {e}")
            return None
    
    def _calculate_opportunity_confidence(self, exchange: ExchangeOpening, time_until_opening: int) -> float:
        """Calculate confidence score for a liquidation opportunity"""
        base_confidence = exchange.liquidation_risk
        
        # Time factor: closer to opening = higher confidence
        time_factor = max(0.1, 1.0 - (time_until_opening / (self.entry_window_minutes * 60)))
        
        # Importance factor: more important exchanges = higher confidence
        importance_factor = exchange.importance / 5.0
        
        # Volume factor: higher expected volume = higher confidence
        volume_factor = min(1.0, exchange.volume_multiplier / 3.0)
        
        # Combine factors
        confidence = base_confidence * 0.4 + time_factor * 0.3 + importance_factor * 0.2 + volume_factor * 0.1
        
        return min(1.0, confidence)
    
    def _calculate_position_size(self, exchange: ExchangeOpening, confidence: float) -> float:
        """
        REMOVED: Position sizing is now handled by hybrid_position_sizer
        This method is kept for backward compatibility but returns a simple fallback
        """
        # Simple fallback - should be replaced with hybrid_position_sizer calls
        return min(self.max_position_size, max(0.01, confidence * 0.05))
    
    def _log_opportunities(self, opportunities: List[LiquidationOpportunity]):
        """Log current liquidation opportunities"""
        if not opportunities:
            return
        
        logger.info(f"🎯 {len(opportunities)} liquidation opportunities detected:")
        
        for opp in opportunities:
            time_str = f"{opp.time_until_opening // 60}m {opp.time_until_opening % 60}s"
            logger.info(f"   📊 {opp.exchange}: {time_str} until opening "
                       f"(confidence: {opp.confidence:.2f}, "
                       f"volume spike: {opp.expected_volume_spike:.1f}x, "
                       f"position: {opp.recommended_position_size:.1%})")
    
    def get_current_opportunities(self) -> List[LiquidationOpportunity]:
        """Get current liquidation opportunities"""
        return self.current_opportunities.copy()
    
    def is_liquidation_hunting_time(self) -> bool:
        """Check if we're currently in a liquidation hunting window"""
        return len(self.current_opportunities) > 0
    
    def get_next_major_opening(self) -> Optional[Dict[str, Any]]:
        """Get information about the next major exchange opening"""
        current_time = datetime.utcnow()
        
        # Find the next opening among all exchanges
        next_openings = []
        for exchange in self.exchanges:
            next_opening = self._get_next_opening_time(exchange, current_time)
            if next_opening:
                time_until = (next_opening - current_time).total_seconds()
                next_openings.append({
                    'exchange': exchange.name,
                    'opening_time': next_opening,
                    'time_until': time_until,
                    'importance': exchange.importance,
                    'liquidation_risk': exchange.liquidation_risk
                })
        
        if not next_openings:
            return None
        
        # Return the next opening
        next_openings.sort(key=lambda x: x['time_until'])
        return next_openings[0]
    
    def get_market_session_info(self) -> Dict[str, Any]:
        """Get current market session information"""
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        
        # Determine which markets are currently open
        active_markets = []
        
        # Asian markets (00:00-06:00 UTC)
        if 0 <= current_hour < 6:
            active_markets.append("Asian")
        
        # European markets (08:00-16:30 UTC)
        if 8 <= current_hour < 16:
            active_markets.append("European")
        
        # US markets (14:30-21:00 UTC)
        if 14 <= current_hour < 21:
            active_markets.append("US")
        
        # Determine session overlap
        session_overlap = len(active_markets) > 1
        
        return {
            'current_time_utc': current_time.isoformat(),
            'active_markets': active_markets,
            'session_overlap': session_overlap,
            'liquidation_risk': 'HIGH' if session_overlap else 'MODERATE',
            'volume_expectation': 'HIGH' if session_overlap else 'NORMAL'
        }

# Global instance
global_liquidation_hunter = LiquidationHunter()
