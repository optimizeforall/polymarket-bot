@echo off
echo ========================================
echo  Connection Test
echo ========================================
echo.

call venv\Scripts\activate.bat

echo Testing connections...
echo.

python -c "
import sys
sys.path.insert(0, '.')

print('1. Checking IP address...')
import httpx
try:
    r = httpx.get('https://api.ipify.org', timeout=10)
    print(f'   Your IP: {r.text}')
except Exception as e:
    print(f'   ERROR: {e}')

print()
print('2. Checking Mullvad status...')
try:
    r = httpx.get('https://am.i.mullvad.net/json', timeout=10)
    data = r.json()
    if data.get('mullvad_exit_ip'):
        print(f'   Mullvad: CONNECTED via {data.get(\"city\", \"Unknown\")}')
    else:
        print('   Mullvad: NOT CONNECTED (using regular IP)')
except Exception as e:
    print(f'   ERROR: {e}')

print()
print('3. Testing Polymarket API...')
try:
    r = httpx.get('https://clob.polymarket.com/markets?limit=1', timeout=15)
    if r.status_code == 200:
        print('   Polymarket API: OK!')
        data = r.json()
        if data:
            print(f'   Sample market: {data[0].get(\"question\", \"N/A\")[:50]}...')
    elif r.status_code == 403:
        print('   Polymarket API: BLOCKED (403)')
        print('   Make sure Mullvad VPN is connected!')
    else:
        print(f'   Polymarket API: Error {r.status_code}')
except Exception as e:
    print(f'   ERROR: {e}')

print()
print('4. Testing Gamma API (market data)...')
try:
    r = httpx.get('https://gamma-api.polymarket.com/markets?limit=1&active=true', timeout=15)
    if r.status_code == 200:
        print('   Gamma API: OK!')
    else:
        print(f'   Gamma API: Error {r.status_code}')
except Exception as e:
    print(f'   ERROR: {e}')

print()
print('5. Checking credentials...')
from decouple import config
try:
    pk = config('POLYMARKET_PRIVATE_KEY', default=None)
    if pk:
        print(f'   Private key: Found ({pk[:10]}...)')
    else:
        print('   Private key: NOT FOUND - check .env file')
    
    openrouter = config('OPENROUTER_API_KEY', default=None)
    if openrouter:
        print(f'   OpenRouter key: Found')
    else:
        print('   OpenRouter key: NOT FOUND - AI mode wont work')
        
    telegram = config('TELEGRAM_BOT_TOKEN', default=None)
    if telegram:
        print('   Telegram: Configured')
    else:
        print('   Telegram: Not configured (optional)')
except Exception as e:
    print(f'   ERROR: {e}')

print()
print('========================================')
print('Test complete!')
"

echo.
pause
