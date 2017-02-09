#!/usr/bin/env python
'''
utilities to make render/java/web interfacing easier
'''
import logging


def jbool(val):
    '''return string representing json string values of py booleans'''
    return 'true' if val else 'false'


def stripLogger(logger):
    '''remove all handlers from a logger -- useful for redefining'''
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
