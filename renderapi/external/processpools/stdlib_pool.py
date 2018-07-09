#!/usr/bin/env python
"""
WithPool style helper functions using python's standard library
"""
from multiprocessing.pool import Pool, ThreadPool


class WithThreadPool(ThreadPool):
    def __init__(self, *args, **kwargs):
        super(WithThreadPool, self).__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        self.join()


class WithDummyMapPool:
    map = map

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class WithMultiprocessingPool(Pool):
    """Multiprocessing.pool.Pool with functioning __exit__ call

    Parameters
    ----------
    *args
        variable length argument list matching input
        to multiprocessing.pool.Pool
    **kwargs
        keyword argument input matching multiprocessing.pool.Pool

    Examples
    --------
    >>> with WithMultiprocessingPool(number_processes) as pool:
    >>>     pool.map(myfunc, myInput)
    """

    def __init__(self, *args, **kwargs):
        super(WithMultiprocessingPool, self).__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        self.join()
