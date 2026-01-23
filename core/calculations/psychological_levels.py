#!/usr/bin/env python3
"""
Psychological Levels Calculator

Fixed intervals (from smallest to strongest gravity):
- $500: Smallest level (gravity: 20)
- $1,000: Stronger level (gravity: 40)
- $2,500: Stronger level (gravity: 60)
- $5,000: Stronger level (gravity: 75)
- $10,000: Stronger level (gravity: 90)
- $100,000: Strongest level (gravity: 100)
"""

from typing import List
from loguru import logger

from .level import Level


class PsychologicalLevelsCalculator:
    """
    Get psychological (round number) support/resistance levels
    
    Fixed intervals (from smallest to strongest gravity):
    - $500: Smallest level (gravity: 20)
    - $1,000: Stronger level (gravity: 40)
    - $2,500: Stronger level (gravity: 60)
    - $5,000: Stronger level (gravity: 75)
    - $10,000: Stronger level (gravity: 90)
    - $100,000: Strongest level (gravity: 100)
    """
    
    def __init__(self):
        """Initialize psychological levels calculator"""
        self.logger = logger
    
    def get_psychological_levels(self, current_price: float, 
                                long_liquidation: float,
                                short_liquidation: float) -> List[Level]:
        """
        Get relevant psychological levels around current price within liquidation range
        
        Psychological levels are fixed intervals - we just identify which ones are relevant:
        - $500, $1,000, $2,500, $5,000, $10,000, $100,000
        
        Args:
            current_price: Current market price
            long_liquidation: LONG liquidation price (for support filtering)
            short_liquidation: SHORT liquidation price (for resistance filtering)
            
        Returns:
            List of Level objects representing relevant psychological levels
        """
        # NOT IMPLEMENTED - Using simpler confluence approach instead
        # 
        # Research showed that adding synthetic psychological levels as separate S/R levels
        # would create noise and complexity without sufficient value.
        # 
        # IMPLEMENTED ALTERNATIVE (see sr_scorer.py):
        # - Simple confluence check: when real S/R level aligns with major round number ($10K),
        #   boost its power by 0-5 points based on proximity
        # - Minimal complexity, real value (confluence detection)
        # - No synthetic levels, no state machines, no overengineering
        # 
        # Round number avoidance for stops is already implemented in risk_manager.py
        logger.debug("🧠 Psychological levels handled via confluence in sr_scorer.py")
        return []
