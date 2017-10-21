import renderapi
import pytest
import json

d = {
    "name":"DAPI",
    "maxIntensity":255,
    "minIntensity":0,
    "mipmapLevels":{
        "0":{
            "imageUrl":"file:///not/a/path",
            "maskUrl":"file:///not/a/mask"
        }
    }
}

def test_channel():
    mml = renderapi.image_pyramid.MipMapLevel(0,
                                              imageUrl='file:///not/a/path',
                                              maskUrl='file:///not/a/mask')
    ip = renderapi.image_pyramid.ImagePyramid(mipMapLevels=[mml])
    channel = renderapi.channel.Channel(name='DAPI',
                                        maxIntensity=255,
                                        minIntensity=0,
                                        ip=ip)

    a=json.loads(renderapi.utils.renderdumps(channel))
    b=json.loads(renderapi.utils.renderdumps(d))
    assert(a==b)
