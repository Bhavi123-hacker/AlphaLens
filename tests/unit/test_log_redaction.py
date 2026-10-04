"""TEST-ONLY sensitive strings demonstrate omission, not real secrets."""

import json
import logging

from alphalens_api.core.logging import SafeJsonFormatter


def test_omit_arbitrary_messages_arguments_and_extras() -> None:
    record = logging.LogRecord(
        "alphalens", logging.ERROR, "TEST_ONLY", 1, "token=%s", ("TEST_ONLY_SECRET",), None
    )
    record.password = "TEST_ONLY_PASSWORD"
    record.request_id = "TEST_ONLY_UNTRUSTED_ID"
    output = SafeJsonFormatter().format(record)
    assert "TEST_ONLY" not in output
    assert json.loads(output)["event"] == "redacted"
    assert json.loads(output)["request_id"] is None


def test_allow_only_event_and_safe_request_fields() -> None:
    record = logging.LogRecord(
        "alphalens", logging.INFO, "TEST_ONLY", 1, "request.completed", (), None
    )
    record.request_id = "00000000-0000-0000-0000-000000000001"
    record.status_code = 503
    record.authorization = "TEST_ONLY_SECRET"
    fields = json.loads(SafeJsonFormatter().format(record))
    assert fields["event"] == "request.completed"
    assert fields["status_code"] == 503
    assert "authorization" not in fields
