import logging
import sys
from pathlib import Path


_LOG_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    handler: logging.Handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger("openrtl")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"openrtl.{name}")
