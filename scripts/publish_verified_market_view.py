"""Publish verified 2026-11-04 market view to update market-view-latest.json pointer."""

import sys
import time
from datetime import UTC, datetime, date
from pathlib import Path

worktree = Path("D:/al-research/p28-worktree/.campaign-worktree")
for p in [".", "apps/api/src", "ml/data/src", "ml/features/src", "ml/labels/src", "ml/training/src", "ml/evaluation/src", "backtesting/src", "decision/src", "portfolio/src"]:
    sys.path.insert(0, str((worktree / p).resolve()))

from workers.nse_market import engine, saved_market
from workers.experimental_nse.acquire import digest, encoded, private_path
from workers.experimental_nse_v2 import data as v2_data
from workers.providers.upstox import Reply

root = Path("D:/al-research/p28-worktree/.local-data/nse-market-expansion")

print("Building verified market frame...", flush=True)
t0 = time.time()
plan = engine._pointed(root, "plan-latest.json")
seed = engine._read(engine.private_path(root, "seed.json"))

identities = [engine._identity(value) for value in plan["identities"]]
keys = {i.provider_key for i in identities}
latest_identities = {item.provider_key: item.model_dump(mode="json") for item in identities}
rows = [row for row in seed["rows"] if row["key"] in keys]
seed_keys = {row["key"] for row in rows}
actions = {key: value for key, value in seed["actions"].items() if key in keys}

states = []
for identity in identities:
    if identity.provider_key in seed_keys:
        states.append({"key": identity.provider_key, "state": "ORIGINAL_V2_OBSERVATIONS_REUSED"})
        continue
    folder = engine._folder(root, identity)
    if not (folder / "response.json").exists():
        continue
    observed = engine._rows(folder, identity)
    rows.extend(observed)
    if (folder / "actions.json").exists():
        actions[identity.provider_key] = engine._read(folder / "actions.json")

daily_dir = engine.private_path(root, "daily")
by_slot = {(row["key"], row["session"]): row for row in rows}
paths = sorted(daily_dir.glob("*/INE*/record.json"))
print(f"Loading {len(paths)} daily items...", flush=True)
for path in paths:
    record = engine._read(path)
    identity = engine._identity(record["identity"])
    if identity.provider_key not in keys:
        continue
    latest_identities[identity.provider_key] = identity.model_dump(mode="json")
    observed = engine._rows(path.parent, identity)
    actions[identity.provider_key] = engine._read(path.parent / "actions.json")
    for row in observed:
        slot = row["key"], row["session"]
        by_slot.setdefault(slot, row)

rows = list(by_slot.values())
rows.sort(key=lambda row: (row["key"], row["session"]))

seed_days = {row["session"] for row in seed["rows"]}
calendar_states: dict[str, str] = {}
for day in sorted({row["session"] for row in rows} - seed_days):
    calendar_path = engine.private_path(root, "calendar", day + ".json")
    if not calendar_path.exists():
        calendar_states[day] = "OFFICIAL_SESSION_EVIDENCE_PENDING"
        continue
    calendar = engine._read(calendar_path)
    raw = bytes.fromhex(calendar["raw_hex"])
    fact = v2_data.timing_fact(
        Reply(200, raw, datetime.fromisoformat(calendar["received_at"]), "ACCEPTED"),
        date.fromisoformat(day),
    )
    calendar_states[day] = (
        "OFFICIAL_TRADING_SESSION" if fact is not None else "OFFICIAL_NON_TRADING_SESSION"
    )

reported_observations = len(rows)
quarantined = [
    {
        "key": row["key"],
        "symbol": row["symbol"],
        "session": row["session"],
        "reason": calendar_states[row["session"]],
    }
    for row in rows
    if row["session"] in calendar_states
    and calendar_states[row["session"]] != "OFFICIAL_TRADING_SESSION"
]
rows = [
    row
    for row in rows
    if row["session"] not in calendar_states
    or calendar_states[row["session"]] == "OFFICIAL_TRADING_SESSION"
]

latest_day = max(row["session"] for row in rows)
latest_timing = seed.get("session_timing")
next_timing = seed.get("next_session_timing")
session_path = engine.private_path(root, "session-links", latest_day + ".json")
if session_path.exists():
    link = engine._read(session_path)
    latest_timing, next_timing = link["session_timing"], link["next_session_timing"]

quality_res = v2_data.quality(rows, actions)
frame = {
    "family": engine.FAMILY,
    "plan_id": plan["plan_id"],
    "rows": rows,
    "identities": [latest_identities[item.provider_key] for item in identities],
    "actions": actions,
    "sessions": sorted({row["session"] for row in rows}),
    "states": states,
    "quality": quality_res,
    "price_basis": seed["price_basis"],
    "source_observed_at": max(row["received_at"] for row in rows),
    "session_timing": latest_timing,
    "next_session_timing": next_timing,
}
frame["quality"].update(
    provider_reported_observations=reported_observations,
    calendar_quarantined_observations=quarantined,
    additional_dated_calendar_states=calendar_states,
)
enc = encoded(frame)
frame["dataset_id"] = digest(enc)
print(f"Frame constructed ({time.time() - t0:.2f}s). Dataset ID: {frame['dataset_id']}, max session: {latest_day}", flush=True)

print("Publishing to market-view-latest.json...", flush=True)
t1 = time.time()
pub_res = saved_market.publish(root, frame, at=datetime.now(UTC))
print(f"Published ({time.time() - t1:.2f}s): {pub_res}", flush=True)

# Verify market-view-latest pointer
mv_ptr = root / "market-view-latest.json"
print("market-view-latest.json exists:", mv_ptr.exists())
if mv_ptr.exists():
    view_data = engine._pointed(root, "market-view-latest.json")
    print("Latest observed session in published view:", view_data.get("latest_observed_session"))
    print("Configured securities count:", len(view_data.get("rows", [])))
