#!/usr/bin/env python3
"""
Dashboard Updater - Single Responsibility: Update Dashboard with Market Data
Extracted from SessionOrchestrator for SRP compliance
"""

from typing import Dict, Any, Optional
from loguru import logger


class DashboardUpdater:
    """Handles dashboard updates with market and session data"""
    
    def __init__(self, dashboard_service, session_manager=None):
        """
        Initialize Dashboard Updater
        
        Args:
            dashboard_service: DashboardService instance
            session_manager: SessionManager instance (optional)
        """
        self.dashboard_service = dashboard_service
        self.session_manager = session_manager
    
    def update_dashboard_with_unified_data(self, unified_data: Dict[str, Any]) -> None:
        """
        Update dashboard with unified market data and session data
        
        Args:
            unified_data: Unified market data dictionary
        """
        try:
            # Update market data with analysis data (includes strategy in unified_data)
            self.dashboard_service.update_market_data(unified_data)
            
            # Update session data from SessionManager (ensure strategy is synced)
            if self.session_manager:
                session_data = self.session_manager.get_current_session_data()
                # Ensure session data has the latest strategy from unified_data
                if "strategy" in unified_data:
                    session_data["strategy"] = unified_data["strategy"]
                    if self.session_manager:
                        self.session_manager.current_session_data["strategy"] = unified_data["strategy"]
                self.dashboard_service.update_session_data(session_data)
                
        except Exception as e:
            logger.error(f"❌ Dashboard update failed: {e}")
    
    def update_strategy_display(self, strategy: str) -> None:
        """
        Update dashboard with strategy display
        
        Args:
            strategy: Strategy name to display
        """
        try:
            self.dashboard_service.update_strategy_display(strategy)
        except Exception as e:
            logger.debug(f"Dashboard strategy update failed (non-critical): {e}")
