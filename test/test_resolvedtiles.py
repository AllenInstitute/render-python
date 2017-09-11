import renderapi
import pytest
import json
import rendersettings

def test_resolved_tiles():
    
    with open(rendersettings.REFERENCE_TRANSFORM_TILESPECS,'r') as fp:
        ds = json.load(fp)
        tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in ds]

    with open(rendersettings.REFERENCE_TRANSFORM_SPECS,'r') as fp:
        ds = json.load(fp)
        transforms = [renderapi.transform.load_transform_json(tf) for tf in ds]
    
    resolved_tiles = renderapi.resolvedtiles.ResolvedTiles(tilespecs =tilespecs,
                                                           transformList=transforms)
