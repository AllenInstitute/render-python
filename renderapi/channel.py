from .image_pyramid import ImagePyramid


class Channel:
    '''class for storing channels of different mipmapsources'''

    def __init__(self, name=None, maxIntensity=None, minIntensity=None,
                 ip=None, json=None):
        '''
        Parameters
        ==========
        name: str
            name of channel
        maxIntensity: int
            maximum intensity to display (optional)
        minIntensity: int
            minimum default intensity to display (optional)
        ip: ImagePyramid
            set of mipmaplevel images for this channel
        json: dict
            json representation of this channel
        '''

        if json is not None:
            self.from_dict(json)
        else:
            self.name = name
            self.maxIntensity = maxIntensity
            self.minIntensity = minIntensity
            self.ip = ip

    def to_dict(self):
        '''method for serializing this class to a json compatible dictionary'''
        d = {}
        d['name'] = self.name
        if self.minIntensity is not None:
            d['minIntensity'] = self.minIntensity
        if self.maxIntensity is not None:
            d['maxIntensity'] = self.maxIntensity
        d['mipmapLevels'] = self.ip.to_dict()
        return d

    def from_dict(self, d):
        '''method for deserializing this class from a json compatible dictionary

        Parameters
        ==========
        d: dict
            json compatible dictionary representation of this channel
        '''
        self.name = d['name']
        self.minIntensity = d['minIntensity']
        self.maxIntensity = d['maxIntensity']
        self.ip = ImagePyramid.from_dict(d['mipmapLevels'])
