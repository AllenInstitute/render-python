#!/usr/bin/env python
'''
Point Match APIs
'''
import requests
import logging
from .render import format_baseurl, renderaccess
from .errors import RenderError
from .utils import NullHandler
import json
logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


@renderaccess
def get_matchcollection_owners(host=None, port=None,
                               session=requests.session(),
                               render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/matchCollectionOwners"
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matchcollections(owner=None, host=None, port=None,
                         session=requests.session(), render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollections" % owner
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_match_groupIds(matchCollection, owner=None, host=None,
                       port=None, session=requests.session(),
                       render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/groupIds" % (owner, matchCollection)
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_outside_group(matchCollection, groupId, mergeCollections=None, owner=None, host=None,
                              port=None, session=requests.session(),
                              render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesOutsideGroup" % (
            owner, matchCollection, groupId)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_within_group(matchCollection, groupId,mergeCollections=None, owner=None,
                             host=None, port=None, session=requests.session(),
                             render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWithinGroup" % (
            owner, matchCollection, groupId)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_from_group_to_group(matchCollection, pgroup, qgroup,mergeCollections=None,
                                    render=None, owner=None, host=None,
                                    port=None,
                                    session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWith/%s" % (
            owner, matchCollection, pgroup, qgroup)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)

def add_merge_collections(request_url,mergeCollections):
    if mergeCollections is not None:
        if type(mergeCollections) is list:
           request_url+="?"+"&".join(['mergeCollection=%s'%mc for mc in mergeCollections])
    return request_url

@renderaccess
def get_matches_from_tile_to_tile(matchCollection, pgroup, pid,
                                  qgroup, qid, mergeCollections=None,render=None, owner=None,
                                  host=None, port=None,
                                  session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        ("/owner/%s/matchCollection/%s/group/%s/id/%s/"
         "matchesWith/%s/id/%s" % (
             owner, matchCollection, pgroup, pid, qgroup, qid))
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_with_group(matchCollection, pgroup,mergeCollections=None, render=None, owner=None,
                           host=None, port=None,
                           session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroup/%s/matches/" % (
            owner, matchCollection, pgroup)
    request_url=add_merge_collections(request_url,mergeCollections)


    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_match_groupIds_from_only(matchCollection, mergeCollections=None,render=None, owner=None,
                                 host=None, port=None,
                                 session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroupIds" % (owner, matchCollection)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_match_groupIds_to_only(matchCollection, mergeCollections=None,render=None, owner=None,
                               host=None, port=None,
                               session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/qGroupIds" % (owner, matchCollection)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_involving_tile(matchCollection, pGroupId, pTileId,
                               mergeCollections=None,
                               owner=None, host=None, port=None,
                               session=requests.session(), **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/{}/matchCollection/{}/group/{}/id/{}/".format(
            owner, matchCollection, pGroupId, pTileId)
    request_url=add_merge_collections(request_url,mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def delete_point_matches_between_groups(matchCollection, pGroupId, qGroupId,
                                        render=None, owner=None, host=None,
                                        port=None, session=requests.session(),
                                        **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/{}/matchCollection/{}/group/{}/matchesWith/{}".format(
            owner, matchCollection, pGroupId, qGroupId)
    try:
        r = session.delete(request_url)
        return r
    except Exception as e:
        logger.error(e)
        logger.error(request_url)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def import_matches(matchCollection, data, owner=None, host=None, port=None,
                   session=requests.session(), render=None, **kwargs):
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/matches" % (owner, matchCollection)
    logger.debug(request_url)
    if not isinstance(data, str):
        data = json.dumps(data)
    r = session.put(request_url, data=data, headers={
        "content-type": "application/json", "Accept": "application/json"})
    return r
