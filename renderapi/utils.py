#!/usr/bin/env python
'''
utilities to make render/java/web/life interfacing easier
'''
import logging
import inspect
import copy
import json


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class RenderEncoder(json.JSONEncoder):
    def default(self, obj):
        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            return obj.to_dict()
        else:
            return obj.__dict__


def renderdumps(obj, *args, **kwargs):
    cls_ = kwargs.pop('cls', RenderEncoder)
    return json.dumps(obj, *args, cls=cls_, **kwargs)


def renderdump(obj, *args, **kwargs):
    cls_ = kwargs.pop('cls', RenderEncoder)
    return json.dump(obj, *args, cls=cls_, **kwargs)


def jbool(val):
    '''return string representing java string values of py booleans'''
    if not isinstance(val, bool):
        logger.warning('Evaluating javastring of non-boolean {} {}'.format(
            type(val), val))
    return 'true' if val else 'false'


def stripLogger(logger_tostrip):
    '''
    remove all handlers from a logger -- useful for redefining
    input:
        logger_tostrip: logging logger as from logging.getLogger
    '''
    if logger_tostrip.handlers:
        for handler in logger_tostrip.handlers:
            logger_tostrip.removeHandler(handler)


def defaultifNone(val, default=None):
    return val if val is not None else default


def fitargspec(f, oldargs, oldkwargs):
    ''' fit function argspec given input args tuple and kwargs dict'''
    try:
        args, varargs, keywords, defaults = inspect.getargspec(f)
        num_expected_args = len(args) - len(defaults)
        new_args = tuple(oldargs[:num_expected_args])
        new_kwargs = copy.copy(oldkwargs)
        for i, arg in enumerate(oldargs[num_expected_args:]):
            new_kwargs.update({args[i + num_expected_args]: arg})
        return new_args, new_kwargs
    except Exception as e:
        logger.error('Cannot fit argspec for {}'.format(f))
        logger.error(e)
        return oldargs, oldkwargs
