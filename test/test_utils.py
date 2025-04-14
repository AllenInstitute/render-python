import importlib
import json
import renderapi
import pytest
import numpy as np
import msgspec

from renderapi.msgspec_json import MsgSpecRenderJson


def cross_py23_reload(module):
    try:
        reload(module)
    except NameError:
        importlib.reload(module)


@pytest.mark.parametrize("use_msgspec", [True, False])
def test_json_load(use_msgspec):
    if not use_msgspec:
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        realimport = builtins.__import__

        def no_msgspec_import(name, globals=None, locals=None,
                              fromlist=(), level=0):
            if 'msgspec' in name:
                raise ImportError
            return realimport(name, globals, locals, fromlist, level)
        builtins.__import__ = no_msgspec_import
    cross_py23_reload(renderapi.utils)
    assert (renderapi.utils.default_json is MsgSpecRenderJson
            if use_msgspec else renderapi.utils.default_json is json)
    assert (
        renderapi.utils.requests.models.complexjson is MsgSpecRenderJson
        if use_msgspec else renderapi.utils.requests.models.complexjson is json)


def test_jbool():
    assert(renderapi.utils.jbool(True) == 'true')
    assert(renderapi.utils.jbool(False) == 'false')
    assert(renderapi.utils.jbool(0) == 'false')
    assert(renderapi.utils.jbool(1) == 'true')


def test_renderdumps_simple():
    s = renderapi.utils.renderdumps({'a': 1})
    assert(s in ['{"a": 1}', '{"a":1}'])

    s = renderapi.utils.renderdumps(5)
    assert(s == '5')


def test_renderdumps_fails():
    with pytest.raises(AttributeError):
        renderapi.utils.renderdumps(np.zeros(3))
