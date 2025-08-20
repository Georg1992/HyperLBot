#!/usr/bin/env python3
"""
Whale Integration Wrapper
Easy integration of whale analytics into existing trading bot
"""

import sys
import os
from typing import Dict, Any, Optional
from loguru import logger

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, 'data'))

try:
    from blockcypher_analyzer import BlockCypherAnalyzer
    WHALE_ANALYTICS_AVAILABLE = True
    logger.info("✅ Whale analytics integration available")
except ImportError as e:
    WHALE_ANALYTICS_AVAILABLE = False
    logger.warning(f"⚠️ Whale analytics not available: {e}")

class WhaleIntegration:
    """Simple wrapper for whale analytics integration"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled and WHALE_ANALYTICS_AVAILABLE
        self.analyzer = None
        
        if self.enabled:
            try:
                self.analyzer = BlockCypherAnalyzer()
                logger.info("🔗 Whale analytics integration initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize whale analytics: {e}")
                self.enabled = False
    
    def is_available(self) -> bool:
        """Check if whale analytics is available"""
        return self.enabled and self.analyzer is not None
    
    def get_whale_sentiment(self) -> Dict[str, Any]:
        """Get current whale sentiment"""
        if not self.is_available():
            return {
                "score": 0.5,
                "sentiment": "neutral",
                "confidence": 0.0,
                "reason": "Whale analytics not available"
            }
        
        try:
            return self.analyzer.get_whale_sentiment_score()
        except Exception as e:
            logger.error(f"❌ Failed to get whale sentiment: {e}")
            return {
                "score": 0.5,
                "sentiment": "neutral",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }
    
    def confirm_trade_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Check if whale activity confirms a trade signal"""
        if not self.is_available():
            return {
                "should_proceed": True,
                "whale_confirmation": "disabled",
                "confidence": 0.0,
                "reason": "Whale analytics not enabled"
            }
        
        try:
            return self.analyzer.should_confirm_trade(signal)
        except Exception as e:
            logger.error(f"❌ Failed to confirm trade signal: {e}")
            return {
                "should_proceed": True,
                "whale_confirmation": "error",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }
    
    def log_whale_analysis(self, trading_logger) -> None:
        """Log current whale analysis to trading logger"""
        if not self.is_available():
            return
        
        try:
            sentiment = self.get_whale_sentiment()
            trading_logger.log_analysis({
                "type": "whale_sentiment",
                "timestamp": sentiment.get("timestamp", 0),
                "datetime": sentiment.get("datetime", ""),
                "score": sentiment.get("score", 0.5),
                "sentiment": sentiment.get("sentiment", "neutral"),
                "confidence": sentiment.get("confidence", 0.0),
                "reason": sentiment.get("reason", ""),
                "whale_activity": sentiment.get("whale_activity", {}),
                "exchange_flows": sentiment.get("exchange_flows", 0),
                "total_inflow": sentiment.get("total_inflow", 0),
                "total_outflow": sentiment.get("total_outflow", 0)
            })
        except Exception as e:
            logger.error(f"❌ Failed to log whale analysis: {e}")

# Simple integration example
def integrate_whale_analytics_into_signal(signal: Dict[str, Any], whale_integration: WhaleIntegration) -> Dict[str, Any]:
    """Integrate whale analytics into an existing trading signal"""
    
    # Get whale confirmation
    whale_confirmation = whale_integration.confirm_trade_signal(signal)
    
    # Add whale data to signal
    signal["whale_confirmation"] = whale_confirmation
    
    # If whale analytics strongly contradicts the signal, consider blocking it
    if (whale_confirmation["whale_confirmation"] == "contradicted" and 
        whale_confirmation["confidence"] > 0.7):
        
        original_should_trade = signal.get("should_trade", False)
        signal["should_trade"] = False
        signal["reason"] = f"{signal.get('reason', '')} | BLOCKED: {whale_confirmation['reason']}"
        
        logger.warning(f"🚫 Trade blocked by whale analytics: {whale_confirmation['reason']}")
        
    elif whale_confirmation["whale_confirmation"] == "confirmed":
        logger.info(f"✅ Trade confirmed by whale analytics: {whale_confirmation['reason']}")
    
    return signal

# Test function
def test_whale_integration():
    """Test the whale integration"""
    logger.info("🧪 Testing Whale Integration...")
    
    # Test with whale analytics enabled
    whale_integration = WhaleIntegration(enabled=True)
    
    if whale_integration.is_available():
        # Test sentiment
        sentiment = whale_integration.get_whale_sentiment()
        logger.info(f"Whale Sentiment: {sentiment}")
        
        # Test trade confirmation
        test_signal = {"side": "BUY", "should_trade": True, "reason": "Test signal"}
        integrated_signal = integrate_whale_analytics_into_signal(test_signal, whale_integration)
        logger.info(f"Integrated Signal: {integrated_signal}")
    else:
        logger.warning("⚠️ Whale analytics not available for testing")
    
    logger.info("✅ Whale Integration test completed")

if __name__ == "__main__":
    test_whale_integration()
