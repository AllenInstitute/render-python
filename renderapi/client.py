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
from .utils import NullHandler, renderdump_temp
from .render import RenderClient, renderaccess
from .stack import set_stack_state, make_stack_params
from pathos.multiprocessing import ProcessingPool as Pool

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class WithPool(Pool):
    '''
    pathos ProcessingPool with functioning __exit__ call
    usage:
        with WithPool(*poolargs, **poolkwargs) as pool:
            pool.map(*mapargs, **mapkwargs)
    '''
    def __init__(self, *args, **kwargs):
        super(WithPool, self).__init__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        super(WithPool, self)._clear()


@renderaccess
def import_single_json_file(stack, jsonfile, transformFile=None,
                            client_scripts=None, host=None, port=None,
                            owner=None, project=None, render=None, **kwargs):
    '''
    calls client script to import given jsonfile

    Args:
        stack (str): stack to import into
        jsonfile (str): path to jsonfile to import
        transformFile (str): path to a file that contains shared
            transform references if necessary
        render (renderapi.render.RenderClient): render connect object
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
    imports json files and transform files in parallel

    Args:
        stack (str): the stack to import within
        jsonfiles (list[str]): "list of tilespec" json paths to import
        transformfiles (list[str]): "list of transform files" paths which matches
            in a 1-1 way with jsonfiles, so referenced transforms
            are shared only within a single element of these matched lists.
            Useful cases where there is as single z transforms shared
            by all tiles within a single z, but not across z's
        poolsize (int): number of processes for multiprocessing pool
        close_stack (bool): whether to mark render stack as COMPLETE after successful import
        render (renderapi.render.RenderClient): render connect object

    '''
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    partial_import = partial(import_single_json_file, stack, render=render,
                             client_scripts=client_scripts, host=host,
                             port=port, owner=owner, project=project)
    with WithPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles, transformfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles_parallel(
        stack, jsonfiles, poolsize=20, transformFile=None,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, render=None, **kwargs):
    '''
    import jsons using client script in parallel

    Args:
        stack (str): the stack to upload into
        jsonfiles (list[str]): list of jsonfile paths to upload
        poolsize (int): number of upload processes spawned by multiprocessing pool
        transformFile (str): a single json file path containing transforms referenced
            in the jsonfiles
        close_stack (boolean): whether to mark render stack as COMPLETE after successful import
        render (renderapi.render.RenderClient): render connect object
    '''
    set_stack_state(stack, 'LOADING', host, port, owner, project)

    partial_import = partial(import_single_json_file, stack, render=render,
                             transformFile=transformFile,
                             client_scripts=client_scripts,
                             host=host, port=port, owner=owner,
                             project=project)
    with WithPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles(stack, jsonfiles, transformFile=None,
                     client_scripts=None, host=None, port=None,
                     owner=None, project=None, close_stack=True,
                     render=None, **kwargs):
    '''
    import jsons using client script serially

    Args:
        jsonfiles (list): iterator of filenames to be uploaded
        transformFile (str): path to a jsonfile that contains shared
            transform references (if necessary)
        close_stack (boolean): mark render stack as COMPLETE after successful import
        render (renderapi.render.RenderClient): render connect object
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
    method to import tilesepcs directly from :class:`renderapi.tilespec.TileSpec` objects

    Args:
         stack (str): stack to which tilespecs will be added
         tilespecs (list[renderapi.tilespec.TileSpec]): list of tilespecs to import
         sharedTransforms (list[renderapi.transform.Transform]): list of shared
             referenced transforms to be ingested
         render (renderapi.render.RenderClient): render connect object
    '''
    tsjson = renderdump_temp(tilespecs)

    if sharedTransforms is not None:
        trjson = renderdump_temp(sharedTransforms)

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
    '''
    method to import tilesepcs directly from :class:`renderapi.tilespec.TileSpec` objects
    using pathos.multiprocessing to parallelize

    Args:
         stack (str): stack to which tilespecs will be added
         tilespecs (list[renderapi.tilespec.TileSpec]): list of tilespecs to import
         sharedTransforms (list[renderapi.transform.Transform]): list of shared
             referenced transforms to be ingested
         poolsize (int): degree of parallelism to use
         subprocess_mode (str): subprocess mode used when calling client side java
         close_stack (boolean): mark render stack as COMPLETE after successful import
         render (renderapi.render.RenderClient): render connect object
    '''
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    partial_import = partial(
        import_tilespecs, stack, sharedTransforms=sharedTransforms,
        subprocess_mode=subprocess_mode, host=host, port=port,
        owner=owner, project=project, client_script=client_script,
        memGB=memGB, **kwargs)

    # TODO this is a weird way to do splits.... is that okay?
    tilespec_groups = [tilespecs[i::poolsize] for i in xrange(poolsize)]
    with WithPool(poolsize) as pool:
        pool.map(partial_import, tilespec_groups)
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

    Args:
        stack (str): stack to which world coordinates are mapped
        points (dict): local points to map to world
        tileId (str): tileId to which points correspond
        subprocess_mode (str): subprocess mode used when calling
            clientside java client
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

    Args:
        stack (str): stack to which world coordinates are mapped
        points (dict): local points to map to world
        subprocess_mode (str): subprocess mode used when calling client side java
        render (renderapi.render.RenderClient): render connect object

    Returns:
        list[list]: dictionaries defining local coordinates
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
    '''run ImportJsonClient.java
        see render documentation (add link here)
    '''
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
    '''run TilePairClient.java
        see render documentation (#add link here)
    '''
    if outjson is None:
        with tempfile.NamedTemporaryFile(
                suffix=".json", mode='r', delete=False) as f:
            outjson = f.name
        delete_json = True

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
                                 changeMode=None, close_stack=True,
                                 subprocess_mode=None,
                                 host=None, port=None, owner=None,
                                 project=None, client_script=None, memGB=None,
                                 render=None, **kwargs):
    '''
    run ImportTransformChangesClient.java
    transformFile: json file in format defined below
        [{{"tileId": <tileId>,
           "transform": <transformDict>}},
          {{"tileId": ...}},
          ...
        ]
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
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


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
def renderSectionClient(stack, rootDirectory, zs, scale=None,
                        maxIntensity=None, minIntensity=None, format=None,
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
             get_param(minIntensity, '--minIntensity') +
             get_param(maxIntensity, '--maxIntensity') +
             get_param(fillWithNoise, '--fillWithNoise') + zs)
    call_run_ws_client('org.janelia.render.client.RenderSectionClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs)


@renderaccess
def transformSectionClient(stack, transformId, transformClass, transformData,
                           zValues, targetProject=None, targetStack=None,
                           replaceLast=None, subprocess_mode=None,
                           host=None, port=None,
                           owner=None, project=None, client_script=None,
                           memGB=None, render=None, **kwargs):
    '''
    run TranformSectionClient.java
    expects:
        transformId -- string unique transform identifier
        transformClass -- string representing mpicbg transform
        transformData -- mpicbg datastring delimited by "," instead of " "
        zValues -- list of z values to apply tform
        optional:
            targetProject -- project to output the transformed sections
            targetStack -- stack to ouput transformed sections
            replaceLast -- bool whether to have transform replace
                last in specList (default false)
    '''
    argvs = (make_stack_params(host, port, owner, project, stack) +
             (['--replaceLast'] if replaceLast else []) +
             get_param(targetProject, '--targetProject') +
             get_param(targetStack, '--targetStack') +
             ['--transformId', transformId, '--transformClass', transformClass,
              '--transformData', transformData] + zValues)
    call_run_ws_client('org.janelia.render.client.TransformSectionClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs)
