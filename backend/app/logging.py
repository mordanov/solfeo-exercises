import json
import logging
import re
import traceback
from datetime import UTC, datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        event = (
            message
            if record.name.startswith(("app.", "worker."))
            and re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", message)
            else "RUNTIME_MESSAGE"
        )
        data: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
        }
        for name in (
            "method",
            "route",
            "status",
            "duration_ms",
            "job_id",
            "error_code",
            "cell",
        ):
            if name in record.__dict__:
                data[name] = record.__dict__[name]
        if record.exc_info and record.exc_info[0]:
            data["error_type"] = record.exc_info[0].__name__
            data["frames"] = [
                {
                    "file": Path(frame.filename).name,
                    "function": frame.name,
                    "line": frame.lineno,
                }
                for frame in traceback.extract_tb(record.exc_info[2])
            ]
        return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
