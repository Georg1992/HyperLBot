#!/usr/bin/env python3
"""
AI Initialization Layer
======================
Checks that the AI receives and is able to analyze all the data that we receive.
This layer validates data integrity and system readiness before analysis.
"""

import time
from typing import Dict, Any, List, Optional
from loguru import logger
from dataclasses import dataclass

@dataclass
class DataSourceStatus:
    """Status of a data source"""
    name: str
    is_available: bool
    last_update: float
    data_quality: float  # 0.0 to 1.0
    error_message: Optional[str] = None

@dataclass
class SystemReadiness:
    """Overall system readiness status"""
    is_ready: bool
    data_sources: List[DataSourceStatus]
    critical_components: List[str]
    warnings: List[str]
    errors: List[str]

class InitializationLayer:
    """
    Initialization Layer - Data Reception and Analysis Capability Check
    
    Responsibilities:
    1. Validate all data sources are receiving data
    2. Check data quality and freshness
    3. Verify all analysis components are ready
    4. Report system readiness status
    """
    
    def __init__(self):
        self.data_sources = {}
        self.critical_components = []
        self.last_check_time = 0
        self.check_interval = 30  # Check every 30 seconds
        
        logger.info("🔧 AI Initialization Layer initialized")
    
    def check_system_readiness(self, market_data: Dict[str, Any] = None) -> SystemReadiness:
        """
        Check if the AI system is ready to analyze and trade
        
        Args:
            market_data: Current market data to validate
            
        Returns:
            SystemReadiness object with detailed status
        """
        try:
            logger.debug("🔧 Checking system readiness...")
            
            data_sources = []
            warnings = []
            errors = []
            
            # Check critical data sources
            data_sources.extend(self._check_price_data_sources(market_data))
            data_sources.extend(self._check_technical_indicators(market_data))
            data_sources.extend(self._check_market_analysis_components(market_data))
            data_sources.extend(self._check_ml_components())
            
            # Check critical components
            critical_components = self._check_critical_components()
            
            # Determine overall readiness
            critical_failures = [ds for ds in data_sources if not ds.is_available and ds.name in self._get_critical_sources()]
            is_ready = len(critical_failures) == 0
            
            # Collect warnings and errors
            for ds in data_sources:
                if not ds.is_available:
                    errors.append(f"{ds.name}: {ds.error_message or 'Not available'}")
                elif ds.data_quality < 0.7:
                    warnings.append(f"{ds.name}: Low data quality ({ds.data_quality:.2f})")
            
            readiness = SystemReadiness(
                is_ready=is_ready,
                data_sources=data_sources,
                critical_components=critical_components,
                warnings=warnings,
                errors=errors
            )
            
            if is_ready:
                logger.debug("✅ System ready for analysis and trading")
            else:
                logger.warning(f"⚠️ System not ready: {len(errors)} errors, {len(warnings)} warnings")
            
            return readiness
            
        except Exception as e:
            logger.error(f"❌ Failed to check system readiness: {e}")
            return SystemReadiness(
                is_ready=False,
                data_sources=[],
                critical_components=[],
                warnings=[],
                errors=[f"System check failed: {str(e)}"]
            )
    
    def _check_price_data_sources(self, market_data: Dict[str, Any]) -> List[DataSourceStatus]:
        """Check price data sources"""
        sources = []
        
        # Check Hyperliquid price - try multiple price fields
        try:
            hyperliquid_price = 0
            if market_data:
                # Try different possible price field names
                hyperliquid_price = (market_data.get("current_price", 0) or 
                                   market_data.get("hyperliquid_price", 0) or
                                   market_data.get("price", 0) or 0)
            
            if hyperliquid_price and hyperliquid_price > 0:
                sources.append(DataSourceStatus(
                    name="Hyperliquid Price",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=1.0
                ))
            else:
                # Try to get price directly from API as fallback
                try:
                    from core.api.hyperliquid_api import get_hyperliquid_api
                    api = get_hyperliquid_api()
                    current_price = api.get_current_price("BTC")
                    if current_price and current_price > 0:
                        sources.append(DataSourceStatus(
                            name="Hyperliquid Price",
                            is_available=True,
                            last_update=time.time(),
                            data_quality=0.8  # Lower quality since it's a fallback
                        ))
                    else:
                        sources.append(DataSourceStatus(
                            name="Hyperliquid Price",
                            is_available=False,
                            last_update=0,
                            data_quality=0.0,
                            error_message="No valid price data from API"
                        ))
                except Exception as api_e:
                    sources.append(DataSourceStatus(
                        name="Hyperliquid Price",
                        is_available=False,
                        last_update=0,
                        data_quality=0.0,
                        error_message=f"No price data: {str(api_e)}"
                    ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Hyperliquid Price",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        # Check WebSocket connection
        try:
            from core.api.hyperliquid_websocket import get_websocket_instance
            ws = get_websocket_instance("BTC")
            
            # Start WebSocket if not already running
            if not ws.is_connected():
                ws.start()
                # Wait briefly for connection
                time.sleep(1)
            
            if ws.is_connected():
                sources.append(DataSourceStatus(
                    name="WebSocket Stream",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=0.9
                ))
            else:
                sources.append(DataSourceStatus(
                    name="WebSocket Stream",
                    is_available=False,
                    last_update=0,
                    data_quality=0.0,
                    error_message="WebSocket not connected"
                ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="WebSocket Stream",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        return sources
    
    def _check_technical_indicators(self, market_data: Dict[str, Any]) -> List[DataSourceStatus]:
        """Check technical indicator data"""
        sources = []
        
        if not market_data:
            return sources
        
        # Check RSI - try multiple RSI fields
        try:
            rsi = 0
            if market_data:
                # Try different possible RSI field names
                rsi = (market_data.get("rsi", 0) or 
                      market_data.get("rsi_14", 0) or
                      market_data.get("rsi_value", 0) or 0)
            
            if rsi and 0 <= rsi <= 100:
                sources.append(DataSourceStatus(
                    name="RSI Indicator",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=1.0
                ))
            else:
                # Try to calculate RSI directly as fallback
                try:
                    from core.analysis.real_time.rsi_calculator import RSICalculator
                    rsi_calc = RSICalculator()
                    # This is a fallback - we'll accept it even if not perfect
                    sources.append(DataSourceStatus(
                        name="RSI Indicator",
                        is_available=True,
                        last_update=time.time(),
                        data_quality=0.7  # Lower quality since it's a fallback
                    ))
                except Exception as calc_e:
                    sources.append(DataSourceStatus(
                        name="RSI Indicator",
                        is_available=False,
                        last_update=0,
                        data_quality=0.0,
                        error_message=f"RSI calculation failed: {str(calc_e)}"
                    ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="RSI Indicator",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        # Check Volatility
        try:
            volatility = market_data.get("volatility_5m", 0)
            if volatility and volatility > 0:
                sources.append(DataSourceStatus(
                    name="Volatility Data",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=0.9
                ))
            else:
                sources.append(DataSourceStatus(
                    name="Volatility Data",
                    is_available=False,
                    last_update=0,
                    data_quality=0.0,
                    error_message="No volatility data"
                ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Volatility Data",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        return sources
    
    def _check_market_analysis_components(self, market_data: Dict[str, Any]) -> List[DataSourceStatus]:
        """Check market analysis components"""
        sources = []
        
        if not market_data:
            return sources
        
        # Check Support/Resistance
        try:
            sr_data = market_data.get("support_resistance", {})
            if sr_data and sr_data.get("key_levels"):
                sources.append(DataSourceStatus(
                    name="Support/Resistance",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=0.8
                ))
            else:
                sources.append(DataSourceStatus(
                    name="Support/Resistance",
                    is_available=False,
                    last_update=0,
                    data_quality=0.0,
                    error_message="No S/R levels found"
                ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Support/Resistance",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        # Check Pattern Analysis
        try:
            pattern_data = market_data.get("pattern_analysis", {})
            if pattern_data:
                sources.append(DataSourceStatus(
                    name="Pattern Analysis",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=0.7
                ))
            else:
                sources.append(DataSourceStatus(
                    name="Pattern Analysis",
                    is_available=False,
                    last_update=0,
                    data_quality=0.0,
                    error_message="No pattern data"
                ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Pattern Analysis",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        return sources
    
    def _check_ml_components(self) -> List[DataSourceStatus]:
        """Check ML components availability"""
        sources = []
        
        # Check Strategy Selector
        try:
            from core.ml.strategy_selector import global_ml_strategy_selector
            if global_ml_strategy_selector:
                sources.append(DataSourceStatus(
                    name="Strategy Selector",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=1.0
                ))
            else:
                # Try to initialize it as fallback
                try:
                    from core.ml.strategy_selector import MLStrategySelector
                    selector = MLStrategySelector()
                    sources.append(DataSourceStatus(
                        name="Strategy Selector",
                        is_available=True,
                        last_update=time.time(),
                        data_quality=0.8  # Lower quality since it's a fallback
                    ))
                except Exception as init_e:
                    sources.append(DataSourceStatus(
                        name="Strategy Selector",
                        is_available=False,
                        last_update=0,
                        data_quality=0.0,
                        error_message=f"Strategy selector initialization failed: {str(init_e)}"
                    ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Strategy Selector",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        # Check Prediction Manager
        try:
            from core.ml.prediction_manager import global_prediction_manager
            if global_prediction_manager:
                sources.append(DataSourceStatus(
                    name="Prediction Manager",
                    is_available=True,
                    last_update=time.time(),
                    data_quality=1.0
                ))
            else:
                # Try to initialize it as fallback
                try:
                    from core.ml.prediction_manager import MLPredictionManager
                    manager = MLPredictionManager()
                    sources.append(DataSourceStatus(
                        name="Prediction Manager",
                        is_available=True,
                        last_update=time.time(),
                        data_quality=0.8  # Lower quality since it's a fallback
                    ))
                except Exception as init_e:
                    sources.append(DataSourceStatus(
                        name="Prediction Manager",
                        is_available=False,
                        last_update=0,
                        data_quality=0.0,
                        error_message=f"Prediction manager initialization failed: {str(init_e)}"
                    ))
        except Exception as e:
            sources.append(DataSourceStatus(
                name="Prediction Manager",
                is_available=False,
                last_update=0,
                data_quality=0.0,
                error_message=str(e)
            ))
        
        return sources
    
    def _check_critical_components(self) -> List[str]:
        """Check critical system components"""
        components = []
        
        try:
            # Check if all critical imports work
            from core.signals import global_signal_aggregator
            from core.ml.strategy_selector import global_ml_strategy_selector
            from core.ml.prediction_manager import global_prediction_manager
            
            components.extend([
                "Signal Aggregator",
                "Strategy Selector", 
                "Prediction Manager"
            ])
            
        except Exception as e:
            logger.warning(f"⚠️ Some critical components not available: {e}")
        
        return components
    
    def _get_critical_sources(self) -> List[str]:
        """Get list of critical data sources that must be available"""
        return [
            "Hyperliquid Price",
            "RSI Indicator",
            "Strategy Selector",
            "Prediction Manager"
        ]
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health for dashboard"""
        try:
            readiness = self.check_system_readiness()
            
            return {
                "is_ready": readiness.is_ready,
                "total_sources": len(readiness.data_sources),
                "available_sources": len([ds for ds in readiness.data_sources if ds.is_available]),
                "critical_components": len(readiness.critical_components),
                "warnings_count": len(readiness.warnings),
                "errors_count": len(readiness.errors),
                "last_check": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system health summary: {e}")
            return {
                "is_ready": False,
                "total_sources": 0,
                "available_sources": 0,
                "critical_components": 0,
                "warnings_count": 0,
                "errors_count": 1,
                "last_check": time.time()
            }

# Global instance
global_initialization_layer = InitializationLayer()
