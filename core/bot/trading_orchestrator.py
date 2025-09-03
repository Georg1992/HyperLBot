#!/usr/bin/env python3
"""
Trading Orchestrator - Clean Architecture Version
Coordinates focused services instead of doing everything
Uses composition and delegation following Single Responsibility Principle
"""

import time
import os
from typing import Dict, Any, Optional, List
from loguru import logger

# Configuration
from config.config import TradingConfig
from core.constants import constants, ui_constants

# Core Services (Clean Architecture)
from core.services.trading_engine import TradingEngine
from core.services.market_data_service import MarketDataService
from core.services.dashboard_service import DashboardService
from core.services.session_orchestrator import SessionOrchestrator
from core.services.system_initializer import SystemInitializer

# Supporting Components
from core.analysis.historical.variability_analyzer import VariabilityAnalyzer
from core.analysis.historical.historical_data_coordinator import MarketDataAnalyzer
from core.execution.trade_quality_manager import TradeManager
from core.execution.position_lifecycle_manager import TradingExecution
from strategies.prediction_engine import PredictionEngine
from core.execution.fee_manager import FeeManager
from core.logging.trading_logger import TradingLogger
from core.state.trade_state_manager import trade_state_manager
from core.simulated_account_manager import account_manager

class TradingOrchestrator:
    """
    Clean Trading Orchestrator - Coordinates focused services
    Single Responsibility: Service coordination (no business logic)
    """
    
    def __init__(self, initial_balance: float = None, strategy_name: str = None, balance_mode: str = "simulated"):
        self.config = TradingConfig()
        self.initial_balance = initial_balance or self.config.DEFAULT_INITIAL_BALANCE
        self.strategy_name = strategy_name or self.config.DEFAULT_STRATEGY
        self.strategy_config = self.config.STRATEGY_CONFIGS.get(self.strategy_name, self.config.STRATEGY_CONFIGS["standard"])
        self.balance_mode = balance_mode
        
        # Initialize supporting components
        self._initialize_components()
        
        # Initialize focused services
        self._initialize_services()
        
        logger.info("🎯 Trading Orchestrator initialized - Clean architecture with focused services")
        logger.info(f"   📊 5 services: TradingEngine, MarketDataService, DashboardService, SessionOrchestrator, SystemInitializer")
        logger.info(f"   ⚡ Single Responsibility Principle: Each service has one clear purpose")
    
    def _initialize_components(self):
        """Initialize supporting components"""
        # Core components
        self.variability_analyzer = VariabilityAnalyzer(lookback_periods=100)
        self.historical_data_coordinator = MarketDataAnalyzer()
        self.prediction_engine = PredictionEngine(self.strategy_config)
        self.fee_manager = FeeManager()
        self.trading_logger = TradingLogger()
        
        # Execution components
        self.trade_quality_manager = TradeManager(self.strategy_config)
        self.position_lifecycle_manager = TradingExecution(self)  # Still needs reference for now
        
        # Initialize state needed by PositionLifecycleManager (backward compatibility)
        self.open_positions = []
        self.closed_positions = []
        self.trade_history = []
        self.paper_balance = self.initial_balance
        self.last_trade_time = 0
        self.yahoo_analysis = {}
        self.leverage_settings = {"max_leverage": self.config.LEVERAGE or 30}
        self.account_manager = account_manager
        
        # Connect trading components
        self.trade_quality_manager.get_open_positions = self.get_open_positions
        
        # Add references needed by PositionLifecycleManager (backward compatibility)
        self.trade_manager = self.trade_quality_manager
        self.trading_logger = self.trading_logger
        self.fee_manager = self.fee_manager
        
        logger.info("🔧 Supporting components initialized")
    
    def _initialize_services(self):
        """Initialize the 5 focused services"""
        # 1. System Initializer
        self.system_initializer = SystemInitializer(self.config)
        
        # 2. Market Data Service  
        self.market_data_service = MarketDataService(
            self.historical_data_coordinator,
            None,  # Will be set after initialization
            None   # Will be set after initialization
        )
        
        # 3. Trading Engine
        self.trading_engine = TradingEngine(
            self.config,
            self.strategy_config,
            self.prediction_engine,
            self.trade_quality_manager,
            self.position_lifecycle_manager,
            self.variability_analyzer
        )
        
        # 4. Dashboard Service
        self.dashboard_service = DashboardService()
        
        # 5. Session Orchestrator
        self.session_orchestrator = SessionOrchestrator(self.config, self.initial_balance)
        
        logger.info("🎯 5 focused services initialized successfully")
        
        # Add API references after initialization (will be set by SystemInitializer)
        self.hyperliquid_api = None
        self.hyperliquid_simulator = None
        self.session_manager = None
    
    def connect(self) -> bool:
        """Connect to APIs (delegate to SystemInitializer)"""
        init_result = self.system_initializer.initialize_system(self.market_data_service)
        
        if init_result["success"]:
            # Update market data service with initialized APIs
            self.market_data_service.hyperliquid_api = init_result["hyperliquid_api"]
            self.market_data_service.hyperliquid_websocket = init_result.get("hyperliquid_websocket")
            
            # Set references for backward compatibility (needed by PositionLifecycleManager)
            self.hyperliquid_api = init_result["hyperliquid_api"]
            self.hyperliquid_simulator = init_result["hyperliquid_simulator"]
            
            # Set up WebSocket price callback for REAL-TIME dashboard updates
            if self.market_data_service.hyperliquid_websocket:
                def on_price_update(price_data):
                    current_price = price_data.get("current_price", 0)
                    if current_price > 0:
                        # Update cached price
                        self.market_data_service.update_cached_websocket_price(current_price)
                        
                        # Real-time RSI updates (enhanced sensitivity for scalping)
                        try:
                            # Calculate real-time RSI (enhanced sensitivity for scalping)
                            from core.market_data_manager import global_rsi_calculator
                            rsi_data = global_rsi_calculator.update_realtime_rsi(current_price)
                            current_rsi = rsi_data.get("rsi", 50.0)
                            
                            # Real-time RSI logging removed - was spamming console
                            
                            # Update dashboard with fixed real-time RSI + price
                            from core.dashboard.dashboard_data_manager import simple_rtm
                            existing_data = simple_rtm.get_market_data()
                            
                            # Real-time RSI (now properly interpolated between Yahoo points)
                            existing_data.update({
                                "current_price": current_price,
                                "rsi": current_rsi,
                                "rsi_trend": rsi_data.get("rsi_trend", "NEUTRAL"),
                                "timestamp": time.time(),
                                "price_source": "hyperliquid_websocket_realtime",
                                "rsi_source": "realtime_enhanced_sensitivity"
                            })
                            
                            self.dashboard_service.update_rtm_market(existing_data)
                            
                        except Exception as e:
                            logger.error(f"❌ Real-time RSI update failed: {e}")
                
                self.market_data_service.hyperliquid_websocket.add_price_callback(on_price_update)
            
            return True
        else:
            logger.error(f"❌ Connection failed: {init_result.get('error', 'Unknown error')}")
            return False
    
    def run_paper_trading(self, max_trades: int = 10, check_interval: int = 5):
        """Run paper trading (delegate to SessionOrchestrator)"""
        if not self.system_initializer.connected:
            logger.error("❌ Not connected to APIs")
            return
        
        # Delegate to session orchestrator
        result = self.session_orchestrator.run_paper_trading_session(
            max_trades, check_interval,
            self.system_initializer, self.market_data_service, 
            self.trading_engine, self.dashboard_service
        )
        
        return result
    
    def close_session(self):
        """Close session gracefully (delegate to DashboardService)"""
        try:
            # End session
            if hasattr(self.session_orchestrator, 'session_manager') and self.session_orchestrator.session_manager:
                self.session_orchestrator.session_manager.end_session()
                logger.info("📅 Session ended")
            
            # Cleanup heartbeat
            self.dashboard_service.cleanup_heartbeat()
            
            # Update dashboard
            self.dashboard_service.update_rtm_activity("🏁 Trading session closed gracefully", "SUCCESS")
            
            logger.success("✅ Session closed gracefully")
            
        except Exception as e:
            logger.error(f"❌ Error closing session: {e}")
    
    # Delegation methods for backward compatibility
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions (delegate to TradingEngine)"""
        return self.trading_engine.get_open_positions()
    
    def should_trade(self, hyperliquid_price: float, yahoo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check if should trade (delegate to TradingEngine)"""
        return self.trading_engine.should_trade(hyperliquid_price, yahoo_analysis, self.market_data_service.hyperliquid_api)
    
    def place_paper_trade(self, side: str, size: float = 0.001, leverage: int = 30, signal_data: Dict = None) -> bool:
        """Place paper trade (delegate to TradingEngine)"""
        return self.trading_engine.place_paper_trade(side, size, leverage, signal_data)
    
    def get_hyperliquid_price(self) -> Optional[float]:
        """Get current price (delegate to MarketDataService)"""
        return self.market_data_service.get_hyperliquid_price()
    
    def get_yahoo_analysis(self, hyperliquid_price: float = None) -> Dict[str, Any]:
        """Get Yahoo analysis (delegate to MarketDataService)"""
        return self.market_data_service.get_yahoo_analysis(hyperliquid_price)
    
    def _update_simple_rtm_activity(self, message: str, level: str = "INFO"):
        """Update RTM activity (delegate to DashboardService)"""
        self.dashboard_service.update_rtm_activity(message, level)
    
    def run_yahoo_hyperliquid_paper_trading(self, max_trades: int = 10, check_interval: int = 5):
        """Run paper trading (backward compatibility - delegate to SessionOrchestrator)"""
        # Set session manager reference so PositionLifecycleManager can access it
        result = self.session_orchestrator.run_paper_trading_session(
            max_trades, check_interval,
            self.system_initializer, self.market_data_service, 
            self.trading_engine, self.dashboard_service
        )
        
        # Set session manager reference for backward compatibility
        if hasattr(self.session_orchestrator, 'session_manager'):
            self.session_manager = self.session_orchestrator.session_manager
            
        return result

# Backward compatibility alias
YahooHyperliquidPaperTradingBot = TradingOrchestrator

def main():
    """Test the clean orchestrator"""
    from core.constants import MagicNumbers
    orchestrator = TradingOrchestrator(initial_balance=MagicNumbers.FALLBACK_BALANCE)
    
    if orchestrator.connect():
        logger.success("✅ Clean orchestrator connected successfully!")
    else:
        logger.error("❌ Clean orchestrator connection failed")

if __name__ == "__main__":
    main()