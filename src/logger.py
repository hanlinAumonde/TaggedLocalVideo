import sys
from pathlib import Path
from loguru import logger


CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)


def console_filter(record: dict) -> bool:
    """Console filter: Info and Warning levels"""
    return record["level"].name in ("INFO", "WARNING")


def error_filter(record: dict) -> bool:
    """Error file filter: Only allow ERROR and above"""
    return record["level"].no >= logger.level("ERROR").no


def setup_logger(
    log_dir: str | Path = "logs",
    console_format: str = CONSOLE_FORMAT,
    file_format: str = FILE_FORMAT,
    rotation: str = "10 MB",
    retention: str = "30 days",
) -> None:
    """
    Configure the logging system

    Args:
        log_dir: Directory for log files
        console_format: Console output format
        file_format: File output format
        rotation: Log rotation size
        retention: Log retention time
    """
    logger.remove()

    # Ensure the log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        sys.stderr,
        format=console_format,
        level="DEBUG",  # Set minimum level, actual output controlled by filter
        filter=console_filter,
        colorize=True,
    )

    logger.add(
        log_path / "error.log",
        format=file_format,
        level="ERROR",
        filter=error_filter,
        rotation=rotation,
        retention=retention,
        backtrace=True,      # Show full traceback
        diagnose=True,       # Show variable values (set to False in production)
        encoding="utf-8",
    )


def get_logger(name: str = None):
    """
    Get a logger bound with the module name

    Args:
        name: Module name, e.g., "video_stream_resolver"

    Returns:
        Logger instance bound with the module name
    """
    if name:
        return logger.bind(name=name)
    return logger
