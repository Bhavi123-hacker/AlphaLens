"""Trusted local checkpoint files and atomic unique PostgreSQL event persistence."""

from fractions import Fraction
from pathlib import Path

from psycopg import Connection
from psycopg.types.json import Jsonb

from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_evaluation.contracts import digest

from .paper_contracts import OrderEvent, PaperFill, PaperOrder, PaperReport, PaperState
from .storage import PostgresPortfolio


def save(root: Path, state: PaperState) -> Path:
    validated = PaperState.model_validate(state.model_dump(mode="json"))
    path = root / (validated.state_id + ".json")
    publish(path, stable_json(validated.model_dump(mode="json")))
    return path


def load(path: Path) -> PaperState:
    state = PaperState.model_validate_json(path.read_bytes())
    if path.stem != state.state_id:
        raise ValueError("Paper checkpoint checksum mismatch")
    return state


class PostgresPaper:
    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.connection = connection
        self.portfolios = PostgresPortfolio(connection)

    def get(self, portfolio_id: str) -> PaperState:
        row = self.connection.execute(
            "SELECT starting_cash FROM portfolio.paper_accounts WHERE portfolio_id=%s",
            (portfolio_id,),
        ).fetchone()
        if not row:
            raise ValueError("Paper account unavailable")
        rows = self.connection.execute(
            "SELECT kind,payload,content_sha256 FROM portfolio.paper_events "
            "WHERE portfolio_id=%s ORDER BY sequence",
            (portfolio_id,),
        ).fetchall()
        orders = []
        events = []
        fills = []
        reports = []
        for kind, payload, checksum in rows:
            if digest(payload) != checksum:
                raise ValueError("Paper event checksum mismatch")
            if kind == "ORDER_INTENT":
                orders.append(PaperOrder.model_validate(payload))
            elif kind == "ORDER_EVENT":
                events.append(OrderEvent.model_validate(payload))
            elif kind == "FILL":
                fills.append(PaperFill.model_validate(payload))
            else:
                reports.append(PaperReport.model_validate(payload))
        return PaperState(
            ledger=self.portfolios.get(portfolio_id),
            starting_cash=Fraction(str(row[0])),
            orders=tuple(orders),
            events=tuple(events),
            fills=tuple(fills),
            reports=tuple(reports),
        )

    def save(self, state: PaperState) -> None:
        state = PaperState.model_validate(state.model_dump(mode="json"))
        account = state.ledger.portfolio.portfolio_id
        with self.connection.transaction():
            self.portfolios.create(state.ledger.portfolio)
            self.connection.execute(
                "SELECT portfolio_id FROM portfolio.accounts WHERE portfolio_id=%s FOR UPDATE",
                (account,),
            ).fetchone()
            row = self.connection.execute(
                "SELECT starting_cash,classification FROM portfolio.paper_accounts "
                "WHERE portfolio_id=%s",
                (account,),
            ).fetchone()
            if row and row != (str(state.starting_cash), state.classification):
                raise ValueError("Paper account configuration conflict")
            if not row:
                self.connection.execute(
                    "INSERT INTO portfolio.paper_accounts VALUES (%s,%s,%s)",
                    (account, str(state.starting_cash), state.classification),
                )
            else:
                current = self.get(account)
                for old, new in (
                    (current.orders, state.orders),
                    (current.events, state.events),
                    (current.fills, state.fills),
                    (current.reports, state.reports),
                    (current.ledger.transactions, state.ledger.transactions),
                ):
                    if new[: len(old)] != old:
                        raise ValueError(
                            "Immutable paper stream prefix conflict; reload current state"
                        )
            for transaction in state.ledger.transactions:
                self.portfolios.append(transaction)
            row = self.connection.execute(
                "SELECT COALESCE(MAX(sequence),0) FROM portfolio.paper_events "
                "WHERE portfolio_id=%s",
                (account,),
            ).fetchone()
            sequence = int(str(row[0])) if row else 0
            records = (
                [("ORDER_INTENT", o.order_id, o) for o in state.orders]
                + [("ORDER_EVENT", e.event_id, e) for e in state.events]
                + [("FILL", f.fill_id, f) for f in state.fills]
                + [("REPORT", r.report_id, r) for r in state.reports]
            )
            for kind, identity, record in records:
                data = record.model_dump(mode="json")
                existing = self.connection.execute(
                    "SELECT content_sha256 FROM portfolio.paper_events "
                    "WHERE portfolio_id=%s AND record_id=%s",
                    (account, identity),
                ).fetchone()
                if existing:
                    if existing[0] != digest(data):
                        raise ValueError("Immutable paper record conflict")
                    continue
                sequence += 1
                self.connection.execute(
                    "INSERT INTO portfolio.paper_events VALUES (%s,%s,%s,%s,%s,%s)",
                    (account, sequence, identity, kind, Jsonb(data), digest(data)),
                )
