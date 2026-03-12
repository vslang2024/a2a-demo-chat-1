import json
import logging
import logging.handlers
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Iterator, Tuple


_CONTEXT_VARS = {
    "session_id": ContextVar("session_id", default=None),
    "agent": ContextVar("agent", default=None),
}
_CONFIGURED = False


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, var in _CONTEXT_VARS.items():
            current = getattr(record, key, None)
            if current not in (None, "", "-"):
                continue
            value = var.get()
            setattr(record, key, value if value else "-")
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", "-"),
            "agent": getattr(record, "agent", "-"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            try:
                log_entry.update(record.extra_fields)
            except Exception:
                pass
        return json.dumps(log_entry)


def _configure_root_logger(log_dir: str | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = log_dir or os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    use_json = _parse_bool(os.getenv("LOG_JSON", ""))
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    json_formatter = JsonFormatter()
    text_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s [session=%(session_id)s agent=%(agent)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter if use_json else text_formatter)

    log_file = os.path.join(log_dir, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setFormatter(json_formatter)

    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)
    file_handler.addFilter(context_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    _CONFIGURED = True


def setup_logger(name: str = __name__, log_dir: str | None = None) -> logging.Logger:
    _configure_root_logger(log_dir)
    return logging.getLogger(name)


def get_logger(name: str = __name__) -> logging.Logger:
    return setup_logger(name)


@contextmanager
def log_context(**kwargs: str) -> Iterator[None]:
    tokens: list[Tuple[ContextVar[str | None], object]] = []
    for key, value in kwargs.items():
        var = _CONTEXT_VARS.get(key)
        if var is None:
            continue
        tokens.append((var, var.set(value)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


logger = setup_logger(__name__)
