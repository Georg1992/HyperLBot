#!/usr/bin/env python3
"""
SRState - Manages cached/broken levels and lifecycle
Responsible for tracking level states, role reversals, and recalculation triggers
"""

import time
from typing import Dict, List, Any, Set
from loguru import logger


class SRState:
    """
    State manager for Support/Resistance levels
    
    Responsibilities:
    - Track broken levels and role reversals
    - Manage recalculation triggers
    - Handle level lifecycle states
    - Prevent memory leaks and cross-session contamination
    """
    
    def __init__(self):
        """Initialize the state manager"""
        self._broken_levels: List[Dict] = []
        self._role_reversals: List[Dict] = []
        self._recalculation_reasons: List[str] = []
        self._last_calculation_time: float = 0.0
        self._last_price: float = 0.0
        self._active_levels: Set[str] = set()
        self._inactive_levels: Set[str] = set()
        
    def reset_session_state(self):
        """
        Reset per-run state to avoid memory leaks and cross-session contamination
        
        This is called at the start of each calculation to ensure clean state.
        Only resets temporary data, preserves historical support/resistance roles.
        """
        # Only reset temporary session data, not historical roles
        self._recalculation_reasons.clear()
        self._active_levels.clear()
        self._inactive_levels.clear()
    
    def should_recalculate(self, current_price: float, current_time: float, 
                          atr_5m: float) -> bool:
        """
        Determine if S/R recalculation is needed with proper break confirmation
        
        When a resistance/support is broken, recalculation happens:
        1. Immediately when price breaks through by >1.5×ATR (confirmed breakout)
        2. When new swing structure forms (new highs/lows)
        3. Every 5 minutes after a break (to find new levels quickly)
        4. Periodic refresh every 15 minutes (normal operation)
        
        Args:
            current_price: Current price
            current_time: Current timestamp
            atr_5m: 5m ATR for volatility scaling
            
        Returns:
            True if recalculation is needed
        """
        try:
            # Always recalculate on first run
            if self._last_calculation_time == 0.0:
                self._recalculation_reasons.append("first_calculation")
                return True
            
            # Check for confirmed level breakouts (>1.5×ATR)
            # This triggers immediately when a level is broken
            if self._last_price > 0 and atr_5m > 0:
                price_change = abs(current_price - self._last_price)
                breakout_threshold = atr_5m * 1.5  # Require 1.5×ATR for confirmed breakout
                
                if price_change > breakout_threshold:
                    self._recalculation_reasons.append(f"confirmed_breakout_{price_change:.2f}")
                    logger.info(f"🔄 S/R recalculation triggered: Level broken (price moved {price_change:.2f} > {breakout_threshold:.2f} ATR)")
                    return True
            
            # Check for new local swing high/low formation
            if self._has_new_swing_structure(current_price, atr_5m):
                self._recalculation_reasons.append("new_swing_structure")
                logger.info(f"🔄 S/R recalculation triggered: New swing structure detected")
                return True
            
            # After a level break, recalculate more frequently (every 5 minutes) to find new levels
            # Check if we have broken levels that need new level detection
            time_since_last = current_time - self._last_calculation_time
            if len(self._broken_levels) > 0:
                # If we have broken levels, recalculate every 5 minutes to find new levels
                if time_since_last > 300:  # 5 minutes
                    self._recalculation_reasons.append("post_break_refresh")
                    logger.info(f"🔄 S/R recalculation triggered: Post-break refresh (broken levels detected)")
                    return True
            
            # Periodic refresh every 15 minutes (normal operation)
            if time_since_last > 900:  # 15 minutes
                self._recalculation_reasons.append("periodic_refresh")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Recalculation check failed: {e}")
            return True  # Default to recalculate on error
    
    def _has_new_swing_structure(self, current_price: float, atr_5m: float) -> bool:
        """
        Check for new structural swing formation beyond last confirmed zone
        
        Args:
            current_price: Current price
            atr_5m: 5m ATR for volatility scaling
            
        Returns:
            True if new swing structure detected
        """
        try:
            if self._last_price > 0 and atr_5m > 0:
                # Check if price has moved beyond last confirmed zone by >1.5×ATR
                price_change_pct = abs(current_price - self._last_price) / self._last_price
                atr_change_pct = atr_5m / self._last_price
                
                # Require significant movement beyond normal volatility
                return price_change_pct > (atr_change_pct * 1.5)
            
            return False
            
        except Exception:
            return False
    
    def update_calculation_state(self, current_price: float, current_time: float):
        """
        Update calculation state after successful calculation
        
        Args:
            current_price: Current price
            current_time: Current timestamp
        """
        self._last_calculation_time = current_time
        self._last_price = current_price
    
    def check_level_status(self, level, current_price: float, atr_14: float) -> str:
        """
        Check if a level is active or inactive based on breakout conditions
        Uses original level_type from swing detection (not price position)
        
        Args:
            level: Level object (has .level and .level_type attributes)
            current_price: Current price
            atr_14: ATR for breakout confirmation
            
        Returns:
            'active' or 'inactive'
        """
        try:
            level_price = level.level
            level_type = level.level_type  # Use original level_type from swing detection
            
            # Use original level_type to determine break conditions
            # Historical levels keep their type: broken resistance is still resistance
            if level_type == 'resistance':
                # Resistance is broken if price has risen ABOVE it by more than ATR
                # Price must be above (level + ATR) to confirm break
                break_threshold = level_price + atr_14
                is_broken = current_price > break_threshold
                if is_broken:
                    return 'inactive'  # Resistance broken - price rose through
            elif level_type == 'support':
                # Support is broken if price has fallen BELOW it by more than ATR
                # Price must be below (level - ATR) to confirm break
                break_threshold = level_price - atr_14
                is_broken = current_price < break_threshold
                if is_broken:
                    return 'inactive'  # Support broken - price fell through
            
            return 'active'
            
        except Exception as e:
            logger.error(f"❌ Level status check failed: {e}")
            return 'active'  # Default to active on error
    
    def track_broken_level(self, level: Dict, current_price: float):
        """
        Track a broken level
        
        Args:
            level: Broken level dictionary
            current_price: Current price when broken
        """
        try:
            broken_level = {
                'level': level.level,
                'type': level.level_type,
                'breakout_price': current_price,
                'timestamp': time.time(),
                'original_touches': level.touches,
                'original_score': level.score
            }
            
            self._broken_levels.append(broken_level)
            
        except Exception as e:
            logger.error(f"❌ Failed to track broken level: {e}")
    
    def track_role_reversal(self, level: Dict, current_price: float):
        """
        Track role reversal (resistance becomes support or vice versa)
        
        Args:
            level: Level dictionary
            current_price: Current price
        """
        try:
            reversal = {
                'original_level': level.level,
                'original_type': level.level_type,
                'new_type': 'support' if level.level_type == 'resistance' else 'resistance',
                'reversal_price': current_price,
                'timestamp': time.time()
            }
            
            self._role_reversals.append(reversal)
            
        except Exception as e:
            logger.error(f"❌ Failed to track role reversal: {e}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get current state summary
        
        Returns:
            Dictionary with state information
        """
        return {
            'broken_levels_count': len(self._broken_levels),
            'role_reversals_count': len(self._role_reversals),
            'recalculation_reasons': self._recalculation_reasons.copy(),
            'last_calculation_time': self._last_calculation_time,
            'last_price': self._last_price,
            'active_levels_count': len(self._active_levels),
            'inactive_levels_count': len(self._inactive_levels)
        }
    
    def get_broken_levels(self) -> List[Dict]:
        """
        Get list of broken levels
        
        Returns:
            List of broken level dictionaries
        """
        return self._broken_levels.copy()
    
    def get_role_reversals(self) -> List[Dict]:
        """
        Get list of role reversals
        
        Returns:
            List of role reversal dictionaries
        """
        return self._role_reversals.copy()
    
    def get_recalculation_reasons(self) -> List[str]:
        """
        Get list of recalculation reasons
        
        Returns:
            List of recalculation reason strings
        """
        return self._recalculation_reasons.copy()
    
    def clear_recalculation_reasons(self):
        """Clear recalculation reasons after use"""
        self._recalculation_reasons.clear()
    
    def add_active_level(self, level_id: str):
        """
        Add level to active set
        
        Args:
            level_id: Unique level identifier
        """
        self._active_levels.add(level_id)
    
    def add_inactive_level(self, level_id: str):
        """
        Add level to inactive set
        
        Args:
            level_id: Unique level identifier
        """
        self._inactive_levels.add(level_id)
    
    def is_level_active(self, level_id: str) -> bool:
        """
        Check if level is active
        
        Args:
            level_id: Unique level identifier
            
        Returns:
            True if level is active
        """
        return level_id in self._active_levels
    
