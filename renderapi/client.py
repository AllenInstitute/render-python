#!/usr/bin/env python
'''
render functions relying on render-ws client scripts
'''
import os
import json
from functools import partial
import logging
import subprocess
import tempfile
from .errors import ClientScriptError
from .render import Render, RenderClient
from .stack import set_stack_state, make_stack_params

# setup logger
logger = logging.getLogger(__name__)

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
    logger.debug(cmd)
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    logger.debug(proc.stdout.read())


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
        transformFile: a single json file containing transforms referenced
            in the jsonfiles
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
                             project=project)

    rs = pool.map(partial_import, jsonfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


def import_jsonfiles(stack, jsonfiles, render=None, transformFile=None,
                     client_scripts=None, host=None, port=None,
                     owner=None, project=None, close_stack=True,
                     **kwargs):
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
                **{'close_stack': close_stack,
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
    logger.debug(cmd)
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    logger.debug(proc.stdout.read())
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


# FIXME paperweight for proper render_ws_client implemntation
def import_jsonfiles_validate_client(stack, jsonfiles, render=None,
                                     transformFile=None, client_scripts=None,
                                     host=None, port=None, owner=None,
                                     project=None, close_stack=True, mem=6,
                                     validator=None,
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
    if validator is None:
        validator_params = [
            '--validatorClass',
            'org.janelia.alignment.spec.validator.TemTileSpecValidator',
            '--validatorData',
            'minCoordinate:-500,maxCoordinate:100000,'
            'minSize:500,maxSize:10000']
    else:
        raise NotImplementedError('No custom validation handling!')

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
    logger.debug(cmd)

    subprocess.call(cmd, env=my_env)

    '''
    proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
    proc.wait()
    logger.debug(proc.stdout.read())
    '''
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


def call_run_ws_client(className, add_args=[], renderclient=None,
                       memGB=None, client_script=None, subprocess_mode=None,
                       **kwargs):
    '''
    simple call for run_ws_client.sh -- all arguments set in add_args
    '''
    if renderclient is not None:
        if isinstance(renderclient, RenderClient):
            return call_run_ws_client(className, add_args=add_args,
                                      subprocess_mode=subprocess_mode,
                                      **renderclient.make_kwargs(
                                          memGB=memGB,
                                          client_script=client_script))

    subprocess_modes = {'call': subprocess.call,
                        'check_call': subprocess.check_call,
                        'check_output': subprocess.check_output}
    if subprocess_mode not in subprocess_modes:
        logging.warning(
            'Unknown subprocess mode {} specified -- '
            'using default subprocess.call'.format(subprocess_mode))
    return subprocess_modes.get(
        subprocess_mode, subprocess.call)(
            map(str, [client_script, memGB, className] + add_args))


def get_param(var, flag):
    return ([flag, var] if var is not None else [])


def importJsonClient(stack, tileFiles=None, transformFile=None,
                     subprocess_mode=None,
                     host=None, port=None, owner=None, project=None,
                     client_script=None, memGB=None,
                     render=None, **kwargs):
    '''run ImportJsonClient.java'''
    if render is not None:
        if isinstance(render, Render):
            return importJsonClient(
                stack, tileFiles=tileFiles, transformFile=transformFile,
                subprocess_mode=subprocess_mode, **render.make_kwargs(
                    host=host, port=port, owner=owner, project=project,
                    client_script=client_script, memGB=memGB, **kwargs))
        else:
            raise ValueError('invalid Render object specified!')

    argvs = (make_stack_params(host, port, owner, project, stack) +
             (['--transformFile', transformFile] if transformFile else []) +
             (tileFiles if isinstance(tileFiles, list)
              else [tileFiles]))
    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       add_args=argvs, subprocess_mode=subprocess_mode,
                       client_script=client_script, memGB=memGB)


def tilePairClient(stack, minz, maxz, outjson=None, delete_json=False,
                   baseowner=None, baseproject=None, basestack=None,
                   xyNeighborFactor=None, zNeighborDistance=None,
                   excludeCornerNeighbors=None,
                   excludeCompletelyObscuredTiles=None,
                   excludeSameLayerNeighbors=None,
                   excludeSameSectionNeighbors=None,
                   excludePairsInMatchCollection=None,
                   minx=None, maxx=None, miny=None, maxy=None,
                   subprocess_mode=None,
                   host=None, port=None, owner=None, project=None,
                   client_script=None, memGB=None,
                   render=None, **kwargs):
    '''run TilePairClient.java'''
    if render is not None:
        if isinstance(render, Render):
            return tilePairClient(
                stack, minz, maxz, outjson=outjson, delete_json=delete_json,
                baseowner=baseowner, baseproject=baseproject,
                basestack=basestack,
                xyNeighborFactor=xyNeighborFactor,
                zNeighborDistance=zNeighborDistance,
                excludeCornerNeighbors=excludeCornerNeighbors,
                excludeCompletelyObscuredTiles=excludeCompletelyObscuredTiles,
                excludeSameLayerNeighbors=excludeSameLayerNeighbors,
                excludeSameSectionNeighbors=excludeSameSectionNeighbors,
                excludePairsInMatchCollection=excludePairsInMatchCollection,
                minx=minx, maxx=maxx, miny=miny, maxy=maxy,
                subprocess_mode=subprocess_mode, **render.make_kwargs(
                    host=host, port=port, owner=owner, project=project,
                    client_script=client_script, memGB=memGB, **kwargs))
        else:
            raise ValueError('invalid Render object specified!')

    if outjson is None:
        tempjson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='r', delete=False)
        tempjson.close()
        delete_json = True
        outjson = tempjson.name

    argvs = (make_stack_params(host, port, owner, project, stack) +
             get_param(baseowner, '--baseOwner') +
             get_param(baseproject, '--baseProject') +
             get_param(basestack, '--baseStack') +
             ['--minZ', minz, '--maxZ', maxz] +
             get_param(xyNeighborFactor, '--xyNeighborFactor') +
             get_param(zNeighborDistance, '--zNeighborDistance') +
             get_param(excludeCornerNeighbors, '--excludeCornerNeighbors') +
             get_param(excludeCompletelyObscuredTiles,
                       '--excludeCompletelyObscuredTiles') +
             get_param(excludeSameLayerNeighbors,
                       '--excludeSameLayerNeighbors') +
             get_param(excludeSameSectionNeighbors,
                       '--excludeSameSectionNeighbors') +
             get_param(excludePairsInMatchCollection,
                       '--excludePairsInMatchCollection') +
             ['--toJson', outjson] +
             get_param(minx, '--minX') + get_param(maxx, '--maxX') +
             get_param(miny, '--minY') + get_param(maxy, '--maxY'))

    call_run_ws_client('org.janelia.render.client.TilePairClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode,
                       add_args=argvs)

    with open(outjson, 'r') as f:
        jsondata = json.load(f)

    if delete_json:
        os.remove(outjson)
    return jsondata


def importTransformChangesClient(stack, targetStack, transformFile,
                                 targetOwner=None, targetProject=None,
                                 changeMode=None, subprocess_mode=None,
                                 host=None, port=None, owner=None,
                                 project=None, client_script=None, memGB=None,
                                 render=None, **kwargs):
    '''
    run ImportTransformChangesClient.java
    '''
    if render is not None:
        if isinstance(render, Render):
            return importTransformChangesClient(
                stack, targetStack, transformFile, targetOwner=targetOwner,
                targetProject=targetProject, changeMode=changeMode,
                subprocess_mode=subprocess_mode, **render.make_kwargs(
                    host=host, port=port, owner=owner, project=project,
                    client_script=client_script, memGB=memGB, **kwargs))
        else:
            raise ValueError('invalid Render object specified!')

    if changeMode not in ['APPEND', 'REPLACE_LAST', 'REPLACE_ALL']:
        raise ClientScriptError(
            'changeMode {} is not valid!'.format(changeMode))

    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--stack', stack, '--targetStack', targetStack] +
             ['--transformFile', transformFile] +
             get_param(targetOwner, '--targetOwner') +
             get_param(targetProject, '--targetProject') +
             get_param(changeMode, '--changeMode'))
    call_run_ws_client(
        'org.janelia.render.client.ImportTransformChangesClient', memGB=memGB,
        client_script=client_script, subprocess_mode=subprocess_mode,
        add_args=argv)


def coordinateClient(stack, z, fromJson=None, toJson=None, localToWorld=None,
                     numberOfThreads=None, delete_fromJson=False,
                     delete_toJson=False, subprocess_mode=None,
                     host=None, port=None, owner=None,
                     project=None, client_script=None, memGB=None,
                     render=None, **kwargs):
    '''
    run CoordinateClient.java
    '''
    if render is not None:
        if isinstance(render, Render):
            return coordinateClient(
                stack, z, fromJson=fromJson, toJson=toJson,
                localToWorld=localToWorld, numberOfThreads=numberOfThreads,
                delete_toJson=delete_toJson, delete_fromJson=delete_fromJson,
                subprocess_mode=subprocess_mode, **render.make_kwargs(
                    host=host, port=port, owner=owner, project=project,
                    client_script=client_script, memGB=memGB, **kwargs))
        else:
            raise ValueError('invalid Render object specified!')

    # TODO allow using array as input for mapping
    if toJson is None:
        tempjson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='r', delete=False)
        tempjson.close()
        delete_toJson = True
        toJson = tempjson.name
    if fromJson is None:
        tempjson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='r', delete=False)
        tempjson.write(input_array)
        tempjson.flush()
        tempjson.close()
        delete_fromJson = True
        fromJson = tempjson.name

    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--z', z, '--fromJson', fromJson, '--toJson', toJson] +
             (['--localToWorld', jbool(localToWorld)]
              if localToWorld is not None else []) +
             get_param(numberOfThreads, '--numberOfThreads'))
    call_run_ws_client('org.janelia.render.client.CoordinateClient')

    with open(toJson, 'r') as f:
        jsondata = json.load(f)

    if delete_toJson:
        os.remove(toJson)
    if delete_fromJson:
        os.remove(fromJson)

    return jsondata
