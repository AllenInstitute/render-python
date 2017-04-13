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
def teststack_tilespec(render):
    '''
    render_test_parameters = {
            'host': render_host,
            'port': 8080,
            'owner': 'test_coordinate',
            'project': 'test_coordinate_project',
            'client_scripts': client_script_location
    }
    render = renderapi.render.connect(**render_test_parameters)
    '''
    with open(tilespec_file, 'r') as f:
        ts_json = json.load(f)
    with open(tform_file, 'r') as f:
        tform_json = json.load(f)

    tilespecs = [renderapi.tilespec.TileSpec(json=ts) for ts in ts_json]
    tforms = [renderapi.transform.load_transform_json(td) for td in tform_json]

    stack = 'test_coordinate_stack'
    render.run(renderapi.stack.create_stack, stack, force_resolution=True)
    render.run(
        renderapi.client.import_tilespecs, stack, tilespecs,
        sharedTransforms=tforms)
    render.run(renderapi.stack.set_stack_state, stack, 'COMPLETE')
    yield (stack, tilespecs[0])
    render.run(renderapi.stack.delete_stack, stack)


@pytest.fixture(scope='module')
def local_corners_json(teststack_tilespec):
    (stack, ts) = teststack_tilespec
    corners = [[10, 10], [ts.width-10, 10],
               [ts.width-10, ts.height-10], [10, ts.height-10]]
    batch = []
    for corner in corners:
        d = {
            'tileId': ts.tileId,
            'visible': True
        }
        d['local'] = corner
        batch.append(d)
    return batch


@pytest.fixture(scope='module')
def world_corners_json(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    corners = [[10, 10], [ts.width-10, 10],
               [ts.width-10, ts.height-10], [10, ts.height-10]]
    world_corners = []
    for corner in corners:
        world_corners.append(renderapi.coordinate.local_to_world_coordinates(
            stack, ts.tileId, corner[0], corner[1], render=render))
    return world_corners


def test_world_to_local_coordinates(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local = render.run(renderapi.coordinate.world_to_local_coordinates,
                       stack, ts.z, 1500, 1500)
    logger.debug(local)
    for tile in local:
        assert('error' not in tile.keys())
        assert(tile['tileId'] == ts.tileId)
        assert(len(tile['local']) >= 2)


def test_local_to_world_coordinates(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    world = render.run(renderapi.coordinate.local_to_world_coordinates,
                       stack, ts.tileId, 0, 0)
    logger.debug(world)
    assert('error' not in world.keys())
    assert(world['tileId'] == ts.tileId)
    assert(len(world['world']) >= 2)


def test_world_to_local_coordinates_batch(render, teststack_tilespec,
                                          world_corners_json):
    (stack, ts) = teststack_tilespec
    local = renderapi.coordinate.world_to_local_coordinates_batch(
        stack, world_corners_json, ts.z, execute_local=False, render=render)
    logger.debug(local)
    assert(len(local) == len(world_corners_json))
    for ans in local:
        for tile in ans:
            assert('error' not in tile.keys())


def test_local_to_world_coordinates_batch(render, teststack_tilespec,
                                          local_corners_json):
    (stack, ts) = teststack_tilespec
    world = renderapi.coordinate.local_to_world_coordinates_batch(
        stack, local_corners_json, ts.z, execute_local=False, render=render)
    assert(len(local_corners_json) == len(world))
    for ans in world:
        assert('error' not in ans.keys())


def test_world_to_local_coordinates_array(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local_corners = np.array([[10, 10], [ts.width-10, 10],
                              [ts.width-10, ts.height-10], [10, ts.height-10]])
    world_corners = renderapi.coordinate.local_to_world_coordinates_array(
        stack, local_corners, ts.tileId, ts.z, render=render)
    local_corners2 = renderapi.coordinate.world_to_local_coordinates_array(
        stack, world_corners, ts.tileId, ts.z, render=render)
    logger.debug('local corners2: {}'.format(local_corners2))
    for pt, ptafter in zip(local_corners, local_corners2):
        assert(np.sum(np.abs(pt-ptafter)) < .1)


def test_local_to_world_coordinates_array(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local_corners = np.array([[10, 10], [ts.width-10, 10],
                              [ts.width-10, ts.height-10], [10, ts.height-10]])
    world_corners = renderapi.coordinate.local_to_world_coordinates_array(
        stack, local_corners, ts.tileId, ts.z, render=render)
    logger.debug('world corners:{}'.format(world_corners))
    assert(world_corners.shape[0] == local_corners.shape[0])


def test_world_to_local_coordinates_clientside(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local_corners = np.array([[10, 10], [ts.width-10, 10],
                              [ts.width-10, ts.height-10], [10, ts.height-10]])
    world_corners = renderapi.coordinate.local_to_world_coordinates_array(
        stack, local_corners, ts.tileId, ts.z,
        render=render, doClientSide=True)
    local_corners2 = renderapi.coordinate.world_to_local_coordinates_array(
        stack, world_corners, ts.tileId, ts.z,
        render=render, doClientSide=True)
    logger.debug('local corners2: {}'.format(local_corners2))
    for pt, ptafter in zip(local_corners, local_corners2):
        assert(np.sum(np.abs(pt-ptafter)) < .1)


def test_local_to_world_coordinates_clientside(render, teststack_tilespec):
    (stack, ts) = teststack_tilespec
    local_corners = np.array([[10, 10], [ts.width-10, 10],
                              [ts.width-10, ts.height-10], [10, ts.height-10]])
    world_corners = renderapi.coordinate.local_to_world_coordinates_array(
        stack, local_corners, ts.tileId, ts.z,
        doClientSide=True, render=render)
    logger.debug('world corners:{}'.format(world_corners))
    assert(world_corners.shape[0] == local_corners.shape[0])
