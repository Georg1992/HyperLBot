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
        
        This is called at the start of each calculation to ensure clean state
        """
        self._broken_levels.clear()
        self._role_reversals.clear()
        self._recalculation_reasons.clear()
        self._active_levels.clear()
        self._inactive_levels.clear()
        logger.debug("📊 Reset S/R session state")
    
    def should_recalculate(self, current_price: float, current_time: float, 
                          atr_5m: float) -> bool:
        """
        Determine if S/R recalculation is needed
        
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
            
            # Check price movement threshold (> 1×ATR)
            if self._last_price > 0 and atr_5m > 0:
                price_change = abs(current_price - self._last_price)
                atr_threshold = atr_5m * 1.0
                
                if price_change > atr_threshold:
                    self._recalculation_reasons.append(f"price_movement_{price_change:.2f}")
                    return True
            
            # Check for new structural swing (simplified check)
            if self._has_new_swing_structure(current_price):
                self._recalculation_reasons.append("new_swing_structure")
                return True
            
            # Periodic refresh every 15 minutes
            time_since_last = current_time - self._last_calculation_time
            if time_since_last > 900:  # 15 minutes
                self._recalculation_reasons.append("periodic_refresh")
                return True
            
            # Check for level breakouts
            if self._has_level_breakouts(current_price, atr_5m):
                self._recalculation_reasons.append("level_breakout")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Recalculation check failed: {e}")
            return True  # Default to recalculate on error
    
    def _has_new_swing_structure(self, current_price: float) -> bool:
        """
        Check for new structural swing formation
        
        Args:
            current_price: Current price
            
        Returns:
            True if new swing structure detected
        """
        try:
            # Simplified swing structure detection
            # In a real implementation, this would analyze recent price action
            # For now, we'll use a simple price change threshold
            if self._last_price > 0:
                price_change_pct = abs(current_price - self._last_price) / self._last_price
                return price_change_pct > 0.005  # 0.5% movement threshold
            
            return False
            
        except Exception:
            return False
    
    def _has_level_breakouts(self, current_price: float, atr_5m: float) -> bool:
        """
        Check if any levels have been broken
        
        Args:
            current_price: Current price
            atr_5m: 5m ATR for breakout confirmation
            
        Returns:
            True if level breakouts detected
        """
        try:
            # This would check against cached levels for breakouts
            # For now, simplified implementation
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
        logger.debug(f"📊 Updated calculation state: price=${current_price:.2f}")
    
    def check_level_status(self, level: Dict, current_price: float, atr_14: float) -> str:
        """
        Check if a level is active or inactive based on breakout conditions
        
        Args:
            level: Level dictionary
            current_price: Current price
            atr_14: ATR for breakout confirmation
            
        Returns:
            'active' or 'inactive'
        """
        try:
            level_price = level['level']
            level_type = level['type']
            
            if level_type == 'support':
                # Support is broken if price falls below it by more than ATR
                if current_price < (level_price - atr_14):
                    return 'inactive'
            elif level_type == 'resistance':
                # Resistance is broken if price rises above it by more than ATR
                if current_price > (level_price + atr_14):
                    return 'inactive'
            
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
                'level': level['level'],
                'type': level['type'],
                'breakout_price': current_price,
                'timestamp': time.time(),
                'original_touches': level.get('touches', 0),
                'original_score': level.get('score', 0)
            }
            
            self._broken_levels.append(broken_level)
            logger.debug(f"📊 Tracked broken {level['type']} at ${level['level']:.2f}")
            
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
                'original_level': level['level'],
                'original_type': level['type'],
                'new_type': 'support' if level['type'] == 'resistance' else 'resistance',
                'reversal_price': current_price,
                'timestamp': time.time()
            }
            
            self._role_reversals.append(reversal)
            logger.debug(f"📊 Tracked role reversal: {level['type']} → {reversal['new_type']}")
            
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
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """
        Clean up old broken levels and role reversals
        
        Args:
            max_age_hours: Maximum age in hours
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            # Clean up old broken levels
            self._broken_levels = [
                level for level in self._broken_levels
                if current_time - level.get('timestamp', 0) < max_age_seconds
            ]
            
            # Clean up old role reversals
            self._role_reversals = [
                reversal for reversal in self._role_reversals
                if current_time - reversal.get('timestamp', 0) < max_age_seconds
            ]
            
            logger.debug(f"📊 Cleaned up old data (max age: {max_age_hours}h)")
            
        except Exception as e:
            logger.error(f"❌ Data cleanup failed: {e}")
