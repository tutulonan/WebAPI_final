import logging
from colorlog import ColoredFormatter
import sys


def setup_colored_logging():
    formatter = ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(name)s%(reset)s | %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # Настраиваем консольный хендлер
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Применяем ко всем логгерам
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Убираем стандартные хендлеры uvicorn
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler != handler:
            root_logger.removeHandler(handler)