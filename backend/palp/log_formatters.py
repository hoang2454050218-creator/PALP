import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production log aggregation."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)
