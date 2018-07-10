from collections import MutableMapping
from .errors import RenderError
import logging
from .utils import NullHandler
import warnings

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class MipMap:
    """MipMap class to represent a image and its mask

    Attributes
    ----------
    imageUrl : str or None
        uri corresponding to image
    maskUrl : str or None
        uri corresponding to mask

    """

    def __init__(self, imageUrl=None, maskUrl=None):
        self.imageUrl = imageUrl
        self.maskUrl = maskUrl

    def to_dict(self):
        """
        Returns
        -------
        dict
            json compatible dictionary representaton
        """
        return dict(self.__iter__())

    def _formatUrls(self):
        d = {}
        if self.imageUrl is not None:
            d.update({'imageUrl': self.imageUrl})
        if self.maskUrl is not None:
            d.update({'maskUrl': self.maskUrl})
        return d

    def __setitem__(self, key, value):
        if key == 'imageUrl':
            self.imageUrl = value
        elif key == 'maskUrl':
            self.maskUrl = value
        else:
            raise KeyError('{} not a valid mipmap attribute'.format(key))

    def __getitem__(self, key):
        if key == 'imageUrl':
            return self.imageUrl
        if key == 'maskUrl':
            return self.maskUrl
        else:
            raise KeyError(
                '{} is not a valid attribute of a mipmapLevel'.format(key))

    def __iter__(self):
        return iter(self._formatUrls().items())

    def __eq__(self, b):
        try:
            return all([self.imageUrl == b.imageUrl,
                        self.maskUrl == b.maskUrl])
        except AttributeError as e:
            return all([self.imageUrl == b.get('imageUrl'),
                        self.maskUrl == b.get('maskUrl')])


class MipMapLevel:
    """MipMapLevel class to represent a level of an image pyramid.
    Can be put in dictionary formatting using dict(mML)

    Attributes
    ----------
    level : int
        level of 2x downsampling represented by mipmaplevel
    imageUrl : str or None
        uri corresponding to image
    maskUrl : str or None
        uri corresponding to mask

    """

    def __init__(self, level, imageUrl=None, maskUrl=None):
        warnings.warn(
            "use of mipmaplevels deprecated, use MipMap and ImagePyramid",
            DeprecationWarning)
        self.level = level
        self.mipmap = MipMap(imageUrl, maskUrl)

    def to_dict(self):
        """
        Returns
        -------
        dict
            json compatible dictionary representaton
        """
        return dict(self.mipmap)

    def __getitem__(self, key):
        if key == 'imageUrl':
            return self.mipmap.imageUrl
        if key == 'maskUrl':
            return self.mipmap.maskUrl
        else:
            raise KeyError(
                '{} is not a valid attribute of a mipmapLevel'.format(key))

    def __iter__(self):
        return iter(self.to_dict().items())

    def __eq__(self, b):
        return self.mipmap == b.mipmap


class TransformedDict(MutableMapping):
    """A dictionary that applies an arbitrary key-altering
       function before accessing the keys"""

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key


class ImagePyramid(TransformedDict):
    '''Image Pyramid class representing a set of MipMapLevels which correspond
    to mipmapped (continuously downsmapled by 2x) representations
    of an image at level 0
    Can be put into dictionary formatting using dict(ip) or OrderedDict(ip)
    '''

    def __keytransform__(self, key):
        try:
            level = int(key)
        except ValueError as e:
            raise RenderError("{} is not a valid mipmap level".format(key))
        if level < 0:
            raise RenderError(
                "{} is not a valid mipmap level (less than 0)".format(key))
        return "{}".format(level)

    def to_dict(self):
        return {k: v.to_dict() for k, v in self.items()}

    @classmethod
    def from_dict(cls, d):
        return cls({l: MipMap(v.get('imageUrl', None),
                              v.get('maskUrl', None))
                    for l, v in d.items()})

    def __iter__(self):
        return iter(sorted(self.store))

    @property
    def levels(self):
        """list of MipMapLevels in this ImagePyramid"""
        return self.store.keys()
