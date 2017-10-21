from collections import OrderedDict

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
        self.level = level
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

    def __iter__(self):
        return iter([(self.level, self._formatUrls())])


class ImagePyramid:
    '''Image Pyramid class representing a set of MipMapLevels which correspond
    to mipmapped (continuously downsmapled by 2x) representations
    of an image at level 0
    Can be put into dictionary formatting using dict(ip) or OrderedDict(ip)

    Attributes
    ----------
    mipMapLevels : :obj:`list` of :class:`MipMapLevel`
        list of :class:`MipMapLevel` objects defining image pyramid

    '''
    def __init__(self, mipMapLevels=[]):
        self.mipMapLevels = mipMapLevels

    def to_dict(self):
        """return dictionary representation of this object"""
        return dict(self.__iter__())

    def to_ordered_dict(self, key=None):
        """returns :class:`OrderedDict` represention of this object,
        ordered by mipmapLevel

        Parameters
        ----------
        key : func
            function to sort ordered dict of
            :class:`mipMapLevel` dicts (default is by level)

        Returns
        -------
        OrderedDict
            sorted dictionary of :class:`mipMapLevels` in ImagePyramid

        """
        return OrderedDict(sorted(
            self.__iter__(), key=((lambda x: x[0]) if key
                                  is None else key)))

    def append(self, mmL):
        """appends a MipMapLevel to this ImagePyramid

        Parameters
        ----------
        mml : :class:`MipMapLevel`
            :class:`MipMapLevel` to append
        """
        self.mipMapLevels.append(mmL)

    def update(self, mmL):
        """updates the ImagePyramid with this MipMapLevel.
        will overwrite existing mipMapLevels with same level

        Args:
            mml (MipMapLevel): mipmap level to update in pyramid
        """
        self.mipMapLevels = [
            l for l in self.mipMapLevels if l.level != mmL.level]
        self.append(mmL)

    def get(self, to_get):
        """gets a specific mipmap level in dictionary form

        Parameters
        ----------
        to_get : int
            level to get

        Returns
        -------
        dict
            representation of requested MipMapLevel
        """
        return self.to_dict()[to_get]  # TODO should this default

    @property
    def levels(self):
        """list of MipMapLevels in this ImagePyramid"""
        return [int(i.level) for i in self.mipMapLevels]

    def __iter__(self):
        return iter([
            l for sl in [list(mmL) for mmL in self.mipMapLevels] for l in sl])