import sys
from loguru import logger

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} {level} {message}", colorize=True)
    # При необходимости можно добавить в файл