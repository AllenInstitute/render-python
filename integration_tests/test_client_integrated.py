import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
from PIL import Image
import numpy as np
from test_data import (render_host, render_port,
                       client_script_location, tilespec_file, tform_file,
                       test_pool_size)
import PIL
from renderapi.external.processpools.stdlib_pool import (
    WithThreadPool, WithDummyMapPool, WithMultiprocessingPool)

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


@pytest.mark.parametrize('call_mode', (
    'call', 'check_call', 'check_output'))
def test_import_jsonfiles_validate_client(
        render, render_example_tilespec_and_transforms, call_mode):
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


@pytest.mark.parametrize('call_mode', ('check_call', 'check_output'))
def test_failed_jsonfiles_validate_client(
        render, render_example_tilespec_and_transforms, call_mode):
    stack = 'test_failed_import_jsonfiles_validate_client'
    renderapi.stack.create_stack(stack, render=render)
    with pytest.raises(renderapi.errors.ClientScriptError):
        renderapi.client.import_jsonfiles_validate_client(
            stack, ['not_a_file'], render=render,
            subprocess_mode=call_mode)


@pytest.mark.parametrize('use_rest,stack',
                         [(True, 'test_import_jsonfiles_parallel'),
                          (False, 'test_import_jsonfiles_parallel_rest')])
def test_import_jsonfiles_parallel(
        render, render_example_tilespec_and_transforms,
        stack, use_rest,
        poolsize=test_pool_size, **kwargs):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)
    renderapi.client.import_jsonfiles_parallel(
        stack, tfiles, transformFile=transformFile,
        render=render, poolsize=poolsize, use_rest=use_rest, **kwargs)
    validate_stack_import(render, stack, tilespecs)
    renderapi.stack.delete_stack(stack, render=render)


def test_bbox_transformed(render, render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    ts = tilespecs[0]
    xy = ts.bbox_transformed(ndiv_inner=0, tf_limit=0)
    assert xy.shape == (5, 2)
    assert np.abs((xy[2, :] - np.array([ts.width, ts.height])).sum()) < 1e-10
    xy = ts.bbox_transformed(ndiv_inner=1, tf_limit=0)
    assert xy.shape == (9, 2)


def square(x):
    return x**2


# this test was added in order to validate that multiple WithPools would work
# pathos was breaking when we did this before.  Should now be not relevant,
# but who ever deletes a test if you don't have to.
def test_import_jsonfiles_parallel_multiple(
        render, render_example_tilespec_and_transforms,
        poolsize=test_pool_size):
    stacks = ['testmultiple1', 'testmultiple2', 'testmultiple3']
    mylist = range(10)
    for stack in stacks:
        with renderapi.client.WithPool(poolsize) as pool:
            results = pool.map(square, mylist)  # noqa: F841
        test_import_jsonfiles_parallel(
            render, render_example_tilespec_and_transforms, stack,
            use_rest=False, poolsize=poolsize)


def test_import_tilespecs_parallel(render,
                                   render_example_tilespec_and_transforms,
                                   stack='test_import_tilespecs_parallel',
                                   **kwargs):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    renderapi.client.import_tilespecs_parallel(
        stack, tilespecs, sharedTransforms=tforms,
        poolsize=test_pool_size, render=render, **kwargs)
    validate_stack_import(render, stack, tilespecs)


def test_import_jsonfiles(render, render_example_tilespec_and_transforms,
                          stack='test_import_jsonfiles'):
    renderapi.stack.create_stack(stack, render=render)
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    (tfiles, transformFile) = render_example_json_files(
        render_example_tilespec_and_transforms)

    renderapi.client.import_jsonfiles(
        stack, tfiles, transformFile=transformFile, poolsize=test_pool_size,
        render=render)
    validate_stack_import(render, stack, tilespecs)


@pytest.fixture(scope="module")
def teststack(render, render_example_tilespec_and_transforms):
    stack = 'teststack'
    test_import_jsonfiles(render, render_example_tilespec_and_transforms,
                          stack=stack)
    yield stack
    renderapi.stack.delete_stack(stack, render=render)

@pytest.fixture(scope="module")
def teststack2(render, render_example_tilespec_and_transforms):
    #copy of teststack for the purpose of testing pointmatchClient with two stacks
    stack = 'teststack2'
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
def test_renderSectionClient(render, teststack, bounds, raises, scale=.05):
    root_directory = tempfile.mkdtemp()
    root.debug('section_directory:{}'.format(root_directory))
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)

    if raises:
        with pytest.raises(renderapi.client.ClientScriptError):
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
            pngfiles += [os.path.join(dirpath, f) for f in filenames
                         if f.endswith('png')]
        assert len(pngfiles) == len(zvalues)
        if bounds is not None:
            for f in pngfiles:
                img = PIL.Image.open(f)
                width, height = img.size
                assert(
                    np.abs(
                        width - (bounds['maxX'] - bounds['minX']) * scale) < 1)
                assert(
                    np.abs(
                        height -
                        (bounds['maxY'] - bounds['minY']) * scale) < 1
                      )


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


def test_point_match_client(teststack, render, tmpdir):
    collection = 'test_client_collection'
    zvalues = np.array(renderapi.stack.get_z_values_for_stack(
        teststack, render=render))
    tilepairjson = renderapi.client.tilePairClient(
        teststack, np.min(zvalues), np.max(zvalues), render=render)

    tile_pairs = [(tp['p']['id'], tp['q']['id']) for tp
                  in tilepairjson['neighborPairs'][0:1]]
    sift_options = renderapi.client.SiftPointMatchOptions(renderScale=.25)
    renderapi.client.pointMatchClient(teststack,
                                      collection,
                                      tile_pairs,
                                      debugDirectory=tmpdir,
                                      sift_options=sift_options,
                                      render=render)
    tp = tilepairjson['neighborPairs'][0]
    pms = renderapi.pointmatch.get_matches_involving_tile(
        collection, tp['p']['groupId'], tp['p']['id'], render=render)
    assert(len(pms) > 0)


def test_point_match_client_2args(teststack, teststack2, render, tmpdir):
    collection = 'test_client_collection'
    zvalues = np.array(renderapi.stack.get_z_values_for_stack(
        teststack, render=render))
    tilepairjson = renderapi.client.tilePairClient(
        teststack, np.min(zvalues), np.max(zvalues), render=render)

    tile_pairs = [(tp['p']['id'], tp['q']['id']) for tp
                  in tilepairjson['neighborPairs'][0:1]] # tile pairs are the same because the two stacks have the same information
    sift_options = renderapi.client.SiftPointMatchOptions(renderScale=.25)
    renderapi.client.pointMatchClient(teststack,
                                      collection,
                                      tile_pairs, stack2 = teststack2,
                                      debugDirectory=tmpdir,
                                      sift_options=sift_options,
                                      render=render)
    tp = tilepairjson['neighborPairs'][0]
    pms = renderapi.pointmatch.get_matches_involving_tile(
        collection, tp['p']['groupId'], tp['p']['id'], render=render)
    assert(len(pms) > 0)


def test_call_run_ws_client_renderclient(render, teststack):
    # class for this test should be something relatively lightweight....
    test_class = 'org.janelia.render.client.ValidateTilesClient'
    zvalues = renderapi.stack.get_z_values_for_stack(teststack, render=render)
    args = renderapi.stack.make_stack_params(
        render.DEFAULT_HOST, render.DEFAULT_PORT, render.DEFAULT_OWNER,
        render.DEFAULT_PROJECT, teststack) + [zvalues[0]]
    assert not renderapi.client.call_run_ws_client(
        test_class, add_args=args, subprocess_mode='call', renderclient=render)


@pytest.mark.parametrize("stackbase,poolclass", [
    ("ThreadPooltest", WithThreadPool),
    ("DummyMapPoolTest", WithDummyMapPool),
    ("MultiprocessingPoolTest", WithMultiprocessingPool)])
def test_processpools_parallelfuncs(
        render, render_example_tilespec_and_transforms,
        stackbase, poolclass, poolsize=test_pool_size):
    test_import_tilespecs_parallel(
        render, render_example_tilespec_and_transforms,
        "{}_tilespecs".format(stackbase), mpPool=poolclass)
    test_import_jsonfiles_parallel(
        render, render_example_tilespec_and_transforms,
        "{}_jsonfiles".format(stackbase), False, poolsize=poolsize,
        mpPool=poolclass)


@pytest.fixture(scope='module')
def example_renderparameters(render, teststack):
    zvalues = render.run(renderapi.stack.get_z_values_for_stack, teststack)
    z = zvalues[0]
    bounds = render.run(renderapi.stack.get_bounds_from_z, teststack, z)
    width = (bounds['maxX'] - bounds['minX']) / 2
    height = (bounds['maxY'] - bounds['minY']) / 2
    x = bounds['minX'] + width / 4
    y = bounds['minY'] + width / 4
    renderparams = renderapi.image.get_bb_renderparams(
        teststack, z, x, y, width, height,
        scale=0.25, render=render)
    yield renderparams


@pytest.fixture(scope='module')
def renderedimg_renderparams(render, example_renderparameters):
    # TODO is there a "render from renderparams" api?
    arr = renderapi.image.get_renderparameters_image(
        example_renderparameters, render=render)
    yield arr, example_renderparameters


@pytest.fixture(scope='module')
def tile_tilespec():
    tile_dims = (256, 256)
    with tempfile.NamedTemporaryFile(suffix='.tif', mode='w') as imgf:
        arr = np.random.randint(0, 256, size=tile_dims, dtype='uint8')
        img = Image.fromarray(arr)
        img.save(imgf.name)

        ts = renderapi.tilespec.TileSpec(
            tileId='myTestTile',
            z=1.,
            sectionId="z1.0",
            width=tile_dims[0],
            height=tile_dims[1],
            minint=0,
            maxint=255,
            imageUrl="file://{}".format(imgf.name))
        ts.minX = 0
        ts.maxX = tile_dims[0]
        ts.minY = 0
        ts.maxY = tile_dims[1]

        yield imgf.name, ts


def test_ARGBrenderclient(render, tile_tilespec):
    tile, tspec = tile_tilespec
    arr = renderapi.client.render_tilespec(tspec, memGB='512M', render=render)
    with Image.open(tile) as tileimg:
        tilearr = np.array(tileimg)
        assert arr.shape[:-1] == (tspec.width, tspec.height) == tilearr.shape
        assert np.all(arr[:, :, 0] == tilearr)


def testRendererClient(render, renderedimg_renderparams):
    renderedarr, renderparams = renderedimg_renderparams
    arr = renderapi.client.render_renderparameters(renderparams, render=render)
    assert arr.shape[:-1] == (
        int(renderparams['height'] * renderparams['scale']),
        int(renderparams['width'] * renderparams['scale'])
    ) == renderedarr.shape[:-1]
    assert np.all(arr == renderedarr)
