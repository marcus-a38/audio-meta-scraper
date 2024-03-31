from __future__ import annotations

import logging
import logging.handlers
import sys

MEBIBYTE = 1024**2

date_format = "%Y-%m-%d @ %H:%M:%S"
file_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt=date_format
)
stream_format = logging.Formatter(
    "[%(levelname)s] %(message)s", datefmt=date_format
)

INFO = 20
WARNING = 30
DEBUG = 10


def logger_setup(filepath: Path, silent=False) -> None:
    """Setups up a logger to handle queued or normal logs."""

    # For some reason, logging 'w' mode won't overwrite. This line ensures
    # that the log will be fresh for each sift & store.
    with open(filepath, "w") as tmp:
        tmp.close()

    h = []

    # Maximum of 5 logs, 10 MiB in size at a time.
    file_handler = logging.handlers.RotatingFileHandler(
        filename=filepath, maxBytes=10 * MEBIBYTE, backupCount=5
    )
    file_handler.setFormatter(file_format)

    h.append(file_handler)

    # Log to stdout if silent mode is NOT enabled
    if not silent:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(stream_format)
        h.append(stream_handler)

    logging.basicConfig(
        level=logging.INFO,
        handlers=h,
        force=True,
    )


def listen(queue: Queue, filepath: Path, silent=False) -> None:
    """Creates a log listener for all processes.
     
    Pulls from the log queue and logs to file and/or stdout (toggled by silent).
    """
    logger_setup(filepath, silent)

    while True:

        record = queue.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def configure_logger(queue: Queue) -> None:
    """Configures and establishes a unique logger for a given process.
    
    Each logger uses a QueueHandler to log to the active multiprocessing Queue.
    MetaSift spawns an extra process (two workers total) for efficient I/O.
    Each file produces some log output, so a Queue is necessary to prevent race
    conditions in the logging system.
    """
    root = logging.getLogger()

    if root.handlers:
        return
    
    qh = logging.handlers.QueueHandler(queue)
    root.addHandler(qh)
    root.setLevel(logging.INFO)


def write_log(level, msg):
    """Encapsulates logging.log(); logs a message with given log level."""
    logging.log(level, msg)


def cleanup():
    """Encapsulates logging.shutdown(); performs cleanup on logging system."""
    logging.shutdown()
