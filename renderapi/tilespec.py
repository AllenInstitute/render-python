#!/usr/bin/env python
from .render import format_preamble, renderaccess
from .utils import NullHandler
from .stack import get_z_values_for_stack
from .transform import TransformList
from .errors import RenderError
from collections import OrderedDict
import logging
import requests

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Layout:
    '''Layout class to describe acquisition settings
    inputs:

    Args:
        sectionId (str): sectionId this tile was taken from
        scopeId (str): what microscope this came from
        cameraId (str): camera this was taken with
        imageRow (int): what row from a row,col layout this was taken
        imageCol (int): column from a row,col layout this was taken
        stageX (float): X stage coordinates for where this was taken
        stageY (float): Y stage coordinates for where this taken 
        rotation (float): angle of camera when this was taken
        pixelsize (float): effective size of pixels (in units of choice) 
        force_pixelsize (bool): whether to default pixelsize to 0.1 
  
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
        
        Returns:
            dict: json compatible dictionary of this object
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

        Args:
            d (dict): dictionary to use to update
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

    Args:
        tileId (str): unique string specifying a tile's identity
        z (float): z values this tile exists within 
        width (int): width in pixels of the raw tile
        height (int): height in pixels of the raw tile
        imageUrl (str): an image path that can be accessed by the render server,
            with an ImageJ.open command or as an s3 url.
            Files on disk should be specified with file:
        maskUrl (str): an image path that can be accessed by the render server
            which can be interpreted as an
            alpha mask for the image (same as spec imageUrl)
        minint (int): pixel intensity value to display as black in a
            linear colormap (default 0)
        maxint (int): pixel intensity value to display as white in a
            linear colormap (default 65535)
        layout (Layout): a Layout object for this tile
        tforms (list[Transform]): Transform objects
            (see :class:`.transform.AffineModel`, 
            :class:`.transform.TransformList`, 
            :class:`.transform.Polynomial2DTransform`,
            :class:`.transform.Transform`, 
            :class:`.transform.ReferenceTransform`) to apply to this tile
        inputfilters (list): a list of filters to apply to
            this tile (not yet implemented)
        mipMapLevels (list[MipMapLevel]): :class:`MipMapLevel` objects for this tile
        json (dict or None): dictionary to initialize this object with
            (if not None overrides and ignores all keyword arguments)
        scale3Url (str): url of a mipmap level 3 image of this tile
            (DEPRECATED, use mipMapLevels, but will override)
        scale2Url (str): url of a mipmap level 2 image of this tile
            (DEPRECATED, use mipMapLevels, but will override)
        scale1Url (str): url of a mipmap level 1 image of this tile
            (DEPRECATED, use mipMapLevels, but will override)

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

        Returns:
            dict: json compatible dictionary representation of this object
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
        '''Method to load tilespec from json dictionary
        
        Args:
            d (dict): dictionary to use to set properties of this object
        '''
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

    Args:
        level (int): level of 2x downsampling represented by mipmaplevel
        imageUrl (str or None): url corresponding to image
        maskUrl (str or None): url corresponding to mask
    '''
    def __init__(self, level, imageUrl=None, maskUrl=None):
        self.level = level
        self.imageUrl = imageUrl
        self.maskUrl = maskUrl

    def to_dict(self):
        '''
        Returns:
            dict: json compatible dictionary representaton
        '''
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

    Args:
        mipMapLevels (list[MipMapLevel]): list of :class:`MipMapLevel` objects
    
    '''
    def __init__(self, mipMapLevels=[]):
        self.mipMapLevels = mipMapLevels

    def to_dict(self):
        '''return dictionary representation of this object'''
        return dict(self.__iter__())

    def to_ordered_dict(self, key=None):
        '''returns :class:`OrderedDict` represention of this object, ordered by mipmapLevel'''
        return OrderedDict(sorted(
            self.__iter__(), key=((lambda x: x[0]) if key
                                  is None else key)))

    def append(self, mmL):
        '''appends a MipMapLevel to this ImagePyramid

        Args:
            mml (MipMapLevel): MipMapLevel to append
        '''
        self.mipMapLevels.append(mmL)

    def update(self, mmL):
        '''updates the ImagePyramid with this MipMapLevel

        Args:
            mml (MipMapLevel): mipmap level to update in pyramid
        '''
        self.mipMapLevels = [
            l for l in self.mipMapLevels if l.level != mmL.level]
        self.append(mmL)

    def get(self, to_get):
        '''gets a specific mipmap level in dictionary form

        Args:
            to_get (int): mipmaplevel to get

        Returns:
            dict: dictionary representation of requested MipMapLevel
        '''
        return self.to_dict()[to_get]  # TODO should this default

    @property
    def levels(self):
        '''list of MipMapLevels in this ImagePyramid'''
        return [int(i.level) for i in self.mipMapLevels]

    def __iter__(self):
        return iter([
            l for sl in [list(mmL) for mmL in self.mipMapLevels] for l in sl])


@renderaccess
def get_tile_spec_renderparameters(stack, tile, host=None, port=None,
                                   owner=None, project=None,
                                   session=requests.session(),
                                   render=None, **kwargs):
    '''renderapi call to get the render parameters of a specific tileId

    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): name of render stack to retrieve
        tile (str): tileId of tile to retrieve    
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with 
    Returns:
        dict: render-parameters json with the tilespec for that tile and dereferenced transforms
        TODO provide example
    '''

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/render-parameters" % (tile)
    r = session.get(request_url)
    try:
        tilespec_json = r.json()
        return tilespec_json
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_tile_spec(stack, tile, host=None, port=None, owner=None,
                  project=None, session=requests.session(),
                  render=None, **kwargs):
    '''renderapi call to get a specific tilespec by tileId
    note that this will return a tilespec with resolved transform references
    by accessing the render-parameters version of this tile

    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): name of render stack to retrieve
        tile (str): tileId of tile to retrieve    
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with 
    Returns:
        TileSepc: TileSpec with dereferenced transforms
    '''

    try:
        tilespec_json = get_tile_spec_renderparameters(
            stack, tile, host, port, owner, project, session)
        return TileSpec(json=tilespec_json['tileSpecs'][0])
    except Exception as e:
        logger.error(e)


@renderaccess
def get_tile_spec_raw(stack, tile, host=None, port=None, owner=None,
                      project=None, session=requests.session(),
                      render=None, **kwargs):
    '''renderapi call to get a specific tilespec by tileId
    note that this will return a tilespec without resolved transform references

    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): name of render stack to retrieve
        tile (str): tileId of tile to retrieve    
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with
    Returns:
        TileSepc: TileSpec with referenced transforms intact
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
        raise RenderError(r.text)
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

    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): name of render stack to retrieve
        z (float): z value of bounding box
        xmin (float): minimum x value
        ymin (float): minimum y value 
        xmax (float): maximum x value 
        ymax (float): maximum y value 
        scale (float): scale to use when retrieving render parameters (not important)
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with
    Returns:
        list[TileSpec]:TileSpec objects with dereferenced tansforms
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
    specified with min x,y values and width, height
    note that this will return a tilespec with resolved transform references

    :func:`renderapi.render.renderaccess` decorated function

     Args:
        stack (str): name of render stack to retrieve
        z (float): z value of bounding box
        x (float): minimum x value
        y (float): minimum y value 
        width (float): width of box (in scale=1.0 units)
        height (float): height of box (in scale=1.0 units)  
        scale (float): scale to use when retrieving render parameters (not important)
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with
    Returns:
        list[TileSpec]:TileSpec objects with dereferenced tansforms
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
        raise RenderError(r.text)
    return [TileSpec(json=tilespec_json)
            for tilespec_json in tilespecs_json['tileSpecs']]


@renderaccess
def get_tile_specs_from_z(stack, z, host=None, port=None,
                          owner=None, project=None, session=requests.session(),
                          render=None, **kwargs):
    '''
    Get all TileSpecs in a specific z values. Returns referenced transforms.

    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): render stack
        z (float): render z
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with
    Returns:
        list[TileSpec]: list of TileSpec objects from that stack at that z
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
        raise RenderError(r.text)

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
    
    :func:`renderapi.render.renderaccess` decorated function

    Args:
        stack (str): render stack
        render (renderapi.render.Render): render connect object
        session (requests.sessions.Session): sessions object to connect with
    Returns:
        list[TileSpec]: list of TileSpec objects from that stack
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
