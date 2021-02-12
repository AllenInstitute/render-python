import copy
import renderapi
import pytest


@pytest.fixture(scope="module")
def matches():
    return [{
        "pGroupId": "0",
        "pId": "0-1",
        "qGroupId": "1",
        "qId": "1-1",
        "matches": {
            "p": [[0, 0],
                  [100, 100],
                  [0, 100],
                  [100, 0]],
            "q": [[0, 0],
                  [100, 100],
                  [0, 100],
                  [100, 0]],
            "w": [1, 1, 1, 1]},
        "matchCount": 4
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
          "w": [1, 1, 1, 1],
        },
        "matchCount": 4
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
          "w": [1, 1],
        },
        "matchCount": 2
      }
    ]


@pytest.fixture(scope="module")
def match(matches):
    return matches[1]


def set_tuple_subscript(obj, tuple_subscript, value):
    o = obj
    for s in tuple_subscript[:-1]:
        o = o.__getitem__(s)
    return o.__setitem__(tuple_subscript[-1], value)


def copymatch_and_compare(input_match, tuple_subscript_to_change,
                          target_value=None):
    orig_match = copy.deepcopy(input_match)
    copied_match = renderapi.pointmatch.copy_match_explicit(orig_match)
    set_tuple_subscript(orig_match, tuple_subscript_to_change, target_value)
    return orig_match == copied_match


def test_copy_match(match):
    # test for top level keys
    for k in (match.keys() - {"matches"}):
        assert not copymatch_and_compare(match, (k,))
    # test for nested values in matches
    for subtup in (("matches", "p", 0, 0),
                   ("matches", "q", 0, 0),
                   ("matches", "w", 0)):
        assert not copymatch_and_compare(match, subtup)


def test_copy_matches(matches):
    assert all([i == j for i, j in zip(
        matches, renderapi.pointmatch.copy_matches_explicit(matches))])
