"""Immutable local ledgers and serialized PostgreSQL append under account row lock."""

from pathlib import Path

from psycopg import Connection
from psycopg.types.json import Jsonb

from alphalens_data.ingestion.storage import publish, stable_json
from alphalens_evaluation.contracts import digest

from .accounting import append
from .contracts import Ledger, Portfolio, Transaction


def save(root: Path, ledger: Ledger) -> Path:
    data = ledger.model_dump(mode="json")
    path = root / (digest(data) + ".json")
    publish(path, stable_json(data))
    return path


def load(path: Path) -> Ledger:
    ledger = Ledger.model_validate_json(path.read_bytes())
    if path.stem != digest(ledger.model_dump(mode="json")):
        raise ValueError("Ledger checksum mismatch")
    result = Ledger(portfolio=ledger.portfolio)
    for t in ledger.transactions:
        result = append(result, t)
    return result


class PostgresPortfolio:
    def __init__(self, connection: Connection[tuple[object, ...]]) -> None:
        self.connection = connection

    def create(self, portfolio: Portfolio) -> None:
        data = portfolio.model_dump(mode="json")
        with self.connection.transaction():
            self.connection.execute(
                "INSERT INTO portfolio.accounts VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (portfolio.portfolio_id, Jsonb(data), digest(data)),
            )
            if self.get(portfolio.portfolio_id).portfolio != portfolio:
                raise ValueError("Immutable portfolio identity conflict")

    def get(self, portfolio_id: str) -> Ledger:
        row = self.connection.execute(
            "SELECT payload FROM portfolio.accounts WHERE portfolio_id=%s", (portfolio_id,)
        ).fetchone()
        if not row:
            raise ValueError("Portfolio unavailable")
        rows = self.connection.execute(
            "SELECT payload FROM portfolio.transactions WHERE portfolio_id=%s "
            "ORDER BY recorded_at, effective_at, transaction_id",
            (portfolio_id,),
        ).fetchall()
        ledger = Ledger(portfolio=Portfolio.model_validate(row[0]))
        for item in rows:
            ledger = append(ledger, Transaction.model_validate(item[0]))
        return ledger

    def append(self, transaction: Transaction) -> Ledger:
        with self.connection.transaction():
            self.connection.execute(
                "SELECT portfolio_id FROM portfolio.accounts WHERE portfolio_id=%s FOR UPDATE",
                (transaction.portfolio_id,),
            ).fetchone()
            ledger = append(self.get(transaction.portfolio_id), transaction)
            data = transaction.model_dump(mode="json")
            self.connection.execute(
                "INSERT INTO portfolio.transactions VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT DO NOTHING",
                (
                    transaction.portfolio_id,
                    transaction.transaction_id,
                    transaction.recorded_at,
                    transaction.effective_at,
                    Jsonb(data),
                    digest(data),
                ),
            )
            return ledger
