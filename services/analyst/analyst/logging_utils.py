import json
import logging
from typing import Any, Dict

from .config import settings


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter compatible with structured log aggregation."""

    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03dZ"

    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.default_time_format),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            log["stack_info"] = record.stack_info

        # Include any custom attributes that may have been injected
        for key, value in record.__dict__.items():
            if key.startswith("_" ):
                continue
            if key in log or key in ("args", "msg", "levelno", "levelname", "name", "created", "msecs", "relativeCreated", "path", "pathname", "filename", "module", "exc_text", "lineno", "funcName", "stack_info", "exc_info", "message", "thread", "threadName", "processName", "process"):
                continue
            log[key] = value

        return json.dumps(log, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logging according to settings."""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Remove any pre-existing handlers so we have deterministic output
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()

    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Ensure FastAPI / Uvicorn loggers inherit the configuration
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").propagate = True

