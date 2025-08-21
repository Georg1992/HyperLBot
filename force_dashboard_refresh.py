#!/usr/bin/env python3
"""
Force dashboard to show current RSI and Volume data by bypassing cache issues
"""
import requests
import json

def force_refresh_test():
    try:
        response = requests.get('http://localhost:5001/api/data', timeout=5)
        if response.status_code == 200:
            data = response.json()
            market = data.get('market', {})
            
            print('🔍 FORCING RSI/VOLUME DISPLAY TEST:')
            print(f'✅ API Status: {response.status_code}')
            print()
            
            # Extract the exact values
            rsi_raw = market.get('rsi')
            volume_raw = market.get('volume_depth')
            imbalance_raw = market.get('orderbook_imbalance')
            
            print('📊 Raw Values from API:')
            print(f'   RSI: {rsi_raw}')
            print(f'   Volume: {volume_raw}') 
            print(f'   Imbalance: {imbalance_raw}')
            print()
            
            # Test JavaScript evaluation
            print('🔧 JavaScript-style Evaluation:')
            rsi_js = f'{rsi_raw:.1f}' if rsi_raw else 'N/A'
            volume_js = f'{volume_raw:.1f}' if volume_raw else 'N/A'
            flow_js = f'{imbalance_raw*100:+.1f}' if imbalance_raw else 'N/A'
            
            print(f'   RSI Display: {rsi_js}')
            print(f'   Volume Display: {volume_js} BTC')
            print(f'   Flow Display: {flow_js}%')
            
            if rsi_js != 'N/A' and volume_js != 'N/A':
                print('\\n✅ SHOULD WORK: Values evaluate correctly')
                print('   Problem is likely browser cache or template generation')
                print('\\n🔧 Solutions:')
                print('   1. HARD REFRESH: Ctrl+F5 or Cmd+Shift+R')
                print('   2. CLEAR CACHE: F12 → Application → Storage → Clear All')
                print('   3. INCOGNITO: New private window → http://localhost:5001')
                print('   4. FORCE BUST: http://localhost:5001/?cache_bust=12345')
            else:
                print('\\n❌ VALUES ARE EVALUATING TO N/A')
                print('   Need to check why truthiness test fails')
                
        else:
            print(f'❌ API Error: {response.status_code}')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    force_refresh_test()