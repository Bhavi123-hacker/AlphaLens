"""Explicit TEST_ONLY schedule supplement; no alteration of P5/P9 canonical history."""

import json
from pathlib import Path

from scripts.build_p6_test_fixture import day, instant

from alphalens_backtesting.contracts import (
    BacktestDefinition,
    BenchmarkEvidence,
    CalendarDay,
    CostScenario,
    ExecutionCalendar,
)
from alphalens_backtesting.evidence import ExecutionEvidence
from alphalens_data.canonical.models import CanonicalBatch, SessionRevision
from alphalens_data.canonical.services import CanonicalReader
from alphalens_evaluation.storage import OOSDataset
from alphalens_features.models import FeatureDataset


def execution_evidence(root: Path) -> ExecutionEvidence:
    batch = CanonicalBatch.model_validate(
        json.loads((root / "canonical/canonical-input.json").read_bytes())["batch"]
    )
    features = FeatureDataset.model_validate_json((root / "features.json").read_bytes())
    return ExecutionEvidence(CanonicalReader(batch), features, calendar(batch))


def calendar(batch: CanonicalBatch) -> ExecutionCalendar:
    sessions = sorted(
        (s for s in batch.revisions if isinstance(s, SessionRevision)), key=lambda s: s.session_date
    )
    return ExecutionCalendar(
        canonical_input_id=batch.input_id,
        classification=batch.classification,
        evidence_reference="TEST_ONLY authored artificial schedule; no NSE clock claim",
        days=tuple(
            CalendarDay(
                session_date=s.session_date,
                status=s.status,
                available_at=instant(0, 1),
                open_at=instant((s.session_date - day(0)).days, 4),
                open_clock_policy="EXPLICIT_SESSION_OPEN_CONVENTION",
                evidence_reference="TEST_ONLY 04:00 UTC opening convention; no real exchange clock",
            )
            for s in sessions
        ),
    )


def definition(
    oos: OOSDataset,
    evidence: ExecutionEvidence,
    family: str,
    costs: CostScenario,
    **overrides: object,
) -> BacktestDefinition:
    return BacktestDefinition.model_validate(
        dict(
            evaluation_id=oos.manifest["evaluation_id"],
            oos_prediction_dataset_id=oos.manifest["oos_prediction_dataset_id"],
            canonical_input_id=evidence.reader.batch.input_id,
            feature_set_id=evidence.features.feature_set_id,
            execution_calendar_id=evidence.calendar.calendar_id,
            universe_definition_id=evidence.reader.batch.definition.universe_id,
            model_family=family,
            horizon=oos.manifest["identity"]["definition"]["horizon"],
            start_session=day(52),
            end_session=day(89),
            costs=costs,
            data_classification=evidence.features.classification,
            benchmark=BenchmarkEvidence(
                security_id="TEST:BENCHMARK",
                name="TEST_ONLY_BENCHMARK",
                canonical_input_id=evidence.reader.batch.input_id,
                classification=evidence.features.classification,
                rights_evidence_reference="TEST_ONLY authored values; no real benchmark",
            ),
        )
        | overrides
    )
