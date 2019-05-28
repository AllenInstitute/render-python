import renderapi
from test_data import render_params, test_2_channels_d
import pytest
import logging
import sys

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

render_params['project'] = 'multi_channel_test'


@pytest.fixture(scope='module')
def render():
    return renderapi.connect(**render_params)


@pytest.fixture(scope='module')
def multichannel_test_stack(render):
    stack = 'multichannel_test'
    tilespecs = [renderapi.tilespec.TileSpec(json=d)
                 for d in test_2_channels_d]
    renderapi.stack.create_stack(stack, render=render)
    renderapi.client.import_tilespecs(stack, tilespecs, render=render)
    renderapi.stack.set_stack_state(stack, 'COMPLETE', render=render)
    return stack

@pytest.fixture(scope='module')
def test_pm_collection(render):
    collection = 'test_multichan_collection'
    renderapi.pointmatch.import_matches(
        collection, test_matches, render=render)
    return collection


def test_section_image_channels(render, multichannel_test_stack):
    section_image = renderapi.image.get_section_image(multichannel_test_stack,
                                                      1.0, channel='DAPI',
                                                      render=render)
    print(section_image.shape)


def test_multichannel_pointmatch_same_channel(render, multichannel_test_stack):
    collection = 'test_multichannel_same_channel_collection'
    sift_options = renderapi.client.SiftPointMatchOptions(renderScale=.25)
    tile_pairs = [['100000001003000', '100000001004000']]
    renderapi.client.pointMatchClient(multichannel_test_stack,
                    collection,
                    tile_pairs,
                    filter=False,
                    excludeAllTransforms=True,
                    stackChannels='DAPI',
                    sift_options=sift_options,
                    render=render)
    pms = renderapi.pointmatch.get_matches_involving_tile(
        collection, collection, '100000001003000', render=render)
    assert(len(pms) > 0)


def test_multichannel_pointmatch_different_channel(render, multichannel_test_stack):
    collection = 'test_multichannel_pointmatch_different_channel'
    sift_options = renderapi.client.SiftPointMatchOptions(renderScale=.25)
    tile_pairs = [['100000001003000', '100000001004000']]
    renderapi.client.pointMatchClient(multichannel_test_stack,
                    collection,
                    tile_pairs,
                    stack2=multichannel_test_stack,
                    filter=False,
                    excludeAllTransforms=True,
                    stackChannels='DAPI',
                    stack2Channels='TdTomato',
                    sift_options=sift_options,
                    render=render)
    try:
        pms = renderapi.pointmatch.get_matches_involving_tile(
            collection, collection, '100000001003000', render=render)
        assert(len(pms) == 0)
    except renderapi.errors.RenderError:
        # The point match collection should not exist.
        return
