import json
from functools import partial
import logging
import subprocess
from renderapi.render import Render  # TODO make relative for final
from renderapi.stack import set_stack_state, make_stack_params

try:
    from pathos.multiprocessing import ProcessingPool as Pool
    has_pathos = True
except ImportError as e:
    logging.warning(e)
    has_pathos = False
    from multiprocessing import Pool


def import_single_json_file(stack, jsonfile, render=None, transformFile=None,
                            client_scripts=None, host=None, port=None,
                            owner=None, project=None, verbose=False, **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        import_single_json_file(stack, jsonfile, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            client_scripts=client_scripts, **{'verbose': verbose,
                                              'transformFile': None}))
        return
    if transformFile is None:
        transform_params = []
    else:
        transform_params = ['--transformFile', transformFile]
    my_env = os.environ.copy()
    stack_params = make_stack_params(
        host, port, owner, project, stack)
    cmd = [os.path.join(client_scripts, 'import_json.sh')] + \
        stack_params + \
        transform_params + \
        [jsonfile]
    if verbose:
        print cmd
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    if verbose:
        print proc.stdout.read()


def import_jsonfiles_and_transforms_parallel_by_z(
        stack, jsonfiles, transformfiles, render=None, poolsize=20,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, verbose=False, **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        import_jsonfiles_and_transforms_parallel_by_z(
            stack, jsonfile, transformfiles, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_scripts=client_scripts, **{'verbose': verbose,
                                                  'close_stack': close_stack,
                                                  'poolsize': poolsize}))
        return
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(import_single_json_file, stack, render=render,
                             client_scripts=client_scripts, host=host,
                             port=port, owner=owner, project=project,
                             verbose=verbose)
    rs = pool.amap(partial_import, jsonfiles, transformfiles)
    rs.wait()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


def import_jsonfiles_parallel(
        stack, jsonfiles, render=None, poolsize=20, transformFile=None,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, verbose=False, **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        import_jsonfiles_parallel(
            stack, jsonfiles, **render.make_kwargs(
                host=host, port=port, owner=owner,
                project=project, client_scripts=client_scripts,
                **{'verbose': verbose,
                   'close_stack': close_stack,
                   'poolsize': poolsize,
                   'transformFile': transformFile}))
        return
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(import_single_json_file, stack, render=render,
                             transformFile=transformFile,
                             client_scripts=client_scripts,
                             host=host, port=port, owner=owner,
                             project=project, verbose=verbose)
    partial_import(jsonfiles[0])
    rs = pool.amap(partial_import, jsonfiles)
    rs.wait()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


def import_jsonfiles(stack, jsonfiles, render=None, transformFile=None,
                     client_scripts=None, host=None, port=None,
                     owner=None, project=None, close_stack=True,
                     verbose=False, **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        import_jsonfiles(
            stack, jsonfiles, **render.make_kwargs(
                host=host, port=port, owner=owner,
                project=project, client_scripts=client_scripts,
                **{'verbose': verbose,
                   'close_stack': close_stack,
                   'transformFile': transformFile}))
        return

    set_stack_state(stack, 'LOADING', host, port, owner, project)
    if transformFile is None:
        transform_params = []
    else:
        transform_params = ['--transformFile', transformFile]
    my_env = os.environ.copy()
    stack_params = make_stack_params(
        host, port, owner, project, stack)
    cmd = [os.path.join(client_scripts, 'import_json.sh')] + \
        stack_params + \
        transform_params + \
        jsonfiles
    if verbose:
        print cmd
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    if verbose:
        print proc.stdout.read()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)
