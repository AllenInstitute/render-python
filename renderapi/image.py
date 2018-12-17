#!/usr/bin/env python

import io
import requests
from PIL import Image
import numpy as np
import logging
from .render import format_preamble, renderaccess
from .errors import RenderError
from .utils import NullHandler, jbool, get_json

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
                 'tiff16': 'tiff16-image',
                 None: 'png-image'}  # Default to png


def _strip_None_value_dictitems(d, exclude_keys=[]):
    return {k: v for k, v in d.items()
            if v is not None and k not in exclude_keys}


@renderaccess
def get_bb_renderparams(stack, z, x, y, width, height, scale=1.0,
                        channel=None, minIntensity=None, maxIntensity=None,
                        binaryMask=None, filter=None, filterListName=None,
                        convertToGray=None, excludeMask=None,
                        host=None, port=None, owner=None,
                        project=None, session=requests.session(),
                        render=None, **kwargs):

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%f/render-parameters" % (
        z, x, y, width, height, scale)

    qparams = _strip_None_value_dictitems({
        "minIntensity": minIntensity,
        "maxIntensity": maxIntensity,
        "binaryMask": binaryMask,
        "filter": filter,
        "filterListName": filterListName,
        "convertToGray": convertToGray,
        "excludeMask": excludeMask,
        "channels": channel})

    return get_json(session, request_url, params=qparams)


@renderaccess
def get_bb_image(stack, z, x, y, width, height, scale=1.0,
                 channel=None,
                 minIntensity=None, maxIntensity=None, binaryMask=None,
                 filter=None, maxTileSpecsToRender=None,
                 host=None, port=None, owner=None, project=None,
                 img_format=None, session=requests.session(),
                 render=None, **kwargs):
    """render image from a bounding box defined in xy and return numpy array:

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        name of render stack to get image from
    z : float
        z value to render
    x : int
        leftmost point of bounding rectangle
    y : int
        topmost pont of bounding rectangle
    width : int
        number of units @scale=1.0 to right (+x() of bounding box to render
    height : int
        number of units @scale=1.0 down (+y) of bounding box to render
    scale : float
        scale to render image at (default 1.0)
    channel : str
        channel name to render, (e.g. 'DAPI') or a weighted average of channels of the format
        e.g 'DAPI___.8___GFP___.2'
    binaryMask : bool
        whether to treat maskimage as binary
    maxTileSpecsToRender : int
        max number of tilespecs to render
    filter : bool
        whether to use server side filtering
    render : :class:`renderapi.render.Render`
        render connect object
    session : :class:`requests.sessions.Session`
        sessions object to connect with

    Returns
    -------
    numpy.array
        [N,M,:] array of image data from render

    Raises
    ------
    RenderError
    """  # noqa: E501
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:  # pragma: no cover
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%f/%s" % (
        z, x, y, width, height, scale, image_ext)
    qparams = {}
    if minIntensity is not None:
        qparams['minIntensity'] = minIntensity
    if maxIntensity is not None:
        qparams['maxIntensity'] = maxIntensity
    if binaryMask is not None:
        qparams['binaryMask'] = jbool(binaryMask)
    if filter is not None:
        qparams['filter'] = jbool(filter)
    if maxTileSpecsToRender is not None:
        qparams['maxTileSpecsToRender'] = maxTileSpecsToRender
    if channel is not None:
        qparams.update({'channels': channel})

    r = session.get(request_url, params=qparams)
    try:
        image = np.asarray(Image.open(io.BytesIO(r.content)))
        return image
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        return RenderError(r.text)


# TODO get tile image renderparams
@renderaccess
def get_tile_image_renderparams():
    pass


@renderaccess
def get_tile_image_data(stack, tileId, channel=None, normalizeForMatching=True,
                        excludeAllTransforms=False, scale=None,
                        filter=None, host=None, port=None, owner=None,
                        project=None, img_format=None,
                        session=requests.session(), render=None, **kwargs):
    """render image from a tile with all transforms and return numpy array

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        name of render stack to get tile from
    tileId : str
        tileId of tile to render
    channel : str
        channel name to render, (e.g. 'DAPI') or a weighted average of channels of the format
        e.g 'DAPI___.8___GFP___.2'
    normalizeForMatching : bool
        whether to render the tile with transformations
        removed ('local' coordinates)
    removeAllOption : bool
        whether to remove all transforms from image when
        doing normalizeForMatching some versions of render
        only remove the last transform from list.
        (or remove till there are max 3 transforms)
    scale : float
        force scale of image
    filter : bool
        whether to apply server side filtering to image
    img_format : str
        image format: one of IMAGE_FORMATS = 'png','.png','jpg',
        'jpeg','.jpg','tif','.tif','tiff'
    render : :obj:`renderapi.render.Render`
        render connect object
    session : :obj:`requests.sessions.Session`
        sessions object to connect with

    Returns
    -------
    numpy.array
        [N,M,:] array of image data from render

    Raises
    ------
    RenderError

    """  # noqa: E501
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:  # pragma: no cover
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/%s" % (tileId, image_ext)

    qparams = {}
    if normalizeForMatching:
        qparams['normalizeForMatching'] = jbool(normalizeForMatching)
    if scale is not None:
        qparams['scale'] = scale
    if filter is not None:
        qparams['filter'] = jbool(filter)
    if excludeAllTransforms is not None:
        qparams['excludeAllTransforms'] = jbool(excludeAllTransforms)
    if channel is not None:
        qparams.update({'channels': channel})
    logger.debug(request_url)

    r = session.get(request_url, params=qparams)
    try:
        img = Image.open(io.BytesIO(r.content))
        array = np.asarray(img)
        return array
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        return RenderError(r.text)


# TODO renderparams for section
def get_section_renderparams():
    pass


@renderaccess
def get_section_image(stack, z, scale=1.0, channel=None,
                      filter=False,
                      maxTileSpecsToRender=None, img_format=None,
                      host=None, port=None, owner=None, project=None,
                      session=requests.session(),
                      render=None, **kwargs):
    """render an section of image

    :func:`renderapi.render.renderaccess` decorated function


    Parameters
    ----------
    stack : str
        name of render stack to render image from
    z : float
        layer Z
    scale : float
        linear scale at which to render image (e.g. 0.5)
    channel: str
        channel name to render, (e.g. 'DAPI') or a weighted average of channels of the format
        e.g 'DAPI___.8___GFP___.2'
    filter : bool
        whether or not to apply server side filtering
    maxTileSpecsToRender : int
        maximum number of tile specs in rendering
    img_format : str
        one of IMAGE_FORMATS 'png','.png','jpg','jpeg',
        '.jpg','tif','.tif','tiff'
    render : :obj:`renderapi.render.Render`
        render connect object
    session : requests.sessions.Session
        sessions object to connect with

    Returns
    -------
    numpy.array
        [N,M,:] array of image data of section from render

    Examples
    --------
    ::

        >>> import renderapi
        >>> render = renderapi.render.connect('server',8080,'me','myproject')
        >>> img = render.run(renderapi.stack.get_section_image,'mystack',3.0)

    """  # noqa: E501
    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:  # pragma: no cover
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/{}/{}'.format(z, image_ext)
    qparams = {'scale': scale, 'filter': jbool(filter)}
    if maxTileSpecsToRender is not None:
        qparams.update({'maxTileSpecsToRender': maxTileSpecsToRender})
    if channel is not None:
        qparams.update({'channels': channel})

    r = session.get(request_url, params=qparams)
    return np.asarray(Image.open(io.BytesIO(r.content)))
