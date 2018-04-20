#!/usr/bin/env python
from .tilespec import TileSpec
from .transform import load_transform_json
from .utils import NullHandler, put_json, jbool, get_json
from .render import format_preamble, renderaccess
from .errors import RenderError
import logging
import requests

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class ResolvedTiles:
    def __init__(self, tilespecs=None, transformList=None, json=None):
        if json is None:
            if tilespecs is None:
                self.tilespecs = []
            else:
                self.tilespecs = tilespecs
            if transformList is None:
                self.transforms = []
            else:
                self.transforms = transformList
        else:
            self.from_dict(json)

    def to_dict(self):
        d = {
            'transformIdToSpecMap': {tf.transformId: tf.to_dict()
                                     for tf in self.transforms},
            'tileIdToSpecMap': {ts.tileId: ts.to_dict()
                                for ts in self.tilespecs}
        }
        return d

    def from_dict(self, d):
        self.tilespecs = []
        self.transforms = []
        for ts in d['tileIdToSpecMap'].values():
            self.tilespecs.append(TileSpec(json=ts))
        for transformId, tform_json in d['transformIdToSpecMap'].items():
            tform_json['transformId'] = transformId
            self.transforms.append(load_transform_json(tform_json))

    # def get_tilespecs():
    """return a set of TileSpecs that include resolved tilespecs

    Returns
    -------
    List(renderapi.tilespec.TileSpec)
        A list of tilespecs stored in this ResolvedTiles with the transformations dereferenced
    """  # noqa: E501


@renderaccess
def put_tilespecs(stack, resolved_tiles=None, deriveData=True,
                  tilespecs=None, shared_transforms=None,
                  host=None, port=None, owner=None, project=None,
                  session=requests.session(), render=None, **kwargs):
    """upload resolved tiles to the server

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        render stack
    resolved_tiles: renderapi.resolvedtiles.ResolvedTiles
        resolved tiles to upload
    deriveData: bool
        whether or not to calculate bounding boxes serverside
    tilespecs: list[renderapi.tilespec.Tilespec]
        list of tilespecs to upload
    sharedTransforms: list[renderapi.transform.Transform]
        list of shared transforms to upload
    render: renderapi.render.Render
        render connect object

    Returns
    -------
    requests.response.Reponse
        server response
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + '/resolvedTiles'
    qparams = {} if deriveData is None else {'deriveData': jbool(deriveData)}
    logger.debug(request_url)
    if resolved_tiles is None:
        if (tilespecs is None):
            raise RenderError("need to pass resolved_tiles or tilespecs")
        resolved_tiles = ResolvedTiles(tilespecs=tilespecs,
                                       transformList=shared_transforms)
    r = put_json(session, request_url, resolved_tiles, qparams)
    logger.debug(r)
    return r


@renderaccess
def get_resolved_tiles_from_z(stack, z, host=None, port=None,
                              owner=None, project=None,
                              session=requests.session(),
                              render=None, **kwargs):
    """Get a set of ResolvedTiles from a specific z value.
    Returns a tuple of tilespecs and referenced transforms.

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        render stack
    z : float
        render z
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        sessions object to connect with

    Returns
    -------
    :obj:`ResolvedTiles`
        ResolvedTiles object containing tilespecs and transforms
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/%f/resolvedTiles' % (z)
    logger.debug(request_url)
    d = get_json(session, request_url)
    return ResolvedTiles(json=d)
