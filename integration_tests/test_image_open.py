import renderapi
from renderapi.image_open import read_mipmap_image, read_mipmap_mask
from test_data import render_params, test_2_channels_d
import pytest
import numpy as np

@pytest.fixture(scope='module')
def test_mml():
    tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in test_2_channels_d]
    mml = tilespecs[0].channels[0].ip[0]
    return mml

def test_image_open(test_mml):
    img = read_mipmap_image(test_mml)
    assert (img.shape == (2048,2048))
    assert (img.dtype == np.uint16)
    assert (img.max() == 23059)

def test_mask_open(test_mml):
    mask = read_mipmap_mask(test_mml)
    assert (mask.shape == (2048,2048))
    assert (mask.dtype == np.uint8)
    assert (mask.max() == np.iinfo(mask.dtype).max)

    