import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
import numpy as np
from test_data import render_host, render_port, \
    client_script_location, tilespec_file, tform_file


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
#
logger.addHandler(ch)


@pytest.fixture(scope='module')
def render():
    render_test_parameters = {
            'host': render_host,
            'port': 8080,
            'owner': 'test_coordinate',
            'project': 'test_coordinate_project',
            'client_scripts': client_script_location
    }
    return renderapi.render.connect(**render_test_parameters)


@pytest.fixture(scope='module')
def teststack_tilespec():
    render_test_parameters = {
            'host': render_host,
            'port': 8080,
            'owner': 'test_coordinate',
            'project': 'test_coordinate_project',
            'client_scripts': client_script_location
    }
    render = renderapi.render.connect(**render_test_parameters)
    with open(tilespec_file, 'r') as f:
        ts_json = json.load(f)
    with open(tform_file, 'r') as f:
        tform_json = json.load(f)

    tilespecs = [renderapi.tilespec.TileSpec(json=ts) for ts in ts_json]
    tforms = [renderapi.transform.load_transform_json(td) for td in tform_json]

    stack = 'test_coordinate_stack'
    r = render.run(renderapi.stack.create_stack, stack, force_resolution=True)
    render.run(
        renderapi.client.import_tilespecs, stack, tilespecs,
        sharedTransforms=tforms)
    r = render.run(renderapi.stack.set_stack_state, stack, 'COMPLETE')
    yield (stack, tilespecs[0])
    render.run(renderapi.stack.delete_stack, stack)


@pytest.fixture(scope='module')
def local_corners_json(teststack_tilespec):
    (stack, ts) = teststack_tilespec
    corners = [[0, 0], [ts.width, 0], [ts.width, ts.height], [0, ts.height]]
    batch = []
    for corner in corners:
        d = {
            'tileId': ts.tileId,
            'visible': True,
        }


def test_world_to_local_coordinates(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local = render.run(renderapi.coordinate.world_to_local_coordinates,
                       stack, ts.z, ts.minX, ts.minY)
    assert(local['error'] == "")
    assert(local['tileId'] == ts.tileId)
    assert(len(local['local']) >= 2)


def test_local_to_world_coordinates(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local = render.run(renderapi.coordinate.local_to_world_coordinates_batch,
                       stack, ts.z, 0)
    assert(local['error'] == "")
    assert(local['tileId'] == ts.tileId)
    assert(len(local['world']) >= 2)


def test_world_to_local_coordinates_batch(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    corners = [[0, 0], [ts.width, 0], [ts.width, ts.height], [0, ts.height]]
    batch = []
    for corner in corners:
        batch.append(renderapi.coordinate.local_to_world_coordinates(
                         stack, ts.z, corner[0], corner[1],render=render))
    local = renderapi.coordinate.world_to_local_coordinates_batch(
        stack, batch, ts.z,execute_local=False,render=render)

    assert(len(local) == len(batch))
    for ans in local:
        assert(len(ans['error']) == 0)


def test_local_to_world_coordinates_batch(render, teststack_tilespec):
    logger.debug('test not implemented yet')
    assert(False)


def old_world_to_local_coordinates_array(render, teststack_tilespec):
    logger.debug('test not implemented yet')
    assert(False)


def test_world_to_local_coordinates_array(render, teststack_tilespec):
    logger.debug('test not implemented yet')
    assert(False)


def old_local_to_world_coordinates_array(render, teststack_tilespec):
    logger.debug('test not implemented yet')
    assert(False)


def local_to_world_coordinates_array(render, teststack_tilespec):
    logger.debug('test not implemented yet')
    assert(False)


def world_to_local_coordinates_clientside():
    logger.debug('test not implemented yet')
    assert(False)


def local_to_world_coordinates_clientside():
    logger.debug('test not implemented yet')
    assert(False)
