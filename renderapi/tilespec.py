#!/usr/bin/env python
from .render import format_preamble, renderaccess
from .utils import NullHandler
from .stack import get_z_values_for_stack
from .transform import TransformList
from collections import OrderedDict
import logging
import requests

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Layout:
    '''Layout class to describe acquisition settings
    inputs:
    keyword arguments
    --sectionId: unique string to describe sectionId this tile was taken from
    --scopeId: string to track what microscope this came from
    --cameraId: string to track what camera this was taken with
    --imageRow: integer to track what row from a row,col layout this was taken
    --imageCol: integer to track what column form a row,col layout this was taken
    --stageX: X stage coordinates (float) for where this was taken
    --stageY: Y stage coordinates (float) for where this taken from
    --rotation: angle of camera when this was taken 
    --pixelsize: size of pixels in units of choice of camera at the magnification it was taken
    --force_pixelsize: whether to default pixelsize to 0.1 (default True)
    '''
    def __init__(self, sectionId=None, scopeId=None, cameraId=None,
                 imageRow=None, imageCol=None, stageX=None, stageY=None,
                 rotation=None, pixelsize=None,
                 force_pixelsize=True, **kwargs):
        self.sectionId = sectionId
        self.scopeId = scopeId
        self.cameraId = cameraId
        self.imageRow = imageRow
        self.imageCol = imageCol
        self.stageX = stageX
        self.stageY = stageY
        self.rotation = rotation
        if force_pixelsize:
            pixelsize = 0.100 if pixelsize is None else pixelsize
        self.pixelsize = pixelsize

    def to_dict(self):
        '''return a dictionary representation of this object
        no inputs
        returns:
        json dictionary of object
        '''
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
        d = {k: v for k, v in d.items() if v is not None}
        return d

    def from_dict(self, d):
        '''set this object equal to the fields found in dictionary
        inputs:
        --d:dictionary to use to update
        '''
        if d is not None:
            self.sectionId = d.get('sectionId')
            self.cameraId = d.get('camera')
            self.scopeId = d.get('temca')
            self.imageRow = d.get('imageRow')
            self.imageCol = d.get('imageCol')
            self.stageX = d.get('stageX')
            self.stageY = d.get('stageY')
            self.rotation = d.get('rotation')
            self.pixelsize = d.get('pixelsize')


class TileSpec:
    '''Fundamental class of render that store image tiles and their transformations
    init:
    Keyword arguments:
    --tileId: unique string specifying a tile's identity
    --z: z values this tile exists within (float)
    --width: width in pixels of the raw tile
    --height: height in pixels of the raw tile
    --imageUrl: an image path that can be accessed by the render server, with an ImageJ.open command
    or as an s3 url.  files on disk should be specified with file:
    --maskUrl: an image path that can be accessed by the render server which can be interpreted as an
    alpha mask for the image (same as spec imageUrl)
    --minint: pixel intensity value to display as black in a linear colormap (default 0)
    --maxint: pixel intensity value to display as white in a linaer colormap (default 65535)
    --layout: a Layout object for this tile
    --tforms: a list of Transform objects (see AffineModel, TransformList, Polynomial2DTransform, Transform, ReferenceTransform) to apply to this tile
    --inputfilters: a list of filters to apply to this tile (not yet implemented)
    --scale3Url: url of a mipmap level 3 image of this tile  (deprecated, see mipMapLevels, but will override)
    --scale2Url: url of a mipmap level 2 image of this tile  (deprecated, see mipMapLevels, but will override)
    --scale1Url: url of a mipmap level 1 image of this tile (deprecated, see mipMapLevels, but will override)
    --mipMapLevels: a list of MipMapLevel objects for this tile
    --json: a json dictionary to initialize this object with (if not None overrides and ignores all keyword arguments)

    '''
    def __init__(self, tileId=None, z=None, width=None, height=None,
                 imageUrl=None, maskUrl=None,
                 minint=0, maxint=65535, layout=None, tforms=[],
                 inputfilters=[], scale3Url=None, scale2Url=None,
                 scale1Url=None, json=None, mipMapLevels=[], **kwargs):
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
            self.inputfilters = inputfilters
            self.layout = Layout(**kwargs) if layout is None else layout

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
        '''method to produce a json tilespec for this tile
        returns a json compatible dictionary
        '''
        thedict = {}
        thedict['tileId'] = self.tileId
        thedict['z'] = self.z
        thedict['width'] = self.width
        thedict['height'] = self.height
        thedict['minIntensity'] = self.minint
        thedict['maxIntensity'] = self.maxint
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

        # TODO filters not implemented
        '''
        if len(self.inputfilters):
            thedict['inputfilters'] = {}
            thedict['inputfilters']['type'] = 'list'
            thedict['inputfilters']['specList'] = [f.to_dict() for f
                                                   in self.inputfilters]
        '''

        thedict = {k: v for k, v in thedict.items() if v is not None}
        return thedict

    def from_dict(self, d):
        '''Method to load tilespec from json dictionary'''
        self.tileId = d['tileId']
        self.z = d['z']
        self.width = d['width']
        self.height = d['height']
        self.minint = d.get('minIntensity')
        self.maxint = d.get('maxIntensity')
        self.frameId = d.get('frameId')
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

        tfl = TransformList(json=d['transforms'])
        self.tforms = tfl.tforms

        # TODO filters not implemented -- should skip
        '''
        self.inputfilters = []
        if d.get('inputfilters', None) is not None:
            for f in d['inputfilters']['specList']:
                f = Filter()
                f.from_dict(f)
                self.inputfilters.append(f)
        '''


class MipMapLevel:
    '''
    MipMapLevel class to represent a level of an image pyramid.
    Can be put in dictionary formatting using dict(mML)

    init:
        level -- integer level of 2x downsampling represented by mipmaplevel
        imageUrl (optional) -- url corresponding to image
        maskUrl (optional) -- url corresponding to mask
    '''
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
    '''
    Image Pyramid class representing a set of MipMapLevels which correspond
        to mipmapped (continuously downsmapled by 2x) representations
        of an image at level 0
    Can be put into dictionary formatting using dict(ip) or OrderedDict(ip)

    init:
        mipMapLevels -- list of MipMapLevel objects
    append:
        adds MipmapLevel without checking if it exists
        input: MipMapLevel object
    update:
        adds MipMapLevel object replacing a corresponding level if it exists
        input: MipMapLevel object
    to_ordered_dict:
        input: key(optional) -- key to sort ordered dictionary
            default sort by level via lambda x: x[0]
    '''
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
    '''renderapi call to get a specific tilespec by tileId
    note that this will return a tilespec with resolved transform references
    by accessing the render-parameters version of this tile

    args:
    --stack: name of render stack to retrieve
    --tile: tileId of tile to retrieve
    keyword args:
    --render: render connect object
    (or host, port, owner, project)
    --session: sessions object to connect with (default make a new one)
    outputs:
    A TileSpec object with dereferenced transforms
    '''

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/render-parameters" % (tile)
    r = session.get(request_url)
    try:
        tilespec_json = r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
    return TileSpec(json=tilespec_json['tileSpecs'][0])

@renderaccess
def get_tile_spec_raw(stack, tile, host=None, port=None, owner=None,
                  project=None, session=requests.session(),
                  render=None, **kwargs):
    '''renderapi call to get a specific tilespec by tileId
    note that this will return a tilespec without resolved transform references
    
    args:
    --stack: name of render stack to retrieve
    --tile: tileId of tile to retrieve
    keyword args:
    --render: render connect object
    (or host, port, owner, project)
    --session: sessions object to connect with (default make a new one)
    outputs:
    a TileSpec object with referenced transforms if present
    '''

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/" % (tile)
    r = session.get(request_url)
    try:
        tilespec_json = r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
    return TileSpec(json=tilespec_json)

@renderaccess
def get_tile_specs_from_minmax_box(stack, z, xmin, xmax, ymin, ymax,
                                   scale=1.0, host=None,
                                   port=None, owner=None, project=None,
                                   session=requests.session(),
                                   render=None, **kwargs):
    '''renderapi call to get all tilespec that exist within a 2d bounding box
    specified with min and max x,y values
    note that this will return a tilespec with resolved transform references
    
    args:
    --stack: name of render stack to retrieve
    --z: z value of bounding box (float)
    --xmin: minimum x value (float)
    --ymin: minimum y value (float)
    --xmax: maximum x value (float)
    --ymax: maximum y value (float)
    keyword args:
    --scale: scale to use when retrieving render parameters (not important)
    --render: render connect object
    (or host, port, owner, project)
    --session: sessions object to connect with (default make a new one)
    outputs:
    a list of TileSpec objects
    '''                              
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
    '''renderapi call to get all tilespec that exist within a 2d bounding box
    specified with min  x,y values and width, height
    note that this will return a tilespec with resolved transform references
    
    args:
    --stack: name of render stack to retrieve
    --z: z value of bounding box (float)
    --xmin: minimum x value (float)
    --ymin: minimum y value (float)
    --xmax: maximum x value (float)
    --ymax: maximum y value (float)
    keyword args:
    --scale: scale to use when retrieving render parameters (not important)
    --render: render connect object
    (or host, port, owner, project)
    --session: sessions object to connect with (default make a new one)
    outputs:
    a list of TileSpec objects
    '''         
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%3.2f/render-parameters" % (
                      z, x, y, width, height, scale)
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        tilespecs_json = r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
    return [TileSpec(json=tilespec_json)
            for tilespec_json in tilespecs_json['tileSpecs']]


@renderaccess
def get_tile_specs_from_z(stack, z, host=None, port=None,
                          owner=None, project=None, session=requests.session(),
                          render=None, **kwargs):
    '''
    input:
        stack -- string render stack
        z -- render z
    keyword arguments:
        render -- render connect object (or host, port, owner, project)
        session -- requests.session (default start a new one)
    output: list of TileSpec objects from that stack at that z
    '''
    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/%f/tile-specs' % (z)
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        tilespecs_json = r.json()
    except Exception as e:
        logger.error(e)
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
    '''get flat list of tilespecs for stack using i for sl in l for i in sl
    input: 
    stack -- string render stack
    keyword arguments:
    render -- render connect object (or host, port, owner, project)
    session -- requests.session (default start a new one)
    output:
    List of TileSpec objects from the stack
    '''
    return [i for sl in [
        get_tile_specs_from_z(stack, z, host=host, port=port,
                              owner=owner, project=project, session=session)
        for z in get_z_values_for_stack(stack, host=host, port=port,
                                        owner=owner, project=project,
                                        session=session)] for i in sl]

# TODO: ADD FEATURES THAT REQUIRED THESE TO SUPPORT.. NOT YET FULLY IMPLEMENTED
# class ResolvedTileSpecMap:
#     def __init__(self, tilespecs=[], transforms=[]):
#         self.tilespecs = tilespecs
#         self.transforms = transforms

#     def to_dict(self):
#         d = {}
#         d['tileIdToSpecMap'] = {}
#         for ts in self.tilespecs:
#             d['tileIdToSpecMap'][ts.tileId] = ts.to_dict()
#         d['transformIdToSpecMap'] = {}
#         for tf in self.transforms:
#             d['transformIdToSpecMap'][tf.transformId] = tf.to_dict()
#         return d

#     def from_dict(self, d):
#         tsmap = d['tileIdToSpecMap']
#         tfmap = d['transformIdToSpecMap']
#         for tsd in tsmap.values():
#             ts = TileSpec()
#             ts.from_dict(tsd)
#             self.tilespecs.append(ts)
#         for tfd in tfmap.values():
#             tf = load_transform_json(tfd)
#             self.transforms.append(tf)


# class ResolvedTileSpecCollection:
#     def __init__(self, tilespecs=[], transforms=[]):
#         self.tilespecs = tilespecs
#         self.transforms = transforms

#     def to_dict(self):
#         d = {}
#         d['tileCount'] = len(self.tilespecs)
#         d['tileSpecs'] = [ts.to_dict() for ts in self.tilespecs]
#         d['transformCount'] = len(self.transforms)
#         d['transformSpecs'] = [tf.to_dict() for tf in self.transforms]
#         return d

#     def from_dict(self, d):
#         self.tilespecs = []
#         self.transforms = []
#         for i in range(d['tileCount']):
#             ts = TileSpec()
#             ts.from_dict(d['tileSpecs'][i])
#             self.tilespecs.append(ts)
#         for i in range(d['tranformCount']):
#             tfd = d['transformSpecs'][i]
#             tf = load_transform_json(tfd)
#             self.transforms.append(tf)


# class Filter:
#     def __init__(self, classname, params={}):
#         self.classname = classname
#         self.params = params

#     def to_dict(self):
#         d = {}
#         d['className'] = self.classname
#         d['params'] = self.params
#         return d

#     def from_dict(self, d):
#         self.classname = d['className']
#         self.params = d['params']
