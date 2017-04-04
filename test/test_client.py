import os
import renderapi
import rendersettings


def test_render_client():
    args = {
        'host': 'renderhost',
        'port': 8080,
        'owner': 'renderowner',
        'project': 'renderproject',
        'client_scripts': '/path/to/client_scripts'
        }
    r = renderapi.render.connect(**args)


def test_default_kwargs(rkwargs=rendersettings.DEFAULT_RENDER, **kwargs):
    r = renderapi.connect(**dict(rkwargs, **kwargs))
    new_r = renderapi.connect(**dict(r.DEFAULT_KWARGS, **kwargs))
    assert(new_r.DEFAULT_KWARGS == r.DEFAULT_KWARGS == rkwargs)


def test_default_kwargs_client():
    test_default_kwargs(rkwargs=rendersettings.DEFAULT_RENDER_CLIENT,
                        validate_client=False)


def test_environment_variables(
        rkwargs=rendersettings.DEFAULT_RENDER,
        renvkwargs=rendersettings.DEFAULT_RENDER_ENVIRONMENT_VARIABLES):
    def valstostring(d):
        return {k: str(v) for k, v in d.items()}
    old_env = os.environ.copy()
    os.environ.update(valstostring(renvkwargs))

    env_render = renderapi.connect()

    # restore environment
    os.environ.clear()
    os.environ.update(old_env)

    kwarg_render = renderapi.connect(**valstostring(rkwargs))
    assert(valstostring(kwarg_render.DEFAULT_KWARGS) ==
           valstostring(env_render.DEFAULT_KWARGS) ==
           valstostring(rkwargs))


'''
def test_environment_variables_client():
    test_environment_variables(rkwargs=rendersettings.DEFAULT_RENDER_CLIENT)
'''
