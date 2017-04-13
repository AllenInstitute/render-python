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
from .utils import renderdump, NullHandler
from .errors import ClientScriptError
from .render import RenderClient, renderaccess
from .stack import set_stack_state, make_stack_params
from pathos.multiprocessing import ProcessingPool as Pool

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


@renderaccess
def import_single_json_file(stack, jsonfile, transformFile=None,
                            client_scripts=None, host=None, port=None,
                            owner=None, project=None, render=None, **kwargs):
    '''
    calls client script to import given jsonfile:
        transformFile: ?
    '''
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


@renderaccess
def import_jsonfiles_and_transforms_parallel_by_z(
        stack, jsonfiles, transformfiles, poolsize=20,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, render=None, **kwargs):
    '''
    imports json files and transform files in parallel:
        jsonfiles: "list of tilespec" jsons to import
        transformfiles: ?
        poolsize: number of processes for multiprocessing pool
        close_stack: mark render stack as COMPLETE after successful import
    '''
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(import_single_json_file, stack, render=render,
                             client_scripts=client_scripts, host=host,
                             port=port, owner=owner, project=project)
    rs = pool.amap(partial_import, jsonfiles, transformfiles)
    rs.wait()
    pool.close()
    pool.join()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles_parallel(
        stack, jsonfiles, poolsize=20, transformFile=None,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, render=None, **kwargs):
    '''
    import jsons using client script in parallel
        jsonfiles: list of jsonfiles to upload
        poolsize: number of upload processes spawned by multiprocessing pool
        transformFile: a single json file containing transforms referenced
            in the jsonfiles
    '''
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(import_single_json_file, stack, render=render,
                             transformFile=transformFile,
                             client_scripts=client_scripts,
                             host=host, port=port, owner=owner,
                             project=project)

    pool.map(partial_import, jsonfiles)
    pool.close()
    pool.join()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles(stack, jsonfiles, transformFile=None,
                     client_scripts=None, host=None, port=None,
                     owner=None, project=None, close_stack=True,
                     render=None, **kwargs):
    '''
    import jsons using client script serially
        jsonfiles: iterator of filenames to be uploaded
        transformFile: ?
        close_stack: ?
    '''
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


@renderaccess
def import_jsonfiles_validate_client(stack, jsonfiles,
                                     transformFile=None, client_scripts=None,
                                     host=None, port=None, owner=None,
                                     project=None, close_stack=True, mem=6,
                                     validator=None,
                                     render=None, **kwargs):
    '''
    Uses java client for parallelization and validation
    '''
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


@renderaccess
def import_tilespecs(stack, tilespecs, sharedTransforms=None,
                     subprocess_mode=None, host=None, port=None,
                     owner=None, project=None, client_script=None,
                     memGB=None, render=None, **kwargs):
    '''
    input:
         stack -- stack to which tilespecs will be added
         tilespecs -- list of tilespecs
         sharedTransforms -- list of shared
             referenced transforms to be ingested
    '''
    tempjson = tempfile.NamedTemporaryFile(
        suffix=".json", mode='r', delete=False)
    tempjson.close()
    tsjson = tempjson.name
    with open(tsjson, 'w') as f:
        renderdump(tilespecs, f)

    if sharedTransforms is not None:
        tempjson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='r', delete=False)
        tempjson.close()
        trjson = tempjson.name
        with open(trjson, 'w') as f:
            renderdump(sharedTransforms, f)
    importJsonClient(stack, tileFiles=[tsjson], transformFile=(
                         trjson if sharedTransforms is not None else None),
                     subprocess_mode=subprocess_mode, host=host, port=port,
                     owner=owner, project=project,
                     client_script=client_script, memGB=memGB)

    os.remove(tsjson)
    if sharedTransforms is not None:
        os.remove(trjson)


@renderaccess
def import_tilespecs_parallel(stack, tilespecs, sharedTransforms=None,
                              subprocess_mode=None, poolsize=20,
                              close_stack=True, host=None, port=None,
                              owner=None, project=None,
                              client_script=None, memGB=None, render=None,
                              **kwargs):
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    pool = Pool(poolsize)
    partial_import = partial(
        import_tilespecs, stack, sharedTransforms=sharedTransforms,
        subprocess_mode=subprocess_mode, host=host, port=port,
        owner=owner, project=project, client_script=client_script,
        memGB=memGB, **kwargs)

    # TODO this is a weird way to do splits.... is that okay?
    tilespec_groups = [tilespecs[i::poolsize] for i in xrange(poolsize)]
    pool.map(partial_import, tilespec_groups)
    pool.close()
    pool.join()
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


# TODO handle fromJson and toJson persistence in these calls
@renderaccess
def local_to_world_array(stack, points, tileId, subprocess_mode=None,
                         host=None, port=None, owner=None, project=None,
                         client_script=None, memGB=None,
                         render=None, **kwargs):
    '''
    placeholder function for coordinateClient localtoworld

    inputs:
        stack -- stack to which world coordinates are mapped
        points -- local points to map to world
        tileId -- tileId to which points correspond
    outputs:
        list of points in world coordinates corresponding to local points
    '''
    raise NotImplementedError('Whoops')


@renderaccess
def world_to_local_array(stack, points, subprocess_mode=None,
                         host=None, port=None, owner=None, project=None,
                         client_script=None, memGB=None,
                         render=None, **kwargs):
    '''
    placeholder function for coordinateClient worldtolocal

    inputs:
        stack -- stack to which world coordinates are mapped
        points -- world points in stack to map to local
    outputs:
        list of list of dictionaries defining local coordinates
            and tileIds corresponding to world point
    '''
    raise NotImplementedError('Whoops.')


def call_run_ws_client(className, add_args=[], renderclient=None,
                       memGB=None, client_script=None, subprocess_mode=None,
                       **kwargs):
    '''
    simple call for run_ws_client.sh -- all arguments set in add_args
    '''
    logger.debug('call_run_ws_client -- classname:{} add_args:{} '
                 'client_script:{} memGB:{}'.format(
                     className, add_args, client_script, memGB))

    if renderclient is not None:
        if isinstance(renderclient, RenderClient):
            return call_run_ws_client(className, add_args=add_args,
                                      subprocess_mode=subprocess_mode,
                                      **renderclient.make_kwargs(
                                          memGB=memGB,
                                          client_script=client_script))
    if memGB is None:
        logger.warning('call_run_ws_client requires memory specification -- '
                       'defaulting to 1G')
        memGB = '1G'

    subprocess_modes = {'call': subprocess.call,
                        'check_call': subprocess.check_call,
                        'check_output': subprocess.check_output}
    if subprocess_mode not in subprocess_modes:
        logger.warning(
            'Unknown subprocess mode {} specified -- '
            'using default subprocess.call'.format(subprocess_mode))
    return subprocess_modes.get(
        subprocess_mode, subprocess.call)(
            map(str, [client_script, memGB, className] + add_args))


def get_param(var, flag):
    return ([flag, var] if var is not None else [])


@renderaccess
def importJsonClient(stack, tileFiles=None, transformFile=None,
                     subprocess_mode=None,
                     host=None, port=None, owner=None, project=None,
                     client_script=None, memGB=None,
                     render=None, **kwargs):
    '''run ImportJsonClient.java'''
    argvs = (make_stack_params(host, port, owner, project, stack) +
             (['--transformFile', transformFile] if transformFile else []) +
             (tileFiles if isinstance(tileFiles, list)
              else [tileFiles]))
    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       add_args=argvs, subprocess_mode=subprocess_mode,
                       client_script=client_script, memGB=memGB)


@renderaccess
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


@renderaccess
def importTransformChangesClient(stack, targetStack, transformFile,
                                 targetOwner=None, targetProject=None,
                                 changeMode=None, subprocess_mode=None,
                                 host=None, port=None, owner=None,
                                 project=None, client_script=None, memGB=None,
                                 render=None, **kwargs):
    '''
    run ImportTransformChangesClient.java
    '''
    if changeMode not in ['APPEND', 'REPLACE_LAST', 'REPLACE_ALL']:
        raise ClientScriptError(
            'changeMode {} is not valid!'.format(changeMode))

    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--targetStack', targetStack] +
             ['--transformFile', transformFile] +
             get_param(targetOwner, '--targetOwner') +
             get_param(targetProject, '--targetProject') +
             get_param(changeMode, '--changeMode'))
    call_run_ws_client(
        'org.janelia.render.client.ImportTransformChangesClient', memGB=memGB,
        client_script=client_script, subprocess_mode=subprocess_mode,
        add_args=argvs)


@renderaccess
def coordinateClient(stack, z, fromJson=None, toJson=None, localToWorld=None,
                     numberOfThreads=None, subprocess_mode=None,
                     host=None, port=None, owner=None,
                     project=None, client_script=None, memGB=None,
                     render=None, **kwargs):
    '''
    run CoordinateClient.java
    expects:
        fromJson -- json in format defined by list of
            coordinate dictionaries (world) or
            list of list of coordinate dictionaries (local)
        toJson -- json to save results of mapping
        localToWorld -- flag defaults to accepting world coordinates
        numberOfThreads -- java-based threads for client script
    '''
    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--z', z, '--fromJson', fromJson, '--toJson', toJson] +
             (['--localToWorld'] if localToWorld else []) +
             get_param(numberOfThreads, '--numberOfThreads'))
    call_run_ws_client('org.janelia.render.client.CoordinateClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs)

    with open(toJson, 'r') as f:
        jsondata = json.load(f)

    return jsondata


@renderaccess
def renderSectionClient(stack, rootDirectory, zs, scale=None, format=None,
                        doFilter=None, fillWithNoise=None,
                        subprocess_mode=None, host=None, port=None, owner=None,
                        project=None, client_script=None, memGB=None,
                        render=None, **kwargs):
    '''
    run RenderSectionClient.java
    '''
    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--rootDirectory', rootDirectory] +
             get_param(scale, '--scale') + get_param(format, '--format') +
             get_param(doFilter, '--doFilter') +
             get_param(fillWithNoise, '--fillWithNoise') + zs)
    call_run_ws_client('org.janelia.render.client.RenderSectionClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs)
