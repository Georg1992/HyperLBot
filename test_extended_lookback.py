import sys
sys.path.append('.')

from core.services.market_data_service import MarketDataService
from core.calculations.support_resistance_calculator import create_sr_calculator

print('=== Testing Extended Lookback for Resistance Detection ===')

# Create MarketDataService with current price
class MockAPI:
    def get_current_price(self, symbol='BTC'):
        return 114817.5  # Current price from dashboard

class MockWebSocket:
    def get_current_price(self):
        return 114817.5

market_service = MarketDataService(MockAPI(), MockWebSocket())

# Register S/R calculator
sr_calc = create_sr_calculator('BTC')
market_service.register_analysis_module('support_resistance', sr_calc)

# Get S/R analysis
sr_data = market_service.get_support_resistance_analysis()
print(f'S/R Status: {sr_data.get("status", "ERROR")}')

if sr_data.get('status') == 'ok':
    current_price = sr_data.get('current_price', 114817.5)
    print(f'Current Price: ${current_price:,.2f}')
    
    levels = sr_data.get('levels', [])
    print(f'Total Levels Found: {len(levels)}')
    
    # Check resistance levels specifically
    resistance_levels = [level for level in levels if level.get('price_level', 0) > current_price]
    support_levels = [level for level in levels if level.get('price_level', 0) < current_price]
    
    print(f'\n=== RESISTANCE LEVELS (Above ${current_price:,.2f}) ===')
    print(f'Found {len(resistance_levels)} resistance levels')
    
    if resistance_levels:
        for i, level in enumerate(resistance_levels, 1):
            price = level.get('price_level', 0)
            score = level.get('strength_score', 0)
            touches = level.get('touches', 0)
            mtf_count = level.get('mtf_count', 0)
            distance_pct = ((price - current_price) / current_price) * 100
            
            print(f'{i}. ${price:,.0f} | Score: {score:.1f} | Touches: {touches}x | MTF: {mtf_count} | Distance: {distance_pct:+.1f}%')
    else:
        print('STILL NO RESISTANCE LEVELS FOUND!')
        print('This means we need even more historical data or different detection logic')
    
    print(f'\n=== SUPPORT LEVELS (Below ${current_price:,.2f}) ===')
    print(f'Found {len(support_levels)} support levels')
    
    # Check strongest levels
    strongest_support = sr_data.get('strongest_support', 0)
    strongest_resistance = sr_data.get('strongest_resistance', 0)
    support_score = sr_data.get('support_score', 0)
    resistance_score = sr_data.get('resistance_score', 0)
    
    print(f'\n=== STRONGEST LEVELS ===')
    print(f'Strongest Support: ${strongest_support:,.0f} (Score: {support_score:.1f})')
    print(f'Strongest Resistance: ${strongest_resistance:,.0f} (Score: {resistance_score:.1f})')
    
    if strongest_resistance > 0:
        print('SUCCESS: Resistance level detected!')
    else:
        print('FAILURE: Still no resistance level detected')
    
else:
    print(f'S/R Error: {sr_data}')
