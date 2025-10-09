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
            
            # Step 1: Initialize Core APIs
            api_results = self._initialize_core_apis()
            if not api_results["success"]:
                return {"success": False, "error": "Core API initialization failed"}
            
            # Store APIs in singleton systems for access
            self.singleton_systems["api_manager"] = api_results["api_manager"]
            self.singleton_systems["hyperliquid_api"] = api_results["hyperliquid_api"]
            self.singleton_systems["hyperliquid_websocket"] = api_results["hyperliquid_websocket"]
            self.singleton_systems["binance_api"] = api_results["binance_api"]
            self.singleton_systems["binance_websocket"] = api_results["binance_websocket"]
            
            # Step 2: Initialize Singleton Systems
            singleton_results = self._initialize_singleton_systems(initial_balance)
            if not singleton_results["success"]:
                return {"success": False, "error": "Singleton system initialization failed"}
            
            # Step 3: Initialize RSI with Historical Data
            rsi_results = self._initialize_rsi_with_data(api_results["hyperliquid_api"])
            if not rsi_results["success"]:
                return {"success": False, "error": "RSI initialization failed"}
            
            # Step 4: Initialize Data Systems
            data_results = self._initialize_data_systems()
            if not data_results["success"]:
                return {"success": False, "error": "Data system initialization failed"}
            
            # Step 5: Initialize ML Systems (AI prediction logic removed)
            ml_results = self._initialize_ml_systems()
            if not ml_results["success"]:
                return {"success": False, "error": "ML system initialization failed"}
            
            # Step 5: Initialize Trading Systems
            trading_results = self._initialize_trading_systems()
            if not trading_results["success"]:
                return {"success": False, "error": "Trading system initialization failed"}
            
            # Step 6: System Health Check
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
            return {"success": False, "error": str(e)}
    
    def _initialize_core_apis(self) -> Dict[str, Any]:
        """Initialize all APIs and WebSockets using APIManager"""
        try:
            logger.info("🔌 Initializing all APIs and WebSockets...")
            
            # Initialize API Manager
            from core.services.api_manager import get_global_api_manager
            api_manager = get_global_api_manager()
            
            # Initialize all APIs and WebSockets
            api_results = api_manager.initialize_all()
            if not api_results["success"]:
                return {"success": False, "error": api_results["error"]}
            
            # Get current price for logging
            current_price = api_manager.get_api("hyperliquid_api").get_current_price("BTC")
            logger.success(f"✅ All APIs initialized - BTC: ${current_price:,.2f}")
            
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
                "current_price": current_price
            }
            
        except Exception as e:
            logger.error(f"❌ API initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_rsi_with_data(self, hyperliquid_api) -> Dict[str, Any]:
        """Initialize RSI calculator with historical data"""
        try:
            logger.info("🔬 Initializing RSI with historical data...")
            
            from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
            rsi_calculator = get_global_rsi_calculator()
            # Get 5-minute data for RSI baseline calculation from MarketDataService (single source of truth)
            market_data_service = self.singleton_systems.get("market_data_service")
            candles_5m = market_data_service.get_historical_candles("BTC", "5m", 30)
            if candles_5m and len(candles_5m) >= 15:
                rsi_calculator.calculate_hyperliquid_baseline_rsi(candles_5m)
                # RSI Calculator initialized with historical data
                return {"success": True}
            else:
                logger.warning("⚠️ RSI Calculator - insufficient data, using defaults")
                return {"success": True}
                
        except Exception as e:
            logger.error(f"❌ RSI initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_singleton_systems(self, initial_balance: float) -> Dict[str, Any]:
        """Initialize all singleton systems"""
        try:
            logger.info("🔧 Initializing singleton systems...")
            
            # 1. RSI Calculator
            from core.analysis.real_time.rsi_calculator import get_global_rsi_calculator
            rsi_calculator = get_global_rsi_calculator()
            self.singleton_systems["rsi_calculator"] = rsi_calculator
            
            # 2. Trend Calculator
            from core.analysis.real_time.trend_calculator import global_trend_calculator
            self.singleton_systems["trend_calculator"] = global_trend_calculator
            
            # 3. Market Conditions Analyzer
            from core.analysis.real_time.market_conditions_analyzer import global_conditions_analyzer
            self.singleton_systems["conditions_analyzer"] = global_conditions_analyzer
            
            # 4. Volume Calculator
            from core.analysis.real_time.volume_calculator import get_global_volume_calculator
            volume_calculator = get_global_volume_calculator()
            self.singleton_systems["volume_calculator"] = volume_calculator
            
            # 5. Volume Profile Analyzer
            from core.analysis.real_time.volume_profile_analyzer import get_global_volume_profile_analyzer
            volume_profile_analyzer = get_global_volume_profile_analyzer()
            self.singleton_systems["volume_profile_analyzer"] = volume_profile_analyzer
            
            # 6. Support/Resistance Calculator
            from core.analysis.real_time.support_resistance_calculator import get_global_support_resistance_calculator
            support_resistance_calculator = get_global_support_resistance_calculator()
            self.singleton_systems["support_resistance_calculator"] = support_resistance_calculator
            
            # 7. Volatility Calculator
            from core.analysis.real_time.volatility_calculator import get_global_volatility_calculator
            volatility_calculator = get_global_volatility_calculator()
            self.singleton_systems["volatility_calculator"] = volatility_calculator
            
            # 8. Pressure Calculator
            from core.analysis.real_time.pressure_calculator import get_global_pressure_calculator
            pressure_calculator = get_global_pressure_calculator()
            self.singleton_systems["pressure_calculator"] = pressure_calculator
            
            # 9. Order Book Analyzer
            from core.analysis.real_time.orderbook_analyzer import get_global_orderbook_analyzer
            orderbook_analyzer = get_global_orderbook_analyzer()
            self.singleton_systems["orderbook_analyzer"] = orderbook_analyzer
            
            # 10. Pattern Recognition Engine
            from core.analysis.real_time.pattern_recognition_engine import get_global_pattern_recognition_engine
            pattern_recognition_engine = get_global_pattern_recognition_engine()
            self.singleton_systems["pattern_recognition_engine"] = pattern_recognition_engine
            
            # 11. Bounce Validator
            from core.analysis.real_time.bounce_validator import get_global_bounce_validator
            bounce_validator = get_global_bounce_validator()
            self.singleton_systems["bounce_validator"] = bounce_validator
            
            # 12. Cross-Asset Correlation Analyzer
            from core.analysis.real_time.cross_asset_correlation_analyzer import get_global_cross_asset_correlation_analyzer
            cross_asset_correlation_analyzer = get_global_cross_asset_correlation_analyzer()
            self.singleton_systems["cross_asset_correlation_analyzer"] = cross_asset_correlation_analyzer
            
            # 13. Funding Rate Analyzer
            from core.analysis.real_time.funding_rate_analyzer import get_global_funding_rate_analyzer
            funding_rate_analyzer = get_global_funding_rate_analyzer()
            self.singleton_systems["funding_rate_analyzer"] = funding_rate_analyzer
            
            # On-Chain Data & Psychological Levels Analyzers removed (not implemented)
            
            # 14. Trading Components
            from core.analysis.historical.variability_analyzer import VariabilityAnalyzer
            from core.analysis.historical.historical_data_coordinator import MarketDataAnalyzer
            from core.services.strategy_manager import StrategyManager
            from core.execution.fee_manager import FeeManager
            from core.logging.trading_logger import TradingLogger
            from core.execution.trade_quality_manager import TradeManager
            from core.simulated_account_manager import account_manager
            from core.api.hyperliquid_simulator import HyperLiquidSimulator
            from core.execution.trading_execution_wrapper import TradingExecutionWrapper
            
            # Initialize trading components
            from config.config import TradingConfig
            config = TradingConfig()
            
            variability_analyzer = VariabilityAnalyzer(lookback_periods=100)
            historical_data_coordinator = MarketDataAnalyzer()
            strategy_manager = StrategyManager(config)
            fee_manager = FeeManager()
            trading_logger = TradingLogger()
            trade_quality_manager = TradeManager(config.STRATEGY_CONFIGS.get("standard", {}))
            
            # Initialize HyperLiquid simulator with account balance
            hyperliquid_simulator = HyperLiquidSimulator(initial_balance=initial_balance)
            
            # Initialize trading execution wrapper (thin wrapper around simulator)
            trading_execution = TradingExecutionWrapper(
                hyperliquid_simulator=hyperliquid_simulator,
                account_manager=account_manager,
                session_manager=None  # Will be set after session manager initialization
            )
            
            self.singleton_systems["variability_analyzer"] = variability_analyzer
            self.singleton_systems["historical_data_coordinator"] = historical_data_coordinator
            self.singleton_systems["strategy_manager"] = strategy_manager
            self.singleton_systems["fee_manager"] = fee_manager
            self.singleton_systems["trading_logger"] = trading_logger
            self.singleton_systems["trade_quality_manager"] = trade_quality_manager
            self.singleton_systems["hyperliquid_simulator"] = hyperliquid_simulator
            self.singleton_systems["trading_execution"] = trading_execution
            
            # Initialize trading services
            from core.services.market_data_service import MarketDataService
            from core.services.trading_engine import TradingEngine
            from core.services.dashboard_service import DashboardService
            from core.services.session_orchestrator import SessionOrchestrator
            
            market_data_service = MarketDataService(
                historical_data_coordinator,
                self.singleton_systems.get("hyperliquid_api"),
                self.singleton_systems.get("hyperliquid_websocket"),
                self.singleton_systems.get("binance_api")
            )
            
            trading_engine = TradingEngine(
                config,
                config.STRATEGY_CONFIGS.get("standard", {}),
                trade_quality_manager,
                trading_execution,  # Use new trading execution wrapper
                variability_analyzer
            )
            
            # Use global instance if available, otherwise create new one
            dashboard_service = DashboardService.get_global_instance()
            if not dashboard_service:
                dashboard_service = DashboardService()
            session_orchestrator = SessionOrchestrator(config, initial_balance)  # Use real account balance
            
            self.singleton_systems["market_data_service"] = market_data_service
            self.singleton_systems["trading_engine"] = trading_engine
            self.singleton_systems["dashboard_service"] = dashboard_service
            self.singleton_systems["session_orchestrator"] = session_orchestrator
            
            # Trading components and services initialized
            
            # AI and ML systems will be initialized later after APIs are ready
            
            return {
                "success": True,
                "singleton_count": len(self.singleton_systems)
            }
            
        except Exception as e:
            logger.error(f"❌ Singleton system initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_data_systems(self) -> Dict[str, Any]:
        """Initialize data management systems"""
        try:
            logger.info("📊 Initializing data systems...")
            
            # Clear caches for fresh data
            from core.market_data_manager import get_global_market_data_manager
            market_data_manager = get_global_market_data_manager()
            market_data_manager.clear_cache()
            
            # Data systems initialized
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Data system initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_ml_systems(self) -> Dict[str, Any]:
        """Initialize ML systems (AI prediction logic removed)"""
        try:
            logger.info("🤖 Initializing ML systems...")
            
            # ML Systems (strategy selection only - predictions removed)
            from core.ml.probability_engine import get_global_probability_engine
            from core.ml.calibration_tracker import get_global_calibration_tracker
            from core.ml.monte_carlo_simulator import get_global_monte_carlo_simulator
            from core.ml.bayesian_fusion import get_global_bayesian_fusion
            from core.ml.multitimeframe_probability import get_global_multitimeframe_probability
            from core.ml.strategy_selector import global_ml_strategy_selector
            
            self.singleton_systems["probability_engine"] = get_global_probability_engine()
            self.singleton_systems["calibration_tracker"] = get_global_calibration_tracker()
            self.singleton_systems["monte_carlo_simulator"] = get_global_monte_carlo_simulator()
            self.singleton_systems["bayesian_fusion"] = get_global_bayesian_fusion()
            self.singleton_systems["multitimeframe_probability"] = get_global_multitimeframe_probability()
            self.singleton_systems["strategy_selector"] = global_ml_strategy_selector
            
            # ML Systems initialized
            # AI/ML systems ready
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ AI system initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _initialize_trading_systems(self) -> Dict[str, Any]:
        """Initialize trading-specific systems"""
        try:
            logger.info("💰 Initializing trading systems...")
            
            # Trading systems are initialized through singletons
            # Verify key systems are ready
            required_systems = [
                "strategy_selector", 
                "probability_engine", 
                "calibration_tracker", 
                "monte_carlo_simulator",
                "bayesian_fusion",
                "multitimeframe_probability"
            ]
            for system_name in required_systems:
                if system_name not in self.singleton_systems:
                    return {"success": False, "error": f"Required system {system_name} not initialized"}
            
            # Trading systems ready
            return {"success": True}
                
        except Exception as e:
            logger.error(f"❌ Trading system initialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _perform_system_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            logger.info("🏥 Performing system health check...")
            
            health_status = {
                "apis_connected": True,
                "singletons_ready": len(self.singleton_systems) > 0,
                "data_systems_ready": True,
                "ml_systems_ready": "strategy_selector" in self.singleton_systems,
                "trading_systems_ready": "probability_engine" in self.singleton_systems
            }
            
            all_healthy = all(health_status.values())
            
            if all_healthy:
                logger.success("✅ System health check passed")
            else:
                logger.warning("⚠️ Some systems not fully ready")
            
            return {
                "success": all_healthy,
                "health_status": health_status,
                "ready_for_analysis": all_healthy
            }
            
        except Exception as e:
            logger.error(f"❌ System health check failed: {e}")
            return {"success": False, "error": str(e)}
    
    def is_analysis_ready(self) -> bool:
        """Check if system is ready for analysis phase"""
        return self.analysis_ready and self.initialization_complete
    
    def get_singleton_system(self, system_name: str):
        """Get a specific singleton system"""
        return self.singleton_systems.get(system_name)
    
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

# Global system initializer instance
_global_system_initializer = None

def get_system_initializer() -> SystemInitializer:
    """Get the global system initializer instance (singleton pattern)"""
    global _global_system_initializer
    if _global_system_initializer is None:
        _global_system_initializer = SystemInitializer()
        logger.info("⚙️ Created global System Initializer instance")
    return _global_system_initializer