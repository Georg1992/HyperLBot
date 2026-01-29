#!/usr/bin/env python3
"""
Volatility Classifier Module
Classifies volatility levels (LOW/MODERATE/HIGH/EXTREME) using config-driven thresholds.
"""

from typing import Dict, Any
from loguru import logger


def _get_classifier_thresholds() -> Dict[str, float]:
    from config.config import TradingConfig
    return {
        "LOW_MAX": float(getattr(TradingConfig, "VOL_LVL_LOW_MAX", 0.0015)),
        "MOD_MAX": float(getattr(TradingConfig, "VOL_LVL_MOD_MAX", 0.0030)),
        "HIGH_MAX": float(getattr(TradingConfig, "VOL_LVL_HIGH_MAX", 0.0060)),
    }


class VolatilityClassifier:
    """
    Classifies volatility into LOW, MODERATE, HIGH, EXTREME using config thresholds.
    Single authoritative source; no constants.py duplication.
    """

    def __init__(self):
        logger.debug("📊 VolatilityClassifier initialized")

    def classify_volatility_level(self, volatility: float) -> Dict[str, Any]:
        """
        Classify volatility: <= LOW_MAX -> LOW, <= MOD_MAX -> MODERATE,
        <= HIGH_MAX -> HIGH, else EXTREME.
        """
        try:
            t = _get_classifier_thresholds()
            low_max, mod_max, high_max = t["LOW_MAX"], t["MOD_MAX"], t["HIGH_MAX"]
            if volatility <= low_max:
                level = "LOW"
                description = "Low volatility - stable market conditions"
            elif volatility <= mod_max:
                level = "MODERATE"
                description = "Moderate volatility - normal market conditions"
            elif volatility <= high_max:
                level = "HIGH"
                description = "High volatility - increased market activity"
            else:
                level = "EXTREME"
                description = "Extreme volatility - very high market activity"

            return {
                "level": level,
                "description": description,
                "volatility": volatility,
                "thresholds": dict(t),
            }
        except Exception as e:
            logger.error(f"❌ Volatility classification failed: {e}")
            raise

    def determine_trading_suitability(self, volatility: float, level: str) -> Dict[str, Any]:
        """Trading suitability from level. Unchanged behavior."""
        try:
            if level == "LOW":
                suitable, reason, risk = True, "Low volatility provides stable trading conditions", "LOW"
            elif level == "MODERATE":
                suitable, reason, risk = True, "Moderate volatility offers good trading opportunities", "MEDIUM"
            elif level == "HIGH":
                suitable, reason, risk = True, "High volatility provides opportunities but requires careful risk management", "HIGH"
            else:
                suitable, reason, risk = False, "Extreme volatility creates unpredictable market conditions", "EXTREME"
            return {
                "suitable_for_trading": suitable,
                "reason": reason,
                "risk_level": risk,
                "volatility_level": level,
                "volatility_value": volatility,
            }
        except Exception as e:
            logger.error(f"❌ Trading suitability determination failed: {e}")
            raise

    def get_volatility_recommendations(self, volatility: float, level: str) -> Dict[str, Any]:
        """Recommendations from level. Unchanged behavior."""
        try:
            recs = []
            if level == "LOW":
                recs = ["Consider range trading strategies", "Monitor for breakout opportunities", "Use tighter stop losses due to low volatility"]
            elif level == "MODERATE":
                recs = ["Standard trading strategies work well", "Monitor trend continuation patterns", "Use normal risk management"]
            elif level == "HIGH":
                recs = ["Use wider stop losses", "Consider position sizing adjustments", "Monitor for trend reversals"]
            else:
                recs = ["Avoid new positions", "Consider reducing position sizes", "Wait for volatility to decrease"]
            return {
                "recommendations": recs,
                "volatility_level": level,
                "volatility_value": volatility,
                "recommendation_count": len(recs),
            }
        except Exception as e:
            logger.error(f"❌ Volatility recommendations failed: {e}")
            raise
