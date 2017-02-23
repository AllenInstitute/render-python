#!/usr/bin/env python
'''
Point Match APIs
'''
import requests
import logging
from .render import Render, format_baseurl

logger = logging.getLogger(__name__)


def get_matchcollection_owners(render=None, host=None, port=None,
                               session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matchcollection_owners(**render.make_kwargs(
            host=host, port=port, **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/matchCollectionOwners"
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matchcollections(render=None, owner=None, host=None, port=None,
                         session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matchcollections(**render.make_kwargs(
            owner=owner, host=host, port=port,
            **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollections" % owner
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_match_groupIds(matchCollection, render=None, owner=None, host=None,
                       port=None, session=requests.session(),**kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_match_groupIds(matchCollection, **render.make_kwargs(
            owner=owner, host=host, port=port,
            **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/groupIds" % (owner, matchCollection)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matches_outside_group(matchCollection, groupId, render=None,
                              owner=None, host=None, port=None,
                              session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matches_outside_group(
            matchCollection, groupId, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesOutsideGroup" % (
            owner, matchCollection, groupId)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matches_within_group(matchCollection, groupId, owner=None,
                             host=None, port=None,
                             session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matches_within_group(
            matchCollection, groupId, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWithinGroup" % (
            owner, matchCollection, groupId)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matches_from_group_to_group(matchCollection, pgroup, qgroup,
                                    render=None, owner=None, host=None,
                                    port=None,
                                    session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matches_from_group_to_group(
            matchCollection, pgroup, qgroup, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/group/%s/matchesWith/%s" % (
            owner, matchCollection, pgroup, qgroup)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matches_from_tile_to_tile(matchCollection, pgroup, pid,
                                  qgroup, qid, render=None, owner=None,
                                  host=None, port=None,
                                  session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matches_from_tile_to_tile(
            matchCollection, pgroup, pid, qgroup, qid, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        ("/owner/%s/matchCollection/%s/group/%s/id/%s/"
         "matchesWith/%s/id/%s" % (
             owner, matchCollection, pgroup, pid, qgroup, qid))
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_matches_with_group(matchCollection, pgroup, render=None, owner=None,
                           host=None, port=None,
                           session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_matches_with_group(
            matchCollection, pgroup, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroup/%s/matches/" % (
            owner, matchCollection, pgroup)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_match_groupIds_from_only(matchCollection, render=None, owner=None,
                                 host=None, port=None,
                                 session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_match_groupIds_from_only(
            matchCollection, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/pGroupIds" % (owner, matchCollection)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def get_match_groupIds_to_only(matchCollection, render=None, owner=None,
                               host=None, port=None,
                               session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_match_groupIds_to_only(
            matchCollection, **render.make_kwargs(
                owner=owner, host=host, port=port,
                **{'session': session}))

    request_url = format_baseurl(host, port) + \
        "/owner/%s/matchCollection/%s/qGroupIds" % (owner, matchCollection)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)
