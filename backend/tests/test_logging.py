import json
import logging
from io import StringIO

from app.logging import JsonFormatter


def test_json_logs_have_stable_fields_and_no_interpolated_secrets() -> None:
    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        __file__,
        1,
        "HTTP Request: https://api.telegram.org/bot%s/getUpdates?token=secret",
        ("private-token",),
        None,
    )
    result = JsonFormatter().format(record)
    data = json.loads(result)
    assert data["event"] == "RUNTIME_MESSAGE"
    assert data["level"] == "INFO"
    assert data["logger"] == "httpx"
    assert data["timestamp"].endswith("+00:00")
    assert "private-token" not in result and "secret" not in result


def test_request_logging_only_accepts_known_structured_fields() -> None:
    record = logging.LogRecord(
        "app.requests", logging.INFO, __file__, 1, "HTTP_REQUEST", (), None
    )
    record.method = "GET"
    record.route = "/api/exercises/{identifier}"
    record.status = 403
    record.duration_ms = 4.5
    record.password = "private-password"
    data = json.loads(JsonFormatter().format(record))
    assert data["event"] == "HTTP_REQUEST"
    assert data["route"] == "/api/exercises/{identifier}"
    assert data["status"] == 403
    assert "password" not in data


def test_worker_failures_log_error_code_and_cell_but_not_other_extras() -> None:
    record = logging.LogRecord(
        "worker.generate_avatar",
        logging.ERROR,
        __file__,
        1,
        "AVATAR_JOB_FAILED",
        (),
        None,
    )
    record.job_id = 1
    record.error_code = "AVATAR_SHEET_INVALID"
    record.cell = "level=3 state=sad"
    record.description = "private description"
    data = json.loads(JsonFormatter().format(record))
    assert data["error_code"] == "AVATAR_SHEET_INVALID"
    assert data["cell"] == "level=3 state=sad"
    assert "description" not in data


def test_exception_logs_keep_type_and_location_without_values() -> None:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("app.test_json")
    logger.addHandler(handler)
    try:
        try:
            raise ValueError("private-password")
        except ValueError:
            logger.exception("REQUEST_FAILED")
        value = json.loads(output.getvalue())
        assert value["error_type"] == "ValueError"
        assert (
            value["frames"][-1]["function"]
            == "test_exception_logs_keep_type_and_location_without_values"
        )
        assert "private-password" not in output.getvalue()
    finally:
        logger.removeHandler(handler)
