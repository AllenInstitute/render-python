import json
from operator import eq
import renderapi
import rendersettings


def test_load_tilespecs_json():
    with open(rendersettings.TEST_TILESPECS_FILE, 'r') as f:
        ts_json = json.load(f)
    # current TileSpec objects do not put, e.g. min/max X/Y values in in dict
    ts_json_expected_fields = ['layout', 'width', 'height', 'tileId',
                               'minIntensity', 'maxIntensity', 'mipmapLevels',
                               'z', 'transforms']
    ts_json_expected = [{k: v for k, v in ts.items()
                         if k in ts_json_expected_fields}
                        for ts in ts_json]
    tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in ts_json]
    assert(all(map(
        lambda x: eq(*x),
        zip(json.loads(
            renderapi.utils.renderdumps(tilespecs)), ts_json_expected))))


def test_load_tilespecs_args():
    with open(rendersettings.TEST_TILESPECS_FILE, 'r') as f:
        ts_json = json.load(f)
    # current TileSpec objects do not put, e.g. min/max X/Y values in in dict
    ts_json_expected_fields = ['layout', 'width', 'height', 'tileId',
                               'minIntensity', 'maxIntensity', 'mipmapLevels',
                               'z', 'transforms']
    ts_json_expected = [{k: v for k, v in ts.items()
                         if k in ts_json_expected_fields}
                        for ts in ts_json]

    tilespecs = [renderapi.tilespec.TileSpec(
        tileId=ts['tileId'], z=ts['z'], width=ts['width'],
        height=ts['height'], mipMapLevels=[
            renderapi.tilespec.MipMapLevel(
                l, d.get('imageUrl'), d.get('maskUrl'))
            for l, d in ts['mipmapLevels'].items()],
        layout=renderapi.tilespec.Layout(
            force_pixelsize=False, **ts['layout']),
        minint=ts['minIntensity'], maxint=ts['maxIntensity'],
        tforms=renderapi.transform.TransformList(
            json=ts['transforms']).tforms)
                 for ts in ts_json_expected]
    assert(all(map(
        lambda x: eq(*x),
        zip([ts.to_dict() for ts in tilespecs], ts_json_expected))))


def test_bbox_shape():
    with open(rendersettings.TEST_TILESPECS_FILE, 'r') as f:
        tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in json.load(f)]

    assert(all([len(ts.bbox) == 4 for ts in tilespecs]))
