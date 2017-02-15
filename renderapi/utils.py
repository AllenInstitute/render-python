#!/usr/bin/env python
'''
utilities to make render/java/web/life interfacing easier
'''
import logging

logger = logging.getLogger(__name__)


def jbool(val):
    '''return string representing java string values of py booleans'''
    if not isinstance(val, bool):
        logger.warning('Evaluating javastring of non-boolean {} {}'.format(
            type(val), val))
    return 'true' if val else 'false'


def stripLogger(logger):
    '''
    remove all handlers from a logger -- useful for redefining
    input:
        logger: logging logger as from logging.getLogger
    '''
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
