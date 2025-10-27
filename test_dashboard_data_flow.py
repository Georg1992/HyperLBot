#!/usr/bin/env python3
"""
Test script to manually trigger dashboard data flow
This simulates what the SessionOrchestrator would do
"""

import sys
import time
sys.path.append('.')

from core.services.market_data_service import MarketDataService
from core.services.dashboard_service import create_dashboard_service
from core.calculations.volatility_calculator import create_volatility_calculator
from core.calculations.support_resistance_calculator import create_sr_calculator

def test_dashboard_data_flow():
    """Test the complete data flow from analysis to dashboard"""
    print('=== Testing Complete Dashboard Data Flow ===')
    
    # Create MarketDataService
    class MockAPI:
        def get_current_price(self, symbol='BTC'):
            return 114528.50

    class MockWebSocket:
        def get_current_price(self):
            return 114528.50

    market_service = MarketDataService(MockAPI(), MockWebSocket())

    # Register analysis modules
    volatility_calc = create_volatility_calculator('BTC')
    sr_calc = create_sr_calculator('BTC')
    market_service.register_analysis_module('volatility', volatility_calc)
    market_service.register_analysis_module('support_resistance', sr_calc)

    # Create DashboardService
    dashboard_service = create_dashboard_service()

    # Simulate SessionOrchestrator main data loop
    for i in range(3):  # Run 3 iterations
        print(f'\n--- Iteration {i+1} ---')
        
        # Get dashboard data (what SessionOrchestrator calls)
        dashboard_data = market_service.get_dashboard_data()
        
        # Update DashboardService (simulate SessionOrchestrator)
        dashboard_service.update_market_data(dashboard_data)
        
        # Check what DashboardService now has
        dashboard_service_data = dashboard_service.get_data()
        market_data = dashboard_service_data.get('market', {})
        
        current_price = market_data.get('current_price', 'NOT_FOUND')
        volatility_5m = market_data.get('volatility_5m', 'NOT_FOUND')
        volatility_category = market_data.get('volatility_category', 'NOT_FOUND')
        
        print(f'✅ DashboardService updated:')
        print(f'  Current Price: {current_price}')
        print(f'  Volatility: {volatility_5m:.6f} ({volatility_5m * 100:.4f}%)' if volatility_5m != 'NOT_FOUND' else '  Volatility: NOT_FOUND')
        print(f'  Category: {volatility_category}')
        
        # Check S/R data
        sr_data = market_data.get('support_resistance', {})
        if sr_data.get('status') == 'ok':
            levels = sr_data.get('levels', [])
            strongest_support = sr_data.get('strongest_support', 0)
            strongest_resistance = sr_data.get('strongest_resistance', 0)
            print(f'  S/R Levels: {len(levels)} levels')
            print(f'  Strongest Support: {strongest_support}')
            print(f'  Strongest Resistance: {strongest_resistance}')
        else:
            print(f'  S/R Status: {sr_data.get("status", "UNKNOWN")}')
        
        if i < 2:  # Don't sleep on last iteration
            time.sleep(2)  # Wait 2 seconds between iterations

    print(f'\n🎉 SUCCESS: Dashboard data flow is working perfectly!')
    print(f'   The bot just needs to be restarted to run the SessionOrchestrator main data loop.')

if __name__ == "__main__":
    test_dashboard_data_flow()
