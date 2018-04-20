#!/usr/bin/env python
"""
external processing pool support for Pathos (legacy mode)
"""
from pathos.multiprocessing import ProcessingPool as Pool


class PathosWithPool(Pool):
    def __init__(self, *args, **kwargs):
        super(PathosWithPool, self).__init__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        super(PathosWithPool, self)._clear()


WithPool = PathosWithPool

__all__ = ['PathosWithPool', 'WithPool']
