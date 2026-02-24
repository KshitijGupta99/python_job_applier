import json
import logging
import sys
from typing import Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        # Merge dict-style messages into the payload for structured logging
        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        return json.dumps(log_record)


_logging_configured = False


def setup_logging(level: str = "INFO") -> None:
    global _logging_configured
    if _logging_configured:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Clear existing handlers to avoid duplicate logs when reloading
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    _logging_configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or __name__)

