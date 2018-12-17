#!/usr/bin/env python
'''
render functions relying on render-ws client scripts
'''
import os
from functools import partial
import logging
import tempfile

import numpy
from PIL import Image

from renderapi.utils import NullHandler, renderdump_temp
from renderapi.render import renderaccess
from renderapi.stack import set_stack_state, make_stack_params
from renderapi.resolvedtiles import put_tilespecs
from renderapi.external.processpools.stdlib_pool import WithMultiprocessingPool

from .utils import renderclientaccess
from .client_calls import importJsonClient, call_run_ws_client, renderClient, rendererClient

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

WithPool = WithMultiprocessingPool


@renderclientaccess
def import_single_json_file(stack, jsonfile, transformFile=None,
                            subprocess_mode=None, client_script=None,
                            memGB=None, host=None, port=None,
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
    importJsonClient(stack, [jsonfile], transformFile,
                     subprocess_mode=subprocess_mode, host=host, port=port,
                     owner=owner, project=project, client_script=client_script,
                     memGB=memGB, **kwargs)


@renderclientaccess
def import_jsonfiles_and_transforms_parallel_by_z(
        stack, jsonfiles, transformfiles, poolsize=20, mpPool=WithPool,
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
    with mpPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles, transformfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderclientaccess
def import_jsonfiles_parallel(
        stack, jsonfiles, poolsize=20, transformFile=None, mpPool=WithPool,
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
    with mpPool(poolsize) as pool:
        pool.map(partial_import, jsonfiles)

    if close_stack:
        set_stack_state(stack, 'COMPLETE', host, port, owner, project)


@renderaccess
def import_jsonfiles(stack, jsonfiles, transformFile=None,
                     subprocess_mode=None, client_script=None, memGB=None,
                     host=None, port=None, owner=None, project=None,
                     close_stack=True, render=None, **kwargs):
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
    importJsonClient(stack, jsonfiles, transformFile,
                     subprocess_mode=subprocess_mode, host=host, port=port,
                     owner=owner, project=project, client_script=client_script,
                     memGB=memGB, **kwargs)
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
                     use_rest=False, deriveData=True,
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
    use_rest: bool
        whether to import the tilespecs using the post method directly with deriveData=True
    deriveData: bool
        if doing use_rest, will determine whether to have the server calculate bounds (default=True)
    render : renderapi.render.Render
        render connect object

    """  # noqa: E501
    if use_rest:
        put_tilespecs(stack,
                      deriveData=deriveData,
                      tilespecs=tilespecs,
                      shared_transforms=sharedTransforms,
                      host=host, port=port, owner=owner,
                      project=project, **kwargs)
    else:
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
                              mpPool=WithPool,
                              close_stack=True, max_tilespecs_per_group=None,
                              host=None, port=None,
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
    max_tilespecs_per_group: int
        maximum tilespecs per import process, default to len(tilespecs)/poolsize
    render : :class:renderapi.render.Render
        render connect object
    kwargs: dict .. all other kwargs to pass on to renderapi.client.import_tilespecs
    """  # noqa: E501
    tslists = (
        max((len(tilespecs) // max_tilespecs_per_group) + 1, poolsize) if
        max_tilespecs_per_group is not None else poolsize)

    set_stack_state(stack, 'LOADING', host, port, owner, project)
    partial_import = partial(
        import_tilespecs, stack, sharedTransforms=sharedTransforms,
        subprocess_mode=subprocess_mode, host=host, port=port,
        owner=owner, project=project, client_script=client_script,
        memGB=memGB, **kwargs)

    # TODO this is a weird way to do splits.... is that okay?
    tilespec_groups = [g for g in
                       (tilespecs[i::tslists] for i in range(tslists)) if g]
    with mpPool(poolsize) as pool:
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


def _defaultval(v, default=None):
    return default if v is None else v


@renderclientaccess
def materialize_tilespec_image(
        tilespec, out_fn=None, height=None, width=None,
        x=None, y=None, res=32,
        subprocess_mode=None,
        client_script=None, memGB=None,
        render=None, **kwargs):
    tspecfile = renderdump_temp([tilespec])

    x = _defaultval(x, tilespec.minX)
    y = _defaultval(y, tilespec.minY)
    width = _defaultval(width, int(float((tilespec.maxX - tilespec.minX))))
    height = _defaultval(height, int(float((tilespec.maxY - tilespec.minY))))
    renderClient(tile_spec_url=tspecfile, out_fn=out_fn,
                 height=height, width=width, x=x, y=y, res=res,
                 subprocess_mode=subprocess_mode,
                 client_script=client_script, memGB=memGB, **kwargs)

    os.remove(tspecfile)


def render_tilespec(*args, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.tif') as f:
        materialize_tilespec_image(*args, out_fn=f.name, **kwargs)
        arr = numpy.array(Image.open(f.name))
    return arr


@renderclientaccess
def materialize_renderparameters_image(
        obj, out_fn=None, subprocess_mode=None, client_script=None, memGB=None,
        render=None, **kwargs):
    tfile = renderdump_temp(obj)
    rendererClient(parameters_url=tfile, out_fn=out_fn,
                   subprocess_mode=subprocess_mode,
                   client_script=client_script, memGB=memGB,**kwargs)
    os.remove(tfile)


def render_renderparameters(*args, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.tif') as f:
        materialize_renderparameters_image(*args, out_fn=f.name, **kwargs)
        arr = numpy.array(Image.open(f.name))
    return arr


__all__ = [
    "import_single_json_file",
    "import_jsonfiles_and_transforms_parallel_by_z",
    "import_jsonfiles_parallel", "import_jsonfiles",
    "import_jsonfiles_validate_client", "import_tilespecs",
    "import_tilespecs_parallel", "local_to_world_array",
    "world_to_local_array", "WithPool",
    "render_tilespec", "materialize_tilespec_image"]
