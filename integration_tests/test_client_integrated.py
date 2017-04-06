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


def test_import_tilespecs_parallel(render, render_example_tilespec_and_transforms, stack = 'test_import_tilespecs_parallel'):
   
    renderapi.stack.create_stack(stack,render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    renderapi.client.import_tilespecs_parallel(stack, tilespecs, sharedTransforms=tforms,
                                               render=render)
    stacks = renderapi.render.get_stacks_by_owner_project(render=render)
    assert stack in stacks
    ts = renderapi.tilespec.get_tile_specs_from_stack(stack, render=render)
    assert len(ts) == len(tilespecs)
    
def test_import_jsonfiles_validate_client(render):
    root.debug('test not implemented yet')
    assert False


def test_import_jsonfiles(render,render_example_tilespec_and_transforms,stack=None):
    if stack is None:
        stack = 'test_import_jsonfiles'
    renderapi.stack.create_stack(stack,render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    tfiles=[]
    for ts in tilespecs:
        tfile = tempfile.NamedTemporaryFile(mode = 'w', suffix = '.json', delete=False)
        tfile.write(renderapi.utils.renderdumps(ts))
        tfile.close()
        tfiles.append(tfile)
    transformFile = tempfile.NamedTemporaryFile(mode = 'w',suffix = '.json', delete=False)
    transformFile.write(renderapi.utils.renderdumps(tforms))

    renderapi.client.import_jsonfiles(stack, tfiles, transformFile = transformFile)
    
    stacks = renderapi.render.get_stacks_by_owner_project(render=render)
    assert stack in stacks
    ts = renderapi.tilespec.get_tile_specs_from_stack(stack, render=render)
    assert len(ts) == len(tilespecs)


@pytest.fixture(scope = "moudle")
def teststack(render,render_example_tilespec_and_transforms):

    stack = 'teststack'
    test_import_jsonfiles(render,render_example_tilespec_and_transforms,stack=stack)
    yield stack
    renderapi.stack.delete_stack(stack, render=render)


def test_tile_pair_client(render,teststack,**kwargs):
    zvalues = np.array(renderapi.stack.get_z_values_for_stack(teststack))
    outjson = kwargs.pop('outjson',None)
    if outjson is None:
        outjson = 'test_tile_pair_client.json'

    renderapi.client.tilePairClient(teststack, np.min(zvalues),
                                    np.max(zvalues), outjson=outjson, 
                                    **kwargs)
    
    tilepairjson = json.load(open(outjson,'r'))
    assert isinstance(tilepairjson,dict)
    assert len(tilepairjson['neighborPairs'])>3

def test_importTransformChangesClient(render):
    root.debug('test not implemented yet')
    assert False


def test_coordinateClient(render):
    root.debug('test not implemented yet')
    assert False