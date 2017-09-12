import renderapi
import pytest
import json
import rendersettings


@pytest.fixture(scope='module')
def referenced_tilespecs_and_transforms():
    with open(rendersettings.REFERENCE_TRANSFORM_TILESPECS,'r') as fp:
        ds = json.load(fp)
        tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in ds]

    with open(rendersettings.REFERENCE_TRANSFORM_SPECS,'r') as fp:
        ds = json.load(fp)
        transforms = [renderapi.transform.load_transform_json(tf) for tf in ds]
    return tilespecs,transforms

@pytest.fixture(scope='module')
def resolvedtiles_object(referenced_tilespecs_and_transforms):
    tilespecs,transforms = referenced_tilespecs_and_transforms
    resolved_tiles = renderapi.resolvedtiles.ResolvedTiles(tilespecs = tilespecs,
                                                           transformList=transforms)
    return resolved_tiles

def test_resolvedtiles_from_dict(resolvedtiles_object,referenced_tilespecs_and_transforms):
    tilespecs,transforms = referenced_tilespecs_and_transforms
    d=resolvedtiles_object.to_dict()
    resolved_tiles = renderapi.resolvedtiles.ResolvedTiles(json=d)
    assert(len(tilespecs)==len(resolved_tiles.tilespecs))
    assert(len(transforms)==len(resolved_tiles.transforms))
