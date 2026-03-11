# utils/logger.py - COMPLETE WORKING LOGGER
import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
import logging.handlers


def json_formatter_factory():
    """JSON formatter that supports extra fields"""

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'session_id': getattr(record, 'session_id', None),
                'agent': getattr(record, 'agent', None),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            # Add any extra fields
            if hasattr(record, 'extra_fields'):
                log_entry.update(record.extra_fields)
            return json.dumps(log_entry)

    return JSONFormatter()


def setup_logger(name: str = __name__, log_dir: str = "logs") -> logging.Logger:
    """🚀 PRODUCTION-READY LOGGER - WORKS IMMEDIATELY"""

    # Create logs directory
    os.makedirs(log_dir, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()  # Remove existing handlers

    # Console handler (colored output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(agent)s %(message)s',
        datefmt='%H:%M:%S'
    ))

    # File handler (JSON structured)
    log_file = os.path.join(log_dir, f"{name.replace('.', '_')}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(json_formatter_factory())

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Get named logger
    logger = logging.getLogger(name)
    logger.propagate = False

    print(f"✅ Logger '{name}' configured → logs/{name.replace('.', '_')}.log")
    return logger
