#!/usr/bin/env python3
"""
Dashboard Sync Service
Single Responsibility: Handle all dashboard synchronization logic
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime


class DashboardSyncService:
    """
    Single Responsibility: Dashboard synchronization
    Handles all dashboard data synchronization from various sources
    """
    
    def __init__(self, dashboard_service):
        self.dashboard_service = dashboard_service
        self._last_sync_time = None
    
    def sync_from_simulator(self, simulator_data: Dict[str, Any]) -> bool:
        """
        Sync dashboard with simulator data
        Returns: True if sync successful, False otherwise
        """
        try:
            logger.debug("🔄 Syncing dashboard with simulator data")
            
            # Extract simulator data
            open_positions = simulator_data.get("open_positions", [])
            closed_positions = simulator_data.get("closed_positions", [])
            balance = simulator_data.get("balance", 0.0)
            total_trades = simulator_data.get("total_trades", 0)
            
            # Update account data
            self._update_account_data(simulator_data)
            
            # Update trade data (preserve pending orders, add simulator trades)
            self._update_trade_data(open_positions, closed_positions)
            
            # Update sync metadata
            self._update_sync_metadata()
            
            logger.debug(f"📊 Dashboard synced: {len(open_positions)} open, {len(closed_positions)} closed, balance: ${balance:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dashboard sync failed: {e}")
            return False
    
    def _update_account_data(self, simulator_data: Dict[str, Any]) -> None:
        """Update account data in dashboard"""
        try:
            with self.dashboard_service._lock:
                self.dashboard_service._data["account"] = {
                    "balance": simulator_data.get("balance", 0.0),
                    "total_balance": simulator_data.get("balance", 0.0),
                    "available_balance": simulator_data.get("balance", 0.0),
                    "used_margin": simulator_data.get("used_margin", 0.0),
                    "open_positions": simulator_data.get("open_positions", []),
                    "closed_positions": simulator_data.get("closed_positions", []),
                    "total_trades": simulator_data.get("total_trades", 0),
                    "total_fees_paid": simulator_data.get("total_fees_paid", 0.0),
                    "unrealized_pnl": simulator_data.get("unrealized_pnl", 0.0),
                    "realized_pnl": simulator_data.get("realized_pnl", 0.0)
                }
        except Exception as e:
            logger.error(f"❌ Failed to update account data: {e}")
    
    def _update_trade_data(self, open_positions: List[Dict], closed_positions: List[Dict]) -> None:
        """Update trade data in dashboard"""
        try:
            with self.dashboard_service._lock:
                # Preserve only the most recent pending order
                pending_orders = [t for t in self.dashboard_service._data.get("trades", []) if t.get("status") == "PENDING"]
                latest_pending = self._get_latest_pending_order(pending_orders)
                
                # Combine pending orders with simulator trades
                simulator_trades = open_positions + closed_positions
                
                # Fix timestamp fields for JavaScript compatibility
                for trade in simulator_trades:
                    # Add timestamp field for JavaScript compatibility
                    if "entry_time" in trade and "timestamp" not in trade:
                        trade["timestamp"] = trade["entry_time"]
                    if "entry_datetime" in trade and "created_at" not in trade:
                        trade["created_at"] = trade["entry_datetime"]
                    
                    # Map P&L field for dashboard compatibility
                    if "pnl" in trade and "net_pnl" not in trade:
                        trade["net_pnl"] = trade["pnl"]
                    if "pnl" in trade and "pnl_amount" not in trade:
                        trade["pnl_amount"] = trade["pnl"]
                
                self.dashboard_service._data["trades"] = latest_pending + simulator_trades
                
        except Exception as e:
            logger.error(f"❌ Failed to update trade data: {e}")
    
    def _get_latest_pending_order(self, pending_orders: List[Dict]) -> List[Dict]:
        """Get the most recent pending order"""
        if not pending_orders:
            return []
        
        try:
            # Sort by timestamp and get the latest
            pending_orders.sort(key=lambda t: t.get("timestamp", 0))
            return [pending_orders[-1]]
        except Exception:
            # Fallback: return the last one
            return [pending_orders[-1]]
    
    def _update_sync_metadata(self) -> None:
        """Update sync metadata"""
        try:
            with self.dashboard_service._lock:
                if "data_sources" not in self.dashboard_service._data:
                    self.dashboard_service._data["data_sources"] = {}
                
                self.dashboard_service._data["data_sources"]["simulator_synced"] = True
                self.dashboard_service._data["data_sources"]["last_sync_time"] = datetime.now().isoformat()
                self._last_sync_time = datetime.now()
                
                # Save data to disk
                self.dashboard_service._save_data()
                
        except Exception as e:
            logger.error(f"❌ Failed to update sync metadata: {e}")
    
    def clear_stale_pending_orders(self) -> None:
        """Clear stale pending orders that are no longer in the lifecycle manager"""
        try:
            with self.dashboard_service._lock:
                current_trades = self.dashboard_service._data.get("trades", [])
                
                # Remove pending orders that are older than 5 minutes
                cutoff_time = datetime.now().timestamp() - 300  # 5 minutes ago
                filtered_trades = []
                
                for trade in current_trades:
                    if trade.get("status") == "PENDING":
                        trade_time = trade.get("timestamp", 0)
                        
                        # Handle both string (ISO format) and float timestamps
                        try:
                            if isinstance(trade_time, str):
                                # Convert ISO string to timestamp
                                trade_timestamp = datetime.fromisoformat(trade_time.replace('Z', '+00:00')).timestamp()
                            else:
                                # Already a timestamp
                                trade_timestamp = float(trade_time)
                            
                            if trade_timestamp > cutoff_time:
                                filtered_trades.append(trade)
                            else:
                                logger.debug(f"🗑️ Removed stale pending order: {trade.get('order_id', 'unknown')}")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"⚠️ Invalid timestamp format for trade {trade.get('order_id', 'unknown')}: {trade_time}")
                            # Keep the trade if we can't parse the timestamp
                            filtered_trades.append(trade)
                    else:
                        filtered_trades.append(trade)
                
                self.dashboard_service._data["trades"] = filtered_trades
                self.dashboard_service._save_data()
                
        except Exception as e:
            logger.error(f"❌ Failed to clear stale pending orders: {e}")


# Factory function for dependency injection
def create_dashboard_sync_service(dashboard_service) -> DashboardSyncService:
    """
    Factory function to create DashboardSyncService with dependency injection
    
    Args:
        dashboard_service: DashboardService instance
    
    Returns:
        Configured DashboardSyncService instance
    """
    return DashboardSyncService(dashboard_service)

# Global instance for backward compatibility
_global_dashboard_sync_service = None

def get_global_dashboard_sync_service(dashboard_service=None) -> DashboardSyncService:
    """Get global dashboard sync service singleton"""
    global _global_dashboard_sync_service
    if _global_dashboard_sync_service is None and dashboard_service:
        _global_dashboard_sync_service = create_dashboard_sync_service(dashboard_service)
    return _global_dashboard_sync_service
