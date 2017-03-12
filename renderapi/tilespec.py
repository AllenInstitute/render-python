#!/usr/bin/env python
from .render import Render, format_baseurl, format_preamble, renderaccess
from .utils import NullHandler
from .stack import get_z_values_for_stack
from .transform import Transform, AffineModel, ReferenceTransform
from collections import OrderedDict
import logging
import requests
import numpy as np

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class ResolvedTileSpecMap:
    def __init__(self, tilespecs=[], transforms=[]):
        self.tilespecs = tilespecs
        self.transforms = transforms

    def to_dict(self):
        d = {}
        d['tileIdToSpecMap'] = {}
        for ts in self.tilespecs:
            d['tileIdToSpecMap'][ts.tileId] = ts.to_dict()
        d['transformIdToSpecMap'] = {}
        for tf in self.transforms:
            d['transformIdToSpecMap'][tf.transformId] = tf.to_dict()
        return d

    def from_dict(self, d):
        tsmap = d['tileIdToSpecMap']
        tfmap = d['transformIdToSpecMap']
        for tsd in tsmap.values():
            ts = TileSpec()
            ts.from_dict(tsd)
            self.tilespecs.append(ts)
        for tfd in tfmap.values():
            tf.Transform()
            tf.from_dict(tfd)
            self.transforms.append(tf)


class ResolvedTileSpecCollection:
    def __init__(self, tilespecs=[], transforms=[]):
        self.tilespecs = tilespecs
        self.transforms = transforms

    def to_dict(self):
        d = {}
        d['tileCount'] = len(self.tilespecs)
        d['tileSpecs'] = [ts.to_dict() for ts in self.tilespecs]
        d['transformCount'] = len(self.transforms)
        d['transformSpecs'] = [tf.to_dict() for tf in self.transforms]
        return d

    def from_dict(self, d):
        self.tilespecs = []
        self.transforms = []
        for i in range(d['tileCount']):
            ts = TileSpec()
            ts.from_dict(d['tileSpecs'][i])
            self.tilespecs.append(ts)
        for i in range(d['tranformCount']):
            tfd = d['transformSpecs'][i]
            if tfd['className'] is 'mpicbg.trakem2.transform.AffineModel2D':
                tf = AffineModel()
            else:
                tf = Transform()
            tf.from_dict(tfd)
            self.transforms.append(tf)


class Filter:
    def __init__(self, classname, params={}):
        self.classname = classname
        self.params = params

    def to_dict(self):
        d = {}
        d['className'] = self.classname
        d['params'] = self.params
        return d

    def from_dict(self, d):
        self.classname = d['className']
        self.params = d['params']


class Layout:
    def __init__(self, sectionId=None, scopeId=None, cameraId=None,
                 imageRow=None, imageCol=None, stageX=None, stageY=None,
                 rotation=None, pixelsize=0.100):
        self.sectionId = str(sectionId)
        self.scopeId = str(scopeId)
        self.cameraId = str(cameraId)
        self.imageRow = imageRow
        self.imageCol = imageCol
        self.stageX = stageX
        self.stageY = stageY
        self.rotation = rotation
        self.pixelsize = pixelsize

    def to_dict(self):
        d = {}
        d['sectionId'] = self.sectionId
        d['temca'] = self.scopeId
        d['camera'] = self.cameraId
        d['imageRow'] = self.imageRow
        d['imageCol'] = self.imageCol
        d['stageX'] = self.stageX
        d['stageY'] = self.stageY
        d['rotation'] = self.rotation
        d['pixelsize'] = self.pixelsize
        return d

    def from_dict(self, d):
        if d is not None:
            self.sectionId = d.get('sectionId', None)
            self.cameraId = d.get('camera', None)
            self.scopeId = d.get('temca', None)
            self.imageRow = d.get('imageRow', None)
            self.imageCol = d.get('imageCol', None)
            self.stageX = d.get('stageX', None)
            self.stageY = d.get('stageY', None)
            self.rotation = d.get('rotation', None)
            self.pixelsize = d.get('pixelsize', None)


class TileSpec:
    def __init__(self, tileId=None, z=None, width=None, height=None,
                 imageUrl=None, frameId=None, maskUrl=None,
                 minint=0, maxint=65535, layout=Layout(), tforms=[],
                 inputfilters=[], scale3Url=None, scale2Url=None,
                 scale1Url=None, json=None, mipMapLevels=[]):
        if json is not None:
            self.from_dict(json)
        else:
            self.tileId = tileId
            self.z = z
            self.width = width
            self.height = height
            self.layout = layout
            self.minint = minint
            self.maxint = maxint
            self.tforms = tforms
            self.frameId = frameId
            self.inputfilters = inputfilters

            self.ip = ImagePyramid(mipMapLevels=mipMapLevels)
            # legacy scaleXUrl
            self.maskUrl = maskUrl
            self.imageUrl = imageUrl
            self.scale3Url = scale3Url
            self.scale2Url = scale2Url
            self.scale1Url = scale1Url

            if imageUrl is not None:
                self.ip.update(MipMapLevel(
                    0, imageUrl=imageUrl, maskUrl=maskUrl))
            if scale1Url is not None:
                self.ip.update(MipMapLevel(1, imageUrl=scale1Url))
            if scale2Url is not None:
                self.ip.update(MipMapLevel(2, imageUrl=scale2Url))
            if scale3Url is not None:
                self.ip.update(MipMapLevel(3, imageUrl=scale3Url))

    @property
    def bbox(self):
        '''bbox defined to fit shapely call'''
        box = (self.minX, self.minY, self.maxX, self.maxY)
        if any([v is None for v in box]):
            logger.error(
                'undefined bounding box for tile {}'.format(self.tileId))
        return box

    def to_dict(self):
        thedict = {}
        thedict['tileId'] = self.tileId
        thedict['z'] = self.z
        thedict['width'] = self.width
        thedict['height'] = self.height
        thedict['minIntensity'] = self.minint
        thedict['maxIntensity'] = self.maxint
        thedict['frameId'] = self.frameId
        if self.layout is not None:
            thedict['layout'] = self.layout.to_dict()
        thedict['mipmapLevels'] = self.ip.to_ordered_dict()
        thedict['transforms'] = {}
        thedict['transforms']['type'] = 'list'
        # thedict['transforms']['specList']=[t.to_dict() for t in self.tforms]
        thedict['transforms']['specList'] = []
        for t in self.tforms:
            strlist = {}
            # added by sharmi - if your speclist contains a speclist (can
            # happen if you run the optimization more than once)
            if isinstance(t, list):
                strlist['type'] = 'list'
                strlist['specList'] = [tt.to_dict() for tt in t]
                thedict['transforms']['specList'].append(strlist)
            else:
                thedict['transforms']['specList'].append(t.to_dict())

        thedict['inputfilters'] = {}
        thedict['inputfilters']['type'] = 'list'
        thedict['inputfilters']['specList'] = [f.to_dict() for f
                                               in self.inputfilters]
        return thedict

    def from_dict(self, d):
        '''Method to load tilespec from json dictionary'''
        self.tileId = d['tileId']
        self.z = d['z']
        self.width = d['width']
        self.height = d['height']
        self.minint = d['minIntensity']
        self.maxint = d['maxIntensity']
        self.frameId = d.get('frameId', None)
        self.layout = Layout()
        self.layout.from_dict(d.get('layout', None))
        self.minX = d.get('minX', None)
        self.maxX = d.get('maxX', None)
        self.maxY = d.get('maxY', None)
        self.minY = d.get('minY', None)
        self.ip = ImagePyramid(mipMapLevels=[
             MipMapLevel(
                 int(l), imageUrl=v.get('imageUrl'), maskUrl=v.get('maskUrl'))
             for l, v in d['mipmapLevels'].items()])

        self.tforms = []
        for t in d['transforms']['specList']:
            if t['type'] == 'ref':
                tf = ReferenceTransform(refId=t['refId'])
            elif t['type'] == 'leaf':
                if t['className'] == AffineModel.className:
                    tf = AffineModel()
                    tf.from_dict(t)
                else:
                    tf = Transform(json=t)
                self.tforms.append(tf)
        self.inputfilters = []
        if d.get('inputfilters', None) is not None:
            for f in d['inputfilters']['specList']:
                f['type']
                f = Filter()
                f.from_dict(f)
                self.inputfilters.append(f)


class MipMapLevel:
    def __init__(self, level, imageUrl=None, maskUrl=None):
        self.level = level
        self.imageUrl = imageUrl
        self.maskUrl = maskUrl

    def to_dict(self):
        return dict(self.__iter__())

    def _formatUrls(self):
        d = {}
        if self.imageUrl is not None:
            d.update({'imageUrl': self.imageUrl})
        if self.maskUrl is not None:
            d.update({'maskUrl': self.maskUrl})
        return d

    def __iter__(self):
        return iter([(self.level, self._formatUrls())])


class ImagePyramid:
    def __init__(self, mipMapLevels=[]):
        self.mipMapLevels = mipMapLevels

    def to_dict(self):
        return dict(self.__iter__())

    def to_ordered_dict(self, key=None):
        '''defaults to order by mipmapLevel'''
        return OrderedDict(sorted(
            self.__iter__(), key=((lambda x: x[0]) if key
                                  is None else key)))

    def append(self, mmL):
        self.mipMapLevels.append(mmL)

    def update(self, mmL):
        self.mipMapLevels = [
            l for l in self.mipMapLevels if l.level != mmL.level]
        self.append(mmL)

    def get(self, to_get):
        return self.to_dict()[to_get]  # TODO should this default

    @property
    def levels(self):
        return [int(i.level) for i in self.mipMapLevels]

    def __iter__(self):
        return iter([
            l for sl in [list(mmL) for mmL in self.mipMapLevels] for l in sl])


@renderaccess
def get_tile_spec(stack, tile, host=None, port=None, owner=None,
                  project=None, session=requests.session(),
                  render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/render-parameters" % (tile)
    r = session.get(request_url)
    try:
        tilespec_json = r.json()
    except:
        logger.error(r.text)
    return TileSpec(json=tilespec_json['tileSpecs'][0])


@renderaccess
def get_tile_specs_from_minmax_box(stack, z, xmin, xmax, ymin, ymax,
                                   scale=1.0, host=None,
                                   port=None, owner=None, project=None,
                                   session=requests.session(),
                                   render=None, **kwargs):
    x = xmin
    y = ymin
    width = xmax - xmin
    height = ymax - ymin
    return get_tile_specs_from_box(stack, z, x, y, width, height,
                                   scale=scale, host=host, port=port,
                                   owner=owner, project=project,
                                   session=session)


@renderaccess
def get_tile_specs_from_box(stack, z, x, y, width, height,
                            scale=1.0, host=None, port=None, owner=None,
                            project=None, session=requests.session(),
                            render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%3.2f/render-parameters" % (
                      z, x, y, width, height, scale)
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        tilespecs_json = r.json()
    except:
        logger.error(r.text)
    return [TileSpec(json=tilespec_json)
            for tilespec_json in tilespecs_json['tileSpecs']]


@renderaccess
def get_tile_specs_from_z(stack, z, host=None, port=None,
                          owner=None, project=None, session=requests.session(),
                          render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/%f/tile-specs' % (z)
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        tilespecs_json = r.json()
    except:
        logger.error(r.text)

    if len(tilespecs_json) == 0:
        return None
    else:
        return [TileSpec(json=tilespec_json)
                for tilespec_json in tilespecs_json]


@renderaccess
def get_tile_specs_from_stack(stack, host=None, port=None,
                              owner=None, project=None,
                              session=requests.session(),
                              render=None, **kwargs):
    '''get flat list of tilespecs for stack using i for sl in l for i in sl'''
    return [i for sl in [
        get_tile_specs_from_z(stack, z, host=host, port=port,
                              owner=owner, project=project, session=session)
        for z in get_z_values_for_stack(stack, host=host, port=port,
                                        owner=owner, project=project,
                                        session=session)] for i in sl]
