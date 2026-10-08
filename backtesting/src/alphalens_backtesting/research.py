"""P10 final-vintage research execution; OOS scores only, exact rational cash.

Normal verified-PIT execution is untouched. Missing prices/actions retain unknown
economic state; no target-based selection or hypothetical recovery value.
"""

import json
from collections import Counter, defaultdict
from fractions import Fraction
from math import ceil
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from alphalens_backtesting.contracts import CostScenario
from alphalens_backtesting.metrics import annual_statistics
from alphalens_backtesting.money import text_money
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchCalendar, lineage


def digest_file(path: Path) -> str:
    import hashlib

    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


class ResearchPrices:
    def __init__(self, root: Path) -> None:
        self.root = root
        manifest = json.loads((root / "canonical-manifest.json").read_bytes())
        self.dataset_id = manifest["dataset_id"]
        if checksum(stable_json(manifest["identity"])) != self.dataset_id:
            raise ValueError("P10_RESEARCH_CANONICAL_ID_MISMATCH")
        self.sessions = ResearchCalendar.model_validate_json(
            (root / "research-calendar.json").read_bytes()
        )
        if self.sessions.calendar_id != manifest["identity"]["calendar_id"]:
            raise ValueError("P10_RESEARCH_CALENDAR_MISMATCH")
        self.tables: dict[str, pa.Table] = {}
        self.indices: dict[str, dict[Any, int]] = {}
        self.files = {}
        self.oos_cache_key: str | None = None
        self.oos_cache: dict[Any, list[dict[str, Any]]] | None = None
        for f in manifest["identity"]["files"]:
            self.files[Path(f["path"]).name] = (root / f["path"], f["sha256"])

    def get(self, security: str, day: Any) -> dict[str, Any] | None:
        # Load only owned/considered identity buckets; never build a 7M-row Python dict.
        bucket = int(checksum(security.encode())[:8], 16) % 64
        key = f"bucket-{bucket:02}.parquet"
        if key not in self.tables:
            path, digest = self.files[key]
            if digest_file(path) != digest:
                raise ValueError("P10_RESEARCH_PRICE_CHECKSUM_MISMATCH")
            table = pq.ParquetFile(path).read(
                columns=[
                    "security_id",
                    "session_date",
                    "open",
                    "close",
                    "quality",
                    "economic_action",
                    "canonical_record_id",
                ]
            )
            if json.loads(table.schema.metadata[b"research_lineage"]) != lineage(
                self.sessions.profile
            ):
                raise ValueError("P10_RESEARCH_PRICE_LINEAGE_MISMATCH")
            self.tables[key] = table
            self.indices[key] = {
                (s, d): i
                for i, (s, d) in enumerate(
                    zip(
                        table.column("security_id").to_pylist(),
                        table.column("session_date").to_pylist(),
                        strict=True,
                    )
                )
            }
        index = self.indices[key].get((security, day))
        if index is None:
            return None
        t = self.tables[key]
        return {
            n: t.column(n)[index].as_py()
            for n in ("open", "close", "quality", "economic_action", "canonical_record_id")
        }


def selected(
    rows: list[dict[str, Any]],
    rule: str,
    slots: int,
    task: str,
) -> list[dict[str, Any]]:
    if slots <= 0:
        return []
    ordered = sorted(rows, key=lambda r: (-r["score"], r["security_id"]))
    if rule == "TOP_K":
        ordered = ordered[:2]
    elif rule == "TOP_PERCENTILE":
        ordered = ordered[: ceil(len(ordered) * 0.2)]
    elif rule == "PREDICTION_THRESHOLD":
        threshold = 0.5 if task == "classification" else 0.0
        ordered = [r for r in ordered if r["score"] >= threshold]
    else:
        raise ValueError("UNSUPPORTED_RESEARCH_SELECTION_POLICY")
    return ordered[:slots]


def run_research(
    reports: list[dict[str, Any]],
    oos_root: Path,
    prices: ResearchPrices,
    scenario: CostScenario,
    rule: str,
    output: Path,
) -> dict[str, Any]:
    if not reports:
        raise ValueError("P10_GENUINE_OOS_REQUIRED")
    first = reports[0]
    task = first["task"]
    h = first["horizon"]
    family = first["model_family"]
    profile = prices.sessions.profile
    if any(
        r["task"] != task
        or r["horizon"] != h
        or r["model_family"] != family
        or r["research_profile_id"] != profile.profile_id
        for r in reports
    ):
        raise ValueError("P10_RESEARCH_MODEL_OR_PROFILE_MISMATCH")
    by_entry: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    dates = prices.sessions.dates
    lookup = {d: i for i, d in enumerate(dates)}
    cache_key = checksum(stable_json([r["oos_sha256"] for r in reports]))
    cached = prices.oos_cache_key == cache_key and prices.oos_cache is not None
    if cached:
        if prices.oos_cache is None:
            raise ValueError("RESEARCH_OOS_CACHE_UNAVAILABLE")
        by_entry = prices.oos_cache
    for report in () if cached else reports:
        path = oos_root / report["oos_file"]
        if digest_file(path) != report["oos_sha256"]:
            raise ValueError("P10_OOS_CHECKSUM_MISMATCH")
        reader = pq.ParquetFile(path)
        metadata = reader.schema_arrow.metadata
        if (
            metadata[b"role"] != b"FOLD_TEST"
            or metadata[b"model_run_id"].decode() != report["model_run_id"]
        ):
            raise ValueError("P10_IN_SAMPLE_OR_UNPINNED_PREDICTIONS_FORBIDDEN")
        if json.loads(metadata[b"research_lineage"]) != lineage(profile):
            raise ValueError("P10_OOS_RESEARCH_LINEAGE_MISMATCH")
        # Targets/outcome/scorable columns are intentionally never read by execution.
        columns = [
            "security_id",
            "session_date",
            "decision_time",
            "prediction_id",
            "score",
            "canonical_record_id",
        ]
        for batch in reader.iter_batches(columns=columns):
            for row in batch.to_pylist():
                source = row["session_date"]
                index = lookup[source]
                if index + 1 >= len(dates):
                    continue
                entry = dates[index + 1]
                if not prices.sessions.entry_allowed(source, entry, row["decision_time"]):
                    raise ValueError("P10_RESEARCH_DECISION_NOT_PROVEN_BEFORE_OPEN_STAGE")
                row["model_run_id"] = report["model_run_id"]
                row["source_index"] = index
                by_entry[entry].append(row)
    prices.oos_cache_key = cache_key
    prices.oos_cache = by_entry
    start = min(by_entry)
    end = max(r["fold"]["test_end"] for r in reports)
    end_index = lookup[next(d for d in reversed(dates) if d.isoformat() <= end)]
    # Never import confirmation/holdout prices to finish development positions.
    if prices.sessions.availability(dates[end_index]) is None:
        end_index -= 1
    scoped = dates[lookup[start] : end_index + 1]
    identity = dict(
        **lineage(profile),
        p9_oos_files=[{"file": r["oos_file"], "sha256": r["oos_sha256"]} for r in reports],
        canonical_dataset_id=prices.dataset_id,
        calendar_id=prices.sessions.calendar_id,
        task=task,
        horizon=h,
        model_family=family,
        costs=scenario.model_dump(mode="json"),
        selection_rule=rule,
        top_k=2,
        top_percentile="0.2",
        maximum_positions=3,
        threshold="0.5" if task == "classification" else "0",
        initial_capital="100000",
        sizing="AVAILABLE_CASH_DIVIDED_BY_FREE_SLOTS_EXACT_RATIONAL",
        execution="RESEARCH_NEXT_SESSION_PRE_OPEN_DECISION_THEN_EVIDENCED_OPEN",
        exit="t+h_CLOSE_NO_MISSING_SESSION_SKIP",
        version="p10.research.v1",
        benchmark="UNAVAILABLE",
        annual_sessions_assumption=252,
        risk_free_annual_assumption=0,
        missing_exit="RETAIN_UNRESOLVED_NO_PRICE_SUBSTITUTION",
    )
    bt_id = checksum(stable_json(identity))
    capital = Fraction(100000)
    cash = capital
    inventory: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    fees = Fraction(0)
    slippage = Fraction(0)
    realized = Fraction(0)
    peak = capital
    previous: Fraction | None = capital
    ever_unknown = False
    skip: Counter[str] = Counter()
    turnover = Fraction(0)
    minimum_cash = cash
    for day in scoped:
        position_count = len(inventory)
        rows = []
        for r in by_entry.get(day, []):
            if r["security_id"] in inventory:
                skip["ALREADY_HELD"] += 1
            else:
                rows.append(r)
        slots = 3 - position_count
        chosen = selected(rows, rule, max(0, slots), task)
        if slots <= 0:
            skip["MAX_POSITIONS"] += len(rows)
        budget = cash / slots if slots > 0 else Fraction(0)
        for row in chosen:
            security = row["security_id"]
            view = prices.get(security, day)
            decision = dict(
                decision_id=checksum(f"{bt_id}:{row['prediction_id']}".encode()),
                prediction_id=row["prediction_id"],
                model_run_id=row["model_run_id"],
                security_id=security,
                source_session=row["session_date"].isoformat(),
                decision_time=row["decision_time"].isoformat(),
                entry_session=day.isoformat(),
                budget=text_money(budget),
                status="FILLED",
            )
            if view is None or view["quality"] == "REJECTED":
                decision["status"] = "NO_FILL_MISSING_OR_REJECTED_OPEN"
                skip[decision["status"]] += 1
                decisions.append(decision)
                continue
            exit_index = row["source_index"] + h
            if exit_index >= len(dates):
                decision["status"] = "NO_FILL_EXIT_CALENDAR_NOT_YET_OBSERVED"
                skip[decision["status"]] += 1
                decisions.append(decision)
                continue
            if budget <= 0 or budget > cash:
                decision["status"] = "NO_FILL_CAPITAL"
                skip[decision["status"]] += 1
                decisions.append(decision)
                continue
            nominal = Fraction(view["open"])
            effective = nominal * (1 + scenario.slip_rate)
            quantity = budget / (effective * (1 + scenario.fee_rate))
            fee = quantity * effective * scenario.fee_rate
            cash -= budget
            fees += fee
            slippage += quantity * (effective - nominal)
            turnover += quantity * nominal
            trade = dict(
                trade_id=checksum(f"{bt_id}:{row['prediction_id']}:fill".encode()),
                prediction_id=row["prediction_id"],
                model_run_id=row["model_run_id"],
                security_id=security,
                entry_session=day.isoformat(),
                planned_exit_session=dates[exit_index].isoformat(),
                exit_session=None,
                entry_price=str(view["open"]),
                quantity=text_money(quantity),
                entry_price_record_id=view["canonical_record_id"],
                entry_budget=text_money(budget),
                net_pnl=None,
                net_return=None,
                holding_sessions=None,
                status="OPEN",
            )
            inventory[security] = dict(
                quantity=quantity,
                budget=budget,
                exit_day=dates[exit_index],
                trade=trade,
                unresolved=False,
            )
            decisions.append(decision)
            trades.append(trade)
        for security, position in list(inventory.items()):
            view = prices.get(security, day)
            # Action evidence for this completed session becomes known at its next
            # assumed boundary. It does not change the earlier pre-open decision.
            if view is not None and view["economic_action"]:
                position["unresolved"] = True
                position["trade"]["status"] = "UNRESOLVED_RAW_ECONOMIC_ACTION"
            if position["exit_day"] == day and not position["unresolved"]:
                if view is None or view["quality"] == "REJECTED":
                    position["unresolved"] = True
                    position["trade"]["status"] = "UNRESOLVED_MISSING_EXIT"
                    continue
                nominal = Fraction(view["close"])
                effective = nominal * (1 - scenario.slip_rate)
                gross = position["quantity"] * effective
                fee = gross * scenario.fee_rate
                net = gross - fee
                cash += net
                fees += fee
                slippage += position["quantity"] * (nominal - effective)
                realized += net - position["budget"]
                turnover += position["quantity"] * nominal
                trade = position["trade"]
                trade.update(
                    exit_session=day.isoformat(),
                    exit_price=str(view["close"]),
                    exit_price_record_id=view["canonical_record_id"],
                    net_pnl=text_money(net - position["budget"]),
                    net_return=float((net - position["budget"]) / position["budget"]),
                    holding_sessions=lookup[day]
                    - lookup[next(d for d in dates if d.isoformat() == trade["entry_session"])]
                    + 1,
                    status="CLOSED",
                )
                del inventory[security]
        value = cash
        known = True
        cost_basis = Fraction(0)
        for security, position in inventory.items():
            view = prices.get(security, day)
            cost_basis += position["budget"]
            if position["unresolved"] or view is None or view["quality"] == "REJECTED":
                known = False
            else:
                value += position["quantity"] * Fraction(view["close"])
        minimum_cash = min(minimum_cash, cash)
        if not known:
            ever_unknown = True
        if known:
            peak = max(peak, value)
        at = prices.sessions.availability(day)
        curve.append(
            dict(
                session=day.isoformat(),
                cash=text_money(cash),
                market_value=text_money(value - cash) if known else None,
                portfolio_value=text_money(value) if known else None,
                realized_pnl=text_money(realized),
                unrealized_pnl=text_money(value - cash - cost_basis) if known else None,
                total_pnl=text_money(value - capital) if known else None,
                session_pnl=text_money(value - previous)
                if known and previous is not None
                else None,
                drawdown=float(value / peak - 1) if known and not ever_unknown else None,
                open_positions=len(inventory),
                cash_utilization=float((value - cash) / value) if known and value > 0 else None,
                freshness="RESEARCH_EOD_AT_ASSUMED_NEXT_SESSION_BOUNDARY",
                quality="DEGRADED",
                knowledge_cutoff=at.isoformat() if at else None,
            )
        )
        previous = value if known else None
    complete = not ever_unknown and not any(p["unresolved"] for p in inventory.values())
    closed = [r for r in trades if r["status"] == "CLOSED"]
    net = [r["net_return"] for r in closed]
    pnl = [float(r["net_pnl"]) for r in closed]
    gains = sum(v for v in pnl if v > 0)
    losses = -sum(v for v in pnl if v < 0)
    maxdd = -min(r["drawdown"] for r in curve) if complete else None
    duration = (scoped[-1] - scoped[0]).days
    annual: dict[str, float | None] = dict(
        cagr=None, annualized_volatility=None, sharpe=None, sortino=None, calmar=None
    )
    if complete and len(curve) >= 252 and duration >= 365:
        annual = annual_statistics(
            [float(r["portfolio_value"]) for r in curve], 100000, duration, 252, 0, maxdd
        )
    summary = dict(
        **lineage(profile),
        backtest_id=bt_id,
        task=task,
        horizon=h,
        model_family=family,
        selection_rule=rule,
        cost_scenario=scenario.name,
        cost_status=scenario.status,
        period=[scoped[0].isoformat(), scoped[-1].isoformat()],
        status="RESEARCH_RAW_PRICE_DIAGNOSTIC" if complete else "UNRESOLVED_ECONOMIC_OUTCOMES",
        total_return=float(Fraction(curve[-1]["portfolio_value"]) / capital - 1)
        if complete
        else None,
        **annual,
        maximum_drawdown=maxdd,
        win_rate=sum(v > 0 for v in net) / len(net) if net else None,
        loss_rate=sum(v < 0 for v in net) / len(net) if net else None,
        average_trade_return=float(np.mean(net)) if net else None,
        median_trade_return=float(np.median(net)) if net else None,
        profit_factor=gains / losses if losses else None,
        expectancy=float(np.mean(pnl)) if pnl else None,
        trade_count=len(trades),
        closed_trade_count=len(closed),
        unresolved_trade_count=sum(r["status"].startswith("UNRESOLVED") for r in trades),
        turnover=float(turnover) / np.mean([float(r["portfolio_value"]) for r in curve])
        if complete
        else None,
        average_holding_sessions=float(np.mean([r["holding_sessions"] for r in closed]))
        if closed
        else None,
        exposure=sum(r["open_positions"] > 0 for r in curve) / len(curve),
        cash_utilization=float(np.mean([r["cash_utilization"] for r in curve]))
        if complete
        else None,
        fees=text_money(fees),
        slippage=text_money(slippage),
        minimum_cash=text_money(minimum_cash),
        skipped=dict(skip),
        benchmark_status="UNAVAILABLE",
        benchmark_relative_return=None,
        trade_statistics_scope="CLOSED_TRADES_ONLY_UNRESOLVED_RETAINED",
        identity=identity,
    )
    destination = output / bt_id
    destination.mkdir(parents=True, exist_ok=True)
    metadata = {b"research_lineage": stable_json(lineage(profile)), b"backtest_id": bt_id.encode()}
    for name, rows in (("equity", curve), ("trades", trades), ("decisions", decisions)):
        if rows:
            pq.write_table(
                pa.Table.from_pylist(rows).replace_schema_metadata(metadata),
                destination / f"{name}.parquet",
            )
    (destination / "summary.json").write_bytes(stable_json(summary))
    return summary
