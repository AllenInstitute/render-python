import renderapi


def test_jbool():
    assert(renderapi.utils.jbool(True) == 'true')
    assert(renderapi.utils.jbool(False) == 'false')
    assert(renderapi.utils.jbool(0) == 'false')
    assert(renderapi.utils.jbool(1) == 'true')
