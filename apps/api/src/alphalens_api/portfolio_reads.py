"""Read-only PostgreSQL adapters reuse P15 FIFO and P16 immutable event recovery."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal

from psycopg import Connection, connect
from psycopg import Error as DatabaseError
from pydantic import JsonValue

from alphalens_evaluation.contracts import digest
from alphalens_portfolio.accounting import reconstruct
from alphalens_portfolio.paper import order_states
from alphalens_portfolio.paper_performance import chart_series, performance
from alphalens_portfolio.paper_storage import PostgresPaper
from alphalens_portfolio.storage import PostgresPortfolio

from .core.config import Settings
from .core.domain_errors import APIError
from .schemas import Classification, Envelope, Page
from .services import response


class PortfolioReads:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.max_concurrent_reads)

    @contextmanager
    def connection(self) -> Iterator[Connection[tuple[object, ...]]]:
        if self.settings.database_url is None:
            raise APIError("DATABASE_NOT_CONFIGURED", "Portfolio database is not configured.")
        if not self._slots.acquire(blocking=False):
            raise APIError("READ_CAPACITY", "Database read capacity is occupied; retry later.", 429)
        try:
            with connect(
                self.settings.database_url.get_secret_value(),
                connect_timeout=3,
                options="-c default_transaction_read_only=on -c statement_timeout=5000",
            ) as connection:
                yield connection
        except DatabaseError as exc:
            raise APIError("DATABASE_UNAVAILABLE", "Portfolio database is unavailable.") from exc
        finally:
            self._slots.release()

    def readiness(self) -> dict[str, JsonValue]:
        try:
            with self.connection() as connection:
                row = connection.execute(
                    "SELECT current_setting('server_version'),"
                    "to_regclass('portfolio.accounts'),to_regclass('portfolio.transactions'),"
                    "to_regclass('portfolio.paper_accounts'),to_regclass('portfolio.paper_events')"
                ).fetchone()
                if row and all(row[1:]):
                    return {
                        "status": "REACHABLE",
                        "postgres_version": str(row[0]),
                        "ledger_schema": "AVAILABLE",
                        "access": "TRANSACTION_READ_ONLY",
                    }
                return {"status": "UNAVAILABLE", "reason": "PORTFOLIO_SCHEMA_UNAVAILABLE"}
        except APIError as exc:
            return {"status": "UNAVAILABLE", "reason": exc.code}

    def _bounded(self, connection: Connection[tuple[object, ...]], portfolio_id: str) -> None:
        row = connection.execute(
            "SELECT payload,content_sha256 FROM portfolio.accounts WHERE portfolio_id=%s",
            (portfolio_id,),
        ).fetchone()
        if not row:
            raise APIError("PORTFOLIO_NOT_FOUND", "Portfolio record was not found.", 404)
        if digest(row[0]) != row[1]:
            raise APIError("LEDGER_CHECKSUM_FAILED", "Portfolio ledger integrity failed.")
        rows = connection.execute(
            "SELECT payload,content_sha256 FROM portfolio.transactions WHERE portfolio_id=%s "
            "ORDER BY recorded_at,effective_at,transaction_id LIMIT %s",
            (portfolio_id, self.settings.max_ledger_records + 1),
        ).fetchall()
        if len(rows) > self.settings.max_ledger_records:
            raise APIError(
                "LEDGER_READ_LIMIT", "Ledger exceeds the bounded reconstruction limit.", 413
            )
        if any(digest(row[0]) != row[1] for row in rows):
            raise APIError("LEDGER_CHECKSUM_FAILED", "Portfolio ledger integrity failed.")

    def accounts(self, paper: bool, limit: int, offset: int) -> Envelope[JsonValue]:
        with self.connection() as connection:
            if paper:
                rows = connection.execute(
                    "SELECT p.payload FROM portfolio.accounts p JOIN portfolio.paper_accounts a "
                    "USING(portfolio_id) ORDER BY p.portfolio_id LIMIT %s OFFSET %s",
                    (limit + 1, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM portfolio.accounts "
                    "ORDER BY portfolio_id LIMIT %s OFFSET %s",
                    (limit + 1, offset),
                ).fetchall()
        result = response(
            [row[0] for row in rows[:limit]],
            "POSTGRESQL_RECORDED_ACCOUNTS",
            page=Page(limit=limit, offset=offset, has_more=len(rows) > limit),
        )
        return result.model_copy(
            update={
                "classification": Classification(
                    data_reality="RECORDED_ACCOUNT_METADATA",
                    usage_classification="MIXED_RECORD_TYPES",
                    final_vintage=None,
                    research_profile=None,
                )
            }
        )

    def portfolio(
        self,
        portfolio_id: str,
        view: Literal["metadata", "holdings", "transactions", "performance"],
        limit: int,
        offset: int,
    ) -> Envelope[JsonValue]:
        with self.connection() as connection:
            self._bounded(connection, portfolio_id)
            ledger = PostgresPortfolio(connection).get(portfolio_id)
        now = datetime.now(UTC)
        state = reconstruct(ledger, now.date(), now)
        page = None
        reasons: tuple[str, ...] = ()
        if view == "metadata":
            data = ledger.portfolio.model_dump(mode="json")
        elif view == "transactions":
            data = {
                "transactions": [
                    t.model_dump(mode="json") for t in ledger.transactions[offset : offset + limit]
                ]
            }
            page = Page(
                limit=limit,
                offset=offset,
                has_more=len(ledger.transactions) > offset + limit,
                total=len(ledger.transactions),
            )
        elif view == "holdings":
            positions = [p for p in state.positions if p.quantity > 0]
            data = {
                "positions": [
                    p.model_dump(mode="json") for p in positions[offset : offset + limit]
                ],
                "market_value": None,
                "unrealized_pnl": None,
                "valuation_status": "UNAVAILABLE",
                "risk_status": "UNAVAILABLE",
                "signal_status": "UNAVAILABLE",
            }
            page = Page(
                limit=limit,
                offset=offset,
                has_more=len(positions) > offset + limit,
                total=len(positions),
            )
            reasons = ("P15_VALUATION_SNAPSHOT_NOT_PERSISTED", "CURRENT_RISK_SIGNAL_UNAVAILABLE")
        else:
            data = {
                "accounting": state.model_dump(mode="json"),
                "portfolio_value": None,
                "market_value": None,
                "unrealized_pnl": None,
                "total_pnl": None,
                "session_pnl": None,
                "performance_history": None,
                "valuation_status": "UNAVAILABLE",
            }
            reasons = (
                "P15_VALUATION_SNAPSHOT_NOT_PERSISTED",
                "RESEARCH_PRICE_NOT_VALIDATED_FOR_USER_HOLDINGS",
            )
        result = response(
            data,
            "P15_POSTGRESQL_FIFO_LEDGER",
            state.ledger_state_id,
            status="PARTIAL" if reasons else "AVAILABLE",
            reasons=reasons,
            page=page,
        )
        return result.model_copy(
            update={
                "classification": Classification(
                    data_reality="USER_RECORDED_RECORDS"
                    if ledger.portfolio.portfolio_type == "USER_RECORDED"
                    else "SIMULATED_RECORDS",
                    usage_classification=ledger.portfolio.classification,
                    final_vintage=None,
                    research_profile=None,
                )
            }
        )

    def paper(
        self,
        account_id: str,
        view: Literal["metadata", "orders", "trades", "performance"],
        limit: int,
        offset: int,
    ) -> Envelope[JsonValue]:
        with self.connection() as connection:
            self._bounded(connection, account_id)
            rows = connection.execute(
                "SELECT record_id FROM portfolio.paper_events WHERE portfolio_id=%s "
                "ORDER BY sequence LIMIT %s",
                (account_id, self.settings.max_ledger_records + 1),
            ).fetchall()
            if len(rows) > self.settings.max_ledger_records:
                raise APIError(
                    "PAPER_READ_LIMIT", "Paper state exceeds bounded recovery limit.", 413
                )
            exists = connection.execute(
                "SELECT portfolio_id FROM portfolio.paper_accounts WHERE portfolio_id=%s",
                (account_id,),
            ).fetchone()
            if not exists:
                raise APIError("PAPER_ACCOUNT_NOT_FOUND", "Paper account was not found.", 404)
            state = PostgresPaper(connection).get(account_id)
        page = None
        if view == "metadata":
            data = {
                "portfolio": state.ledger.portfolio.model_dump(mode="json"),
                "performance": performance(state).model_dump(mode="json"),
                "simulation_only": True,
                "state_id": state.state_id,
            }
        elif view in {"orders", "trades"}:
            items = state.orders if view == "orders" else state.fills
            data = {
                view: [item.model_dump(mode="json") for item in items[offset : offset + limit]],
                "simulation_only": True,
            }
            if view == "orders":
                data["order_states"] = order_states(state)
            page = Page(
                limit=limit, offset=offset, has_more=len(items) > offset + limit, total=len(items)
            )
        else:
            charts = chart_series(state)
            equity, drawdown = charts["equity"], charts["drawdown"]
            if not isinstance(equity, list) or not isinstance(drawdown, list):
                raise APIError("PAPER_CONTRACT_INVALID", "Paper chart contract is invalid.")
            data = {
                "performance": performance(state).model_dump(mode="json"),
                "equity": equity[offset : offset + limit],
                "drawdown": drawdown[offset : offset + limit],
                "simulation_only": True,
            }
            page = Page(
                limit=limit,
                offset=offset,
                has_more=len(state.reports) > offset + limit,
                total=len(state.reports),
            )
        result = response(
            data,
            "P16_IMMUTABLE_SIMULATED_EVENTS_P15_VALUATION",
            state.state_id,
            page=page,
            reasons=("SIMULATED_NOT_BROKER_EXECUTION",),
        )
        return result.model_copy(
            update={
                "classification": Classification(
                    data_reality="SIMULATED_RECORDS",
                    usage_classification=state.classification,
                    final_vintage=None,
                    research_profile=None,
                )
            }
        )
