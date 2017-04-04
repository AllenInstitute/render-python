#!/usr/bin/env python

import io
import requests
from PIL import Image
import numpy as np
import logging
from .render import format_preamble, renderaccess
from .utils import NullHandler, jbool

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

# define acceptable image formats -- currently render generates png, jpeg, tiff
IMAGE_FORMATS = {'png': 'png-image',
                 '.png': 'png-image',
                 'jpg': 'jpeg-image',
                 'jpeg': 'jpeg-image',
                 '.jpg': 'jpeg-image',
                 'tif': 'tiff-image',
                 '.tif': 'tiff-image',
                 'tiff': 'tiff-image',
                 None: 'png-image'}  # Default to png


@renderaccess
def get_bb_image(stack, z, x, y, width, height, scale=1.0,
                 minIntensity=None, maxIntensity=None,
                 host=None, port=None, owner=None, project=None,
                 img_format=None, session=requests.session(),
                 render=None, **kwargs):
    '''
    render image from a bounding box defined in xy and return numpy array:
        z: layer
        x: leftmost point of bounding rectangle
        y: topmost pont of bounding rectangle
        width: extent to right in x
        height: extent down in y
    '''
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%3.2f/%s?" % (
                      z, x, y, width, height, scale, image_ext)
    args = []
    if minIntensity is not None:
        args += ['minIntensity=%d' % minIntensity]
    if maxIntensity is not None:
        args += ['maxIntensity=%d' % maxIntensity]
    if len(args) > 0:
        args = "&".join(args)
        request_url += args

    r = session.get(request_url)
    try:
        image = np.asarray(Image.open(io.BytesIO(r.content)))
        return image
    except Exception as e:
        logger.error(e)
        logger.error(r.text)


@renderaccess
def get_tile_image_data(stack, tileId, normalizeForMatching=True,
                        host=None, port=None, owner=None, project=None,
                        img_format=None, session=requests.session(),
                        render=None, **kwargs):
    '''
    render image from a tile with all transforms and return numpy array
    '''
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/%s" % (tileId, image_ext)
    if normalizeForMatching:
        request_url += "?normalizeForMatching=true"
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        img = Image.open(io.BytesIO(r.content))
        array = np.asarray(img)
        return array
    except Exception as e:
        logger.error(e)
        logger.error(r.text)


@renderaccess
def get_section_image(stack, z, scale=1.0, filter=False,
                      maxTileSpecsToRender=None, img_format=None,
                      host=None, port=None, owner=None, project=None,
                      session=requests.session(),
                      render=None, **kwargs):
    '''
    z: layer Z
    scale: float -- linear scale at which to render image (e.g. 0.5)
    filter: boolean -- whether or not to apply Khaled's preferred filter
    maxTileSpecsToRender: int -- maximum number of tile specs in rendering
    img_format: string -- format defined by IMAGE_FORMATS
    '''
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/{}/{}'.format(z, image_ext)
    qparams = {'scale': scale, 'filter': jbool(filter)}
    if maxTileSpecsToRender is not None:
        qparams.update({'maxTileSpecsToRender': maxTileSpecsToRender})
    r = session.get(request_url, params=qparams)
    return np.asarray(Image.open(io.BytesIO(r.content)))
