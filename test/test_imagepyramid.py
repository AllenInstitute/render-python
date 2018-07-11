from renderapi import image_pyramid
from renderapi.errors import RenderError
import pytest

image_filename = "not_a_file.jpg"
alt_image_filename = "not_a_file2.jpg"
mask_filename = "not_a_mask.png"
alt_mask_filename = "not_a_mask2.png"


def test_basic_pyramid():

    ip = image_pyramid.ImagePyramid()
    ip[0] = image_pyramid.MipMap(imageUrl=image_filename,
                                 maskUrl=mask_filename)

    assert(ip[0].imageUrl == image_filename)
    assert(ip[0].maskUrl == mask_filename)
    assert(len(ip.levels) == 1)
    with pytest.raises(RenderError):
        ip['not_a_level']

    with pytest.raises(RenderError):
        ip[-1]

    assert(ip.to_dict()['0']['imageUrl'] == image_filename)

    ip[1] = image_pyramid.MipMap(imageUrl=image_filename,
                                 maskUrl=mask_filename)
    assert(ip[1].imageUrl == image_filename)

    # test __setitem__ interface
    ip[1]['imageUrl'] = alt_image_filename
    ip[1]['maskUrl'] = alt_mask_filename
    assert(ip[1].imageUrl == alt_image_filename)
    assert(ip[1].maskUrl == alt_mask_filename)

    with pytest.raises(KeyError):
        ip[1]['notvalid'] = 'test'

    assert(len(ip) == 2)
    ip.pop(1)
    assert(len(ip) == 1)
    with pytest.raises(KeyError):
        ip[1]


def test_pyramid_deserialize():
    d = {
        "0": {
            "imageUrl": image_filename,
            "maskUrl": mask_filename
        }
    }
    ip = image_pyramid.ImagePyramid.from_dict(d)
    assert(ip[0].imageUrl == image_filename)
    assert(ip[0].maskUrl == mask_filename)

    mm2 = image_pyramid.MipMap(imageUrl=image_filename,
                               maskUrl=mask_filename)
    ip2 = image_pyramid.ImagePyramid({0: mm2})
    assert(ip == ip2)

    assert(ip[0] == d["0"])
    mm3 = image_pyramid.MipMap(imageUrl=image_filename)
    ip3 = image_pyramid.ImagePyramid({0: mm3})
    assert(ip != ip3)

    assert(mm3['imageUrl'] == image_filename)
    assert(mm3['maskUrl'] is None)

    with pytest.raises(KeyError):
        mm3['not_a_key']


def test_mipmaplevel_deprecated():
    mml = image_pyramid.MipMapLevel(0,
                                    imageUrl=image_filename,
                                    maskUrl=mask_filename)
    assert(mml['imageUrl'] == image_filename)
    assert(mml['maskUrl'] == mask_filename)
    with pytest.raises(KeyError):
        mml['not_a_key']

    assert(mml == mml)

    mml2 = image_pyramid.MipMapLevel(0,
                                     imageUrl=image_filename)
    assert(mml != mml2)
    assert(len([k for k, v in mml]) == 2)


def test_transformed_mapping():
    d = image_pyramid.TransformedDict()
    d[1] = 'a'
    d[2] = 'b'
    mylist = [k for k in d]
    assert(len(mylist) == 2)
