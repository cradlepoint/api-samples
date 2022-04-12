"""
This file contains sample code to set up a rudimentary logger that sends
formatted text to stdout.

IN REAL LIFE:
You would probably update this to log to a file in a location and
format that is consistent with your other logs.
"""
import logging
import sys


def get_logger():
    """
    :return: python logger object
    """
    logger = logging.getLogger("mysample")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s|%(name)s|%(levelname)s|%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
