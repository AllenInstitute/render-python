from decorator import decorator
import os

from renderapi.errors import ClientScriptError
from renderapi.utils import fitargspec
from renderapi.render import RenderClient, Render


@decorator
def renderclientaccess(f, *args, **kwargs):
    """Decorator allowing functions asking for host, port, owner, project,
    client_script to default to a connection defined by :class:`RenderClient`
    object using its :func:`RenderClient.make_kwargs` method.
    Will also attempt to derive a :class:`RenderClient` from an input
    :class:`Render` object and fail if client scripts cannot be reached.

    Parameters
    ----------
    f : func
        function to decorate
    Returns
    -------
    obj
        output of decorated function
    """
    args, kwargs = fitargspec(f, args, kwargs)
    render = kwargs.get('render')
    if render is not None:
        if not isinstance(render, RenderClient):
            if isinstance(render, Render):
                render = RenderClient(**render.make_kwargs(**kwargs))
            else:
                raise ValueError(
                    'invalid RenderClient object type {} specified!'.format(
                        type(render)))
        return f(*args, **render.make_kwargs(**kwargs))
    else:
        try:
            client_script = kwargs.get('client_script')
            cs_valid = os.path.isfile(client_script)
        except TypeError:
            try:
                client_scripts = kwargs.get('client_scripts')
                if os.path.isdir(client_scripts):
                    client_script = os.path.join(client_scripts,
                                                 'run_ws_client.sh')
                    cs_valid = os.path.isfile(client_script)
                else:
                    raise ClientScriptError(
                        'invalid client_scripts directory {}'.format(
                            client_scripts))
            except TypeError:
                raise ClientScriptError(
                    'No client script information specified: '
                    'client_scripts={} client_script={}'.format(
                        kwargs.get('client_scripts'),
                        kwargs.get('client_script')))
        if not cs_valid:
            # TODO should also check for executability
            raise ClientScriptError(
                'invalid client script: {} not a file'.format(client_script))
    return f(*args, **kwargs)
