"""
Market Opening Service
Simple service to detect next major market opening and calculate time remaining
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz

logger = logging.getLogger(__name__)

class MarketOpeningService:
    """Simple market opening detector for dashboard display"""
    
    def __init__(self):
        self.utc = pytz.UTC
        self.ny_tz = pytz.timezone('America/New_York')
        self.london_tz = pytz.timezone('Europe/London')
        self.tokyo_tz = pytz.timezone('Asia/Tokyo')
        
        # Major market opening times (UTC)
        self.market_openings = [
            {
                "name": "Tokyo Stock Exchange",
                "exchange": "TSE",
                "time_utc": "00:00",  # 9:00 AM JST
                "timezone": self.tokyo_tz,
                "importance": 3
            },
            {
                "name": "London Stock Exchange", 
                "exchange": "LSE",
                "time_utc": "08:00",  # 9:00 AM BST
                "timezone": self.london_tz,
                "importance": 4
            },
            {
                "name": "New York Stock Exchange",
                "exchange": "NYSE", 
                "time_utc": "13:30",  # 9:30 AM EST
                "timezone": self.ny_tz,
                "importance": 5
            }
        ]
        
        logger.info("🌍 Market Opening Service initialized")
    
    def get_next_major_opening(self) -> Optional[Dict[str, Any]]:
        """
        Get the next major market opening
        
        Returns:
            Dict with opening info or None if no opening found
        """
        try:
            current_time = datetime.now(self.utc)
            next_opening = None
            min_time_diff = float('inf')
            
            for market in self.market_openings:
                # Calculate next opening time for this market
                opening_time = self._get_next_opening_time(market, current_time)
                
                if opening_time:
                    time_diff = (opening_time - current_time).total_seconds()
                    
                    # Find the closest opening
                    if time_diff > 0 and time_diff < min_time_diff:
                        min_time_diff = time_diff
                        next_opening = {
                            "market_name": market["name"],
                            "exchange": market["exchange"],
                            "opening_time": opening_time,
                            "time_until": time_diff,
                            "importance": market["importance"],
                            "liquidation_risk": 0.0  # Not applicable for simple display
                        }
            
            if next_opening:
                logger.debug(f"🕐 Next market opening: {next_opening['market_name']} in {next_opening['time_until']/3600:.1f} hours")
            
            return next_opening
            
        except Exception as e:
            logger.error(f"❌ Failed to get next market opening: {e}")
            return None
    
    def _get_next_opening_time(self, market: Dict[str, Any], current_time: datetime) -> Optional[datetime]:
        """Get the next opening time for a specific market"""
        try:
            # Parse opening time
            opening_hour, opening_minute = map(int, market["time_utc"].split(":"))
            
            # Create opening time for today
            today_opening = current_time.replace(
                hour=opening_hour, 
                minute=opening_minute, 
                second=0, 
                microsecond=0
            )
            
            # If today's opening has passed, get tomorrow's opening
            if today_opening <= current_time:
                tomorrow_opening = today_opening + timedelta(days=1)
                return tomorrow_opening
            else:
                return today_opening
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate opening time for {market['name']}: {e}")
            return None
    
    def is_market_opening_time(self) -> bool:
        """Check if we're currently in a market opening window (within 30 minutes)"""
        try:
            next_opening = self.get_next_major_opening()
            if not next_opening:
                return False
            
            # Consider it "opening time" if within 30 minutes
            return next_opening["time_until"] <= 1800  # 30 minutes in seconds
            
        except Exception as e:
            logger.error(f"❌ Failed to check market opening time: {e}")
            return False
    
    def get_market_session_info(self) -> Dict[str, Any]:
        """Get current market session information"""
        try:
            next_opening = self.get_next_major_opening()
            
            return {
                "active_markets": ["Global Markets"],  # Simplified
                "session_overlap": False,  # Simplified
                "liquidation_risk": "LOW"  # Not applicable for simple display
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get market session info: {e}")
            return {
                "active_markets": [],
                "session_overlap": False,
                "liquidation_risk": "UNKNOWN"
            }

# Factory function for dependency injection
def create_market_opening_service() -> MarketOpeningService:
    """
    Factory function to create MarketOpeningService with dependency injection
    
    Returns:
        Configured MarketOpeningService instance
    """
    return MarketOpeningService()

# Global instance for backward compatibility
global_market_opening_service = create_market_opening_service()
