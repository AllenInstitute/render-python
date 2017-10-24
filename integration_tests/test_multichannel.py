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

render_params['project']='multi_channel_test'

@pytest.fixture(scope='module')
def render():
    return renderapi.connect(**render_params)

@pytest.fixture(scope='module')
def multichannel_test_stack(render):
    stack = 'multichannel_test'
    tilespecs = [renderapi.tilespec.TileSpec(json = d) for d in test_2_channels_d]
    renderapi.stack.create_stack(stack,render=render)
    renderapi.client.import_tilespecs(stack,tilespecs, render=render)
    renderapi.stack.set_stack_state(stack, 'COMPLETE',render=render)
    return stack

def test_section_image_channels(render,multichannel_test_stack):
    section_image = renderapi.image.get_section_image(multichannel_test_stack,
                                                      1.0,channel='DAPI',
                                                      render=render)
    print(section_image.shape)
