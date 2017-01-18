#!/usr/bin/env python

import io
import requests
from PIL import Image
import numpy as np
from render import Render, format_baseurl, format_preamble

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


def get_bb_image(stack, z, x, y, width, height, render=None, scale=1.0,
                 host=None, port=None, owner=None, project=None,
                 img_format=None, session=requests.session(), **kwargs):
    '''
    render image from a bounding box defined in xy and return numpy array:
        z: layer
        x: leftmost point of bounding rectangle
        y: topmost pont of bounding rectangle
        width: extent to right in x
        height: extent down in y
    '''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_bb_image(
            stack, z, x, y, width, height,
            **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'scale': scale, 'img_format': img_format,
                   'session': session}))

    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/box/%d,%d,%d,%d,%3.2f/%s" % (
                      z, x, y, width, height, scale, image_ext)
    r = session.get(request_url)
    try:
        image = np.asarray(Image.open(io.BytesIO(r.content)))
        return image
    except:
        logging.error(r.text)


def get_tile_image_data(stack, tileId, render=None,
                        normalizeForMatching=True, host=None, port=None,
                        owner=None, project=None, img_format=None,
                        session=requests.session(), verbose=False, **kwargs):
    '''
    render image from a tile with all transforms and return numpy array
    '''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_tile_image_data(stack, tileId, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            **{'img_format': img_format, 'session': session}))

    try:
        image_ext = IMAGE_FORMATS[img_format]
    except KeyError as e:
        raise ValueError('{} is not a valid render image format!'.format(e))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/png-image" % (tileId)
    if normalizeForMatching:
        request_url += "?normalizeForMatching=true"
    if verbose:
        print request_url
    r = session.get(request_url)
    try:
        img = Image.open(io.BytesIO(r.content))
        array = np.asarray(img)
        return array
    except:
        logging.error(r.text)
        return None
