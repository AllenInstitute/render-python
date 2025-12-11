import io
import msgspec
import numpy
from typing import Any, Type


def is_binary(f):
    return isinstance(f, (io.RawIOBase, io.BufferedIOBase))


def render_encode_hook(obj: Any) -> Any:
    if isinstance(obj, numpy.integer):
        return int(obj)
    if isinstance(obj, numpy.floating):
        return float(obj)
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return obj.to_dict()
    else:
        try:
            return dict(obj)
        except TypeError as e:
            return obj.__dict__

render_enc = msgspec.json.Encoder(enc_hook=render_encode_hook)


class MsgSpecRenderJson:
    @staticmethod
    def loads(j, *args, **kwargs):
        return msgspec.json.decode(j)

    @staticmethod
    def dumps(o, *args, **kwargs):
        return render_enc.encode(o).decode()

    @staticmethod
    def dump(o, fp, *args, **kwargs):
        if is_binary(fp):
            fp.write(render_enc.encode(o))
        else:
            fp.write(render_enc.encode(o).decode())

    @staticmethod
    def load(fp, *args, **kwargs):
        if is_binary(fp):
            msgspec.json.decode(fp.read())
        else:
           msgspec.json.decode(fp.read())
