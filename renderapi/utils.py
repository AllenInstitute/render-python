#!/usr/bin/env python
'''
utilities to make render/java/web/life interfacing easier
'''
import logging
import json

logger = logging.getLogger(__name__)


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


def _load_dict(obj, d):
    obj.__dict__.update({k: v for k, v in d.items()})


def _load_json(obj, j):
    '''load object from dictionary-style json'''
    with open(j, 'r') as f:
        jd = json.load(f)
    _load_dict(obj, jd)


def defaultifNone(val, default=None):
    return val if val is not None else default
