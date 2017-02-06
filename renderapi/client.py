#!/usr/bin/env python
'''
render functions relying on render-ws client scripts
'''
import json
from functools import partial
import logging
import subprocess
from .render import Render
from .stack import set_stack_state, make_stack_params

try:
    from pathos.multiprocessing import ProcessingPool as Pool
    has_pathos = True
except ImportError as e:
    logging.warning(e)
    has_pathos = False
    from multiprocessing import Pool


def import_single_json_file(stack, jsonfile, render=None, transformFile=None,
                            client_scripts=None, host=None, port=None,
                            owner=None, project=None, **kwargs):
    '''
    calls client script to import given jsonfile:
        transformFile: ?
    '''
    # process render-based default configuration
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return import_single_json_file(stack, jsonfile, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            client_scripts=client_scripts, **{'transformFile': None}))

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
    logging.debug(cmd)
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    logging.debug(proc.stdout.read())


def import_jsonfiles_and_transforms_parallel_by_z(
        stack, jsonfiles, transformfiles, render=None, poolsize=20,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, **kwargs):
    '''
    imports json files and transform files in parallel:
        jsonfiles: "list of tilespec" jsons to import
        transformfiles: ?
        poolsize: number of processes for multiprocessing pool
        close_stack: mark render stack as COMPLETE after successful import
    '''
    # process render-based default configuration
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return import_jsonfiles_and_transforms_parallel_by_z(
            stack, jsonfile, transformfiles, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_scripts=client_scripts, **{'close_stack': close_stack,
                                                  'poolsize': poolsize}))

    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(import_single_json_file, stack, render=render,
                             client_scripts=client_scripts, host=host,
                             port=port, owner=owner, project=project)
    rs = pool.amap(partial_import, jsonfiles, transformfiles)
    rs.wait()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


def import_jsonfiles_parallel(
        stack, jsonfiles, render=None, poolsize=20, transformFile=None,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, **kwargs):
    '''
    import jsons using client script in parallel
        jsonfiles: list of jsonfiles to upload
        poolsize: number of upload processes spawned by multiprocessing pool
        transformFile: ?
    '''
    # process render-based default configuration
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return import_jsonfiles_parallel(
            stack, jsonfiles, **render.make_kwargs(
                host=host, port=port, owner=owner,
                project=project, client_scripts=client_scripts,
                **{'close_stack': close_stack,
                   'poolsize': poolsize, 'transformFile': transformFile}))

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
    '''
    import jsons using client script serially
        jsonfiles: iterator of filenames to be uploaded
        transformFile: ?
        close_stack: ?
    '''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return import_jsonfiles(
            stack, jsonfiles, **render.make_kwargs(
                host=host, port=port, owner=owner,
                project=project, client_scripts=client_scripts,
                **{'verbose': verbose, 'close_stack': close_stack,
                   'transformFile': transformFile}))

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


# FIXME paperweight for proper render_ws_client implemntation
# TODO this should allow you to set validator parameters
def import_jsonfiles_validate_client(stack, jsonfiles, render=None,
                                     transformFile=None, client_scripts=None,
                                     host=None, port=None, owner=None,
                                     project=None, close_stack=True, mem=6,
                                     **kwargs):
    '''
    Uses java client for parallelization and validation
    '''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return import_jsonfiles_validate_client(
            stack, jsonfiles, **render.make_kwargs(
                host=host, port=port, owner=owner,
                project=project, client_scripts=client_scripts,
                **{'close_stack': close_stack, 'mem': mem,
                   'transformFile': transformFile}))

    transform_params = (['--transformFile', transformFile]
                        if transformFile is not None else [])
    validator_params = [
        '--validatorClass',
        'org.janelia.alignment.spec.validator.TemTileSpecValidator',
        '--validatorData',
        'minCoordinate:-500,maxCoordinate:50000,minSize:500,maxSize:10000']
    my_env = os.environ.copy()
    stack_params = make_stack_params(host, port, owner, project, stack)
    cmd = [os.path.join(client_scripts, 'run_ws_client.sh')] + \
        ['{}G'.format(str(int(mem))),
         'org.janelia.render.client.ImportJsonClient'] + \
        stack_params + \
        validator_params + \
        transform_params + \
        jsonfiles

    set_stack_state(stack, 'LOADING', host, port, owner, project)
    logging.debug(cmd)

    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    logging.debug(proc.stdout.read())

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)
