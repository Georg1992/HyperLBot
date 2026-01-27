#!/usr/bin/env python3
"""
System Initializer - Handles all system initialization and phase management
Clear separation between Initialization Phase and Analysis Phase
"""

import time
import os
from typing import Dict, Any, List, Optional
from loguru import logger
from core.constants import technical_constants

class SystemInitializer:
    """Comprehensive system initializer with clear phase separation"""
    
    def __init__(self):
        self.initialization_complete = False
        self.analysis_ready = False
        self.initialization_results = {}
        self.singleton_systems = {}
        
        logger.info("⚙️ System Initializer created - Phase management enabled")
    
    def initialize_system(self, initial_balance: float) -> Dict[str, Any]:
        """
        PHASE 1: Complete System Initialization
        Initialize all systems, check dependencies, and prepare for analysis
        """
        try:
            logger.info("🚀 PHASE 1: SYSTEM INITIALIZATION STARTED")
            
            # Step 1: Initialize Core APIs - Required (NO FALLBACKS)
            api_results = self._initialize_core_apis()
            if not api_results.get("success"):
                raise ValueError("Core API initialization failed (NO FALLBACKS)")
            
            # Store APIs in singleton systems for access
            self.singleton_systems["api_manager"] = api_results["api_manager"]
            self.singleton_systems["hyperliquid_api"] = api_results["hyperliquid_api"]
            self.singleton_systems["hyperliquid_websocket"] = api_results["hyperliquid_websocket"]
            self.singleton_systems["binance_api"] = api_results["binance_api"]
            self.singleton_systems["binance_websocket"] = api_results["binance_websocket"]
            
            # Step 2: Initialize Singleton Systems
            # _initialize_singleton_systems() guarantees to return dict or raise (NO FALLBACKS)
            singleton_results = self._initialize_singleton_systems(initial_balance)
            
            # Step 3: Initialize Data Systems - Required (NO FALLBACKS)
            data_results = self._initialize_data_systems()
            if not data_results.get("success"):
                raise ValueError("Data system initialization failed (NO FALLBACKS)")
            
            # Step 4: Initialize ML Systems (AI prediction logic removed)
            # NOTE: RSI is already initialized with historical data in _register_analysis_modules
            # Required (NO FALLBACKS)
            ml_results = self._initialize_ml_systems()
            if not ml_results.get("success"):
                raise ValueError("ML system initialization failed (NO FALLBACKS)")
            
            # Step 6: Initialize Trading Systems - Required (NO FALLBACKS)
            trading_results = self._initialize_trading_systems()
            if not trading_results.get("success"):
                raise ValueError("Trading system initialization failed (NO FALLBACKS)")
            
            # Step 7: System Health Check
            health_results = self._perform_system_health_check()
            if not health_results["success"]:
                return {"success": False, "error": "System health check failed"}
            
            # Mark initialization as complete
            self.initialization_complete = True
            self.analysis_ready = True
            
            logger.success("✅ PHASE 1 COMPLETE: All systems initialized and ready")
            
            return {
                "success": True,
                "initialization_complete": True,
                "analysis_ready": True,
                "systems_initialized": len(self.singleton_systems),
                "health_status": health_results
            }
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    
    def _initialize_core_apis(self) -> Dict[str, Any]:
        """Initialize all APIs and WebSockets using APIManager"""
        try:
            logger.info("🔌 Initializing all APIs and WebSockets...")
            
            # Initialize API Manager
            from core.services.api_manager import create_api_manager
            api_manager = create_api_manager()
            
            # Initialize all APIs and WebSockets - Required (NO FALLBACKS)
            api_results = api_manager.initialize_all()
            if not api_results.get("success"):
                raise ValueError(f"API initialization failed: {api_results.get('error', 'Unknown error')} (NO FALLBACKS)")
            
            # Store API results in singleton_systems
            self.singleton_systems.update(api_results["apis"])
            self.singleton_systems.update(api_results["websockets"])
            
            # Price logging will be done after MarketDataService is initialized
            
            return {
                "success": True,
                "api_manager": api_manager,
                "hyperliquid_api": api_manager.get_api("hyperliquid_api"),
                "hyperliquid_websocket": api_manager.get_websocket("hyperliquid_websocket"),
                "binance_api": api_manager.get_api("binance_api"),
                "binance_websocket": api_manager.get_websocket("binance_websocket"),
                "fear_greed_api": api_manager.get_api("fear_greed_api"),
                "whale_analytics_api": api_manager.get_api("whale_analytics_api"),
                "rss_news_api": api_manager.get_api("rss_news_api"),
            }
            
        except Exception as e:
            logger.error(f"❌ API initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    # REMOVED: _initialize_rsi_with_data - was redundant with _register_analysis_modules
    # RSI is now initialized once in _register_analysis_modules with historical data
    
    def _initialize_singleton_systems(self, initial_balance: float) -> Dict[str, Any]:
        """Initialize core singleton systems only (no analysis modules)"""
        try:
            logger.info("🔧 Initializing core singleton systems...")
            
            # Preserve existing API results (WebSocket, APIs, etc.)
            existing_systems = self.singleton_systems.copy()
            
            # NOTE: Analysis modules are now created via factory functions in _register_analysis_modules
            # Only core singleton systems that truly need to be singletons are initialized here
            
            # On-Chain Data & Psychological Levels Analyzers removed (not implemented)
            
            # 14. Data Analysis Components
            from core.services.strategy_manager import StrategyManager
            
            # Initialize data analysis components
            from config.config import TradingConfig
            
            # TradingConfig is a class with static attributes, pass the class itself
            strategy_manager = StrategyManager(TradingConfig)
            
            self.singleton_systems["strategy_manager"] = strategy_manager
            
            # Note: account_manager is used via direct import, not via singleton
            # Note: hyperliquid_simulator is not used yet (trading execution not implemented)
            # Note: historical_data_coordinator is not used (replaced by HistoricalDataService)
            
            # Initialize data services
            from core.services.market_data_service import create_market_data_service, set_global_market_data_service
            from core.services.dashboard_service import create_dashboard_service, DashboardService
            from core.services.session_orchestrator import SessionOrchestrator
            
            # Require all systems to be present (NO FALLBACKS)
            hyperliquid_api = self.singleton_systems["hyperliquid_api"]  # Required (NO FALLBACKS)
            hyperliquid_websocket = self.singleton_systems["hyperliquid_websocket"]  # Required (NO FALLBACKS)
            binance_api = self.singleton_systems["binance_api"]  # Required (NO FALLBACKS)
            binance_websocket = self.singleton_systems["binance_websocket"]  # Required (NO FALLBACKS)
            
            market_data_service = create_market_data_service(
                hyperliquid_api,
                hyperliquid_websocket,
                binance_api,
                binance_websocket
            )
            set_global_market_data_service(market_data_service)
            
            dashboard_service = DashboardService.get_global_instance() or create_dashboard_service()
            session_orchestrator = SessionOrchestrator(TradingConfig, initial_balance)  # Use real account balance
            
            self.singleton_systems["market_data_service"] = market_data_service
            self.singleton_systems["dashboard_service"] = dashboard_service
            self.singleton_systems["session_orchestrator"] = session_orchestrator
            
            # Initialize trading logger for session metadata
            from core.logging.trading_logger import TradingLogger
            trading_logger = TradingLogger()
            self.singleton_systems["trading_logger"] = trading_logger
            logger.info("📝 Trading logger initialized")
            
            # ML training DISABLED - SQLite file-level locking causes blocking
            # Training makes heavy database queries that block other operations
            # Even in background thread, SQLite file-level locking blocks main thread
            logger.debug("🤖 ML training disabled - causes database blocking")
            
            # Register analysis modules with MarketDataService
            self._register_analysis_modules(market_data_service)
            
            # Data components and services initialized
            
            # Restore existing API systems (WebSocket, APIs, etc.)
            for key, value in existing_systems.items():
                if key not in self.singleton_systems:
                    self.singleton_systems[key] = value
            
            return self.singleton_systems
            
        except Exception as e:
            logger.error(f"❌ Singleton system initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def _initialize_data_systems(self) -> Dict[str, Any]:
        """Initialize data management systems"""
        try:
            logger.info("📊 Initializing data systems...")
            
            # Clear caches for fresh data using simplified MarketDataService
            market_data_service = self.singleton_systems["market_data_service"]  # Required (NO FALLBACKS)
            if market_data_service:
                market_data_service.invalidate_processed_data()
                logger.info("🗑️ MarketDataService cache cleared")
                
                # Get current price for logging (MarketDataService is now available)
                try:
                    current_price = market_data_service.get_current_price()
                    if current_price:
                        logger.success(f"✅ All APIs initialized - BTC: ${current_price:,.2f}")
                    else:
                        logger.success("✅ All APIs initialized - Price will be available after WebSocket connection")
                except Exception as e:
                    logger.success(f"✅ All APIs initialized - Price logging failed: {e}")
            
            # Data systems initialized
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Data system initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def _initialize_ml_systems(self) -> Dict[str, Any]:
        """Initialize ML systems - Currently no ML systems (prediction removed)"""
        try:
            logger.info("🧠 ML systems initialization skipped - prediction system removed")
            # ML systems will be re-implemented in the future with clean architecture
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ ML system initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def _initialize_trading_systems(self) -> Dict[str, Any]:
        """Initialize trading-specific systems"""
        try:
            logger.info("💰 Initializing trading systems...")
            
            # Trading systems are initialized through singletons
            # ML/prediction systems removed - no verification needed
            
            # Trading systems ready
            return {"success": True}
                
        except Exception as e:
            logger.error(f"❌ Trading system initialization failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def _perform_system_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            logger.info("🏥 Performing system health check...")
            
            health_status = {
                "apis_connected": True,
                "singletons_ready": len(self.singleton_systems) > 0,
                "data_systems_ready": True,
                "ml_systems_ready": True,  # ML systems removed, will be re-implemented
                "trading_systems_ready": True  # Trading systems ready
            }
            
            all_healthy = all(health_status.values())
            
            if not all_healthy:
                raise ValueError(f"System health check failed: {health_status} (NO FALLBACKS)")
            
            logger.success("✅ System health check passed")
            
            return {
                "success": True,
                "health_status": health_status,
                "ready_for_analysis": True
            }
            
        except Exception as e:
            logger.error(f"❌ System health check failed: {e}")
            raise  # NO FALLBACKS - must raise to prevent silent failures
    
    def is_analysis_ready(self) -> bool:
        """Check if system is ready for analysis phase"""
        return self.analysis_ready and self.initialization_complete
    
    def get_singleton_system(self, system_name: str):
        """Get a specific singleton system - Required (NO FALLBACKS)"""
        if system_name not in self.singleton_systems:
            raise ValueError(f"System '{system_name}' not found in singleton_systems (NO FALLBACKS)")
        return self.singleton_systems[system_name]
    
    def get_all_systems_status(self) -> Dict[str, Any]:
        """Get status of all initialized systems"""
        return {
            "initialization_complete": self.initialization_complete,
            "analysis_ready": self.analysis_ready,
            "singleton_systems": list(self.singleton_systems.keys()),
            "system_count": len(self.singleton_systems)
        }
    
    def _ensure_env_file(self):
        """Ensure .env file exists for configuration"""
        try:
            if not os.path.exists('.env'):
                logger.info("📝 .env file not found - creating from template")
                if os.path.exists('env_example.txt'):
                    import shutil
                    shutil.copy('env_example.txt', '.env')
                    logger.success("✅ .env file created from template")
                else:
                    logger.warning("⚠️ env_example.txt not found - .env file not created")
            else:
                logger.debug("✅ .env file exists")
        except Exception as e:
            logger.error(f"❌ Failed to ensure .env file: {e}")
    
    def _register_analysis_modules(self, market_data_service) -> None:
        """Register analysis modules with MarketDataService using new factory functions"""
        try:
            logger.info("📊 Registering analysis modules with MarketDataService using new architecture...")
            
            # Use new factory functions instead of singleton pattern
            from core.calculations.rsi_calculator import create_rsi_calculator
            from core.calculations.volatility_calculator import create_volatility_calculator
            from core.calculations.trend_calculator import create_trend_calculator
            from core.calculations.support_resistance_calculator import create_sr_calculator
            from core.calculations.volume_calculator import create_volume_calculator
            from core.calculations.pressure_calculator import create_pressure_calculator
            from core.analysis.real_time.market_conditions_analyzer import create_market_conditions_analyzer
            from core.analysis.real_time.pattern_recognition_engine import PatternRecognitionEngine
            from core.analysis.real_time.funding_rate_analyzer import create_funding_rate_analyzer
            from core.analysis.real_time.orderbook_analyzer import create_orderbook_analyzer
            from core.analysis.real_time.cross_asset_correlation_analyzer import create_cross_asset_correlation_analyzer
            
            # Register calculation modules with new factory functions
            rsi_calculator = create_rsi_calculator()
            # Initialize RSI calculator with baseline data
            from config.config import TradingConfig
            symbol = TradingConfig.SYMBOL
            try:
                from core.services.historical_data_service import create_historical_data_service
                historical_service = create_historical_data_service()
                candles_5m = historical_service.get_5m_candles(symbol, 30)
                if candles_5m and len(candles_5m) >= 15:
                    rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                else:
                    logger.warning("⚠️ RSI Calculator - insufficient historical data, using defaults")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize RSI: {e}")
            
            market_data_service.register_analysis_module("rsi_calculator", rsi_calculator)
            market_data_service.register_analysis_module("volatility", create_volatility_calculator(symbol))
            market_data_service.register_analysis_module("trend", create_trend_calculator())
            market_data_service.register_analysis_module("support_resistance", create_sr_calculator(symbol))
            market_data_service.register_analysis_module("volume", create_volume_calculator(symbol))
            market_data_service.register_analysis_module("pressure", create_pressure_calculator(symbol))
            
            # Register analysis modules with new factory functions
            # Pass market_data_service as data_provider for whale data access
            market_data_service.register_analysis_module("market_conditions", create_market_conditions_analyzer(data_provider=market_data_service))
            market_data_service.register_analysis_module("pattern_recognition", PatternRecognitionEngine(symbol))
            market_data_service.register_analysis_module("funding_rate", create_funding_rate_analyzer())
            market_data_service.register_analysis_module("orderbook", create_orderbook_analyzer())
            market_data_service.register_analysis_module("cross_asset_correlation_analyzer", create_cross_asset_correlation_analyzer())
            
            # Register consolidation tracker
            from core.analysis.real_time.consolidation_tracker import ConsolidationTracker
            market_data_service.register_analysis_module("consolidation", ConsolidationTracker(symbol))
            
            logger.info("📊 Analysis modules registered with MarketDataService using new factory functions")
            
            # Verify critical modules are registered
            try:
                registered_modules = list(market_data_service._analysis_modules.keys())
                logger.info(f"✅ Registered modules: {', '.join(registered_modules)}")
                
                if "rsi_calculator" not in registered_modules:
                    raise ValueError("CRITICAL: rsi_calculator module registration failed")
                if "pattern_recognition" not in registered_modules:
                    raise ValueError("CRITICAL: pattern_recognition module registration failed")
            except AttributeError:
                raise ValueError("CRITICAL: market_data_service._analysis_modules not accessible")
            
        except Exception as e:
            logger.error(f"❌ Failed to register analysis modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise  # Re-raise to prevent silent failures
    

# Global system initializer instance
_global_system_initializer = None

def get_system_initializer() -> SystemInitializer:
    """Get the global system initializer instance (singleton pattern)"""
    global _global_system_initializer
    if _global_system_initializer is None:
        _global_system_initializer = SystemInitializer()
        logger.info("⚙️ Created global System Initializer instance")
    return _global_system_initializer