#!/usr/bin/env python
'''
Custom errors for render api
'''


class ClientScriptError(Exception):
    pass


class ConversionError(Exception):
    pass


class EstimationError(Exception):
    pass


class SpecError(Exception):
    pass
