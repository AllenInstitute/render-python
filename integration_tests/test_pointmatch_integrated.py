import renderapi
import pytest
import tempfile
import os
import logging
import sys
import json
import numpy as np
from test_data import render_host, render_port, \
    client_script_location, tilespec_file, tform_file


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
#
logger.addHandler(ch)

test_matches = [
  {
    "pGroupId": "0",
    "pId": "0-1",
    "qGroupId": "1",
    "qId": "1-1",
    "matches": {
      "p": [
        [0, 0],
        [100, 100],
        [0, 100],
        [100, 0]
      ],
      "q": [
        [0, 0],
        [100, 100],
        [0, 100],
        [100, 0]
      ],
      "w": [1, 1, 1, 1]
    }
  },
    {
    "pGroupId": "0",
    "pId": "0-1",
    "qGroupId": "2",
    "qId": "2-1",
    "matches": {
      "p": [
        [0, 0],
        [100, 100],
        [0, 100],
        [100, 0]
      ],
      "q": [
        [0, 0],
        [100, 100],
        [0, 100],
        [100, 0]
      ],
      "w": [1, 1, 1, 1]
    }
  },
  {
    "pGroupId": "0",
    "pId": "0-1",
    "qGroupId": "0",
    "qId": "0-2",
    "matches": {
      "p": [
        [100, 100],
        [100, 0]
      ],
      "q": [
        [0, 100],
        [0, 0]
      ],
      "w": [1, 1]
    }
  }
]


@pytest.fixture(scope='module')
def render():
    render_test_parameters = {
            'host': render_host,
            'port': 8080,
            'owner': 'test',
            'project': 'test_pointmatch_project',
            'client_scripts': client_script_location
    }
    return renderapi.render.connect(**render_test_parameters)


@pytest.fixture(scope='module')
def test_pm_collection(render):
    collection = 'test_collection'
    renderapi.pointmatch.import_matches(
        collection, test_matches, render=render)
    return collection


def test_get_matchcollection_owners(render, test_pm_collection):
    owners = renderapi.pointmatch.get_matchcollection_owners(render=render)
    assert 'test' in owners


def test_get_matchcollections(render, test_pm_collection):
    collections = renderapi.pointmatch.get_matchcollections(render=render)
    matched_collection = next(
        coljson for coljson in collections
        if coljson['collectionId']['name'] == test_pm_collection)
    assert matched_collection is not None


def test_get_matches_involving_tile(render, test_pm_collection):
    matches = renderapi.pointmatch.get_matches_involving_tile(
        test_pm_collection, "0", "0-1", render=render)
    assert len(matches) == 3


def test_get_match_groupIds(render, test_pm_collection):
    groups = renderapi.pointmatch.get_match_groupIds(
        test_pm_collection, render=render)
    assert len(groups) == 3


def test_get_matches_outside_group(render, test_pm_collection):
    matches = renderapi.pointmatch.get_matches_outside_group(
        test_pm_collection, "0", render=render)
    assert test_matches[0] in matches
    assert test_matches[1] in matches


def test_get_matches_within_group(render, test_pm_collection):
    matches = renderapi.pointmatch.get_matches_within_group(
        test_pm_collection, "0", render=render)
    assert matches[0] == test_matches[2]


def test_get_matches_from_group_to_group(render, test_pm_collection):
    group1 = "0"
    group2 = "1"
    matches = renderapi.pointmatch.get_matches_from_group_to_group(
        test_pm_collection, group1, group2, render=render)
    assert matches[0] == test_matches[0]


def test_get_matches_from_tile_to_tile(render, test_pm_collection):
    group1 = "0"
    group2 = "1"
    tile1 = "0-1"
    tile2 = "1-1"
    matches = renderapi.pointmatch.get_matches_from_tile_to_tile(
        test_pm_collection, group1, tile1, group2, tile2, render=render)
    assert matches[0] == test_matches[0]


def test_get_matches_with_group(render, test_pm_collection):
    group1 = "0"
    matches = renderapi.pointmatch.get_matches_with_group(
        test_pm_collection, group1, render=render)
    assert len(matches) == 3


def test_get_match_groupIds_from_only(render, test_pm_collection):
    groups = renderapi.pointmatch.get_match_groupIds_from_only(
        test_pm_collection, render=render)
    assert len(groups) == 1


def test_get_match_groupIds_to_only(render, test_pm_collection):
    groups = renderapi.pointmatch.get_match_groupIds_to_only(
        test_pm_collection, render=render)
    assert len(groups) == 3


def test_delete_point_matches_between_groups(render):
    collection = 'test_delete'
    owner = 'test'
    renderapi.pointmatch.import_matches(
        collection, test_matches, render=render)
    group1 = '0'
    group2 = '1'
    renderapi.pointmatch.delete_point_matches_between_groups(
        collection, '0', '1', render=render)
    groups = renderapi.pointmatch.get_match_groupIds(collection, render=render)
    assert len(groups) == 2
