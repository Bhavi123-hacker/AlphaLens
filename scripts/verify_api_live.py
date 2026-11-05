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

# 4. Technical Analysis Engine Live Check
req = urllib.request.Request(f'http://127.0.0.1:8041/api/v1/nse-market/technical-analysis?key={first_key}', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    tdata = json.loads(resp.read().decode())
    td = tdata.get('data', {})
    scores = td.get('scores', {})
    plan = td.get('trade_plan', {})
    patterns = td.get('recent_patterns', [])
    print(f"4. Technical Intelligence for {first_key} ({td.get('symbol')}):")
    print(f"   Composite Score: {scores.get('composite_technical_intelligence_score')}/100")
    print(f"   Trend Score: {scores.get('trend_score')}, Momentum: {scores.get('momentum_score')}, Volume: {scores.get('volume_score')}")
    print(f"   Trade Plan: Ref INR {plan.get('reference_price')}, Stop INR {plan.get('stop_loss')}, Target1 INR {plan.get('target_1')}, R/R {plan.get('risk_reward_ratio')}")
    print(f"   Recent Patterns Detected ({len(patterns)}): {[p.get('pattern_name') for p in patterns]}")

# 5. Candidate Rankings with Technical Intelligence
req = urllib.request.Request('http://127.0.0.1:8041/api/v1/nse-market/research?page=1&page_size=5', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    rdata = json.loads(resp.read().decode())
    candidates = rdata.get('data', {}).get('candidates', [])
    print(f"5. Candidate Rankings ({len(candidates)} candidates):")
    for c in candidates[:3]:
        tech = c.get('technical_intelligence', {})
        print(f"   - {c.get('symbol')} ({c.get('key')}): Model Score {c.get('score'):.4f} | Tech Trend: {tech.get('trend_score')} | Align: {tech.get('trend_alignment')} | R/R: {tech.get('risk_reward_ratio')}")

# 6. Economic research
req = urllib.request.Request('http://127.0.0.1:8041/api/v1/nse-market/economic-research', headers={'Origin': 'http://127.0.0.1:8041'})
with opener.open(req) as resp:
    edata = json.loads(resp.read().decode())
    print('6. Economic research state:', edata.get('data', {}).get('state', 'AVAILABLE'))
    print(f"   Historical profiles count: {len(edata.get('data', {}).get('profiles', []))}")
