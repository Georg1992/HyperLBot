#!/usr/bin/env python3
"""
Calibration Hooks for Confidence Validation

Provides infrastructure to log predictions and outcomes for confidence calibration.
This enables validation of confidence estimates against actual results.

NO ML MODELS - Pure infrastructure for logging and calibration metrics.
"""

import sqlite3
import threading
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from contextlib import contextmanager
from loguru import logger
from dataclasses import dataclass, asdict
import json

from config.config import TradingConfig


def _nested_get(data: Dict[str, Any], path: List[str]) -> Optional[Any]:
    """Follow path (e.g. ['trend','strength']) into data. Return None if any key missing."""
    cur = data
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _require_calibration_key(
    unified_data: Dict[str, Any],
    path: List[str],
    context: str,
) -> Any:
    """Read required calibration key from nested path. Raise ValueError if missing (NO FALLBACKS)."""
    v = _nested_get(unified_data, path)
    if v is None:
        raise ValueError(
            f"Calibration required key missing (NO FALLBACKS): path={path!r} ({context})"
        )
    return v


@dataclass
class PredictionRecord:
    """Record of a prediction for calibration"""
    prediction_id: str
    timestamp: float
    strategy: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: Optional[float]
    reasoning: str
    # Feature data for calibration
    long_score: float
    short_score: float
    score_diff: float
    entry_score: float
    volatility_category: str
    trend_direction: str
    volume_category: str
    rsi_value: float
    # Raw feature dict for future ML use
    features_json: str  # JSON string of all features


@dataclass
class OutcomeRecord:
    """Record of prediction outcome for calibration"""
    prediction_id: str
    outcome_timestamp: float
    hit_stop: bool
    hit_target: bool
    profit_pct: float
    duration_seconds: float
    final_price: float
    max_favorable_excursion: float  # Best price reached
    max_adverse_excursion: float  # Worst price reached


class CalibrationHooks:
    """
    Calibration infrastructure for confidence validation
    
    Provides hooks to:
    1. Log predictions with all features
    2. Log outcomes when trades complete
    3. Calculate calibration metrics (Brier score, calibration curve, etc.)
    4. Export data for ML training
    """
    
    def __init__(self, db_path: str = "data/calibration.db"):
        """
        Initialize calibration hooks
        
        Args:
            db_path: Path to SQLite database for storing predictions/outcomes
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.consecutive_failures = 0
        self._init_database()
        logger.info(f"📊 Calibration hooks initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize calibration database schema"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Predictions table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS predictions (
                            prediction_id TEXT PRIMARY KEY,
                            timestamp REAL NOT NULL,
                            strategy TEXT NOT NULL,
                            direction TEXT NOT NULL,
                            entry_price REAL NOT NULL,
                            stop_loss REAL NOT NULL,
                            take_profit REAL NOT NULL,
                            confidence REAL,
                            reasoning TEXT,
                            long_score REAL,
                            short_score REAL,
                            score_diff REAL,
                            entry_score REAL,
                            volatility_category TEXT,
                            trend_direction TEXT,
                            volume_category TEXT,
                            rsi_value REAL,
                            features_json TEXT
                        )
                    """)
                    
                    # Outcomes table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS outcomes (
                            prediction_id TEXT PRIMARY KEY,
                            outcome_timestamp REAL NOT NULL,
                            hit_stop INTEGER NOT NULL,
                            hit_target INTEGER NOT NULL,
                            profit_pct REAL NOT NULL,
                            duration_seconds REAL NOT NULL,
                            final_price REAL NOT NULL,
                            max_favorable_excursion REAL,
                            max_adverse_excursion REAL,
                            FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
                        )
                    """)
                    
                    # Indexes for fast queries
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_predictions_timestamp 
                        ON predictions(timestamp)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_predictions_strategy 
                        ON predictions(strategy)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp 
                        ON outcomes(outcome_timestamp)
                    """)
                    
                    logger.info("✅ Calibration database initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize calibration database: {e}")
                raise
    
    def _extract_calibration_features(self, unified_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Extract calibration features from nested unified_data. NO FALLBACKS for required keys.
        Optional keys: if missing, record in inactive_features as "optional_missing".
        """
        required_paths = {
            "volatility_category": ["volatility_category"],
            "volatility_5m": ["volatility_5m"],
            "trend_direction": ["trend_direction"],
            "volume_category": ["volume_category"],
            "rsi_value": ["rsi_value"],
        }
        optional_paths = {
            "trend_strength": ["trend", "strength"],
            "rsi_trend": ["rsi", "rsi_trend"],
            "spread_pct": ["orderbook_analysis", "bid_ask_spread", "percentage"],
            "liquidity_score": ["orderbook_analysis", "liquidity_depth", "depth_score"],
            "net_pressure": ["pressure", "net_pressure"],
            "pressure_ratio": ["pressure", "pressure_ratio"],
            "funding_direction": ["funding_analysis", "funding_trend", "direction"],
            "volume_trend_strength": ["volume", "volume_trend_strength"],
            "spike_intensity": ["volatility", "spike_intensity"],
            "risk_level": ["market_conditions", "risk_level"],
        }
        inactive: Dict[str, str] = {}
        features: Dict[str, Any] = {}

        for key, path in required_paths.items():
            v = _require_calibration_key(unified_data, path, f"key={key}")
            if key == "rsi_value":
                features[key] = float(v)
            elif key == "volatility_5m":
                features[key] = float(v)
            else:
                features[key] = v

        for key, path in optional_paths.items():
            v = _nested_get(unified_data, path)
            if v is None:
                inactive[key] = "optional_missing"
                continue
            if key in ("trend_strength", "spread_pct", "liquidity_score", "net_pressure", "pressure_ratio", "volume_trend_strength"):
                try:
                    features[key] = float(v)
                except (TypeError, ValueError):
                    inactive[key] = "optional_missing"
            else:
                features[key] = v

        if inactive:
            features["inactive_features"] = inactive
        return features, inactive

    def log_prediction(self, prediction, unified_data: Dict[str, Any], 
                      direction_scores: Dict[str, float], entry_score: float) -> str:
        """
        Log a prediction for calibration. Reads from nested unified_data; no silent defaults.
        Required keys (raise if missing): volatility_category, volatility_5m, trend_direction,
        volume_category, rsi_value. Optional keys use nested paths; missing → inactive_features.
        """
        try:
            prediction_id = f"pred_{int(prediction.timestamp * 1000)}"
            features, _ = self._extract_calibration_features(unified_data)

            record = PredictionRecord(
                prediction_id=prediction_id,
                timestamp=prediction.timestamp,
                strategy=prediction.strategy,
                direction=prediction.direction,
                entry_price=prediction.entry_price,
                stop_loss=prediction.stop_loss,
                take_profit=prediction.take_profit,
                confidence=prediction.confidence,
                reasoning=prediction.reasoning,
                long_score=float(direction_scores.get("long_score") or 0.0),
                short_score=float(direction_scores.get("short_score") or 0.0),
                score_diff=float(direction_scores.get("score_diff") or 0.0),
                entry_score=entry_score,
                volatility_category=str(features["volatility_category"]),
                trend_direction=str(features["trend_direction"]),
                volume_category=str(features["volume_category"]),
                rsi_value=float(features["rsi_value"]),
                features_json=json.dumps(features),
            )

            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO predictions 
                        (prediction_id, timestamp, strategy, direction, entry_price, stop_loss, 
                         take_profit, confidence, reasoning, long_score, short_score, score_diff,
                         entry_score, volatility_category, trend_direction, volume_category, rsi_value, features_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.prediction_id, record.timestamp, record.strategy, record.direction,
                        record.entry_price, record.stop_loss, record.take_profit, record.confidence,
                        record.reasoning, record.long_score, record.short_score, record.score_diff,
                        record.entry_score, record.volatility_category, record.trend_direction,
                        record.volume_category, record.rsi_value, record.features_json
                    ))

            self.consecutive_failures = 0
            logger.debug(f"📊 Logged prediction {prediction_id} for calibration")
            return prediction_id

        except ValueError as e:
            req_key_msg = "Calibration required key missing"
            if req_key_msg in str(e):
                self.consecutive_failures += 1
                threshold = int(getattr(TradingConfig, "CALIBRATION_FAILURE_THRESHOLD", 50))
                if self.consecutive_failures >= threshold:
                    raise RuntimeError(
                        "Calibration disabled: repeated required-key failures"
                    ) from e
            logger.error(f"❌ Failed to log prediction for calibration: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to log prediction for calibration: {e}")
            raise  # NO FALLBACKS - propagate so caller can handle
    
    def log_outcome(self, prediction_id: str, outcome: Dict[str, Any]) -> bool:
        """
        Log outcome for a prediction.
        outcome_timestamp: use from outcome if present; else use prediction timestamp (from DB).
        Never use 0.0 (no dummy timestamps).
        
        Args:
            prediction_id: ID from log_prediction()
            outcome: Dict with:
                - outcome_timestamp: float (optional; else prediction timestamp used)
                - hit_stop: bool
                - hit_target: bool
                - profit_pct: float
                - duration_seconds: float
                - final_price: float
                - max_favorable_excursion: float (optional)
                - max_adverse_excursion: float (optional)
        
        Returns:
            True if logged successfully
        """
        if not prediction_id:
            return False
        
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    ot = outcome.get("outcome_timestamp")
                    if ot is not None:
                        try:
                            outcome_ts = float(ot)
                        except (TypeError, ValueError):
                            outcome_ts = None
                    else:
                        outcome_ts = None
                    if outcome_ts is None:
                        cursor.execute(
                            "SELECT timestamp FROM predictions WHERE prediction_id = ?",
                            (prediction_id,),
                        )
                        row = cursor.fetchone()
                        if not row or row[0] is None:
                            raise ValueError(
                                "log_outcome: outcome_timestamp missing and no prediction timestamp (NO FALLBACKS)"
                            )
                        outcome_ts = float(row[0])
                    cursor.execute("""
                        INSERT OR REPLACE INTO outcomes
                        (prediction_id, outcome_timestamp, hit_stop, hit_target, profit_pct,
                         duration_seconds, final_price, max_favorable_excursion, max_adverse_excursion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        prediction_id,
                        outcome_ts,
                        int(outcome.get("hit_stop", False)),
                        int(outcome.get("hit_target", False)),
                        outcome.get("profit_pct", 0.0),
                        outcome.get("duration_seconds", 0.0),
                        outcome.get("final_price", 0.0),
                        outcome.get("max_favorable_excursion", 0.0),
                        outcome.get("max_adverse_excursion", 0.0)
                    ))
            
            logger.debug(f"📊 Logged outcome for prediction {prediction_id}")
            return True

        except ValueError:
            raise  # No timestamp available, etc. (NO FALLBACKS)
        except Exception as e:
            logger.error(f"❌ Failed to log outcome for calibration: {e}")
            return False
    
    def get_calibration_metrics(self, strategy: Optional[str] = None,
                               start_time: Optional[float] = None,
                               end_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate calibration metrics for confidence validation
        
        Metrics:
        - Brier Score: Measures calibration quality (lower is better, 0 = perfect)
        - Calibration Curve: Confidence bins vs actual win rate
        - Expected Calibration Error (ECE): Average calibration error
        - Overconfidence/Underconfidence: Systematic bias
        
        Args:
            strategy: Filter by strategy (None = all strategies)
            start_time: Start timestamp (None = all time)
            end_time: End timestamp (None = all time)
        
        Returns:
            Dict with calibration metrics
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Build query
                    query = """
                        SELECT p.confidence, o.hit_target, o.profit_pct
                        FROM predictions p
                        INNER JOIN outcomes o ON p.prediction_id = o.prediction_id
                        WHERE p.confidence IS NOT NULL
                    """
                    params = []
                    
                    if strategy:
                        query += " AND p.strategy = ?"
                        params.append(strategy)
                    
                    if start_time:
                        query += " AND p.timestamp >= ?"
                        params.append(start_time)
                    
                    if end_time:
                        query += " AND p.timestamp <= ?"
                        params.append(end_time)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
            
            if len(rows) < 10:
                return {
                    "error": "Insufficient data",
                    "sample_count": len(rows),
                    "message": "Need at least 10 predictions with outcomes for calibration"
                }
            
            # Calculate metrics
            confidences = []
            outcomes = []
            profits = []
            
            for row in rows:
                conf = row["confidence"]
                hit = bool(row["hit_target"])
                profit = row["profit_pct"]
                
                if conf is not None:
                    confidences.append(conf / 100.0)  # Convert to 0-1 range
                    outcomes.append(1.0 if hit else 0.0)
                    profits.append(profit)
            
            # Brier Score: mean((confidence - outcome)^2)
            brier_scores = [(c - o) ** 2 for c, o in zip(confidences, outcomes)]
            brier_score = sum(brier_scores) / len(brier_scores) if brier_scores else 0.0
            
            # Expected Calibration Error (ECE)
            # Bin predictions by confidence and compare to actual win rate
            bins = 10
            bin_width = 1.0 / bins
            ece = 0.0
            calibration_curve = []
            
            for i in range(bins):
                bin_low = i * bin_width
                bin_high = (i + 1) * bin_width
                
                bin_indices = [j for j, c in enumerate(confidences) 
                              if bin_low <= c < bin_high]
                
                if len(bin_indices) > 0:
                    bin_conf = sum(confidences[j] for j in bin_indices) / len(bin_indices)
                    bin_actual = sum(outcomes[j] for j in bin_indices) / len(bin_indices)
                    bin_weight = len(bin_indices) / len(confidences)
                    
                    ece += bin_weight * abs(bin_conf - bin_actual)
                    
                    calibration_curve.append({
                        "confidence_bin": f"{bin_low:.1f}-{bin_high:.1f}",
                        "avg_confidence": bin_conf,
                        "actual_win_rate": bin_actual,
                        "sample_count": len(bin_indices)
                    })
            
            # Overall statistics
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            actual_win_rate = sum(outcomes) / len(outcomes) if outcomes else 0.0
            overconfidence = avg_confidence - actual_win_rate
            
            return {
                "sample_count": len(rows),
                "brier_score": brier_score,
                "expected_calibration_error": ece,
                "avg_confidence": avg_confidence,
                "actual_win_rate": actual_win_rate,
                "overconfidence": overconfidence,
                "calibration_curve": calibration_curve,
                "avg_profit_pct": sum(profits) / len(profits) if profits else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate calibration metrics: {e}")
            return {"error": str(e)}
    
    def get_calibration_data(self, strategy: Optional[str] = None,
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get prediction + outcome data for calibration analysis
        
        Returns:
            List of dicts with prediction and outcome data
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    query = """
                        SELECT p.*, o.hit_stop, o.hit_target, o.profit_pct, o.duration_seconds
                        FROM predictions p
                        INNER JOIN outcomes o ON p.prediction_id = o.prediction_id
                        WHERE 1=1
                    """
                    params = []
                    
                    if strategy:
                        query += " AND p.strategy = ?"
                        params.append(strategy)
                    
                    if start_time:
                        query += " AND p.timestamp >= ?"
                        params.append(start_time)
                    
                    if end_time:
                        query += " AND p.timestamp <= ?"
                        params.append(end_time)
                    
                    query += " ORDER BY p.timestamp ASC"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"❌ Failed to get calibration data: {e}")
            return []
