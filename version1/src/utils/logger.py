"""Logging configuration using loguru."""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Set up logging for VK Media Downloader with both console and file outputs.
    
    Args:
        log_level: Minimum level to log at ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_file: Optional path to log file (default: logs/vk_media_downloader.log)
    """
    # Remove default logger to configure our own
    logger.remove()
    
    # Console sink with colorized output
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File sink with rotation
    if log_file is None:
        log_file = "logs/vk_media_downloader.log"
        
    Path(log_file).parent.mkdir(exist_ok=True)
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )


# Preconfigured logger instance
setup_logger()