#!/usr/bin/env python
'''
Custom errors for render api
'''


class RenderError(Exception):
    pass


class ClientScriptError(RenderError):
    pass


class ConversionError(RenderError):
    pass


class EstimationError(RenderError):
    pass


class SpecError(RenderError):
    pass
