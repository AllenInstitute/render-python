import renderapi
import pytest
import numpy as np

def test_jbool():
    assert(renderapi.utils.jbool(True) == 'true')
    assert(renderapi.utils.jbool(False) == 'false')
    assert(renderapi.utils.jbool(0) == 'false')
    assert(renderapi.utils.jbool(1) == 'true')

def test_renderdumps_simple():
    s=renderapi.utils.renderdumps({'a':1})
    assert(s=='{"a": 1}')

    s=renderapi.utils.renderdumps(5)
    assert(s=='5')

def test_renderdumps_fails():
    with pytest.raises(AttributeError):
        renderapi.utils.renderdumps(np.zeros(3))