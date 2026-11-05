import urllib.request, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Authenticate
payload = json.dumps({'username': 'completion_qa', 'password': 'AlphaLens@Research2026!'}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:8041/api/v1/auth/login',
    data=payload,
    headers={'Content-Type': 'application/json', 'X-AlphaLens-Local': 'p21', 'Origin': 'http://127.0.0.1:8041'},
    method='POST'
)
with opener.open(req) as resp:
    print('1. Auth status:', resp.status)

# 2. Saved market
req = urllib.request.Request('http://127.0.0.1:8041/api/v1/nse-market/saved-market?limit=5', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    rows = data['data']['rows']
    print('2. Saved market:')
    print(f"   Total securities: {data['data']['total']}")
    print(f"   Latest observed session: {data['data']['latest_observed_session']}")
    for r in rows[:5]:
        print(f"   - {r['symbol']}: Close INR {r['close']}, Change: {r.get('change_percent')}% (Session: {r['session']})")

# 3. Stock research
first_key = rows[0]['key']
req = urllib.request.Request(f'http://127.0.0.1:8041/api/v1/nse-market/stock-research?key={first_key}', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    sdata = json.loads(resp.read().decode())
    identity = sdata.get('data', {}).get('identity', {})
    history = sdata.get('data', {}).get('history', [])
    print(f"3. Stock research for {first_key}:")
    print(f"   Symbol: {identity.get('symbol')}, Name: {identity.get('name')}")
    print(f"   History candle bars: {len(history)}")
    if history:
        print(f"   Latest candle session: {history[-1].get('session')}, Close: INR {history[-1].get('close')}")

# 4. Economic research
req = urllib.request.Request('http://127.0.0.1:8041/api/v1/nse-market/economic-research', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    edata = json.loads(resp.read().decode())
    print('4. Economic research state:', edata.get('data', {}).get('state', 'AVAILABLE'))
    print(f"   Historical profiles count: {len(edata.get('data', {}).get('profiles', []))}")
