
try:
    from urlparse import urlparse
    from urllib import unquote, urlopen
except ImportError as e:
    from urllib.parse import urlparse, unquote 
    from urllib.request import urlopen
import tifffile
import numpy as np
import os
from PIL import Image
import boto3
import tempfile
import io

def read_mipmap_image(mml,apply_mask=False):
    """function to read a raw image from a mipmaplevel 

    Parameters
    ==========
    mml : renderapi.image_pyramid.MipMapLevel
        mip map level to read image of
    apply_mask: bool
        whether to apply mask to image (default=False)
    
    Returns
    =======
    numpy.array
        numpy array of image
    """
    img= read_image_url(mml.imageUrl)
    if apply_mask:
        mask = read_mipmap_mask(mml)
        mask = np.array(mask,dtype=np.float)/np.max(mask)
        img = np.array(img*mask,dtype=img.dtype)
    return img

def read_mipmap_mask(mml):
    """function to read mask from a mipmaplevel

    Parameters
    ==========
    mml : renderapi.image_pyramid.MipMapLevel
        mipmaplevel to read image from

    Returns
    =======
    numpy.array
        numpy array of mask
    """
    return read_image_url(mml.maskUrl)

def read_image_url(url):
    """function to read in a render url to an image to a numpy array

    Parameters
    ==========
    url: str or unicode
        url to image to read
    dtype: numpy.dtype or None
        dtype to convert image to (default to our judgement)

    Returns
    =======
    numpy.array
        an numpy array containing the image data
    """
    (scheme, netloc, path, params, query, fragment) = urlparse(url)
    filepath = unquote(path)
    filetype = os.path.splitext(filepath)[1][1:]
    
    if (scheme == 'file') or (scheme == ''):
        if filetype == 'tif':
            array = tifffile.imread(filepath)
        else:
            with open(filepath, 'r') as fp:
                array = np.asarray(Image.open(fp))

    if (scheme == 'http') or (scheme == 'https'):
        with urlopen(url) as fp:
            array = np.asarray(Image.open(fp))
    if (scheme == 's3'):
        client = boto3.client('s3')
        path=path[1:]
        if filetype == 'tif':
            fp,tfile = tempfile.mkstemp()
            client.download_file(netloc, path, tfile)
            array = tifffile.imread(tfile)
            os.remove(tfile)
        else:
            obj = client.get_object(Bucket=netloc,Key=path)
            array = np.asarray(Image.open(io.BytesIO(obj['Body'].read())))

    return array
