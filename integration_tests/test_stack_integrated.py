import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
import numpy as np
from test_data import (render_host, render_port,
                       client_script_location, tilespec_file, 
                       tform_file, test_2_channels_d)

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
    tform = renderapi.transform.AffineModel(labels=['simple'])
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
    root.debug(tforms)
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


def test_remove_section(render, simpletilespec, tmpdir):
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
    stack_zs_before = render.run(renderapi.stack.get_z_values_for_stack,
                                 'test_insert')
    assert simpletilespec.z in stack_zs_before
    r = render.run(renderapi.stack.set_stack_state,
                   'test_insert', 'LOADING')
    r = renderapi.stack.delete_section('test_insert',
                                       simpletilespec.z, render=render)
    stack_zs_after = render.run(renderapi.stack.get_z_values_for_stack,
                                'test_insert')
    assert len(stack_zs_after) == (len(stack_zs_before) - 1)
    assert simpletilespec.z not in stack_zs_after
    render.run(renderapi.stack.delete_stack, 'test_insert')


@pytest.fixture(scope="module")
def teststack(request, render, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
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
    expected_bounds = {u'maxZ': 3408.0, u'maxX': 5103.0, u'maxY': 5386.0,
                       u'minX': 149.0, u'minY': 130.0, u'minZ': 3407.0}

    for key in stack_bounds.keys():
        assert np.abs(stack_bounds[key]-expected_bounds[key]) < 1.0


def test_z_bounds(render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    # check a single z stack bounds
    zbounds = render.run(renderapi.stack.get_bounds_from_z,
                         teststack, tilespecs[0].z)

    expected_bounds = {u'maxZ': 3407.0, u'maxX': 4918.0, u'maxY': 4507.0,
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


def test_clone_stack(render, teststack):
    stack2 = 'cloned_stack'
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)
    renderapi.stack.clone_stack(teststack, stack2, render=render)
    zvalues2 = renderapi.stack.get_z_values_for_stack(stack2, render=render)
    renderapi.stack.delete_stack(stack2, render=render)
    assert zvalues == zvalues2


def test_clone_stack_subset(render, teststack):
    stack2 = 'cloned_stack_subset'
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)
    renderapi.stack.clone_stack(
        teststack, stack2, zs=zvalues[0:1], render=render)
    zvalues2 = renderapi.stack.get_z_values_for_stack(stack2, render=render)
    renderapi.stack.delete_stack(stack2, render=render)
    assert zvalues[0:1] == zvalues2


def test_get_stack_sectionData(render, teststack):
    sectionData = renderapi.stack.get_stack_sectionData(
        teststack, render=render)
    assert len(sectionData) == 2


def test_get_z_values(render, teststack):
    # check get z values
    zvalues = render.run(renderapi.stack.get_z_values_for_stack, teststack)
    assert zvalues == [3407.0, 3408.0]


def test_uniq_value(render):
    # check likelyUniqueId
    uniq = render.run(renderapi.stack.likelyUniqueId)
    assert len(uniq) >= len('58ceebb7a7b11b0001dc4e32')


def test_bb_image(render, teststack, **kwargs):
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
                          scale=.25, img_format=fmt, **kwargs)
        dr = data.ravel()
        assert data.shape[0] == (np.floor(height*.25))
        assert data.shape[1] == (np.floor(width*.25))
        assert data.shape[2] >= 3


def test_bb_image_options(render, teststack):
    test_bb_image(render, teststack, filter=True,
                  binaryMask=True, maxTileSpecsToRender=20, minIntensity=0,
                  maxIntensity=255)


def test_tile_image(render, teststack, render_example_tilespec_and_transforms,
                    **kwargs):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    fmt = 'png'
    data = render.run(renderapi.image.get_tile_image_data,
                      teststack, tilespecs[0].tileId, **kwargs)
    if kwargs.get('scale') is None:
        testscale = 1.
    else:
        testscale = kwargs['scale']

    assert len(data.shape) == 3
    assert data.shape[0] >= np.floor(tilespecs[0].height * testscale)
    assert data.shape[1] >= np.floor(tilespecs[0].width * testscale)


def test_tile_image_options(render, teststack,
                            render_example_tilespec_and_transforms):
    testscale = 0.5
    test_tile_image(
        render, teststack, render_example_tilespec_and_transforms,
        scale=testscale, filter=True, normalizeForMatching=False)


def test_section_image(render, teststack, **kwargs):
    zvalues = render.run(renderapi.stack.get_z_values_for_stack, teststack)
    z = zvalues[0]
    bounds = render.run(renderapi.stack.get_bounds_from_z, teststack, z)

    width = bounds['maxX'] - bounds['minX']
    height = bounds['maxY'] - bounds['minY']
    fmt = 'png'
    scalefactor = 0.05
    data = render.run(renderapi.image.get_section_image, teststack, z,
                      scale=scalefactor, img_format=fmt, **kwargs)
    assert data.shape[0] == (np.floor(height * scalefactor))
    assert data.shape[1] == (np.floor(width * scalefactor))
    assert data.shape[2] >= 3


def test_section_image_options(render, teststack):
    img = test_section_image(render, teststack, filter=True,
                             maxTileSpecsToRender=50)


def fail_image_get(render, teststack, render_example_tilespec_and_transforms):
    with pytest.raises(KeyError):
        render.run(renderapi.image.get_tile_image_data, teststack,
                   'test', img_format='JUNK')


def test_get_tilespecs_from_z(render, teststack,
                              render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    tiles = renderapi.tilespec.get_tile_specs_from_z(
        teststack, tilespecs[0].z, render=render)
    tsz = [ts for ts in tilespecs if ts.z == tilespecs[0].z]
    assert len(tiles) == len(tsz)

def test_get_tilespec_raw(
        render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    ts = renderapi.tilespec.get_tile_spec_raw(teststack, tilespecs[0].tileId, render=render)
    assert ts.to_dict() == tilespecs[0].to_dict()

def test_get_tile_specs_from_minmax_box(
        render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    z = tilespecs[0].z
    tsz = [ts for ts in tilespecs if ts.z == tilespecs[0].z]
    zbounds = renderapi.stack.get_bounds_from_z(teststack, z, render=render)
    ts = renderapi.tilespec.get_tile_specs_from_minmax_box(
        teststack, z, zbounds['minX'], zbounds['maxX'],
        zbounds['minY'], zbounds['maxY'], render=render)
    assert len(ts) == len(tsz)


def test_get_tile_specs_from_box(render, teststack,
                                 render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    z = tilespecs[0].z
    tsz = [ts for ts in tilespecs if ts.z == tilespecs[0].z]
    zbounds = renderapi.stack.get_bounds_from_z(teststack, z, render=render)
    width = zbounds['maxX']-zbounds['minX']
    height = zbounds['maxY']-zbounds['minY']

    ts = renderapi.tilespec.get_tile_specs_from_box(
        teststack, z, zbounds['minX'],
        zbounds['minY'], width, height, render=render)
    assert len(ts) == len(tsz)


def test_get_tile_specs_from_stack(render, teststack,
                                   render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    ts = renderapi.tilespec.get_tile_specs_from_stack(teststack, render=render)
    assert len(ts) == len(tilespecs)

def test_get_sectionId_for_z(render, teststack, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    sectionId = render.run(renderapi.stack.get_sectionId_for_z, teststack, tilespecs[0].z)
    assert (sectionId == tilespecs[0].layout.sectionId)

def test_get_resolvedtiles_from_z(render, teststack,
                                  render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    resolved_tiles = renderapi.resolvedtiles.get_resolved_tiles_from_z(teststack,
                                                                       tilespecs[0].z,
                                                                       render=render)
    tsz = [ts for ts in tilespecs if ts.z == tilespecs[0].z]
    assert(len(tsz)==len(resolved_tiles.tilespecs))
    matching_ts = next(ts for ts in resolved_tiles.tilespecs if ts.tileId == tsz[0].tileId)
    assert (len(matching_ts.tforms)==len(tsz[0].tforms))



