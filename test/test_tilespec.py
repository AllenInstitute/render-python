import json
from operator import eq
import renderapi
import rendersettings


def test_load_tilespecs():
    with open(rendersettings.TEST_TILESPECS_FILE, 'r') as f:
        ts_json = json.load(f)
    ts_jsons = json.dumps(ts_json)
    tilespecs = [renderapi.tilespec.TileSpec(json=d) for d in ts_json]
    assert(map(
        lambda x: eq(*x),
        zip(json.loads(renderapi.utils.renderdumps(tilespecs)), ts_json)))
