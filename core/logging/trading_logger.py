#!/usr/bin/env python3
"""
Trading Logger for Strategy Analysis and Improvement
Comprehensive logging system for all bot activities, trades, and market data
"""

import json
import time
# import os  # Removed unused import
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from loguru import logger
import csv
from pathlib import Path

class TradingLogger:
    def __init__(self, log_directory: str = "logs"):
        """Initialize the trading logger"""
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.log_directory / "trades").mkdir(exist_ok=True)
        (self.log_directory / "market_data").mkdir(exist_ok=True)
        (self.log_directory / "signals").mkdir(exist_ok=True)
        (self.log_directory / "analysis").mkdir(exist_ok=True)
        (self.log_directory / "performance").mkdir(exist_ok=True)
        (self.log_directory / "errors").mkdir(exist_ok=True)
        
        # Initialize log files
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trade_log_file = self.log_directory / "trades" / f"trades_{self.session_id}.json"
        self.market_data_file = self.log_directory / "market_data" / f"market_data_{self.session_id}.json"
        self.signal_log_file = self.log_directory / "signals" / f"signals_{self.session_id}.json"
        self.analysis_log_file = self.log_directory / "analysis" / f"analysis_{self.session_id}.json"
        self.performance_file = self.log_directory / "performance" / f"performance_{self.session_id}.json"
        self.error_log_file = self.log_directory / "errors" / f"errors_{self.session_id}.json"
        
        # Initialize data structures
        self.trades = []
        self.market_data_points = []
        self.signals = []
        self.analysis_records = []
        self.performance_metrics = {
            "session_start": time.time(),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_fees": 0.0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "average_profit": 0.0,
            "average_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0
        }
        self.errors = []
        
        # Create session metadata
        self.session_metadata = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "bot_version": "Enhanced BTC 5-Min Strategy v2.0",
            "strategy": "standard",  # Will be updated by strategy manager
            "max_leverage": 40,
            "initial_balance": 0.0,  # Will be updated by bot
            "analysis_frequency": {
                "price_updates": "5 seconds",
                "market_analysis": "10 seconds", 
                "signal_checks": "30 seconds",
                "candle_updates": "5 minutes",
                "hourly_analysis": "1 hour"
            }
        }
        
        # Save session metadata
        self._save_session_metadata()
        
        logger.info(f"📊 Trading Logger initialized: {self.session_id}")
        logger.info(f"   Log directory: {self.log_directory}")
    
    def _save_session_metadata(self):
        """Save session metadata"""
        metadata_file = self.log_directory / f"session_metadata_{self.session_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.session_metadata, f, indent=2)
    
    def update_initial_balance(self, balance: float):
        """Update initial balance in session metadata"""
        if balance is None:
            balance = 0.0
        self.session_metadata["initial_balance"] = balance
        self._save_session_metadata()
        logger.info(f"💰 Updated initial balance: ${balance:.2f}")
    
    def update_strategy(self, strategy: str):
        """Update strategy in session metadata"""
        if strategy:
            self.session_metadata["strategy"] = strategy
            self._save_session_metadata()
            logger.info(f"🎯 Updated strategy: {strategy}")
    
    def update_current_balance(self, balance: float):
        """Update current balance in session metadata for real-time dashboard updates"""
        if balance is None:
            balance = 0.0
        self.session_metadata["current_balance"] = balance
        self.session_metadata["last_balance_update"] = datetime.now().isoformat()
        
        # Calculate P&L from initial balance
        initial_balance = self.session_metadata.get("initial_balance", balance)
        balance_change = balance - initial_balance
        balance_change_pct = (balance_change / initial_balance * 100) if initial_balance > 0 else 0
        
        self.session_metadata["balance_change"] = balance_change
        self.session_metadata["balance_change_pct"] = balance_change_pct
        
        self._save_session_metadata()

    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log a completed trade with comprehensive details"""
        trade_record = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "trade_id": trade_data.get("trade_id", f"trade_{len(self.trades) + 1}"),
            "side": trade_data.get("side"),
            "price": trade_data.get("price"),
            "size": trade_data.get("size"),
            "leverage": trade_data.get("leverage"),
            "order_type": trade_data.get("order_type", "LIMIT"),
            "fees": trade_data.get("fees", {}),
            "signal_data": trade_data.get("signal_data", {}),
            "order_result": trade_data.get("order_result", {}),
            "market_conditions": {
                "current_price": trade_data.get("current_price"),
                "support": trade_data.get("support"),
                "resistance": trade_data.get("resistance"),
                "trend_5m": trade_data.get("trend_5m"),
                "trend_1h": trade_data.get("trend_1h"),
                "variability_score": trade_data.get("variability_score"),
                "market_condition": trade_data.get("market_condition")
            },
            "strategy_info": {
                "signal_reason": trade_data.get("signal_reason"),
                "profit_target": trade_data.get("profit_target"),
                "stop_loss": trade_data.get("stop_loss"),
                "risk_level": trade_data.get("risk_level", "STANDARD")
            }
        }
        
        self.trades.append(trade_record)
        
        # Save to file immediately
        with open(self.trade_log_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
        
        logger.info(f"📝 Trade logged: {trade_record['trade_id']} - {trade_record['side']} {trade_record['size']} @ ${trade_record['price']:,.2f}")
    
    def log_market_data(self, market_data: Dict[str, Any]):
        """Log market data points for analysis"""
        data_point = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "price": market_data.get("price"),
            "volume": market_data.get("volume"),
            "bid": market_data.get("bid"),
            "ask": market_data.get("ask"),
            "spread": market_data.get("spread"),
            "candles_5m": market_data.get("candles_5m", []),
            "candles_1h": market_data.get("candles_1h", []),
            "support_resistance": market_data.get("support_resistance", {}),
            "trend_analysis": market_data.get("trend_analysis", {}),
            "variability_data": market_data.get("variability_data", {})
        }
        
        self.market_data_points.append(data_point)
        
        # Save to file (limit to last 1000 points to prevent huge files)
        if len(self.market_data_points) > 1000:
            self.market_data_points = self.market_data_points[-1000:]
        
        with open(self.market_data_file, 'w') as f:
            json.dump(self.market_data_points, f, indent=2)
    
    def log_signal(self, signal_data: Dict[str, Any]):
        """Log trading signals for analysis"""
        signal_record = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "signal_id": f"signal_{len(self.signals) + 1}",
            "should_trade": signal_data.get("should_trade", False),
            "reason": signal_data.get("reason"),
            "side": signal_data.get("side"),
            "current_price": signal_data.get("current_price"),
            "target_price": signal_data.get("target"),
            "stop_price": signal_data.get("stop"),
            "market_analysis": {
                "support_5m": signal_data.get("support_5m"),
                "resistance_5m": signal_data.get("resistance_5m"),
                "trend_5m": signal_data.get("trend_5m"),
                "trend_1h": signal_data.get("trend_1h"),
                "volatility_5m": signal_data.get("volatility_5m"),
                "market_condition": signal_data.get("market_condition")
            },
            "variability_analysis": {},  # Variability analysis is handled separately
            "profitability_analysis": signal_data.get("profitability", {}),
            "optimal_params": signal_data.get("optimal_params", {})
        }
        
        self.signals.append(signal_record)
        
        # Save to file
        with open(self.signal_log_file, 'w') as f:
            json.dump(self.signals, f, indent=2)
        
        if signal_record["should_trade"]:
            logger.info(f"📊 Signal logged: {signal_record['signal_id']} - {signal_record['side']} {signal_record['reason']}")
    
    def log_analysis(self, analysis_data: Dict[str, Any]):
        """Log detailed analysis for strategy improvement"""
        # Start with timestamp and datetime
        analysis_record = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
        }
        
        # Add all fields from analysis_data, with defaults for core fields
        analysis_record.update({
            "analysis_type": analysis_data.get("type", "general"),
            "timeframe": analysis_data.get("timeframe", "5m"),
            "indicators": analysis_data.get("indicators", {}),
            "patterns": analysis_data.get("patterns", []),
            "support_resistance": analysis_data.get("support_resistance", {}),
            "trend_analysis": analysis_data.get("trend_analysis", {}),
            "volume_analysis": analysis_data.get("volume_analysis", {}),
            "volatility_analysis": analysis_data.get("volatility_analysis", {}),
            "momentum_analysis": analysis_data.get("momentum_analysis", {}),
            "market_condition": analysis_data.get("market_condition", "UNKNOWN"),
            "confidence_score": analysis_data.get("confidence_score", 0.0),
            "recommendations": analysis_data.get("recommendations", [])
        })
        
        # Add any additional fields from analysis_data (like hyperliquid_price)
        for key, value in analysis_data.items():
            if key not in analysis_record and key != "type":  # 'type' is already mapped to 'analysis_type'
                analysis_record[key] = value
        
        self.analysis_records.append(analysis_record)
        
        # Save to file
        with open(self.analysis_log_file, 'w') as f:
            json.dump(self.analysis_records, f, indent=2)
    
    def log_error(self, error_data: Dict[str, Any]):
        """Log errors for debugging and improvement"""
        error_record = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "error_type": error_data.get("type", "unknown"),
            "error_message": error_data.get("message", ""),
            "error_details": error_data.get("details", {}),
            "context": error_data.get("context", {}),
            "stack_trace": error_data.get("stack_trace", ""),
            "recovery_action": error_data.get("recovery_action", "")
        }
        
        self.errors.append(error_record)
        
        # Save to file
        with open(self.error_log_file, 'w') as f:
            json.dump(self.errors, f, indent=2)
        
        logger.error(f"❌ Error logged: {error_record['error_type']} - {error_record['error_message']}")
    
    def update_trade_result(self, trade_id: str, result_data: Dict[str, Any]):
        """Update trade with result data (profit/loss, exit price, etc.)"""
        for trade in self.trades:
            if trade["trade_id"] == trade_id:
                trade.update({
                    "exit_timestamp": time.time(),
                    "exit_datetime": datetime.now().isoformat(),
                    "exit_price": result_data.get("exit_price"),
                    "profit_loss": result_data.get("profit_loss"),
                    "profit_loss_pct": result_data.get("profit_loss_pct"),
                    "fees_paid": result_data.get("fees_paid"),
                    "net_profit_loss": result_data.get("net_profit_loss"),
                    "holding_time": result_data.get("holding_time"),
                    "exit_reason": result_data.get("exit_reason", "manual"),
                    "was_profitable": result_data.get("was_profitable", False)
                })
                break
        
        # Save updated trades
        with open(self.trade_log_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return self.performance_metrics
        
        profitable_trades = [t for t in self.trades if t.get("was_profitable", False)]
        losing_trades = [t for t in self.trades if not t.get("was_profitable", True)]
        
        total_profit = sum(t.get("profit_loss", 0) for t in profitable_trades)
        total_loss = abs(sum(t.get("profit_loss", 0) for t in losing_trades))
        total_fees = sum(t.get("fees_paid", 0) for t in self.trades)
        
        self.performance_metrics.update({
            "session_end": time.time(),
            "session_duration": time.time() - self.performance_metrics["session_start"],
            "total_trades": len(self.trades),
            "winning_trades": len(profitable_trades),
            "losing_trades": len(losing_trades),
            "total_profit": total_profit,
            "total_loss": total_loss,
            "total_fees": total_fees,
            "net_profit": total_profit - total_loss - total_fees,
            "win_rate": len(profitable_trades) / len(self.trades) if self.trades else 0,
            "average_profit": total_profit / len(profitable_trades) if profitable_trades else 0,
            "average_loss": total_loss / len(losing_trades) if losing_trades else 0,
            "largest_win": max((t.get("profit_loss", 0) for t in profitable_trades), default=0),
            "largest_loss": min((t.get("profit_loss", 0) for t in losing_trades), default=0),
            "profit_factor": total_profit / total_loss if total_loss > 0 else float('inf'),
            "average_trade": (total_profit - total_loss) / len(self.trades) if self.trades else 0
        })
        
        # Calculate drawdown
        running_balance = 0
        max_balance = 0
        max_drawdown = 0
        
        for trade in self.trades:
            running_balance += trade.get("net_profit_loss", 0)
            max_balance = max(max_balance, running_balance)
            drawdown = max_balance - running_balance
            max_drawdown = max(max_drawdown, drawdown)
        
        self.performance_metrics["max_drawdown"] = max_drawdown
        
        # Save performance metrics
        with open(self.performance_file, 'w') as f:
            json.dump(self.performance_metrics, f, indent=2)
        
        return self.performance_metrics
    
    def generate_trading_report(self) -> Dict[str, Any]:
        """Generate comprehensive trading report"""
        performance = self.calculate_performance_metrics()
        
        report = {
            "session_info": self.session_metadata,
            "performance_summary": performance,
            "trade_analysis": {
                "total_trades": len(self.trades),
                "win_rate": f"{performance['win_rate']*100:.2f}%",
                "profit_factor": f"{performance['profit_factor']:.2f}",
                "average_trade": f"${performance['average_trade']:.4f}",
                "net_profit": f"${performance['net_profit']:.4f}",
                "total_fees": f"${performance['total_fees']:.4f}",
                "max_drawdown": f"${performance['max_drawdown']:.4f}"
            },
            "signal_analysis": {
                "total_signals": len(self.signals),
                "signals_taken": len([s for s in self.signals if s["should_trade"]]),
                "signal_accuracy": len([s for s in self.signals if s["should_trade"]]) / len(self.signals) if self.signals else 0
            },
            "market_analysis": {
                "data_points": len(self.market_data_points),
                "analysis_records": len(self.analysis_records)
            },
            "error_summary": {
                "total_errors": len(self.errors),
                "error_types": {}
            }
        }
        
        # Count error types
        for error in self.errors:
            error_type = error["error_type"]
            report["error_summary"]["error_types"][error_type] = report["error_summary"]["error_types"].get(error_type, 0) + 1
        
        return report
    
    def export_to_csv(self, export_directory: str = "csv_exports"):
        """Export trading data to CSV files for external analysis"""
        export_dir = Path(export_directory)
        export_dir.mkdir(exist_ok=True)
        
        # Export trades
        if self.trades:
            trades_file = export_dir / f"trades_{self.session_id}.csv"
            with open(trades_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)
        
        # Export signals
        if self.signals:
            signals_file = export_dir / f"signals_{self.session_id}.csv"
            with open(signals_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.signals[0].keys())
                writer.writeheader()
                writer.writerows(self.signals)
        
        # Export performance metrics
        performance = self.calculate_performance_metrics()
        perf_file = export_dir / f"performance_{self.session_id}.csv"
        with open(perf_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            for key, value in performance.items():
                writer.writerow([key, value])
        
        logger.info(f"📊 Data exported to CSV: {export_dir}")
    
    def get_strategy_insights(self) -> Dict[str, Any]:
        """Generate insights for strategy improvement"""
        insights = {
            "best_performing_conditions": {},
            "worst_performing_conditions": {},
            "signal_effectiveness": {},
            "fee_impact": {},
            "timing_analysis": {},
            "recommendations": []
        }
        
        if not self.trades:
            return insights
        
        # Analyze performance by market conditions
        condition_performance = {}
        for trade in self.trades:
            condition = trade.get("market_conditions", {}).get("market_condition", "UNKNOWN")
            if condition not in condition_performance:
                condition_performance[condition] = {"trades": [], "total_pnl": 0}
            
            condition_performance[condition]["trades"].append(trade)
            condition_performance[condition]["total_pnl"] += trade.get("net_profit_loss", 0)
        
        # Find best and worst conditions
        if condition_performance:
            best_condition = max(condition_performance.items(), key=lambda x: x[1]["total_pnl"])
            worst_condition = min(condition_performance.items(), key=lambda x: x[1]["total_pnl"])
            
            insights["best_performing_conditions"] = {
                "condition": best_condition[0],
                "total_pnl": best_condition[1]["total_pnl"],
                "trade_count": len(best_condition[1]["trades"])
            }
            
            insights["worst_performing_conditions"] = {
                "condition": worst_condition[0],
                "total_pnl": worst_condition[1]["total_pnl"],
                "trade_count": len(worst_condition[1]["trades"])
            }
        
        # Analyze signal effectiveness
        signal_reasons = {}
        for signal in self.signals:
            if signal["should_trade"]:
                reason = signal["reason"]
                if reason not in signal_reasons:
                    signal_reasons[reason] = {"count": 0, "successful": 0}
                signal_reasons[reason]["count"] += 1
        
        # Match signals to trade results
        for trade in self.trades:
            signal_reason = trade.get("strategy_info", {}).get("signal_reason")
            if signal_reason in signal_reasons and trade.get("was_profitable"):
                signal_reasons[signal_reason]["successful"] += 1
        
        insights["signal_effectiveness"] = signal_reasons
        
        # Fee impact analysis
        total_fees = sum(t.get("fees_paid", 0) for t in self.trades)
        total_gross_profit = sum(t.get("profit_loss", 0) for t in self.trades)
        fee_impact = (total_fees / total_gross_profit * 100) if total_gross_profit > 0 else 0
        
        insights["fee_impact"] = {
            "total_fees": total_fees,
            "fee_impact_percentage": fee_impact,
            "average_fee_per_trade": total_fees / len(self.trades) if self.trades else 0
        }
        
        # Generate recommendations
        recommendations = []
        
        if fee_impact > 20:
            recommendations.append("Consider reducing trading frequency to minimize fee impact")
        
        if insights["worst_performing_conditions"]["total_pnl"] < -100:
            recommendations.append(f"Avoid trading in {insights['worst_performing_conditions']['condition']} conditions")
        
        if performance := self.calculate_performance_metrics():
            if performance["win_rate"] < 0.4:
                recommendations.append("Consider tightening entry criteria to improve win rate")
            
            if performance["profit_factor"] < 1.2:
                recommendations.append("Review risk-reward ratios to improve profit factor")
        
        insights["recommendations"] = recommendations
        
        return insights

    def cleanup_old_sessions(self, keep_sessions: int = 3):
        """Clean up old sessions, keeping only the specified number of most recent ones"""
        try:
            logger.info(f"🧹 Starting log cleanup - keeping last {keep_sessions} sessions")
            
            # Get all session metadata files
            metadata_files = list(self.log_directory.glob("session_metadata_*.json"))
            
            if len(metadata_files) <= keep_sessions:
                logger.info(f"📁 Only {len(metadata_files)} sessions found, no cleanup needed")
                return
            
            # Sort by modification time (newest first)
            metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep the most recent sessions
            sessions_to_keep = metadata_files[:keep_sessions]
            sessions_to_delete = metadata_files[keep_sessions:]
            
            logger.info(f"📁 Found {len(metadata_files)} total sessions")
            logger.info(f"💾 Keeping {len(sessions_to_keep)} recent sessions")
            logger.info(f"🗑️ Deleting {len(sessions_to_delete)} old sessions")
            
            # Delete old sessions
            for metadata_file in sessions_to_delete:
                session_id = metadata_file.stem.replace("session_metadata_", "")
                logger.info(f"🗑️ Cleaning up session: {session_id}")
                
                # Delete all files for this session
                for subdir in ["trades", "market_data", "signals", "analysis", "performance", "errors"]:
                    subdir_path = self.log_directory / subdir
                    if subdir_path.exists():
                        session_files = list(subdir_path.glob(f"*_{session_id}.*"))
                        for file in session_files:
                            try:
                                file.unlink()
                                logger.debug(f"   Deleted: {file.name}")
                            except Exception as e:
                                logger.warning(f"   Failed to delete {file.name}: {e}")
                
                # Delete the metadata file itself
                try:
                    metadata_file.unlink()
                    logger.debug(f"   Deleted: {metadata_file.name}")
                except Exception as e:
                    logger.warning(f"   Failed to delete {metadata_file.name}: {e}")
            
            logger.info(f"✅ Log cleanup completed - kept {len(sessions_to_keep)} sessions")
            
        except Exception as e:
            logger.error(f"❌ Error during log cleanup: {e}")

def generate_logging_report():
    """Generate a report showing the logging system capabilities"""
    logger.info("📊 Trading Logger System Report")
    logger.info("=" * 50)
    
    # Create a sample logger
    sample_logger = TradingLogger("sample_logs")
    
    logger.info("📁 Log Directory Structure:")
    logger.info(f"   {sample_logger.log_directory}/")
    logger.info("   ├── trades/          # All trade records")
    logger.info("   ├── market_data/     # Market data points")
    logger.info("   ├── signals/         # Trading signals")
    logger.info("   ├── analysis/        # Technical analysis")
    logger.info("   ├── performance/     # Performance metrics")
    logger.info("   ├── errors/          # Error logs")
    logger.info("   └── csv_exports/     # CSV exports")
    logger.info("")
    
    logger.info("📝 What Gets Logged:")
    logger.info("   • Complete trade details (entry/exit, fees, P&L)")
    logger.info("   • Market data (price, volume, support/resistance)")
    logger.info("   • Trading signals (decisions, reasons)")
    logger.info("   • Technical analysis (indicators, patterns)")
    logger.info("   • Performance metrics (win rate, profit factor)")
    logger.info("   • Error tracking (for debugging)")
    logger.info("")
    
    logger.info("📊 Analysis Capabilities:")
    logger.info("   • Performance by market conditions")
    logger.info("   • Signal effectiveness analysis")
    logger.info("   • Fee impact assessment")
    logger.info("   • Strategy improvement recommendations")
    logger.info("   • CSV export for external analysis")
    logger.info("")
    
    logger.info("🎯 Benefits:")
    logger.info("   • Track strategy performance over time")
    logger.info("   • Identify best/worst market conditions")
    logger.info("   • Optimize entry/exit criteria")
    logger.info("   • Reduce fees and improve profitability")
    logger.info("   • Debug issues and improve reliability")
    logger.info("")
    
    logger.info("=" * 50)
    logger.info("📊 Ready for comprehensive trading analysis!")

if __name__ == "__main__":
    generate_logging_report()
