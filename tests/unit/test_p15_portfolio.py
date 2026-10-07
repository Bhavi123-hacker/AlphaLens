"""Constructed fixtures only. Independent exact FIFO and PIT portfolio checks."""

from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest
from scripts.build_p6_test_fixture import build_history as build_prices
from scripts.build_p15_test_fixture import account, bought, clock, event, funded

from alphalens_backtesting.contracts import BenchmarkEvidence
from alphalens_data.canonical.models import ReadContext
from alphalens_data.canonical.services import CanonicalReader
from alphalens_data.ingestion.contracts import Classification
from alphalens_portfolio.accounting import append, reconstruct
from alphalens_portfolio.history import benchmark_comparison, build_history, price_history
from alphalens_portfolio.storage import load, save
from alphalens_portfolio.valuation import value


@pytest.fixture(scope="module")
def reader(tmp_path_factory: pytest.TempPathFactory) -> CanonicalReader:
    batch, _ = build_prices(tmp_path_factory.mktemp("p15"), length=20, revision=(9, 19, "999"))
    return CanonicalReader(batch)


def test_exact_fifo_partial_multiple_lots_fees() -> None:
    ledger = append(bought(), event("BUY", 3, "buy2", price="120", fees="20"))
    ledger = append(ledger, event("SELL", 4, "sell", quantity="15", price="150", fees="15"))
    state = reconstruct(ledger, date(2024, 1, 4), clock(4))
    p = state.positions[0]
    assert p.quantity == 5 and p.cost_basis == 610
    assert p.realized_pnl == 615  # 2250-15-(1010+610)
    assert p.fees == 45 and state.cash == 10005
    assert len(p.lots) == 1 and p.lots[0].transaction_id == "buy2"


def test_complete_exit_retains_realized_history() -> None:
    ledger = append(bought(), event("SELL", 3, "sell", price="110", fees="5"))
    p = reconstruct(ledger, date(2024, 1, 3), clock(3)).positions[0]
    assert p.quantity == p.cost_basis == 0 and p.realized_pnl == 85 and p.lots == ()


@pytest.mark.parametrize(
    "kind,kwargs",
    [
        ("SELL", {"quantity": "11"}),
        ("BUY", {"quantity": "1000"}),
        ("CASH_WITHDRAWAL", {"cash_amount": "100000"}),
    ],
)
def test_no_short_or_overdraft(kind: str, kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="NO_SHORT|NO_OVERDRAFT"):
        append(bought(), event(kind, 3, "bad", **kwargs))


def test_deposits_withdrawals_external_capital() -> None:
    ledger = append(funded(), event("CASH_WITHDRAWAL", 2, "withdraw", cash_amount="300"))
    state = reconstruct(ledger, date(2024, 1, 2), clock(2))
    assert state.cash == state.net_external_capital == 9700


def test_opening_import_preserves_declared_basis_without_cash_deduction() -> None:
    ledger = append(
        account(), event("OPENING_POSITION", 2, "opening", price="0", declared_cost_basis="735")
    )
    state = reconstruct(ledger, date(2024, 1, 2), clock(2))
    assert state.cash == 0 and state.net_external_capital == 735
    assert state.positions[0].cost_basis == 735
    assert reconstruct(ledger, date(2024, 1, 1), clock(1)).positions == ()


@pytest.mark.parametrize(
    "change",
    [
        {"price": 10.5},
        {"quantity": "-1"},
        {"recorded_at": clock(1, 0)},
        {"currency": "USD"},
        {"classification": "PAPER"},
    ],
)
def test_transaction_contract_guards(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        append(funded(), event("BUY", 1, "bad", **change))


def test_duplicate_id_is_idempotent_conflicting_payload_rejected() -> None:
    ledger = bought()
    assert append(ledger, ledger.transactions[-1]) == ledger
    with pytest.raises(ValueError, match="identity conflict"):
        append(ledger, event("BUY", 2, "buy", price="99"))


def test_current_valuation_pnl_and_identity(reader: CanonicalReader) -> None:
    ledger = bought()
    v = value(ledger, reader, date(2024, 1, 10), clock(10))
    p = v.positions[0]
    bar = next(
        p
        for p in reader.prices_as_of(
            date(2024, 1, 10), date(2024, 1, 10), ReadContext(knowledge_cutoff=clock(10))
        ).records
        if p.observation.security_id == "TEST:ALPHA"
    )
    assert bar.observation.values is not None
    close = Fraction(bar.observation.values.close)
    assert p.market_value == close * 10
    assert p.unrealized_pnl == close * 10 - 1010
    assert p.total_pnl == p.unrealized_pnl
    assert v.portfolio_value == 8990 + close * 10
    assert v.freshness == "EOD_COMPLETE"
    assert v.disclaimer == "TEST_ONLY — NOT A REAL MARKET VALUATION"
    assert value(ledger, reader, v.session, clock(10)) == v
    assert p.decisions.signals == {} and p.decisions.risk_level == "UNAVAILABLE"


def test_partial_sell_realized_plus_unrealized(reader: CanonicalReader) -> None:
    ledger = append(bought(), event("SELL", 5, "sell", quantity="4", price="110", fees="4"))
    v = value(ledger, reader, date(2024, 1, 10), clock(10))
    assert v.realized_pnl == 32 and v.total_cost_basis == 606
    assert v.total_pnl == v.realized_pnl + (v.unrealized_pnl or 0)


def test_stale_and_unavailable_never_guess_price(reader: CanonicalReader) -> None:
    stale = value(bought(), reader, date(2024, 1, 21), clock(21))
    assert stale.freshness == "STALE" and stale.positions[0].valuation_session == date(2024, 1, 20)
    ledger = append(funded(), event("BUY", 2, "missing", security_id="TEST:MISSING"))
    missing = value(ledger, reader, date(2024, 1, 10), clock(10))
    assert missing.portfolio_value is None and missing.total_pnl is None
    assert missing.unavailable_positions == ("TEST:MISSING",)


def test_real_manual_holding_cannot_use_test_market_values(reader: CanonicalReader) -> None:
    ledger = bought().model_copy(update={"portfolio": account("USER_RECORDED").portfolio})
    v = value(ledger, reader, date(2024, 1, 10), clock(10))
    assert v.portfolio_value is None and v.positions[0].reasons == ("CLASSIFICATION_BLOCKED",)


def test_history_no_preentry_or_interpolation_session_pnl(reader: CanonicalReader) -> None:
    observations = tuple((date(2024, 1, d), clock(d)) for d in (1, 5, 10, 21))
    h = build_history(bought(), reader, observations)
    assert h.per_security["TEST:ALPHA"][0]["session"] == "2024-01-05"
    assert h.portfolio_series[-1]["freshness"] == "STALE"
    assert h.valuations[-1].session_pnl is None
    assert h.valuations[2].session_pnl == h.valuations[2].total_pnl - h.valuations[1].total_pnl  # type: ignore[operator]
    assert price_history(reader, "TEST:ALPHA", date(2024, 1, 1), date(2024, 1, 10), clock(10))


def test_cash_deposit_is_not_session_profit(reader: CanonicalReader) -> None:
    ledger = append(bought(), event("CASH_DEPOSIT", 10, "newcash", cash_amount="500"))
    old = value(ledger, reader, date(2024, 1, 5), clock(5))
    new = value(ledger, reader, date(2024, 1, 10), clock(10), previous=old)
    assert new.session_pnl == new.total_pnl - old.total_pnl  # type: ignore[operator]


def test_benchmark_unavailable_and_evidenced_alignment(reader: CanonicalReader) -> None:
    h = build_history(
        bought(), reader, ((date(2024, 1, 5), clock(5)), (date(2024, 1, 10), clock(10)))
    )
    assert benchmark_comparison(h, reader).availability == "UNAVAILABLE"
    evidence = BenchmarkEvidence(
        security_id="TEST:ALPHA",
        name="TEST_ONLY_BENCHMARK",
        classification=Classification.TEST_ONLY,
        canonical_input_id=reader.batch.input_id,
        rights_evidence_reference="CONSTRUCTED_TEST_ONLY",
    )
    result = benchmark_comparison(h, reader, evidence)
    assert result.availability == "AVAILABLE" and len(result.points) == 2
    assert (
        result.points[0]["portfolio_normalized"]
        == result.points[0]["benchmark_normalized"]
        == "100"
    )
    with pytest.raises(ValueError):
        BenchmarkEvidence.model_validate({**evidence.model_dump(mode="json"), "name": "NIFTY 50"})


def test_future_transaction_cannot_rewrite_old_snapshot(reader: CanonicalReader) -> None:
    old = value(bought(), reader, date(2024, 1, 10), clock(10))
    later = append(bought(), event("SELL", 15, "future", price="1000"))
    assert value(later, reader, date(2024, 1, 10), clock(10)) == old


def test_later_recorded_backdated_transaction_not_known(reader: CanonicalReader) -> None:
    ledger = append(bought(), event("SELL", 5, "late", quantity="1", recorded_at=clock(15)))
    assert value(ledger, reader, date(2024, 1, 10), clock(10)) == value(
        bought(), reader, date(2024, 1, 10), clock(10)
    )


def test_actual_future_price_revision_cannot_change_old_values(reader: CanonicalReader) -> None:
    # P5 fixture contains a genuine later-available correction to the January 10 bar.
    earlier = value(bought(), reader, date(2024, 1, 10), clock(10))
    later = value(bought(), reader, date(2024, 1, 10), clock(20))
    assert earlier.positions[0].valuation_price != later.positions[0].valuation_price
    assert value(bought(), reader, date(2024, 1, 10), clock(10)) == earlier


def test_local_storage_recovery_and_tamper(tmp_path: Path) -> None:
    ledger = bought()
    path = save(tmp_path, ledger)
    assert load(path) == ledger and save(tmp_path, ledger) == path
    path.write_text(path.read_text().replace("TEST_ONLY portfolio", "tampered"))
    with pytest.raises(ValueError, match="checksum"):
        load(path)


def test_symbol_change_stable_identity_and_actions_unresolved(reader: CanonicalReader) -> None:
    # Canonical fixture has durable TEST:ALPHA identity changes; no duplicate position arises.
    v = value(bought(), reader, date(2024, 1, 20), clock(20))
    assert len(v.positions) == 1 and v.positions[0].accounting.security_id == "TEST:ALPHA"
    assert v.positions[0].symbol == next(
        e.fact.symbol
        for e in reader.security_metadata_as_of(
            v.session, ReadContext(knowledge_cutoff=clock(20))
        ).records
        if e.security_id == "TEST:ALPHA"
    )


def test_session_pnl_rejects_future_snapshot(reader: CanonicalReader) -> None:
    future = value(bought(), reader, date(2024, 1, 20), clock(20))
    with pytest.raises(ValueError, match="strictly prior"):
        value(bought(), reader, date(2024, 1, 10), clock(10), previous=future)


@pytest.mark.parametrize("kind", ["SPLIT", "BONUS", "MERGER", "DELISTING"])
def test_real_canonical_action_evidence_remains_unresolved(
    reader: CanonicalReader,
    tmp_path: Path,
    kind: str,
) -> None:
    from test_p9_future_knowledge import append_reference

    from alphalens_data.canonical.models import ActionRevision

    original = reader.batch.revisions[0]
    action = ActionRevision.model_validate(
        dict(
            logical_record_id="TEST_ONLY_ACTION",
            revision_id="r1",
            revision_number=1,
            security_id="TEST:ALPHA",
            effective_from=date(2024, 1, 5),
            ex_date=date(2024, 1, 5),
            corporate_action_id="TEST_ONLY_ACTION",
            event_type=kind,
            factor="2",
            provenance=original.provenance.model_copy(update={"available_at": clock(8)}),
        )
    )
    changed = CanonicalReader(append_reference(reader.batch, action, tmp_path / "action"))
    before = value(bought(), changed, date(2024, 1, 5), clock(5))
    original_before = value(bought(), reader, date(2024, 1, 5), clock(5))
    assert before.positions == original_before.positions
    after = value(bought(), changed, date(2024, 1, 10), clock(10))
    assert after.positions[0].freshness == "UNRESOLVED" and after.portfolio_value is None
    assert after.positions[0].accounting.quantity == 10


def test_canonical_symbol_change_retains_one_holding(
    reader: CanonicalReader, tmp_path: Path
) -> None:
    from test_p9_future_knowledge import append_reference

    from alphalens_data.canonical.models import IdentityRevision

    old = next(
        r
        for r in reader.batch.revisions
        if isinstance(r, IdentityRevision) and r.security_id == "TEST:ALPHA"
    )
    provenance = old.provenance.model_copy(update={"available_at": clock(8)})
    fact = old.fact.model_copy(
        update={
            "revision_id": "r2",
            "supersedes_revision_id": "r1",
            "symbol": "TEST_RENAMED",
            "provenance": provenance,
        }
    )
    revised = old.model_copy(
        update={
            "revision_id": "r2",
            "revision_number": 2,
            "supersedes_revision_id": "r1",
            "fact": fact,
            "provenance": provenance,
        }
    )
    changed = CanonicalReader(append_reference(reader.batch, revised, tmp_path / "rename"))
    earlier = value(bought(), changed, date(2024, 1, 5), clock(5))
    later = value(bought(), changed, date(2024, 1, 10), clock(10))
    assert (
        earlier.positions[0].symbol == "TEST_ALPHA" and later.positions[0].symbol == "TEST_RENAMED"
    )
    assert len(later.positions) == 1 and later.positions[0].accounting.quantity == 10


def test_delisted_membership_retains_unresolved_accounting(
    reader: CanonicalReader, tmp_path: Path
) -> None:
    from test_p9_future_knowledge import append_reference

    from alphalens_data.canonical.models import MembershipRevision

    old = next(
        r
        for r in reader.batch.revisions
        if isinstance(r, MembershipRevision) and r.security_id == "TEST:ALPHA"
    )
    fact = old.fact.model_copy(
        update={"revision_id": "r2", "supersedes_revision_id": "r1", "listing_status": "DELISTED"}
    )
    revised = old.model_copy(
        update={
            "revision_id": "r2",
            "revision_number": 2,
            "supersedes_revision_id": "r1",
            "fact": fact,
        }
    )
    changed = CanonicalReader(append_reference(reader.batch, revised, tmp_path / "delisted"))
    v = value(bought(), changed, date(2024, 1, 10), clock(10))
    assert v.positions[0].reasons == ("TERMINAL_VALUE_UNRESOLVED",)
    assert v.positions[0].accounting.cost_basis == 1010 and v.portfolio_value is None


def test_optional_decision_history_chart_refs_and_future_filtering() -> None:
    from test_p13_signals import evidence

    from alphalens_decision.explanations import explain
    from alphalens_decision.signal_contracts import SignalPolicy
    from alphalens_decision.signals import evaluate
    from alphalens_portfolio.history import monitoring_history
    from alphalens_portfolio.valuation import DecisionHistory, references

    ranking, risk = evidence()
    signal = evaluate(ranking, "TEST:A", (risk,), SignalPolicy(horizon=5))
    explanation = explain(signal, ranking, (risk,))
    history = DecisionHistory(
        risks=(risk,), rankings=(ranking,), signals=(signal,), explanations=(explanation,)
    )
    refs = references(
        history, "TEST:A", signal.session_date, signal.knowledge_cutoff, Classification.TEST_ONLY
    )
    assert refs.ranks == {"5": 1} and refs.signals == {"5": signal.state}
    assert (
        refs.annotations == (explanation.annotation(),)
        and refs.risk_snapshot_id == risk.risk_snapshot_id
    )
    past = references(history, "TEST:A", date(2024, 1, 1), clock(1), Classification.TEST_ONLY)
    assert past.signal_ids == () and past.annotations == () and past.ranks == {}
    assert monitoring_history(history, "TEST:A", signal.session_date, signal.knowledge_cutoff)[
        "risk"
    ]


def test_no_known_prices_still_returns_unavailable_snapshot(reader: "CanonicalReader") -> None:
    ledger = append(
        account(), event("OPENING_POSITION", 1, "opening", price="0", declared_cost_basis="1000")
    )
    result = value(ledger, reader, date(2024, 1, 1), clock(1, 3))
    assert result.portfolio_value is None and result.freshness == "UNAVAILABLE"
    assert result.positions[0].accounting.quantity == 10


def test_unknown_basis_is_unavailable_even_with_numeric_price(reader: "CanonicalReader") -> None:
    from alphalens_data.canonical.models import PriceRevision, PriceView
    from alphalens_portfolio.valuation import valid_price

    record = next(r for r in reader.batch.revisions if isinstance(r, PriceRevision) and r.values)
    record = record.model_copy(
        update={"price_basis": "OBSERVED_UNKNOWN_BASIS", "price_basis_evidence": None}
    )
    view = PriceView(
        observation=record,
        quality="VALID",
        availability="AVAILABLE",
        universe_membership=True,
        analysis_eligible=True,
        reason_codes=(),
    )
    assert not valid_price(view)


def test_cli_positions_and_valuation_disclaimer(
    reader: "CanonicalReader",
    tmp_path: "Path",
    monkeypatch: "pytest.MonkeyPatch",
    capsys: "pytest.CaptureFixture[str]",
) -> None:
    import sys

    from alphalens_portfolio.cli import main

    path = save(tmp_path, bought())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphalens-portfolio",
            "positions",
            "--input",
            str(path),
            "--session",
            "2024-01-10",
            "--cutoff",
            "2024-01-10T12:00:00Z",
        ],
    )
    assert main() == 0
    assert "TEST:ALPHA" in capsys.readouterr().out
    monkeypatch.setattr("alphalens_portfolio.cli.canonical", lambda _: reader)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphalens-portfolio",
            "value",
            "--input",
            str(path),
            "--canonical",
            "verified-local-input",
            "--session",
            "2024-01-10",
            "--cutoff",
            "2024-01-10T12:00:00Z",
        ],
    )
    assert main() == 0
    output = capsys.readouterr().out
    assert "TEST_ONLY — NOT A REAL MARKET VALUATION" in output and '"portfolio_value"' in output
