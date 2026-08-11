import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "client_ip"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()

    if not settings.LOG_ENABLED:
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.CRITICAL + 1)
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("sqlalchemy.engine").setLevel(level if settings.LOG_SQL_ENABLED else logging.WARNING)
    logging.getLogger("uvicorn.access").disabled = not settings.LOG_UVICORN_ACCESS_ENABLED
