#!/usr/bin/env python3
"""
Fee Manager for Trading Bot
Handles fee calculations and profitability analysis
"""

import time
from typing import Dict, Any
from loguru import logger

# Import core module to setup paths
import core

from config.config import TradingConfig

class FeeManager:
    def __init__(self):
        self.config = TradingConfig()
        self.api = None
        
        # Hyperliquid Fee Structure (as of 2024)
        self.fee_rates = {
            "maker": 0.0001,  # 0.01% for maker orders (limit orders that add liquidity)
            "taker": 0.0002,  # 0.02% for taker orders (market orders that remove liquidity)
            "funding_rate": 0.0001,  # 0.01% per 8-hour funding period
            "liquidation_fee": 0.0005,  # 0.05% liquidation fee
            "minimum_fee": 0.000001  # Minimum fee in USD
        }
        
        # Slippage estimates
        self.slippage_rates = {
            "small_order": 0.0001,  # 0.01% for orders < $100
            "medium_order": 0.0002,  # 0.02% for orders $100-$1000
            "large_order": 0.0005,   # 0.05% for orders > $1000
        }
        
        # Track cumulative fees
        self.total_fees_paid = 0.0
        self.total_trades = 0
        self.fee_history = []
        
    def connect(self) -> bool:
        """Connect to Hyperliquid API"""
        try:
            self.api = core.HyperliquidAPI(self.config.WALLET_ADDRESS, self.config.WALLET_PRIVATE_KEY)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect for fee management: {e}")
            return False
    
    def calculate_order_fees(self, order_size: float, order_price: float, order_type: str = "LIMIT") -> Dict[str, float]:
        """
        Calculate fees for a specific order
        
        Args:
            order_size: Size of the order in BTC
            order_price: Price per BTC
            order_type: "LIMIT" (maker) or "MARKET" (taker)
        
        Returns:
            Dictionary with fee breakdown
        """
        order_value = order_size * order_price
        
        # Determine fee rate based on order type
        if order_type.upper() == "LIMIT":
            fee_rate = self.fee_rates["maker"]
            fee_type = "maker"
        else:  # MARKET
            fee_rate = self.fee_rates["taker"]
            fee_type = "taker"
        
        # Calculate base fee
        base_fee = order_value * fee_rate
        
        # Apply minimum fee
        if base_fee < self.fee_rates["minimum_fee"]:
            base_fee = self.fee_rates["minimum_fee"]
        
        # Estimate slippage
        slippage_rate = self._estimate_slippage(order_value)
        slippage_cost = order_value * slippage_rate
        
        # Total cost
        total_cost = base_fee + slippage_cost
        
        return {
            "order_value": order_value,
            "fee_type": fee_type,
            "fee_rate": fee_rate,
            "base_fee": base_fee,
            "slippage_rate": slippage_rate,
            "slippage_cost": slippage_cost,
            "total_cost": total_cost,
            "cost_percentage": (total_cost / order_value) * 100
        }
    
    def _estimate_slippage(self, order_value: float) -> float:
        """Estimate slippage based on order size"""
        if order_value < 100:
            return self.slippage_rates["small_order"]
        elif order_value < 1000:
            return self.slippage_rates["medium_order"]
        else:
            return self.slippage_rates["large_order"]
    
    def calculate_leverage_costs(self, position_size: float, leverage: int, holding_hours: float = 1.0) -> Dict[str, float]:
        """
        Calculate costs associated with leveraged positions
        
        Args:
            position_size: Size of position in BTC
            leverage: Leverage used (e.g., 30x)
            holding_hours: Expected holding time in hours
        
        Returns:
            Dictionary with leverage cost breakdown
        """
        # Funding rate costs (paid every 8 hours)
        funding_periods = holding_hours / 8.0
        funding_cost = position_size * self.fee_rates["funding_rate"] * funding_periods
        
        # Liquidation risk cost (estimated)
        liquidation_risk = position_size * self.fee_rates["liquidation_fee"] * 0.01  # 1% chance
        
        # Opportunity cost (capital tied up)
        opportunity_cost = position_size * 0.0001 * holding_hours  # 0.01% per hour
        
        total_leverage_cost = funding_cost + liquidation_risk + opportunity_cost
        
        return {
            "position_size": position_size,
            "leverage": leverage,
            "holding_hours": holding_hours,
            "funding_cost": funding_cost,
            "liquidation_risk": liquidation_risk,
            "opportunity_cost": opportunity_cost,
            "total_leverage_cost": total_leverage_cost,
            "cost_percentage": (total_leverage_cost / position_size) * 100
        }
    
    def calculate_profit_after_fees(self, entry_price: float, exit_price: float, 
                                  position_size: float, leverage: int = 30, side: str = "BUY") -> Dict[str, float]:
        """
        Calculate actual profit after all fees and costs
        
        Args:
            entry_price: Entry price per BTC
            exit_price: Exit price per BTC
            position_size: Size of position in BTC
            leverage: Leverage used
            side: "BUY" or "SELL" to determine profit calculation direction
        
        Returns:
            Dictionary with profit breakdown
        """
        # Calculate raw profit/loss based on trade side
        if side == "BUY":
            # For BUY: profit when exit_price > entry_price
            price_change = exit_price - entry_price
        else:  # SELL
            # For SELL: profit when entry_price > exit_price (price goes down)
            price_change = entry_price - exit_price
            
        raw_pnl = price_change * position_size * leverage
        
        # Calculate fees for entry and exit
        entry_fees = self.calculate_order_fees(position_size, entry_price, "LIMIT")
        exit_fees = self.calculate_order_fees(position_size, exit_price, "LIMIT")
        
        # Calculate leverage costs (assuming 5-minute holding time)
        leverage_costs = self.calculate_leverage_costs(position_size, leverage, 5/60)  # 5 minutes
        
        # Total costs
        total_costs = entry_fees["total_cost"] + exit_fees["total_cost"] + leverage_costs["total_leverage_cost"]
        
        # Net profit/loss
        net_pnl = raw_pnl - total_costs
        
        # Calculate break-even price
        break_even_price = entry_price + (total_costs / (position_size * leverage))
        
        return {
            "raw_pnl": raw_pnl,
            "entry_fees": entry_fees["total_cost"],
            "exit_fees": exit_fees["total_cost"],
            "leverage_costs": leverage_costs["total_leverage_cost"],
            "total_costs": total_costs,
            "net_pnl": net_pnl,
            "break_even_price": break_even_price,
            "profit_margin": (net_pnl / raw_pnl * 100) if raw_pnl != 0 else 0
        }
    
    def is_trade_profitable(self, entry_price: float, target_price: float, 
                           position_size: float, leverage: int = 30, side: str = "BUY") -> Dict[str, Any]:
        """
        Determine if a trade is profitable after fees
        
        Args:
            entry_price: Entry price
            target_price: Target exit price
            position_size: Position size
            leverage: Leverage used
            side: "BUY" or "SELL" to determine profit calculation direction
        
        Returns:
            Dictionary with profitability analysis
        """
        profit_analysis = self.calculate_profit_after_fees(entry_price, target_price, position_size, leverage, side)
        
        is_profitable = profit_analysis["net_pnl"] > 0
        min_profit_margin = 0.1  # 0.1% minimum profit margin
        
        return {
            "is_profitable": is_profitable,
            "net_pnl": profit_analysis["net_pnl"],
            "profit_margin": profit_analysis["profit_margin"],
            "meets_minimum_margin": profit_analysis["profit_margin"] >= min_profit_margin,
            "break_even_price": profit_analysis["break_even_price"],
            "recommended_target": entry_price * (1 + (profit_analysis["total_costs"] / (position_size * leverage * entry_price) + 0.001))
        }
    
    def record_trade_fees(self, trade_data: Dict[str, Any]):
        """Record fees for a completed trade"""
        try:
            fees = trade_data.get("fees", {})
            self.total_fees_paid += fees.get("total_cost", 0)
            self.total_trades += 1
            
            fee_record = {
                "timestamp": time.time(),
                "trade_id": trade_data.get("trade_id", f"trade_{self.total_trades}"),
                "fees": fees,
                "cumulative_fees": self.total_fees_paid
            }
            
            self.fee_history.append(fee_record)
            
            logger.info(f"💰 Trade fees recorded: ${fees.get('total_cost', 0):.4f}")
            logger.info(f"📊 Total fees paid: ${self.total_fees_paid:.4f} ({self.total_trades} trades)")
            
        except Exception as e:
            logger.error(f"❌ Failed to record trade fees: {e}")
    
    def get_fee_summary(self) -> Dict[str, Any]:
        """Get summary of all fees paid"""
        if self.total_trades == 0:
            return {
                "total_fees": 0,
                "total_trades": 0,
                "average_fee_per_trade": 0,
                "fee_history": []
            }
        
        return {
            "total_fees": self.total_fees_paid,
            "total_trades": self.total_trades,
            "average_fee_per_trade": self.total_fees_paid / self.total_trades,
            "fee_history": self.fee_history[-10:]  # Last 10 trades
        }
    
    # REMOVED: optimize_position_size method - use hybrid_position_sizer instead
    
    def get_fee_breakdown_for_strategy(self, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get fee breakdown for a specific trading strategy
        
        Args:
            strategy_params: Dictionary with strategy parameters
        
        Returns:
            Dictionary with fee analysis
        """
        position_size = strategy_params.get("position_size", 0.001)
        leverage = strategy_params.get("leverage", 30)
        trades_per_day = strategy_params.get("trades_per_day", 10)
        avg_holding_time = strategy_params.get("avg_holding_time_hours", 5/60)  # 5 minutes
        
        # Daily fee calculations
        daily_trading_fees = trades_per_day * 2 * position_size * 50000 * self.fee_rates["maker"]  # Entry + exit
        daily_leverage_costs = trades_per_day * self.calculate_leverage_costs(position_size, leverage, avg_holding_time)["total_leverage_cost"]
        
        total_daily_costs = daily_trading_fees + daily_leverage_costs
        
        return {
            "position_size": position_size,
            "leverage": leverage,
            "trades_per_day": trades_per_day,
            "daily_trading_fees": daily_trading_fees,
            "daily_leverage_costs": daily_leverage_costs,
            "total_daily_costs": total_daily_costs,
            "monthly_costs": total_daily_costs * 30,
            "break_even_daily_profit": total_daily_costs,
            "recommended_min_daily_profit": total_daily_costs * 1.5  # 50% buffer
        }

def main():
    """Test fee management system"""
    logger.info("💰 Testing Fee Management System")
    
    fee_manager = FeeManager()
    
    # Test basic fee calculation
    fees = fee_manager.calculate_order_fees(0.001, 50000, "LIMIT")
    logger.info(f"📊 Order fees: {fees}")
    
    # Test leverage costs
    leverage_costs = fee_manager.calculate_leverage_costs(0.001, 30, 5/60)
    logger.info(f"📊 Leverage costs: {leverage_costs}")
    
    # Test profitability analysis
    profit_analysis = fee_manager.is_trade_profitable(50000, 50100, 0.001, 30)
    logger.info(f"📊 Profitability: {profit_analysis}")
    
    # Test strategy fee breakdown
    strategy_params = {
        "position_size": 0.001,
        "leverage": 30,
        "trades_per_day": 10,
        "avg_holding_time_hours": 5/60
    }
    
    strategy_fees = fee_manager.get_fee_breakdown_for_strategy(strategy_params)
    logger.info(f"📊 Strategy fees: {strategy_fees}")

if __name__ == "__main__":
    main()
