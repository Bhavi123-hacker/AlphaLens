"""Cutoff-aware FIFO reconstruction with exact rational lot allocation."""

from datetime import date, datetime
from fractions import Fraction

from alphalens_evaluation.contracts import digest

from .contracts import AccountingState, Ledger, Lot, Position, Transaction


def visible(ledger: Ledger, session: date, cutoff: datetime) -> tuple[Transaction, ...]:
    if cutoff < ledger.portfolio.created_at:
        raise ValueError("Portfolio did not exist at cutoff")
    return tuple(
        sorted(
            (
                t
                for t in ledger.transactions
                if t.session <= session and t.recorded_at <= cutoff and t.effective_at <= cutoff
            ),
            key=lambda t: (t.effective_at, t.recorded_at, t.transaction_id),
        )
    )


def reconstruct(ledger: Ledger, session: date, cutoff: datetime) -> AccountingState:
    events = visible(ledger, session, cutoff)
    cash = Fraction(0)
    capital = Fraction(0)
    positions: dict[str, Position] = {}
    for t in events:
        if t.kind in {"CASH_DEPOSIT", "CASH_WITHDRAWAL"}:
            delta = t.cash_amount * (1 if t.kind == "CASH_DEPOSIT" else -1)
            cash += delta
            capital += delta
        else:
            if t.security_id is None or t.symbol is None:
                raise ValueError("Position identity unavailable")
            p = positions.get(t.security_id) or Position(
                security_id=t.security_id,
                transaction_symbol=t.symbol,
                first_session=t.session,
                quantity=Fraction(0),
                cost_basis=Fraction(0),
                gross_acquisition_basis=Fraction(0),
                realized_pnl=Fraction(0),
                fees=Fraction(0),
                lots=(),
            )
            lots = list(p.lots)
            basis = p.cost_basis
            gross = p.gross_acquisition_basis
            realized = p.realized_pnl
            if t.kind in {"BUY", "OPENING_POSITION"}:
                amount = t.quantity * t.price + t.fees
                if t.kind == "OPENING_POSITION":
                    if t.declared_cost_basis is None:
                        raise ValueError("Opening basis unavailable")
                    amount = t.declared_cost_basis
                    capital += amount
                else:
                    cash -= amount
                lots.append(
                    Lot(
                        transaction_id=t.transaction_id,
                        session=t.session,
                        quantity=t.quantity,
                        cost_basis=amount,
                        provenance=t.classification,
                    )
                )
                basis += amount
                gross += amount
            else:
                if t.quantity > p.quantity:
                    raise ValueError("NO_SHORT_SELLING: sell exceeds owned quantity")
                remaining = t.quantity
                removed = Fraction(0)
                while remaining:
                    lot = lots.pop(0)
                    used = min(remaining, lot.quantity)
                    allocated = lot.cost_basis * used / lot.quantity
                    removed += allocated
                    remaining -= used
                    if used < lot.quantity:
                        lots.insert(
                            0,
                            lot.model_copy(
                                update={
                                    "quantity": lot.quantity - used,
                                    "cost_basis": lot.cost_basis - allocated,
                                }
                            ),
                        )
                proceeds = t.quantity * t.price - t.fees
                realized += proceeds - removed
                basis -= removed
                cash += proceeds
            positions[t.security_id] = p.model_copy(
                update={
                    "transaction_symbol": t.symbol,
                    "quantity": sum((lot.quantity for lot in lots), Fraction(0)),
                    "cost_basis": basis,
                    "gross_acquisition_basis": gross,
                    "realized_pnl": realized,
                    "fees": p.fees + t.fees,
                    "lots": tuple(lots),
                }
            )
        if cash < 0:
            raise ValueError("NO_OVERDRAFT: insufficient cash")
    return AccountingState(
        ledger_state_id=digest(
            {
                "portfolio": ledger.portfolio.model_dump(mode="json"),
                "transactions": [t.model_dump(mode="json") for t in events],
            }
        ),
        cash=cash,
        net_external_capital=capital,
        positions=tuple(positions[k] for k in sorted(positions)),
        transaction_ids=tuple(t.transaction_id for t in events),
    )


def append(ledger: Ledger, transaction: Transaction) -> Ledger:
    previous = next(
        (t for t in ledger.transactions if t.transaction_id == transaction.transaction_id), None
    )
    if previous:
        if previous != transaction:
            raise ValueError("Immutable transaction identity conflict")
        return ledger
    candidate = Ledger(portfolio=ledger.portfolio, transactions=(*ledger.transactions, transaction))
    # A backdated import must also leave every subsequent ledger prefix valid.
    for event in candidate.transactions:
        reconstruct(candidate, event.session, event.recorded_at)
    return candidate
