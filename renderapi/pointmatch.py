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

    """get all the matchCollection owners

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    render : renderapi.render.Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`unicode`
        matchCollection owners

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
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
    """get all the matchCollections owned by owner

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`unicode`
        matchcollections owned by owner

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
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
    """get all the groupIds in a matchCollection

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    owner : str
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`str`
        groupIds in matchCollection

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
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
def get_matches_outside_group(matchCollection, groupId, mergeCollections=None,
                              owner=None, host=None,
                              port=None, session=requests.session(),
                              render=None, **kwargs):
    """get all the matches outside a groupId in a matchCollection
    returns all matches where pGroupId == groupId and qGroupId != groupId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    groupId : str
        groupId to query
    mergeCollections : :obj:`list` of :obj:`str`
        other matchCollections to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesOutsideGroup" % (
            owner, matchCollection, groupId)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_within_group(matchCollection, groupId, mergeCollections=None,
                             owner=None, host=None, port=None,
                             session=requests.session(),
                             render=None, **kwargs):
    """get all the matches within a groupId in a matchCollection
    returns all matches where pGroupId == groupId and qGroupId == groupId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    groupId : str
        groupId to query
    mergeCollections : :obj:`list` of :obj:`str` or None
        other matchCollections
        to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : RenderClient
        RenderClient connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWithinGroup" % (
            owner, matchCollection, groupId)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_from_group_to_group(matchCollection, pgroup, qgroup,
                                    mergeCollections=None,
                                    render=None, owner=None, host=None,
                                    port=None,
                                    session=requests.session(), **kwargs):
    """get all the matches between two specific groups
    returns all matches where pgroup == pGroupId and qgroup == qGroupId
    OR pgroup == qGroupId and qgroup == pGroupId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    pgroup : str
        first group
    qgroup : str
        second group
    mergeCollections : :obj:`list` of :obj:`str` or None
        other matchCollections
        to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : RenderClient
        RenderClient connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server

    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWith/%s" % (
            owner, matchCollection, pgroup, qgroup)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


def add_merge_collections(request_url, mcs):
    """utility function to add mergeCollections to request_url

    Parameters
    ----------
    request_url : str
        request url
    mcs : :obj:`list` of :obj:`str`
        list of mergeCollections to add
    Returns
    -------
    str
        request_url with ?mergeCollection=mc[0]&mergeCollection=mc[1]...
        appended
    """
    if mcs is not None:
        if type(mcs) is list:
            request_url += "?"+"&".join(
                ['mergeCollection=%s' % mc for mc in mcs])
    return request_url


@renderaccess
def get_matches_from_tile_to_tile(matchCollection, pgroup, pid,
                                  qgroup, qid, mergeCollections=None,
                                  render=None, owner=None,
                                  host=None, port=None,
                                  session=requests.session(), **kwargs):
    """get all the matches between two specific tiles
    returns all matches where
    pgroup == pGroupId and pid=pId and qgroup == qGroupId and qid == qId
    OR
    qgroup == pGroupId and Qid=pId and Pgroup == qGroupId and pid == qId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    pgroup : str
        first group
    pid : str
        first id
    qgroup : str
        second group
    qid : str
        second id
    mergeCollections : :obj:`list` of :obj:`str` or None
        other matchCollections to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : RenderClient
        RenderClient connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        ("/owner/%s/matchCollection/%s/group/%s/id/%s/"
         "matchesWith/%s/id/%s" % (
             owner, matchCollection, pgroup, pid, qgroup, qid))
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_with_group(matchCollection, pgroup, mergeCollections=None,
                           render=None, owner=None,
                           host=None, port=None,
                           session=requests.session(), **kwargs):
    """get all the matches from a specific groups
    returns all matches where pgroup == pGroupId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    pgroup : str
        source group to query
    mergeCollections : :obj:`list` of :obj:`str` or None
        other matchCollections to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroup/%s/matches/" % (
            owner, matchCollection, pgroup)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_match_groupIds_from_only(matchCollection, mergeCollections=None,
                                 render=None, owner=None,
                                 host=None, port=None,
                                 session=requests.session(), **kwargs):
    """get all the source pGroupIds in a matchCollection

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : RenderClient
        RenderClient connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`str`
        pGroupIds in matchCollection

    Raises
    ------
    RenderError
        if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroupIds" % (owner, matchCollection)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_match_groupIds_to_only(matchCollection, mergeCollections=None,
                               render=None, owner=None,
                               host=None, port=None,
                               session=requests.session(), **kwargs):
    """get all the destination qGroupIds in a matchCollection

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`str`
        qGroupIds in matchCollection

    Raises
    ------
    RenderError
        if cannot get a reponse from server

    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/qGroupIds" % (owner, matchCollection)
    request_url = add_merge_collections(request_url, mergeCollections)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_matches_involving_tile(matchCollection, groupId, id,
                               mergeCollections=None,
                               owner=None, host=None, port=None,
                               session=requests.session(), **kwargs):
    """get all the matches involving a specific tile
     returns all matches where groupId == pGroupId and id == pId
     OR groupId == qGroupId and id == qId

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    groupId : str
        groupId to query
    id : str
        id to query
    mergeCollections : :obj:`list` of :obj:`str`, optional
        other matchCollections to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
       if cannot get a reponse from server
    """
    request_url = format_baseurl(host, port) + \
        "/owner/{}/matchCollection/{}/group/{}/id/{}/".format(
            owner, matchCollection, groupId, id)
    request_url = add_merge_collections(request_url, mergeCollections)

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
    """delete all the matches between two specific groups
    deletes all matches where (pgroup == pGroupId and qgroup == qGroupId)
    OR (pgroup == qGroupId and qgroup == pGroupId()

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    pgroup : str
        first group
    qgroup : str
        second group
    mergeCollections : :obj:`list` of :obj:`str` or None
        other matchCollections to aggregate into answer
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    :obj:`list` of :obj:`dict`
        list of matches (see matches definition)

    Raises
    ------
    RenderError
        if cannot get a reponse from server

    """
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
    """import matches into render database

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    matchCollection : str
        matchCollection name
    data : :obj:`list` of :obj:`dict`
        list of matches to import (see matches definition)
    owner : unicode
        matchCollection owner (fallback to render.DEFAULT_OWNER)
        (note match owner != stack owner always)
    render : Render
        Render connection object
    session : requests.session.Session
        requests session

    Returns
    -------
    requests.response.Reponse
        server response

    """
    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/matches" % (owner, matchCollection)
    logger.debug(request_url)
    if not isinstance(data, str):
        data = json.dumps(data)
    r = session.put(request_url, data=data, headers={
        "content-type": "application/json", "Accept": "application/json"})
    return r
