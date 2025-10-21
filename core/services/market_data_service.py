#!/usr/bin/env python3
"""
Market Data Service - Processed Data Coordinator Architecture
Single Responsibility: Coordinate processed analysis data from analysis modules
New Flow: Raw Data → Analysis Modules → MarketDataService → SessionOrchestrator
"""

import time
from typing import Dict, Any, Optional, List
from loguru import logger

class MarketDataService:
    """Processed data coordinator - receives analysis from modules, coordinates for consumers"""
    
    def __init__(self, hyperliquid_api, hyperliquid_websocket, binance_api=None):
        self.hyperliquid_api = hyperliquid_api
        self.hyperliquid_websocket = hyperliquid_websocket
        self.binance_api = binance_api
        
        # Processed data storage (from analysis modules)
        self._processed_data = {}
        self._data_timestamps = {}
        self._update_schedules = {
            "volatility": 60,      # 1 minute
            "trend": 60,           # 1 minute  
            "support_resistance": 300,  # 5 minutes
            "rsi": 60,             # 1 minute
            "volume": 30,          # 30 seconds
            "market_conditions": 300,  # 5 minutes
        }
        
        # Analysis module references (will be set by SystemInitializer)
        self._analysis_modules = {}
        
        logger.info("📊 Processed Data Coordinator initialized - New architecture")
    
    # ==================================================================================
    # ANALYSIS MODULE COORDINATION - Register and manage analysis modules
    # ==================================================================================
    
    def register_analysis_module(self, module_name: str, module_instance: Any) -> None:
        """Register an analysis module for data coordination"""
        self._analysis_modules[module_name] = module_instance
        logger.debug(f"📊 Registered analysis module: {module_name}")
    
    def _is_data_valid(self, data_type: str) -> bool:
        """Check if processed data is still valid based on schedule"""
        if data_type not in self._data_timestamps:
            return False
        
        duration = self._update_schedules.get(data_type, 300)  # Default 5 minutes
        return time.time() - self._data_timestamps[data_type] < duration
    
    def _store_processed_data(self, data_type: str, data: Any) -> None:
        """Store processed data from analysis modules"""
        self._processed_data[data_type] = data
        self._data_timestamps[data_type] = time.time()
        logger.debug(f"📊 Stored processed data: {data_type}")
    
    def _get_processed_data(self, data_type: str) -> Any:
        """Get processed data if valid"""
        if self._is_data_valid(data_type):
            logger.debug(f"📊 Using processed data: {data_type}")
            return self._processed_data.get(data_type)
        return None
    
    # ==================================================================================
    # PROCESSED DATA COORDINATION - Coordinate analysis from modules
    # ==================================================================================
    
    def update_analysis_data(self, data_type: str, analysis_data: Any) -> None:
        """Receive processed analysis data from analysis modules"""
        self._store_processed_data(data_type, analysis_data)
        logger.debug(f"📊 Updated {data_type} analysis data")
    
    def get_volatility_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get volatility analysis from VolatilityCalculator"""
        try:
            # Check if we have valid processed data
            volatility_data = self._get_processed_data("volatility")
            if volatility_data:
                return volatility_data
            
            # If no valid data, trigger analysis module to process
            if "volatility" in self._analysis_modules:
                logger.info("📊 Triggering volatility analysis...")
                # Analysis module will process raw data and call update_analysis_data
                return self._analysis_modules["volatility"].get_latest_analysis()
            
            logger.warning("⚠️ No volatility analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get volatility analysis: {e}")
            return {}
    
    def get_trend_analysis(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get trend analysis from TrendCalculator"""
        try:
            trend_data = self._get_processed_data("trend")
            if trend_data:
                return trend_data
            
            if "trend" in self._analysis_modules:
                logger.info("📊 Triggering trend analysis...")
                return self._analysis_modules["trend"].get_latest_analysis()
            
            logger.warning("⚠️ No trend analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend analysis: {e}")
            return {}
    
    def get_support_resistance_analysis(self) -> Dict[str, Any]:
        """Get S/R analysis from SupportResistanceCalculator"""
        try:
            sr_data = self._get_processed_data("support_resistance")
            if sr_data:
                return sr_data
            
            if "support_resistance" in self._analysis_modules:
                logger.info("📊 Triggering S/R analysis...")
                return self._analysis_modules["support_resistance"].get_latest_analysis()
            
            logger.warning("⚠️ No S/R analysis module registered")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get S/R analysis: {e}")
            return {}
    
    # ==================================================================================
    # UNIFIED PROCESSED DATA PACKAGES - Pre-processed data for consumers
    # ==================================================================================
    
    def get_unified_analysis_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get all processed analysis data in one package for SessionOrchestrator"""
        try:
            logger.info("📊 Coordinating unified analysis data...")
            
            # Get all processed analysis data
            unified_data = {
                "volatility": self.get_volatility_analysis(strategy),
                "trend": self.get_trend_analysis(strategy),
                "support_resistance": self.get_support_resistance_analysis(),
                "timestamp": time.time(),
                "strategy": strategy
            }
            
            # Add any additional analysis modules
            for module_name, module_instance in self._analysis_modules.items():
                if module_name not in ["volatility", "trend", "support_resistance"]:
                    try:
                        analysis_data = self._get_processed_data(module_name)
                        if analysis_data:
                            unified_data[module_name] = analysis_data
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get {module_name} analysis: {e}")
            
            logger.info("📊 Unified analysis data coordinated")
            return unified_data
            
        except Exception as e:
            logger.error(f"❌ Failed to coordinate unified analysis data: {e}")
            return {}
    
    def get_prediction_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get optimized data package for prediction engine"""
        try:
            # Get unified analysis data
            analysis_data = self.get_unified_analysis_data(strategy)
            
            # Add raw data access for prediction engine
            prediction_data = {
                **analysis_data,
                "raw_data_access": {
                    "hyperliquid_api": self.hyperliquid_api,
                    "hyperliquid_websocket": self.hyperliquid_websocket,
                    "binance_api": self.binance_api
                }
            }
            
            return prediction_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get prediction data: {e}")
            return {}
    
    def get_dashboard_data(self, strategy: str = "standard") -> Dict[str, Any]:
        """Get optimized data package for dashboard UI"""
        try:
            # Get unified analysis data
            analysis_data = self.get_unified_analysis_data(strategy)
            
            # Add dashboard-specific data
            dashboard_data = {
                **analysis_data,
                "dashboard_ready": True,
                "last_update": time.time()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            return {}
    
    # ==================================================================================
    # DATA STATUS AND MONITORING - Track processed data status
    # ==================================================================================
    
    def get_data_status(self) -> Dict[str, Any]:
        """Get current processed data status"""
        try:
            current_time = time.time()
            data_status = {}
            
            for data_type, timestamp in self._data_timestamps.items():
                age = current_time - timestamp
                data_status[data_type] = {
                    "age_seconds": round(age, 2),
                    "is_valid": self._is_data_valid(data_type),
                    "last_update": timestamp
                }
            
            return {
                "processed_data_count": len(self._processed_data),
                "registered_modules": list(self._analysis_modules.keys()),
                "data_status": data_status,
                "update_schedules": self._update_schedules,
                "last_coordination": current_time
            }
        except Exception as e:
            logger.error(f"❌ Failed to get data status: {e}")
            return {}
    
    def invalidate_processed_data(self, data_type: str = None):
        """Invalidate processed data - specific type or all"""
        try:
            if data_type:
                # Invalidate specific data type
                self._processed_data.pop(data_type, None)
                self._data_timestamps.pop(data_type, None)
                logger.info(f"🗑️ Invalidated {data_type} processed data")
            else:
                # Invalidate all processed data
                self._processed_data.clear()
                self._data_timestamps.clear()
                logger.info("🗑️ Invalidated all processed data")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate processed data: {e}")
    
    def get_analysis_module_status(self) -> Dict[str, Any]:
        """Get status of registered analysis modules"""
        try:
            module_status = {}
            for module_name, module_instance in self._analysis_modules.items():
                try:
                    # Try to get status from module if it has a status method
                    if hasattr(module_instance, 'get_status'):
                        module_status[module_name] = module_instance.get_status()
                    else:
                        module_status[module_name] = {"status": "registered", "type": type(module_instance).__name__}
                except Exception as e:
                    module_status[module_name] = {"status": "error", "error": str(e)}
            
            return {
                "total_modules": len(self._analysis_modules),
                "module_status": module_status
            }
        except Exception as e:
            logger.error(f"❌ Failed to get analysis module status: {e}")
            return {}
    
    def get_data_update_status(self) -> Dict[str, Any]:
        """Get current data update status for processed data coordination"""
        return {
            "hyperliquid_connected": True,
            "websocket_connected": self.hyperliquid_websocket.is_connected() if self.hyperliquid_websocket else False,
            "processed_data_count": len(self._processed_data),
            "registered_modules": list(self._analysis_modules.keys()),
            "last_update": time.time()
        }

# Global instance
_global_market_data_service = None

def get_global_market_data_service() -> MarketDataService:
    """Get the global MarketDataService singleton instance"""
    global _global_market_data_service
    if _global_market_data_service is None:
        # This will be set by SystemInitializer
        logger.warning("⚠️ MarketDataService not initialized - call SystemInitializer first")
    return _global_market_data_service

def set_global_market_data_service(service: MarketDataService):
    """Set the global MarketDataService instance"""
    global _global_market_data_service
    _global_market_data_service = service
    logger.info("📊 Global MarketDataService instance set")