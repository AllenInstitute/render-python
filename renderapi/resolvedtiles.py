#!/usr/bin/env python
from .tilespec import TileSpec
from .transform import load_transform_json
from .utils import NullHandler
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

    #def get_tilespecs():
    """return a set of TileSpecs that include resolved tilespecs

    Returns
    -------
    List(renderapi.tilespec.TileSpec)
        A list of tilespecs stored in this ResolvedTiles with the transformations dereferenced
    """


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
    r = session.get(request_url)
    try:
        d = r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)
    return ResolvedTiles(json=d)
