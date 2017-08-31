import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
import numpy as np
import dill
from test_data import (render_host, render_port,
                       client_script_location, tilespec_file, tform_file)
from pathos.multiprocessing import ProcessingPool as Pool

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


def render_example_json_files(render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    tfiles = []
    for ts in tilespecs:
        tfile = renderapi.utils.renderdump_temp([ts])
        tfiles.append(tfile)
    tfjson = renderapi.utils.renderdump_temp(tforms)

    return (tfiles, tfjson)


def validate_stack_import(render, stack, tilespecs):
    stacks = renderapi.render.get_stacks_by_owner_project(render=render)
    assert stack in stacks
    ts = renderapi.tilespec.get_tile_specs_from_stack(stack, render=render)
    assert len(ts) == len(tilespecs)


def test_import_jsonfiles_validate_client(
        render, render_example_tilespec_and_transforms):
    stack = 'test_import_jsonfiles_validate_client'
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)
    renderapi.client.import_jsonfiles_validate_client(
        stack, tfiles, transformFile=transformFile, render=render)
    validate_stack_import(render, stack, tilespecs)
    renderapi.stack.delete_stack(stack, render=render)


def test_import_jsonfiles_parallel(
        render, render_example_tilespec_and_transforms,
        stack='test_import_jsonfiles_parallel', poolsize=5):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)
    renderapi.client.import_jsonfiles_parallel(
        stack, tfiles, transformFile=transformFile,
        render=render, poolsize=poolsize)
    validate_stack_import(render, stack, tilespecs)
    renderapi.stack.delete_stack(stack, render=render)


def test_import_jsonfiles_parallel_multiple(
        render, render_example_tilespec_and_transforms, poolsize=5):
    stacks = ['testmultiple1', 'testmultiple2', 'testmultiple3']
    mylist = range(10)
    for stack in stacks:
        with renderapi.client.WithPool(poolsize) as pool:
            results = pool.map(lambda x: x**2, mylist)
        test_import_jsonfiles_parallel(
            render, render_example_tilespec_and_transforms, stack, poolsize)


def test_import_tilespecs_parallel(render,
                                   render_example_tilespec_and_transforms,
                                   stack='test_import_tilespecs_parallel'):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    renderapi.client.import_tilespecs_parallel(
        stack, tilespecs, sharedTransforms=tforms,
        poolsize=3, render=render)
    validate_stack_import(render, stack, tilespecs)


def test_import_jsonfiles(render, render_example_tilespec_and_transforms,
                          stack='test_import_jsonfiles'):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)

    renderapi.client.import_jsonfiles(
        stack, tfiles, transformFile=transformFile, poolsize=3, render=render)
    validate_stack_import(render, stack, tilespecs)


@pytest.fixture(scope="module")
def teststack(render, render_example_tilespec_and_transforms):
    stack = 'teststack'
    test_import_jsonfiles(render, render_example_tilespec_and_transforms,
                          stack=stack)
    yield stack
    renderapi.stack.delete_stack(stack, render=render)


def test_tile_pair_client(render, teststack, **kwargs):
    zvalues = np.array(renderapi.stack.get_z_values_for_stack(
        teststack, render=render))
    outjson = kwargs.pop('outjson', None)
    tilepairjson = renderapi.client.tilePairClient(
        teststack, np.min(zvalues), np.max(zvalues), outjson=outjson,
        render=render, **kwargs)
    assert isinstance(tilepairjson, dict)
    assert len(tilepairjson['neighborPairs']) > 3


def test_renderSectionClient(render, teststack):
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)
    root_directory = tempfile.mkdtemp()
    root.debug('section_directory:{}'.format(root_directory))
    renderapi.client.renderSectionClient(teststack,
                                         root_directory,
                                         zvalues,
                                         scale=.05,
                                         render=render,
                                         format='png')

    section_directory = os.path.join(
        root_directory, 'test_project', teststack, 'sections_at_0.05')
    pngfiles = []
    for (dirpath, dirname, filenames) in os.walk(section_directory):
        pngfiles += [f for f in filenames if f.endswith('png')]
    assert len(pngfiles) == len(zvalues)


def test_importTransformChangesClient(render, teststack):
    deststack = 'test_stack_TCC'

    tform_to_append = renderapi.transform.AffineModel()

    TCCjson = renderapi.utils.renderdump_temp(
        [{'tileId': tileId, 'transform': tform_to_append}
         for tileId in renderapi.stack.get_stack_tileIds(
             teststack, render=render)])
    renderapi.client.importTransformChangesClient(
        teststack, deststack, TCCjson, changeMode='APPEND', render=render)
    renderapi.stack.set_stack_state(deststack, 'COMPLETE', render=render)
    os.remove(TCCjson)
    
    output_ts = renderapi.tilespec.get_tile_specs_from_stack(
                    deststack, render=render)

    assert all([ts.tforms[-1].to_dict() == tform_to_append.to_dict()
                for ts in output_ts])
    renderapi.stack.delete_stack(deststack, render=render)


def test_transformSectionClient(render, teststack,
                                render_example_tilespec_and_transforms):
    deststack = 'test_stack_TSC'
    transformId = 'TSC_testtransform'
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)
    tform = renderapi.transform.AffineModel()

    renderapi.client.transformSectionClient(
        teststack, transformId, tform.className,
        tform.dataString.replace(" ", ","), zvalues, targetStack=deststack,
        render=render)
    renderapi.stack.set_stack_state(deststack, 'COMPLETE', render=render)

    output_ts = renderapi.tilespec.get_tile_specs_from_stack(
                    deststack, render=render)
    root.debug(output_ts[0].tforms[0].to_dict())
    root.debug(output_ts[-1].tforms[-1].to_dict())
    root.debug(tform.to_dict())
    assert all([ts.tforms[-1].to_dict() == tform.to_dict()
                for ts in output_ts])
    renderapi.stack.delete_stack(deststack, render=render)
