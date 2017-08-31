import os
import renderapi
import rendersettings

args = {
    'host': 'renderhost',
    'port': 8080,
    'owner': 'renderowner',
    'project': 'renderproject',
    'client_scripts': '/path/to/client_scripts'
    }
def test_render_client():
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
        renvkwargs=rendersettings.DEFAULT_RENDER_ENVIRONMENT_VARIABLES,
        **kwargs):
    def valstostring(d):
        return {k: str(v) for k, v in d.items()}
    old_env = os.environ.copy()
    os.environ.update(valstostring(renvkwargs))

    env_render = renderapi.connect(**kwargs)

    # restore environment
    os.environ.clear()
    os.environ.update(old_env)

    kwarg_render = renderapi.connect(**dict(valstostring(rkwargs), **kwargs))
    assert(valstostring(kwarg_render.DEFAULT_KWARGS) ==
           valstostring(env_render.DEFAULT_KWARGS) ==
           valstostring(rkwargs))


def test_environment_variables_client():
    test_environment_variables(
        rkwargs=rendersettings.DEFAULT_RENDER_CLIENT,
        renvkwargs=rendersettings.DEFAULT_RENDER_CLIENT_ENVIRONMENT_VARIABLES,
        validate_client=False)

@renderapi.render.renderaccess
def my_decorated(myparameter, owner=None, host=None, port=None,
              project=None,client_scripts=None, **kwargs):
    return (owner,host,port,project,client_scripts)

def test_decorator():
    r = renderapi.render.connect(**args)
    (owner,host,port,project,client_scripts)=my_decorated(5,render=r)
    assert(owner == args['owner'])
    (owner,host,port,project,client_scripts)=my_decorated(5,owner='newowner',render=r)
    assert(owner == 'newowner')  
