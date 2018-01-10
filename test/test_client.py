import os
import pytest
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
def renderaccess_decorated(myparameter, owner=None, host=None, port=None,
                           project=None, client_scripts=None, **kwargs):
    return (owner, host, port, project, client_scripts)


@renderapi.client.renderclientaccess
def renderclientaccess_decorated(myparameter, owner=None, host=None,
                                 port=None, project=None,
                                 client_scripts=None, client_script=None,
                                 **kwargs):
    return (owner, host, port, project, client_scripts, client_script)


def test_decorator(my_decorated=renderaccess_decorated):
    r = renderapi.render.connect(**args)
    (owner, host, port, project, client_scripts) = my_decorated(5, render=r)
    assert(owner == args['owner'])
    (owner, host, port, project, client_scripts) = my_decorated(
        5, owner='newowner', render=r)
    assert(owner == 'newowner')


def test_renderaccess_decorator(tmpdir):
    def checkexpected(expectation, values):
        return all([i == j for i, j in zip(expectation, values)])

    newargs = dict(args, **{'client_scripts': str(tmpdir)})

    assert not os.path.isfile(
        renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)))

    expected = (newargs['owner'], newargs['host'], newargs['port'],
                newargs['project'], newargs['client_scripts'],
                renderapi.render.RenderClient.clientscript_from_clientscripts(
                    newargs['client_scripts']))

    with open(renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)), 'w') as f:
        # test that renderclientaccess decorated funtion works with Render
        #     objects missing client_script
        assert checkexpected(expected, renderclientaccess_decorated(
            5, render=renderapi.render.Render(**newargs)))
        # test that RenderClient objects continue to work
        assert checkexpected(expected, renderclientaccess_decorated(
            5, render=renderapi.render.RenderClient(**newargs)))
        # test with renderapi.connect set RenderObjects
        assert checkexpected(expected, renderclientaccess_decorated(
            5, render=renderapi.connect(force_http=False, **newargs)))

    os.remove(renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)))


def test_renderclientaccess_decorator_fail(tmpdir):
    # test that common methods of defining renderclient options fail quickly
    newargs = dict(args, **{'client_scripts': str(tmpdir)})

    assert not os.path.isfile(
        renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)))

    with pytest.raises(renderapi.errors.ClientScriptError):
        _ = renderclientaccess_decorated(
            5, render=renderapi.render.Render(**newargs))

    with pytest.raises(renderapi.errors.ClientScriptError):
        _ = renderclientaccess_decorated(
            5, render=renderapi.render.RenderClient(**newargs))

    with pytest.raises(renderapi.errors.ClientScriptError):
        _ = renderclientaccess_decorated(
            5, render=renderapi.connect(force_http=False, **newargs))


def test_renderclientaccess_override(tmpdir):
    def checkexpected(expectation, values):
        return all([i == j for i, j in zip(expectation, values)])

    newargs = dict(args, **{'client_scripts': str(tmpdir)})

    assert not os.path.isfile(
        renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)))

    expected = ('newowner', newargs['host'], newargs['port'],
                newargs['project'], newargs['client_scripts'],
                renderapi.render.RenderClient.clientscript_from_clientscripts(
                    newargs['client_scripts']))

    with open(renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)), 'w') as f:
        # test that renderclientaccess decorated funtion works with Render
        #     objects missing client_script
        assert checkexpected(expected, renderclientaccess_decorated(
            5, owner='newowner', render=renderapi.render.Render(**newargs)))
        # test that RenderClient objects continue to work
        assert checkexpected(expected, renderclientaccess_decorated(
            5, owner='newowner',
            render=renderapi.render.RenderClient(**newargs)))
        # test with renderapi.connect set RenderObjects
        assert checkexpected(expected, renderclientaccess_decorated(
            5, owner='newowner',
            render=renderapi.connect(force_http=False, **newargs)))

    os.remove(renderapi.render.RenderClient.clientscript_from_clientscripts(
            str(tmpdir)))
