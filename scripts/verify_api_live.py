"""Verify live API endpoints on localhost:8041."""

import json
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root / "apps" / "api" / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "apps" / "api" / "src"))

from alphalens_api.auth.secret_vault import get_operator_password

password = get_operator_password()
if not password:
    raise RuntimeError("OPERATOR_CREDENTIAL_NOT_CONFIGURED: Set ALPHALENS_QA_PASSWORD or initialize DPAPI protected vault.")

# 1. Login with local headers
login_data = json.dumps({"username": "completion_qa", "password": password}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8041/api/v1/auth/login",
    data=login_data,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://127.0.0.1:8041",
        "x-alphalens-local": "p21",
    }
)

with opener.open(req) as resp:
    body = json.loads(resp.read().decode())
    print(f"1. Auth login status: {resp.status} | User: {body.get('username')} | Account ID: {body.get('account_id')}")

# 2. Universe Screener
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/universe?page=1&page_size=5", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    rows = data.get("data", {}).get("rows", [])
    total = data.get("data", {}).get("total", 0)
    print(f"2. Universe Screener: Total instruments: {total}, Showing: {len(rows)}")

# 3. Status endpoint
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/status", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    print("3. Status endpoint: State:", data.get("data", {}).get("state"), "| Provider requests:", data.get("data", {}).get("provider_requests"))

# 4. Prospective evaluation endpoint
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/prospective-evaluation", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    print("4. Prospective evaluation: State:", data.get("data", {}).get("state", "AVAILABLE"))

# 5. Technical analysis endpoint (RELIANCE)
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/technical-analysis?key=NSE_EQ|INE002A01018", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    ti = data.get("data", {})
    scores = ti.get("scores", {})
    plan = ti.get("trade_plan", {})
    patterns = ti.get("patterns", [])
    print(f"5. Technical Intelligence for RELIANCE (INE002A01018):")
    print(f"   Composite Score: {scores.get('composite_technical_intelligence_score')}/100")
    print(f"   Trend Score: {scores.get('trend_score')}, Momentum: {scores.get('momentum_score')}, Volume: {scores.get('volume_score')}")
    print(f"   Trade Plan: Ref INR {plan.get('reference_price')}, Stop INR {plan.get('stop_loss')}, Target1 INR {plan.get('target_1')}, R/R: {plan.get('risk_reward_ratio')}")

# 6. Candidate research endpoint with enriched technical intelligence
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/research?page=1&page_size=5", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    candidates = data.get("data", {}).get("candidates", [])
    print(f"6. Candidates ({len(candidates)} on page 1):")
    for c in candidates[:3]:
        t = c.get("technical_intelligence", {})
        print(f"   - {c.get('symbol')} ({c.get('key')}): ML Model: {c.get('score'):.4f} | Tech: {t.get('composite_score')} | Align: {t.get('trend_alignment')} | R/R: {t.get('risk_reward_ratio')}")

# 7. Stock research details (/stock-research)
req = urllib.request.Request("http://127.0.0.1:8041/api/v1/nse-market/stock-research?key=NSE_EQ|INE002A01018&limit=50", headers={"Origin": "http://127.0.0.1:8041"})
with opener.open(req) as resp:
    data = json.loads(resp.read().decode())
    s_data = data.get("data", {})
    symbol = s_data.get("symbol")
    bars = s_data.get("bars", [])
    scores = s_data.get("scores", [])
    print(f"7. Stock research for {symbol} (INE002A01018):")
    print(f"   Historical bars returned: {len(bars)}")
    print(f"   Saved scores returned: {len(scores)}")

print("\n>>> ALL DASHBOARD APIS RESPONDING HTTP 200 SUCCESS <<<")
