import logging
from logging.handlers import TimedRotatingFileHandler
from sys import stdout


def create_logger(logger_name):
    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter(
        "%(name)s %(asctime)s %(levelname)s %(message)s")
    logger.setLevel(logging.INFO)
    logger_stdout = logging.StreamHandler(stdout)
    logger_handler_file = TimedRotatingFileHandler(f"./logs/{logger_name}.log",
                                                   when='h',
                                                   interval=24,
                                                   backupCount=3)
    logger_handler_file.setLevel(logging.INFO)
    logger_stdout.setLevel(logging.INFO)
    logger.addHandler(logger_handler_file)
    logger.addHandler(logger_stdout)
    logger_handler_file.setFormatter(formatter)
    logger_stdout.setFormatter(formatter)
    return logger
