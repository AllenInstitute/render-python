import renderapi


def test_blank_stackversion():
    sv = renderapi.stack.StackVersion()
    der_sv = renderapi.stack.StackVersion(**sv.to_dict())
    fd_sv = renderapi.stack.StackVersion()
    fd_sv.from_dict(sv.to_dict())
    assert(sv.to_dict() == der_sv.to_dict() == fd_sv.to_dict())
