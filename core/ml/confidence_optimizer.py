#!/usr/bin/env python3
"""
Confidence Optimizer - Data-Driven Threshold Balancing
Uses historical trade data to optimize confidence calculation weights and thresholds
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split


@dataclass
class ConfidenceFactor:
    """Individual confidence factor with optimized parameters"""
    name: str
    weight: float = 0.0
    threshold: float = 0.0
    boost_value: float = 0.0
    penalty_value: float = 0.0
    is_active: bool = True
    importance_score: float = 0.0


@dataclass
class TradeRecord:
    """Historical trade record for optimization"""
    timestamp: float
    direction: str
    confidence: float
    market_data: Dict[str, Any]
    outcome: str  # "WIN", "LOSS", "BREAKEVEN"
    profit_loss: float
    hold_time: float
    factors: Dict[str, float]  # Individual factor contributions


class ConfidenceOptimizer:
    """
    Data-driven confidence threshold and weight optimizer
    
    Uses machine learning to:
    1. Analyze historical trade performance
    2. Identify most predictive factors
    3. Optimize weights and thresholds
    4. Continuously improve based on new data
    """
    
    def __init__(self, data_path: str = "data/confidence_optimization"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        # Trade history for optimization
        self.trade_history: List[TradeRecord] = []
        self.optimized_factors: Dict[str, ConfidenceFactor] = {}
        
        # ML models for factor importance
        self.factor_importance_model = None
        self.weight_optimization_model = None
        
        # Performance tracking
        self.optimization_history = []
        
        # Load existing data
        self._load_optimization_data()
        
        logger.info("🎯 Confidence Optimizer initialized")
    
    def add_trade_record(self, trade_record: TradeRecord) -> None:
        """Add a new trade record for optimization"""
        self.trade_history.append(trade_record)
        
        # Keep only last 10,000 records for performance
        if len(self.trade_history) > 10000:
            self.trade_history = self.trade_history[-10000:]
        
        logger.debug(f"📊 Added trade record: {trade_record.outcome} (confidence: {trade_record.confidence:.1%})")
    
    def optimize_confidence_calculation(self) -> Dict[str, ConfidenceFactor]:
        """
        Optimize confidence calculation using historical data
        
        Returns:
            Dict of optimized confidence factors
        """
        if len(self.trade_history) < 50:
            logger.warning("⚠️ Insufficient trade data for optimization (need 50+ trades)")
            return self._get_default_factors()
        
        try:
            # Prepare data for ML analysis
            X, y = self._prepare_ml_data()
            
            if len(X) < 50:
                logger.warning("⚠️ Insufficient data for ML analysis")
                return self._get_default_factors()
            
            # Split data for training and testing
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # 1. Analyze factor importance using Random Forest
            self._analyze_factor_importance(X_train, y_train)
            
            # 2. Optimize weights using Logistic Regression
            self._optimize_weights(X_train, y_train, X_test, y_test)
            
            # 3. Optimize thresholds using performance analysis
            self._optimize_thresholds()
            
            # 4. Generate optimized factors
            optimized_factors = self._generate_optimized_factors()
            
            # Save optimization results
            self._save_optimization_results(optimized_factors)
            
            logger.success(f"✅ Confidence optimization completed with {len(self.trade_history)} trades")
            return optimized_factors
            
        except Exception as e:
            logger.error(f"❌ Confidence optimization failed: {e}")
            return self._get_default_factors()
    
    def _prepare_ml_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for machine learning analysis"""
        features = []
        outcomes = []
        
        for trade in self.trade_history:
            # Extract features from market data
            feature_vector = self._extract_features(trade.market_data, trade.factors)
            features.append(feature_vector)
            
            # Convert outcome to binary (1 = win, 0 = loss/breakeven)
            outcome = 1 if trade.outcome == "WIN" else 0
            outcomes.append(outcome)
        
        return np.array(features), np.array(outcomes)
    
    def _extract_features(self, market_data: Dict[str, Any], factors: Dict[str, float]) -> List[float]:
        """Extract feature vector from market data and factors"""
        features = []
        
        # Core market features
        features.extend([
            market_data.get("rsi", 50) / 100.0,  # Normalize RSI
            market_data.get("volatility_5m", 0.01),
            market_data.get("volume_category", "NORMAL") in ["HIGH", "VERY_HIGH", "EXTREME"],
            market_data.get("pressure_data", {}).get("direction", "NEUTRAL") in ["BUY", "STRONG_BUY"],
            market_data.get("market_conditions_analysis", {}).get("market_quality", "UNKNOWN") == "EXCELLENT",
        ])
        
        # Factor contributions
        factor_names = [
            "expected_value", "rsi_signal", "volume_confirmation", "pressure_momentum",
            "pattern_confirmation", "trend_alignment", "sr_proximity", "market_quality",
            "sentiment_alignment", "funding_alignment", "poc_proximity",
            "cross_asset_correlation", "volatility_penalty"
        ]
        
        for factor_name in factor_names:
            features.append(factors.get(factor_name, 0.0))
        
        return features
    
    def _analyze_factor_importance(self, X: np.ndarray, y: np.ndarray) -> None:
        """Analyze which factors are most important for prediction success"""
        try:
            # Use Random Forest to get feature importance
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            rf.fit(X, y)
            
            # Get feature importance scores
            importance_scores = rf.feature_importances_
            
            # Map importance to factor names
            factor_names = [
                "rsi", "volatility", "high_volume", "buy_pressure", "excellent_market",
                "expected_value", "rsi_signal", "volume_confirmation", "pressure_momentum",
                "pattern_confirmation", "trend_alignment", "sr_proximity", "market_quality",
                "sentiment_alignment", "funding_alignment", "poc_proximity",
                "cross_asset_correlation", "volatility_penalty"
            ]
            
            self.factor_importance = dict(zip(factor_names, importance_scores))
            
            logger.info("📊 Factor importance analysis completed")
            for factor, importance in sorted(self.factor_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"   {factor}: {importance:.3f}")
                
        except Exception as e:
            logger.error(f"❌ Factor importance analysis failed: {e}")
            self.factor_importance = {}
    
    def _optimize_weights(self, X_train: np.ndarray, y_train: np.ndarray, 
                         X_test: np.ndarray, y_test: np.ndarray) -> None:
        """Optimize factor weights using logistic regression"""
        try:
            # Train logistic regression model
            lr = LogisticRegression(random_state=42, max_iter=1000)
            lr.fit(X_train, y_train)
            
            # Get predictions and performance metrics
            y_pred = lr.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            logger.info(f"📈 ML Model Performance:")
            logger.info(f"   Accuracy: {accuracy:.3f}")
            logger.info(f"   Precision: {precision:.3f}")
            logger.info(f"   Recall: {recall:.3f}")
            logger.info(f"   F1-Score: {f1:.3f}")
            
            # Extract optimized weights from model coefficients
            self.optimized_weights = lr.coef_[0]
            self.model_performance = {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
            
        except Exception as e:
            logger.error(f"❌ Weight optimization failed: {e}")
            self.optimized_weights = None
            self.model_performance = {}
    
    def _optimize_thresholds(self) -> None:
        """Optimize confidence thresholds based on performance analysis"""
        try:
            # Analyze performance by confidence ranges
            confidence_ranges = [
                (0.0, 0.3), (0.3, 0.5), (0.5, 0.6), (0.6, 0.7), 
                (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)
            ]
            
            range_performance = {}
            
            for low_conf, high_conf in confidence_ranges:
                range_trades = [
                    trade for trade in self.trade_history 
                    if low_conf <= trade.confidence < high_conf
                ]
                
                if len(range_trades) >= 5:  # Minimum sample size
                    wins = sum(1 for trade in range_trades if trade.outcome == "WIN")
                    win_rate = wins / len(range_trades)
                    avg_profit = np.mean([trade.profit_loss for trade in range_trades])
                    
                    range_performance[f"{low_conf:.1f}-{high_conf:.1f}"] = {
                        "win_rate": win_rate,
                        "avg_profit": avg_profit,
                        "sample_size": len(range_trades)
                    }
            
            # Find optimal confidence threshold
            optimal_threshold = 0.6  # Default
            best_performance = 0.0
            
            for range_name, perf in range_performance.items():
                # Combined score: win_rate * avg_profit
                combined_score = perf["win_rate"] * max(0, perf["avg_profit"])
                
                if combined_score > best_performance and perf["sample_size"] >= 10:
                    best_performance = combined_score
                    optimal_threshold = float(range_name.split("-")[0])
            
            self.optimal_confidence_threshold = optimal_threshold
            self.range_performance = range_performance
            
            logger.info(f"🎯 Optimal confidence threshold: {optimal_threshold:.1%}")
            
        except Exception as e:
            logger.error(f"❌ Threshold optimization failed: {e}")
            self.optimal_confidence_threshold = 0.6
            self.range_performance = {}
    
    def _generate_optimized_factors(self) -> Dict[str, ConfidenceFactor]:
        """Generate optimized confidence factors based on analysis"""
        factors = {}
        
        # Core factors with optimized weights
        factor_configs = {
            "expected_value": {"weight": 0.20, "threshold": 0.05, "boost": 0.20, "penalty": -0.15},
            "rsi_signal": {"weight": 0.15, "threshold": 30.0, "boost": 0.15, "penalty": 0.0},
            "volume_confirmation": {"weight": 0.15, "threshold": 0.0, "boost": 0.15, "penalty": -0.08},
            "pressure_momentum": {"weight": 0.08, "threshold": 0.0, "boost": 0.08, "penalty": -0.08},
            "pattern_confirmation": {"weight": 0.06, "threshold": 0.0, "boost": 0.06, "penalty": 0.0},
            "trend_alignment": {"weight": 0.05, "threshold": 0.0, "boost": 0.05, "penalty": -0.05},
            "sr_proximity": {"weight": 0.10, "threshold": 0.01, "boost": 0.10, "penalty": 0.0},
            "market_quality": {"weight": 0.08, "threshold": 0.0, "boost": 0.08, "penalty": -0.10},
            "sentiment_alignment": {"weight": 0.03, "threshold": 0.0, "boost": 0.03, "penalty": 0.0},
            "funding_alignment": {"weight": 0.03, "threshold": 0.0, "boost": 0.03, "penalty": 0.0},
            "poc_proximity": {"weight": 0.03, "threshold": 0.01, "boost": 0.03, "penalty": 0.0},
            "cross_asset_correlation": {"weight": 0.02, "threshold": 0.5, "boost": 0.02, "penalty": 0.0},
            "volatility_penalty": {"weight": 0.0, "threshold": 0.0, "boost": 0.0, "penalty": -0.08}
        }
        
        # Apply ML-optimized adjustments
        if hasattr(self, 'factor_importance') and self.factor_importance:
            for factor_name, config in factor_configs.items():
                # Adjust weight based on importance
                importance = self.factor_importance.get(factor_name, 0.0)
                adjusted_weight = config["weight"] * (1 + importance * 0.5)  # Boost important factors
                
                factors[factor_name] = ConfidenceFactor(
                    name=factor_name,
                    weight=min(0.25, adjusted_weight),  # Cap at 25%
                    threshold=config["threshold"],
                    boost_value=config["boost"],
                    penalty_value=config["penalty"],
                    is_active=True,
                    importance_score=importance
                )
        else:
            # Use default configuration
            for factor_name, config in factor_configs.items():
                factors[factor_name] = ConfidenceFactor(
                    name=factor_name,
                    weight=config["weight"],
                    threshold=config["threshold"],
                    boost_value=config["boost"],
                    penalty_value=config["penalty"],
                    is_active=True,
                    importance_score=0.0
                )
        
        return factors
    
    def _get_default_factors(self) -> Dict[str, ConfidenceFactor]:
        """Get default confidence factors when optimization is not available"""
        return {
            "expected_value": ConfidenceFactor("expected_value", 0.20, 0.05, 0.20, -0.15),
            "rsi_signal": ConfidenceFactor("rsi_signal", 0.15, 30.0, 0.15, 0.0),
            "volume_confirmation": ConfidenceFactor("volume_confirmation", 0.15, 0.0, 0.15, -0.08),
            "pressure_momentum": ConfidenceFactor("pressure_momentum", 0.08, 0.0, 0.08, -0.08),
            "pattern_confirmation": ConfidenceFactor("pattern_confirmation", 0.06, 0.0, 0.06, 0.0),
            "trend_alignment": ConfidenceFactor("trend_alignment", 0.05, 0.0, 0.05, -0.05),
            "sr_proximity": ConfidenceFactor("sr_proximity", 0.10, 0.01, 0.10, 0.0),
            "market_quality": ConfidenceFactor("market_quality", 0.08, 0.0, 0.08, -0.10),
            "sentiment_alignment": ConfidenceFactor("sentiment_alignment", 0.03, 0.0, 0.03, 0.0),
            "funding_alignment": ConfidenceFactor("funding_alignment", 0.03, 0.0, 0.03, 0.0),
            "poc_proximity": ConfidenceFactor("poc_proximity", 0.03, 0.01, 0.03, 0.0),
            "cross_asset_correlation": ConfidenceFactor("cross_asset_correlation", 0.02, 0.5, 0.02, 0.0),
            "volatility_penalty": ConfidenceFactor("volatility_penalty", 0.0, 0.0, 0.0, -0.08)
        }
    
    def _save_optimization_results(self, factors: Dict[str, ConfidenceFactor]) -> None:
        """Save optimization results to disk"""
        try:
            results = {
                "timestamp": pd.Timestamp.now().isoformat(),
                "trade_count": len(self.trade_history),
                "factors": {name: {
                    "weight": factor.weight,
                    "threshold": factor.threshold,
                    "boost_value": factor.boost_value,
                    "penalty_value": factor.penalty_value,
                    "importance_score": factor.importance_score
                } for name, factor in factors.items()},
                "optimal_threshold": getattr(self, 'optimal_confidence_threshold', 0.6),
                "model_performance": getattr(self, 'model_performance', {}),
                "range_performance": getattr(self, 'range_performance', {})
            }
            
            with open(self.data_path / "optimization_results.json", "w") as f:
                json.dump(results, f, indent=2)
            
            logger.info("💾 Optimization results saved")
            
        except Exception as e:
            logger.error(f"❌ Failed to save optimization results: {e}")
    
    def _load_optimization_data(self) -> None:
        """Load existing optimization data"""
        try:
            results_file = self.data_path / "optimization_results.json"
            if results_file.exists():
                with open(results_file, "r") as f:
                    results = json.load(f)
                
                # Load optimized factors
                if "factors" in results:
                    for name, config in results["factors"].items():
                        self.optimized_factors[name] = ConfidenceFactor(
                            name=name,
                            weight=config["weight"],
                            threshold=config["threshold"],
                            boost_value=config["boost_value"],
                            penalty_value=config["penalty_value"],
                            importance_score=config.get("importance_score", 0.0)
                        )
                
                logger.info(f"📊 Loaded optimization data from {results['trade_count']} trades")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load optimization data: {e}")
    
    def get_optimized_factors(self) -> Dict[str, ConfidenceFactor]:
        """Get current optimized factors"""
        if self.optimized_factors:
            return self.optimized_factors
        else:
            return self._get_default_factors()
    
    def get_optimal_threshold(self) -> float:
        """Get optimal confidence threshold"""
        return getattr(self, 'optimal_confidence_threshold', 0.6)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring"""
        return {
            "total_trades": len(self.trade_history),
            "optimization_available": len(self.trade_history) >= 50,
            "optimal_threshold": self.get_optimal_threshold(),
            "model_performance": getattr(self, 'model_performance', {}),
            "range_performance": getattr(self, 'range_performance', {})
        }


# Global optimizer instance
_global_confidence_optimizer = None

def get_global_confidence_optimizer() -> ConfidenceOptimizer:
    """Get global confidence optimizer singleton"""
    global _global_confidence_optimizer
    if _global_confidence_optimizer is None:
        _global_confidence_optimizer = ConfidenceOptimizer()
    return _global_confidence_optimizer
