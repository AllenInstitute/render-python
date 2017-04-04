import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
import numpy as np
from test_data import (render_host, render_port,
                       client_script_location, tilespec_file, tform_file)

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


@pytest.fixture(scope='module')
def render():
    render_test_parameters = {
        'host': render_host,
        'port': render_port,
        'owner': 'test',
        'project': 'test_project',
        'client_scripts': client_script_location}
    return renderapi.render.connect(**render_test_parameters)


@pytest.fixture
def simpletilespec():
    mml = renderapi.tilespec.MipMapLevel(0, '/not/a/path.jpg')
    tform = renderapi.transform.AffineModel()
    layout = renderapi.tilespec.Layout(sectionId="section0",
                                       scopeId="testscope",
                                       cameraId="testcamera",
                                       imageRow=1,
                                       imageCol=1,
                                       stageX=40.0,
                                       stageY=50.0,
                                       rotation=0)
    ts = renderapi.tilespec.TileSpec(tileId="1000",
                                     width=2048,
                                     height=2048,
                                     mipMapLevels=[mml],
                                     z=0,
                                     tforms=[tform],
                                     layout=layout)
    return ts


@pytest.fixture(scope='module')
def render_example_tilespec_and_transforms():
    with open(tilespec_file, 'r') as f:
        ts_json = json.load(f)
    with open(tform_file, 'r') as f:
        tform_json = json.load(f)

    tilespecs = [renderapi.tilespec.TileSpec(json=ts) for ts in ts_json]
    tforms = [renderapi.transform.load_transform_json(td) for td in tform_json]
    print tforms
    return (tilespecs, tforms)


def test_stack_creation_deletion(render):
    test_stack = 'test_stack1'
    r = render.run(renderapi.stack.create_stack,
                   test_stack, force_resolution=True)
    assert (r.status_code == 201)

    sv = render.run(renderapi.stack.get_stack_metadata, test_stack)
    assert (sv is not None)

    assert(sv.stackResolutionX == 1.0)
    assert(sv.stackResolutionY == 1.0)
    assert(sv.stackResolutionZ == 1.0)

    owners = render.run(renderapi.render.get_owners)
    assert('test' in owners)

    projects = render.run(renderapi.render.get_projects_by_owner)
    assert('test_project' in projects)

    stacks = render.run(renderapi.render.get_stacks_by_owner_project)
    assert(test_stack in stacks)

    r = render.run(renderapi.stack.delete_stack, test_stack)

    assert (r.status_code != 400)


def test_failed_metadata(render):
    with pytest.raises(renderapi.errors.RenderError):
        render.run(renderapi.stack.get_stack_metadata, 'NOTASTACKNAME')


def test_set_stack_metadata(render):
    test_stack = 'test_stack2'
    r = render.run(renderapi.stack.create_stack,
                   test_stack, force_resolution=True)
    assert (r.status_code == 201)

    sv = render.run(renderapi.stack.get_stack_metadata, test_stack)
    sv.stackResolutionX = 2.0
    sv.stackResolutionY = 3.0
    sv.stackResolutionZ = 4.0

    r = render.run(renderapi.stack.set_stack_metadata, test_stack, sv)
    assert r.status_code == 201
    sv = render.run(renderapi.stack.get_stack_metadata, test_stack)
    assert sv.stackResolutionX == 2.0
    assert sv.stackResolutionY == 3.0
    assert sv.stackResolutionZ == 4.0

def test_simple_import(render, simpletilespec, tmpdir):
    # open a temporary file
    tfile = tmpdir.join('testfile.json')
    fp = tfile.open('w')

    # write the file to disk
    renderapi.utils.renderdump([simpletilespec], fp)
    fp.close()

    r = render.run(renderapi.stack.create_stack,
                   'test_insert', force_resolution=True)
    render.run(renderapi.client.import_single_json_file,
               'test_insert', str(tfile))
    r = render.run(renderapi.stack.set_stack_state,
                   'test_insert', 'COMPLETE')
    assert (r.status_code == 201)
    ts_out = render.run(renderapi.tilespec.get_tile_spec,
                        'test_insert', simpletilespec.tileId)
    assert (ts_out.z == simpletilespec.z)
    render.run(renderapi.stack.delete_stack, 'test_insert')

def test_simple_import_with_transforms(
        render, render_example_tilespec_and_transforms, tmpdir):
    (tilespecs, tforms) = render_example_tilespec_and_transforms

    # open a temporary file
    tilespecfile = tmpdir.join('tilespecs.json')
    fp = tilespecfile.open('w')
    # write the file to disk
    renderapi.utils.renderdump(tilespecs, fp)
    fp.close()

    transformfile = tmpdir.join('transforms.json')
    fp = transformfile.open('w')
    # write the file to disk
    renderapi.utils.renderdump(tforms, fp)
    fp.close()

    r = render.run(renderapi.stack.create_stack,
                   'test_insert_tform', force_resolution=True)
    render.run(renderapi.client.import_single_json_file, 'test_insert_tform',
               str(tilespecfile), transformFile=str(transformfile))
    r = render.run(renderapi.stack.set_stack_state,
                   'test_insert_tform', 'COMPLETE')
    assert r.status_code == 201
    ts_out = render.run(renderapi.tilespec.get_tile_spec,
                        'test_insert_tform', tilespecs[0].tileId)
    assert ts_out.z == tilespecs[0].z
    render.run(renderapi.stack.delete_stack, 'test_insert_tform')

def test_import_tilespecs(render, simpletilespec):
    stack = 'test_insert2'
    render.run(renderapi.stack.create_stack, stack, force_resolution=True)
    render.run(renderapi.client.import_tilespecs, stack, [simpletilespec])
    response = render.run(renderapi.stack.set_stack_state, stack, 'COMPLETE')
    assert response.status_code == 201
    ts_out = render.run(renderapi.tilespec.get_tile_spec,
                        stack, simpletilespec.tileId)
    assert ts_out.z == simpletilespec.z
    render.run(renderapi.stack.delete_stack, stack)


def test_import_tilespecs_parallel(render):
    root.debug('test not implemented yet')
    assert False

def test_import_jsonfiles_validate_client(render):
    root.debug('test not implemented yet')
    assert False

def test_import_jsonfiles(render):
    root.debug('test not implemented yet')
    assert False

def test_import_parallel(render):
    root.debug('test not implemented yet')
    assert False

def test_tile_pair_client(render):
    root.debug('test not implemented yet')
    assert False


def test_importTransformChangesClient(render):
    root.debug('test not implemented yet')
    assert False

def test_coordinateClient(render):
    root.debug('test not implemented yet')
    assert False

@pytest.fixture(scope="module")
def teststack(request,render,render_example_tilespec_and_transforms):
    (tilespecs,tforms)=render_example_tilespec_and_transforms

    stack = 'test_insert3'
    r = render.run(renderapi.stack.create_stack, stack, force_resolution=True)
    render.run(renderapi.client.import_tilespecs, stack, tilespecs,
               sharedTransforms=tforms)
    r = render.run(renderapi.stack.set_stack_state, stack, 'COMPLETE')
    yield stack
    render.run(renderapi.stack.delete_stack, stack)

def test_stack_bounds(render, teststack):
    # check the stack bounds
    stack_bounds = render.run(renderapi.stack.get_stack_bounds, teststack)
    expected_bounds = {u'maxZ': 3408.0, u'maxX': 5102.0, u'maxY': 5385.0,
                       u'minX': 149.0, u'minY': 130.0, u'minZ': 3407.0}

    for key in stack_bounds.keys():
        assert np.abs(stack_bounds[key]-expected_bounds[key]) < 1.0

def test_z_bounds(render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    # check a single z stack bounds
    zbounds = render.run(renderapi.stack.get_bounds_from_z,
                         teststack, tilespecs[0].z)

    expected_bounds = {u'maxZ': 3407.0, u'maxX': 4917.0, u'maxY': 4506.0,
                       u'minX': 149.0, u'minY': 130.0, u'minZ': 3407.0}
    for key in zbounds.keys():
        assert np.abs(zbounds[key]-expected_bounds[key]) < 1.0 

def test_get_section_z(render, teststack):
    # check getting section Z
    z = render.run(renderapi.stack.get_section_z_value,
                   teststack, "3407.0")
    assert z == 3407
    z = render.run(renderapi.stack.get_z_value_for_section,
                   teststack, "3407.0")
    assert z == 3407

def test_get_z_values(render, teststack):
    # check get z values
    zvalues = render.run(renderapi.stack.get_z_values_for_stack, teststack)
    assert zvalues == [3407.0, 3408.0]

def test_uniq_value(render):
    # check likelyUniqueId
    uniq = render.run(renderapi.stack.likelyUniqueId)
    assert len(uniq) >= len('58ceebb7a7b11b0001dc4e32')

def test_bb_image(render, teststack):
    formats = renderapi.image.IMAGE_FORMATS.keys()
    zvalues = render.run(renderapi.stack.get_z_values_for_stack, teststack)
    z = zvalues[0]
    bounds = render.run(renderapi.stack.get_bounds_from_z, teststack, z)
    width = (bounds['maxX'] - bounds['minX']) / 2
    height = (bounds['maxY'] - bounds['minY']) / 2
    x = bounds['minX'] + width / 4
    y = bounds['minY'] + width / 4

    for fmt in formats:
        data = render.run(renderapi.image.get_bb_image,
                          teststack, z, x, y, width, height,
                          scale=.25, img_format=fmt)
        dr = data.ravel()
        assert data.shape[0] == (np.floor(height*.25))
        assert data.shape[1] == (np.floor(width*.25))
        assert data.shape[2] >= 3

def test_tile_image(render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    format = 'png'
    data = render.run(renderapi.image.get_tile_image_data,
                      teststack, tilespecs[0].tileId)
    assert len(data.shape) == 3
    assert data.shape[0] >= tilespecs[0].height
    assert data.shape[1] >= tilespecs[0].width

def fail_image_get(render, teststack, render_example_tilespec_and_transforms):
    with pytest.raises(KeyError):
        render.run(renderapi.image.get_tile_image_data, teststack,
                   'test', img_format='JUNK')
