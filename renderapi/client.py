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
from decorator import decorator
from .errors import ClientScriptError
from .utils import NullHandler, renderdump_temp, fitargspec
from .render import RenderClient, renderaccess, Render, format_preamble, format_baseurl
from .stack import set_stack_state, make_stack_params
from pathos.multiprocessing import ProcessingPool as Pool

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


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
        except TypeError as e:
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
            except TypeError as e:
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


class WithPool(Pool):
    """pathos ProcessingPool with functioning __exit__ call

    Parameters
    ----------
    *args
        variable length argument list matching input
        to pathos.multiprocessing.Pool
    **kwargs
        keyword argument input matching pathos.multiprocessing.Pool

    Examples
    --------
    >>> with WithPool(number_processes) as pool:
    >>>     pool.map(myfunc, myInput)
    """

    def __init__(self, *args, **kwargs):
        super(WithPool, self).__init__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        super(WithPool, self)._clear()


@renderclientaccess
def import_single_json_file(stack, jsonfile, transformFile=None,
                            subprocess_mode=None,
                            client_script=None, memGB=None, host=None, port=None,
                            owner=None, project=None, render=None, **kwargs):
    """calls client script to import given jsonfile

    Parameters
    ----------
    stack : str
        stack to import into
    jsonfile : str
        path to jsonfile to import
    transformFile : str
        path to a file that contains shared
        transform references if necessary
    render : renderapi.render.RenderClient
        render connect object
    """
    if transformFile is None:
        transform_params = []
    else:
        transform_params = ['--transformFile', transformFile]
    stack_params = make_stack_params(
        host, port, owner, project, stack)
    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       stack_params + transform_params + [jsonfile],
                       client_script=client_script, memGB=memGB,
                       subprocess_mode=subprocess_mode, **kwargs)


@renderclientaccess
def import_jsonfiles_and_transforms_parallel_by_z(
        stack, jsonfiles, transformfiles, poolsize=20,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, render=None, **kwargs):
    """imports json files and transform files in parallel

    Parameters
    ----------
    stack : str
        the stack to import within
    jsonfiles : :obj:`list` of :obj:`str`
        "list of tilespec" json paths to import
    transformfiles : :obj:`list` of :obj:`str`
        "list of transform files" paths which matches
        in a 1-1 way with jsonfiles, so referenced transforms
        are shared only within a single element of these matched lists.
        Useful cases where there is as single z transforms shared
        by all tiles within a single z, but not across z's
    poolsize : int, optional
        number of processes for multiprocessing pool
    close_stack : bool, optional
        whether to mark render stack as COMPLETE after successful import
    render : renderapi.render.Render
        render connect object
    **kwargs
        arbitrary keyword arguments

    """
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    partial_import = partial(import_single_json_file, stack, render=render,
                             client_scripts=client_scripts, host=host,
                             port=port, owner=owner, project=project)
    with WithPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles, transformfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderclientaccess
def import_jsonfiles_parallel(
        stack, jsonfiles, poolsize=20, transformFile=None,
        client_scripts=None, host=None, port=None, owner=None,
        project=None, close_stack=True, render=None, **kwargs):
    """import jsons using client script in parallel

    Parameters
    ----------
    stack : str
        the stack to upload into
    jsonfiles : :obj:`list` of :obj:`str`
        list of jsonfile paths to upload
    poolsize : int
        number of upload processes spawned by multiprocessing pool
    transformFile : str
        a single json file path containing transforms referenced
        in the jsonfiles
    close_stack : bool
        whether to mark render stack as COMPLETE after successful import
    render : renderapi.render.Render
        render connect object
    **kwargs
        arbitrary keyword arguments

    """
    set_stack_state(stack, 'LOADING', host, port, owner, project)

    partial_import = partial(import_single_json_file, stack, render=render,
                             transformFile=transformFile,
                             client_scripts=client_scripts,
                             host=host, port=port, owner=owner,
                             project=project, **kwargs)
    with WithPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles(stack, jsonfiles, transformFile=None, subprocess_mode=None,
                     client_script=None, memGB=None, host=None, port=None,
                     owner=None, project=None, close_stack=True,
                     render=None, **kwargs):
    """import jsons using client script serially

    Parameters
    ----------
    jsonfiles : :obj:`list` of :obj:`str`
        iterator of filenames to be uploaded
    transformFile : str
        path to a jsonfile that contains shared
        transform references (if necessary)
    close_stack : bool
        mark render stack as COMPLETE after successful import
    render : renderapi.render.Render
        render connect object

    """

    set_stack_state(stack, 'LOADING', host, port, owner, project)
    if transformFile is None:
        transform_params = []
    else:
        transform_params = ['--transformFile', transformFile]
    stack_params = make_stack_params(
        host, port, owner, project, stack)
    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       stack_params + transform_params + jsonfiles,
                       client_script=client_script, memGB=memGB,
                       subprocess_mode=subprocess_mode, **kwargs)
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderclientaccess
def import_jsonfiles_validate_client(stack, jsonfiles,
                                     transformFile=None, client_script=None,
                                     host=None, port=None, owner=None,
                                     project=None, close_stack=True, mem=6,
                                     validator=None, subprocess_mode=None,
                                     memGB=None,
                                     render=None, **kwargs):
    """Uses java client for parallelization and validation

    Parameters
    ----------
    stack: str
        stack to which jsonfiles should be uploaded
    jsonfiles: :obj:`list` of :obj:`str`
        tilespecs in json files
    transformFile: str, optional
        json file listing transformspecs with ids which are referenced
        in tilespecs contained in jsonfiles

    """
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
    set_stack_state(stack, 'LOADING', host, port, owner, project)

    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       stack_params +
                       validator_params +
                       transform_params +
                       jsonfiles, client_script=client_script,
                       memGB=memGB, subprocess_mode=subprocess_mode,
                       **kwargs)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderclientaccess
def import_tilespecs(stack, tilespecs, sharedTransforms=None,
                     subprocess_mode=None, host=None, port=None,
                     owner=None, project=None, client_script=None,
                     memGB=None, render=None, **kwargs):
    """method to import tilesepcs directly from
    :class:`renderapi.tilespec.TileSpec` objects

    Parameters
    ----------
    stack : str
        stack to which tilespecs will be added
    tilespecs : :obj:`list` of :class:`renderapi.tilespec.TileSpec`
        list of tilespecs to import
    sharedTransforms : :obj:`list` of :class:`renderapi.transform.Transform` or :class:`renderapi.transform.TransformList` or :class:`renderapi.transform.InterpolatedTransform`, optional
        list of shared referenced transforms to be ingested
    render : renderapi.render.Render
        render connect object

    """
    tsjson = renderdump_temp(tilespecs)

    if sharedTransforms is not None:
        trjson = renderdump_temp(sharedTransforms)

    importJsonClient(stack, tileFiles=[tsjson], transformFile=(
        trjson if sharedTransforms is not None else None),
        subprocess_mode=subprocess_mode, host=host, port=port,
        owner=owner, project=project,
        client_script=client_script, memGB=memGB, **kwargs)

    os.remove(tsjson)
    if sharedTransforms is not None:
        os.remove(trjson)


@renderclientaccess
def import_tilespecs_parallel(stack, tilespecs, sharedTransforms=None,
                              subprocess_mode=None, poolsize=20,
                              close_stack=True, host=None, port=None,
                              owner=None, project=None,
                              client_script=None, memGB=None, render=None,
                              **kwargs):
    """method to import tilesepcs directly from
    :class:`renderapi.tilespec.TileSpec` objects using
    pathos.multiprocessing to parallelize

    Parameters
    ----------
    stack : str
     stack to which tilespecs will be added
    tilespecs : :obj:`list` of :class:`renderapi.tilespec.TileSpec`
        list of tilespecs to import
    sharedTransforms : obj:`list` of :obj:`renderapi.transform.Transform` or :class:`renderapi.transform.TransformList` or :class:`renderapi.transform.InterpolatedTransform`, optional
        list of shared referenced transforms to be ingested
    poolsize : int
        degree of parallelism to use
    subprocess_mode : str
        subprocess mode used when calling client side java
    close_stack : bool
        mark render stack as COMPLETE after successful import
    render : :class:renderapi.render.Render
        render connect object
    """
    set_stack_state(stack, 'LOADING', host, port, owner, project)
    partial_import = partial(
        import_tilespecs, stack, sharedTransforms=sharedTransforms,
        subprocess_mode=subprocess_mode, host=host, port=port,
        owner=owner, project=project, client_script=client_script,
        memGB=memGB, **kwargs)

    # TODO this is a weird way to do splits.... is that okay?
    tilespec_groups = [tilespecs[i::poolsize] for i in range(poolsize)]
    with WithPool(poolsize) as pool:
        pool.map(partial_import, tilespec_groups)
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


# TODO handle fromJson and toJson persistence in these calls
@renderclientaccess
def local_to_world_array(stack, points, tileId, subprocess_mode=None,
                         host=None, port=None, owner=None, project=None,
                         client_script=None, memGB=None,
                         render=None, **kwargs):
    """placeholder function for coordinateClient localtoworld

    Parameters
    ----------
    stack : str
        stack to which world coordinates are mapped
    points : dict
        local points to map to world
    tileId : str
        tileId to which points correspond
    subprocess_mode : str
        subprocess mode used when calling
        clientside java client
    Returns
    -------
    list
        points in world coordinates corresponding to local points
    """
    raise NotImplementedError('Whoops')


@renderclientaccess
def world_to_local_array(stack, points, subprocess_mode=None,
                         host=None, port=None, owner=None, project=None,
                         client_script=None, memGB=None,
                         render=None, **kwargs):
    """placeholder function for coordinateClient worldtolocal

    Parameters
    ----------
    stack : str
        stack to which world coordinates are mapped
    points : dict
        local points to map to world
    subprocess_mode : str
        subprocess mode used when calling client side java
    render : :class:`renderapi.render.Render`
        render connect object

    Returns
    -------
    :obj:`list` of :obj:`list`
        dictionaries defining local coordinates
        and tileIds corresponding to world point
    """
    raise NotImplementedError('Whoops.')


def run_subprocess_mode(args, subprocess_mode=None, **kwargs):
    subprocess_options = ['bufsize', 'executable', 'stdin', 'stdout',
                          'stderr', 'preexec_fn', 'close_fds', 'shell',
                          'cwd', 'env', 'universal_newlines', 'startupinfo',
                          'creationflags']
    subprocess_kwargs = {k: v for k, v in kwargs.items()
                         if k in subprocess_options}
    subprocess_modes = {'call': subprocess.call,
                        'check_call': subprocess.check_call,
                        'check_output': subprocess.check_output,
                        None: subprocess.check_call}
    if subprocess_mode not in subprocess_modes:
        logger.warning(
            'Unknown subprocess mode {} specified -- '
            'using default subprocess.check_call'.format(subprocess_mode))
    sub_mode = subprocess_modes.get(subprocess_mode, subprocess.check_call)
    return sub_mode(args, **subprocess_kwargs)


def call_run_ws_client(className, add_args=[], renderclient=None,
                       memGB=None, client_script=None,
                       **kwargs):
    """simple call for run_ws_client.sh -- all arguments set in add_args

    Parameters
    ----------
    className : str
        Render java client classname to call as first argv for
        Render's call_run_ws_client.sh wrapper script
    add_args : :obj:`list` of :obj:`str`, optional
        command line arguments
    renderclient : :class:`renderapi.render.RenderClient`, optional
        render client connection object
    memGB : str, optional
        GB memory for this java process
        (defaults to '1G' or value defined in renderclient)
    client_script : str, optional
        client script to be used as the Render library's call_run_ws_client.sh
        wrapper script (this option overrides value in renderclient)
    subprocess_mode: str, optional
        subprocess mode 'call', 'check_call', 'check_output' (default 'call')


    Returns
    -------
    obj
        result of subprocess_mode call
    """
    logger.debug('call_run_ws_client -- classname:{} add_args:{} '
                 'client_script:{} memGB:{}'.format(
                     className, add_args, client_script, memGB))

    if renderclient is not None:
        if isinstance(renderclient, RenderClient):
            return call_run_ws_client(className, add_args=add_args,
                                      subprocess_mode=subprocess_mode,
                                      **renderclient.make_kwargs(
                                          memGB=memGB,
                                          client_script=client_script,
                                          **kwargs))
    if memGB is None:
        logger.warning('call_run_ws_client requires memory specification -- '
                       'defaulting to 1G')
        memGB = '1G'
    args = map(str, [client_script, memGB, className] + add_args)
    try:
        ret_val = run_subprocess_mode(args, **kwargs)
    except subprocess.CalledProcessError as e:
        raise ClientScriptError('client_script call {} failed'.format(args))

    return ret_val


def get_param(var, flag):
    return ([flag, var] if var is not None else [])


@renderclientaccess
def importJsonClient(stack, tileFiles=None, transformFile=None,
                     subprocess_mode=None,
                     host=None, port=None, owner=None, project=None,
                     client_script=None, memGB=None,
                     render=None, **kwargs):
    """run ImportJsonClient.java
    see render documentation (add link here)

    Parameters
    ----------
    stack : str
        stack to which tilespecs in tileFiles will be imported
    tileFiles : :obj:`list` of :obj:`str`
        json files containing tilespecs to import
    transformFile : str, optional
        json file containing transform specs which are
        referenced by tilespecs in tileFiles
    render : :class:`renderapi.render.Render`
        render connection object
    """
    argvs = (make_stack_params(host, port, owner, project, stack) +
             (['--transformFile', transformFile] if transformFile else []) +
             (tileFiles if isinstance(tileFiles, list)
              else [tileFiles]))
    call_run_ws_client('org.janelia.render.client.ImportJsonClient',
                       add_args=argvs, subprocess_mode=subprocess_mode,
                       client_script=client_script, memGB=memGB, **kwargs)


@renderclientaccess
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
    """run TilePairClient.java
    see render documentation (#add link here)

    This client selects a set of tiles 'p' based on its position in
    a stack and then searches for nearby 'q' tiles using geometric parameters

    Parameters
    ----------
    stack : str
        stack from which tilepairs should be considered
    minz : str
        minimum z bound from which tile 'p' is selected
    maxz : str
        maximum z bound from which tile 'p' is selected
    outjson : str or None
        json to which tile pair file should be written
        (defaults to using temporary file and deleting after completion)
    delete_json : bool
        whether to delete outjson on function exit (True if outjson is None)
    baseowner : str
        owner of stack from which stack was derived
    baseproject : str
        project of stack from which stack was derived
    basestack : str
        stack from which stack was derived
    xyNeighborFactor : float
        factor to multiply by max(width, height) of tile 'p' in order
        to generate search radius in z (0.9 if None)
    zNeighborDistance : int
        number of z sections defining the half-height of search cylinder
        for tile 'p' (2 if None)
    excludeCornerNeighbors : bool
        whether to exclude potential 'q' tiles based on center points
        falling outside search (True if None)
    excludeCompletelyObscuredTiles : bool
        whether to exclude potential 'q' tiles that are obscured by other tiles
        based on Render's sorting (True if None)
    excludeSameLayerNeighbors : bool
        whether to exclude potential 'q' tiles in the same z layer as 'p'
    excludeSameSectionNeighbors : bool
        whether to exclude potential 'q' tiles with the same sectionId as 'p'
    excludePairsInMatchCollection : str
        a matchCollection whose 'p' and 'q' pairs will be ignored
        if generated using this client
    minx : float
        minimum x bound from which tile 'p' is selected
    maxx : float
        maximum x bound from wich tile 'p' is selected
    miny : float
        minimum y bound from which tile 'p' is selected
    maxy : float
        maximum y bound from wich tile 'p' is selected

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of tilepairs
    """
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
                       add_args=argvs, **kwargs)

    with open(outjson, 'r') as f:
        jsondata = json.load(f)

    if delete_json:
        os.remove(outjson)
    return jsondata


@renderclientaccess
def importTransformChangesClient(stack, targetStack, transformFile,
                                 targetOwner=None, targetProject=None,
                                 changeMode=None, close_stack=True,
                                 subprocess_mode=None,
                                 host=None, port=None, owner=None,
                                 project=None, client_script=None, memGB=None,
                                 render=None, **kwargs):
    """run ImportTransformChangesClient.java

    Parameters
    ----------
    stack : str
        stack from which tiles will be transformed
    targetStack : str
        stack that will hold results of transforms
    transformFile : str
        locaiton of json file in format defined below
        ::
            [{{"tileId": <tileId>,
               "transform": <transformDict>}},
              {{"tileId": ...}},
              ...
            ]
    targetOwner : str
        owner of target stack
    targetProject : str
        project of target stack
    changeMode : str
        method to apply transform to tiles.  Options are:
        'APPEND' -- add transform to tilespec's list of transforms
        'REPLACE_LAST' -- change last transform in tilespec's
            list of transforms to match transform
        'REPLACE_ALL' -- overwrite tilespec's transforms field to match
            transform

    Raises
    ------
    ClientScriptError
        if changeMode is not valid
    """
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
        add_args=argvs, **kwargs)
    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderclientaccess
def coordinateClient(stack, z, fromJson=None, toJson=None, localToWorld=None,
                     numberOfThreads=None, subprocess_mode=None,
                     host=None, port=None, owner=None,
                     project=None, client_script=None, memGB=None,
                     render=None, **kwargs):
    """run CoordinateClient.java

    map coordinates between local and world systems

    Parameters
    ----------
    stack : str
        stack representing the world coordinates
    z : str
        z value of the section containing the tiles to map
    fromJson : str
        input json file in format defined by
        list of coordinate dictionaries (for world to local)
        or list of list of coordinate dictionaries (local to world)
    toJson : str
        json to save results of mapping coordinates
    localToWorld : bool
        whether to transform form local to world coordinates (False if None)
    numberOfThreads : int
        number of threads for java process (1 if None)

    Returns
    -------
    :obj:`list` of :obj:`dict` for local to world or :obj:`list` of :obj:`list` of :obj:`dict` for world to local
        list representing mapped coordinates
    """
    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--z', z, '--fromJson', fromJson, '--toJson', toJson] +
             (['--localToWorld'] if localToWorld else []) +
             get_param(numberOfThreads, '--numberOfThreads'))
    call_run_ws_client('org.janelia.render.client.CoordinateClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs,
                       **kwargs)

    with open(toJson, 'r') as f:
        jsondata = json.load(f)

    return jsondata


@renderclientaccess
def renderSectionClient(stack, rootDirectory, zs, scale=None,
                        maxIntensity=None, minIntensity=None, bounds=None,
                        format=None, channel=None, customOutputFolder=None,
                        customSubFolder=None,padFileNamesWithZeros=None,
                        doFilter=None, fillWithNoise=None, imageType=None,
                        subprocess_mode=None, host=None, port=None, owner=None,
                        project=None, client_script=None, memGB=None,
                        render=None, **kwargs):
    """run RenderSectionClient.java

    Parameters
    ----------
    stack : str
        stack to which zs to render belong
    rootDirectory : str
        directory to which rendered sections should be generated
    zs : :obj:`list` of :obj:`str`
        z indices of sections to render
    scale : float
        factor by which section image should be scaled
        (this materialization is 32-bit limited)
    maxIntensity : int
        value todisplay as white on a linear colormap
    minIntensity : int
        value to display as black on a linear colormap
    bounds: dict
        dictionary with keys of minX maxX minY maxY
    format : str
        output image format in 'PNG', 'TIFF', 'JPEG'
    channel : str
        channel to render out (use on multichannel stack)
    customOutputFolder : str
        folder to save all images in (overrides default of sections_at_%scale)
    customSubFolder : str
        folder to save all images in under outputFolder (overrides default of none)
    padFileNamesWithZeros: bool
        whether to pad file names with zeros to make sortable
    imageType: int
        8,16,24 to specify what kind of image type to save
    doFilter : str
        string representing java boolean for whether to render image
        with default filter (varies with render version)
    fillWithNoise : str
        string representing java boolean for whether to replace saturated
        image values with uniform noise

    """
    if bounds is not None:
        try:
            if bounds['maxX'] < bounds['minX']:
                raise ClientScriptError('maxX:{} is less than minX:{}'.format(
                    bounds['maxX'], bounds['minX']))
            if bounds['maxY'] < bounds['minY']:
                raise ClientScriptError('maxY:{} is less than minY:{}'.format(
                    bounds['maxY'], bounds['minY']))
            bound_list = ','.join(map(lambda x: str(int(x)),
                                      [bounds['minX'], bounds['maxX'], bounds['minY'], bounds['maxY']]))
            bound_param = ['--bounds', bound_list]
        except KeyError as e:
            raise ClientScriptError(
                'bounds does not contain correct keys {}'.format(bounds))
    else:
        bound_param = []

    argvs = (make_stack_params(host, port, owner, project, stack) +
             ['--rootDirectory', rootDirectory] +
             get_param(scale, '--scale') + get_param(format, '--format') +
             get_param(doFilter, '--doFilter') +
             get_param(minIntensity, '--minIntensity') +
             get_param(maxIntensity, '--maxIntensity') +
             get_param(fillWithNoise, '--fillWithNoise') +
             get_param(customOutputFolder, '--customOutputFolder')+
             get_param(imageType,'--imageType')+
             get_param(channel,'--channels')+
             get_param(customSubFolder,'--customSubFolder')+
             get_param(padFileNamesWithZeros,'--padFileNamesWithZeros')+
             bound_param + zs)
    call_run_ws_client('org.janelia.render.client.RenderSectionClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs,
                       **kwargs)


@renderclientaccess
def transformSectionClient(stack, transformId, transformClass, transformData,
                           zValues, targetProject=None, targetStack=None,
                           replaceLast=None, subprocess_mode=None,
                           host=None, port=None,
                           owner=None, project=None, client_script=None,
                           memGB=None, render=None, **kwargs):
    """run TranformSectionClient.java

    Parameters
    ----------
    stack : str
        stack containing section to transform
    transformId : str
        unique transform identifier
    transformClass : str
        transform className defined by the java mpicbg library
    transformData : str
        mpicbg datastring delimited by "," instead of " "
    zValues : list
        z values to which transform should be applied
    targetProject : str, optional
        project to which transformed sections should be added
    targetStack : str, optional
        stack to which transformed sections should be added
    replaceLast : bool, optional
        whether to replace the last transform in the section
        with this transform

    """
    argvs = (make_stack_params(host, port, owner, project, stack) +
             (['--replaceLast'] if replaceLast else []) +
             get_param(targetProject, '--targetProject') +
             get_param(targetStack, '--targetStack') +
             ['--transformId', transformId, '--transformClass', transformClass,
              '--transformData', transformData] + zValues)
    call_run_ws_client('org.janelia.render.client.TransformSectionClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs,
                       **kwargs)


@renderclientaccess
def get_canvas_url_template(
        stack, filter=False, renderWithoutMask=False,
        normalizeForMatching=True, excludeTransformsAfterLast=None,
        excludeFirstTransformAndAllAfter=None, excludeAllTransforms=False,
        host=None, port=None, owner=None, project=None, client_script=None,
        render=None, **kwargs):
    """function for making a render-parameters url template for point matching

    Parameters
    ----------
    stack: str
        render stack name
    filter: bool
        whether to apply default filtering to tile (default=False)
    renderWithoutMask: bool
        whether to exclude the mask when rendering tile (default=False)
    normalizeForMatching: bool
        whether to apply traditional 'normalizeForMatching' transform manipulation to image
        this removes the last transform from the transformList, then if there are more than 3 transforms
        continues to remove transforms until there are exactly 3.  Then assumes the image will be near 0,0
        with a width/height that is about equal to the raw image width/height.  This is true for Janelia's
        conventions for transformation alignment, but use at your own risk. (default=True)
    excludeTransformsAfterLast: str or None
        alternative to normalizeForMatching, which uses transformLabels.  Will remove all transformations
        after the last transformation with this transform label.  i.e. if all lens corrections have a 'lens'
        label.  Then this will remove all non-lens transformations from the list.
        This is more general than normalizeForMatching=true, but requires you have transform labels applied.
        default = None
    excludeFirstTransformAndAllAfter: str
        alternative to normalizeForMatching which finds the first transform in the list with a given label
        and then removes that transform and all transforms that follow it. i.e. if you had a compound list
        of transformations, and you had labelled the first non-local transform 'montage' then setting
        excludeFirstTransformAndAllAfter='montage' would remove that montage transform and any other
        transforms that you had applied after it. default= None.
    excludeAllTransforms: bool
        alternative to normalizeForMatching which simply removes all transforms from the list.
        default=False
    """
    request_url = format_preamble(host, port, owner, project, stack)
    tile_base_url = request_url+"/tile"
    url_suffix = "render-parameters"
    if filter:
        url_suffix += '?filter=true'
    else:
        url_suffix += '?filter=false'

    if normalizeForMatching:
        url_suffix += '&normalizeForMatching=true'
    else:
        url_suffix += '&normalizeForMatching=false'

    if renderWithoutMask:
        url_suffix += '&renderWithoutMask=true'
    else:
        url_suffix += '&renderWithoutMask=false'

    if excludeTransformsAfterLast is not None:
        url_suffix += '&excludeTransformsAfterLast={}'.format(
            excludeTransformsAfterLast)
    if excludeFirstTransformAndAllAfter is not None:
        url_suffix += '&excludeFirstTransformAndAllAfter={}'.format(
            excludeFirstTransformAndAllAfter)
    if excludeAllTransforms:
        url_suffix += '&excludeAllTransforms=true'

    canvas_url_template = "%s/{}/%s" % (tile_base_url,
                                        url_suffix)
    return canvas_url_template


class ArgumentParameters(object):
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def sanitize_cmd(cmd):
        def jbool_str(c):
            return str(c) if type(c) is not bool else "true" if c else "false"
        if any([i is None for i in cmd]):
            raise ClientScriptError(
                'missing argument in command "{}"'.format(map(str, cmd)))
        return map(jbool_str, cmd)

    @staticmethod
    def get_cmd_opt(v, flag=None):
        return [] if v is None else [v] if flag is None else [flag, v]

    @staticmethod
    def get_flag_cmd(v, flag=None):
        # for arity 0
        return [flag] if v else []

    def to_java_args(self):
        args = []
        for key, value in self.__dict__.items():
            if (value is not None) and not (key == 'kwargs'):
                args += self.get_cmd_opt(value, "--{}".format(key))
        return self.sanitize_cmd(args)


class FeatureExtractionParameters(ArgumentParameters):
    def __init__(self, SIFTfdSize=None, SIFTmaxScale=None,
                 SIFTminScale=None, SIFTsteps=None, **kwargs):
        super(FeatureExtractionParameters, self).__init__(**kwargs)
        self.SIFTfdSize = SIFTfdSize
        self.SIFTmaxScale = SIFTmaxScale
        self.SIFTminScale = SIFTminScale
        self.SIFTsteps = SIFTsteps


class MatchDerivationParameters(ArgumentParameters):
    def __init__(self, matchIterations=None,
                 matchMaxEpsilon=None, matchMaxNumInliers=None,
                 matchMaxTrust=None,  matchMinInlierRatio=None,
                 matchMinNumInliers=None,
                 matchModelType=None, matchRod=None, **kwargs):
        super(MatchDerivationParameters, self).__init__(**kwargs)
        self.matchIterations = matchIterations
        self.matchMaxEpsilon = matchMaxEpsilon
        self.matchMaxNumInliers = matchMaxNumInliers
        self.matchMaxTrust = matchMaxTrust
        self.matchMinInlierRatio = matchMinInlierRatio
        self.matchMinNumInliers = matchMinNumInliers
        self.matchMinNumInliers = matchMinNumInliers
        self.matchModelType = matchModelType
        self.matchRod = matchRod


class SiftPointMatchOptions(MatchDerivationParameters,
                            FeatureExtractionParameters):
    def __init__(self, renderScale=None, fillWithNoise=None, **kwargs):
        # TODO add missing parameters
        super(SiftPointMatchOptions, self).__init__(**kwargs)
        self.renderScale = renderScale
        self.fillWithNoise = fillWithNoise


@renderclientaccess
def pointMatchClient(stack, collection, tile_pairs,
                     sift_options=None,
                     pointMatchRender=None,
                     debugDirectory=None,
                     filter=False,
                     renderWithoutMask=False, normalizeForMatching=True,
                     excludeTransformsAfterLast=None,
                     excludeAllTransforms=None,
                     excludeFirstTransformAndAllAfter=None,
                     subprocess_mode=None,
                     host=None, port=None,
                     owner=None, project=None, client_script=None,
                     memGB=None, render=None, **kwargs):
    """run SiftPointMatchClient.java

    Parameters
    ----------
    stack : str
        stack containing the tiles
    collection : str
        point match collection to save results into
    tile_pairs : iterable
        list of iterables of length 2 containing tileIds to calculate point matches between
    sift_options: SiftOptions
        options for running point matching
    pointMatchRender : renderapi.render.renderaccess
        renderaccess object specifying the render server to store point matches in
        defaults to values specified by render and its keyword argument overrides
    debugDirectory : str
        directory to store debug results (optional)
    filter: bool
        whether to apply default filtering to tile (default=False)
    renderWithoutMask: bool
        whether to exclude the mask when rendering tile (default=False)
    normalizeForMatching: bool
        whether to apply traditional 'normalizeForMatching' transform manipulation to image
        this removes the last transform from the transformList, then if there are more than 3 transforms
        continues to remove transforms until there are exactly 3.  Then assumes the image will be near 0,0
        with a width/height that is about equal to the raw image width/height.  This is true for Janelia's
        conventions for transformation alignment, but use at your own risk. (default=True)
    excludeTransformsAfterLast: str or None
        alternative to normalizeForMatching, which uses transformLabels.  Will remove all transformations
        after the last transformation with this transform label.  i.e. if all lens corrections have a 'lens'
        label.  Then this will remove all non-lens transformations from the list.
        This is more general than normalizeForMatching=true, but requires you have transform labels applied.
        default = None
    excludeFirstTransformAndAllAfter: str
        alternative to normalizeForMatching which finds the first transform in the list with a given label
        and then removes that transform and all transforms that follow it. i.e. if you had a compound list
        of transformations, and you had labelled the first non-local transform 'montage' then setting
        excludeFirstTransformAndAllAfter='montage' would remove that montage transform and any other
        transforms that you had applied after it. default= None.
    excludeAllTransforms: bool
        alternative to normalizeForMatching which simply removes all transforms from the list.
        default=False

    """
    sift_options = (SiftPointMatchOptions(**kwargs) if sift_options is None
                    else sift_options)

    if pointMatchRender is None:
        pointMatchRender = Render(host, port, owner, project, client_script)

    baseDataUrl = format_baseurl(pointMatchRender.DEFAULT_KWARGS['host'],
                                 pointMatchRender.DEFAULT_KWARGS['port'])
    argvs = []
    argvs += ['--baseDataUrl', baseDataUrl]
    argvs += ['--owner', pointMatchRender.DEFAULT_KWARGS['owner']]
    argvs += ['--collection', collection]
    if debugDirectory is not None:
        argvs += ['--debugDirectory', debugDirectory]
    argvs += sift_options.to_java_args()

    canvas_url_template = get_canvas_url_template(
                            stack,
                            filter,
                            renderWithoutMask,
                            normalizeForMatching,
                            excludeTransformsAfterLast,
                            excludeFirstTransformAndAllAfter,
                            excludeAllTransforms,
                            host=host,
                            port=port,
                            owner=owner,
                            project=project,
                            client_script=client_script)

    for tile1, tile2 in tile_pairs:
        argvs += [canvas_url_template.format(tile1),
                  canvas_url_template.format(tile2)]

    call_run_ws_client('org.janelia.render.client.PointMatchClient',
                       memGB=memGB, client_script=client_script,
                       subprocess_mode=subprocess_mode, add_args=argvs,
                       **kwargs)
