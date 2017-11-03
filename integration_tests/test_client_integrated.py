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
                       client_script_location, tilespec_file, tform_file, test_pool_size)
from pathos.multiprocessing import ProcessingPool as Pool
import PIL

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
    root.debug(tforms)
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

@pytest.mark.parametrize('call_mode',('call','check_call','check_output'))
def test_import_jsonfiles_validate_client(
        render, render_example_tilespec_and_transforms,call_mode):
    stack = 'test_import_jsonfiles_validate_client'
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)
    renderapi.client.import_jsonfiles_validate_client(
        stack, tfiles, transformFile=transformFile, render=render,
        subprocess_mode=call_mode)
    validate_stack_import(render, stack, tilespecs)
    renderapi.stack.delete_stack(stack, render=render)

@pytest.mark.parametrize('call_mode',('check_call','check_output'))
def test_failed_jsonfiles_validate_client(
    render, render_example_tilespec_and_transforms,call_mode):
    stack = 'test_failed_import_jsonfiles_validate_client'
    renderapi.stack.create_stack(stack, render=render)
    with pytest.raises(renderapi.errors.ClientScriptError):
        renderapi.client.import_jsonfiles_validate_client(
            stack, ['not_a_file'], render=render,
            subprocess_mode=call_mode)

def test_import_jsonfiles_parallel(
        render, render_example_tilespec_and_transforms,
        stack='test_import_jsonfiles_parallel', poolsize=test_pool_size):
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
        render, render_example_tilespec_and_transforms, poolsize=test_pool_size):
    stacks = ['testmultiple1', 'testmultiple2', 'testmultiple3']
    mylist = range(10)
    for stack in stacks:
        with renderapi.client.WithPool(poolsize) as pool:
            results = pool.map(lambda x: x**2, mylist)
        test_import_jsonfiles_parallel(
            render, render_example_tilespec_and_transforms, stack, poolsize=poolsize)


def test_import_tilespecs_parallel(render,
                                   render_example_tilespec_and_transforms,
                                   stack='test_import_tilespecs_parallel'):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    renderapi.client.import_tilespecs_parallel(
        stack, tilespecs, sharedTransforms=tforms,
        poolsize=test_pool_size, render=render)
    validate_stack_import(render, stack, tilespecs)


def test_import_jsonfiles(render, render_example_tilespec_and_transforms,
                          stack='test_import_jsonfiles'):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)

    renderapi.client.import_jsonfiles(
        stack, tfiles, transformFile=transformFile, poolsize=test_pool_size, render=render)
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


@pytest.mark.parametrize("bounds,raises", [
    ({}, True),
    ({'maxX': 1000, 'minX': 2000, 'minY': 1000, 'maxY': 2000}, True),
    ({'maxX': 2000, 'minX': 1000, 'minY': 2000, 'maxY': 1000}, True),
    ({'maxX': 2000, 'minX': 1000, 'minY': 1000, 'maxY': 2000}, False),
    (None, False)
])
def test_renderSectionClient(render,teststack, bounds, raises, scale=.05):
    root_directory = tempfile.mkdtemp()
    root.debug('section_directory:{}'.format(root_directory))
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)

    if raises:
        with pytest.raises(renderapi.client.ClientScriptError) as e:
            renderapi.client.renderSectionClient(teststack,
                                                 root_directory,
                                                 zvalues,
                                                 scale=scale,
                                                 render=render,
                                                 bounds=bounds,
                                                 format='png')
    else:
        renderapi.client.renderSectionClient(teststack,
                                             root_directory,
                                             zvalues,
                                             scale=scale,
                                             render=render,
                                             bounds=bounds,
                                             format='png')
        pngfiles = []
        for (dirpath, dirname, filenames) in os.walk(root_directory):
            pngfiles += [os.path.join(dirpath,f) for f in filenames if f.endswith('png')]
        assert len(pngfiles) == len(zvalues)
        if bounds is not None:
            for f in pngfiles:
                img = PIL.Image.open(f)
                width, height = img.size
                assert(
                    np.abs(width - (bounds['maxX'] - bounds['minX']) * scale) < 1)
                assert(
                    np.abs(height - (bounds['maxY'] - bounds['minY']) * scale) < 1)


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
    tform = renderapi.transform.AffineModel(transformId=transformId)

    renderapi.client.transformSectionClient(
        teststack, transformId, tform.className,
        tform.dataString.replace(" ", ","), zvalues, targetStack=deststack,
        render=render)
    renderapi.stack.set_stack_state(deststack, 'COMPLETE', render=render)

    output_ts = renderapi.tilespec.get_tile_specs_from_stack(
        deststack, render=render)
    root.debug(output_ts[0].tforms[-1].to_dict())
    root.debug(output_ts[-1].tforms[-1].to_dict())
    root.debug(tform.to_dict())
    assert all([ts.tforms[-1].to_dict() == tform.to_dict()
                for ts in output_ts])
    renderapi.stack.delete_stack(deststack, render=render)
