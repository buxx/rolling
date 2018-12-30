# coding: utf-8
import logging
import sys

SERVER_LOGGER_NAME = "server"
GUI_LOGGER_NAME = "gui"
KERNEL_LOGGER_NAME = "kernel"

# Prepare default logger
server_logger = logging.getLogger(SERVER_LOGGER_NAME)
gui_logger = logging.getLogger(GUI_LOGGER_NAME)
kernel_logger = logging.getLogger(KERNEL_LOGGER_NAME)


_stdout_handler = logging.StreamHandler(sys.stdout)
_file_handler = logging.FileHandler("logs.txt")
_formatter = logging.Formatter("%(asctime)s|%(name)s|%(levelname)s: %(message)s")
_stdout_handler.setFormatter(_formatter)
_file_handler.setFormatter(_formatter)
server_logger.addHandler(_stdout_handler)
gui_logger.addHandler(_file_handler)
kernel_logger.addHandler(_stdout_handler)


def configure_logging(log_level: int) -> None:
    """
    Set logging level of current applications
    :param log_level: a logging.XXXX level
    """
    server_logger.setLevel(log_level)
    gui_logger.setLevel(log_level)
    kernel_logger.setLevel(log_level)
