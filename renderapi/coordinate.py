#!/usr/bin/env python
'''
coordinate mapping functions for render api
'''

from .render import Render, format_preamble
import logging
import requests
import json
logger = logging.getLogger(__name__)


def world_to_local_coordinates(stack, z, x, y, render=None, host=None,
                               port=None, owner=None, project=None,
                               session=requests.session(), **kwargs):
    ''''''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return world_to_local_coordinates(stack, z, x, y, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            **{'session': session}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates/%f,%f" % (z, x, y)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def local_to_world_coordinates(stack, tileId, x, y, render=None,
                               host=None, port=None, owner=None, project=None,
                               session=requests.session(), **kwargs):
    ''''''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return local_to_world_coordinates(
            stack, tileId, x, y, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'session': session}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/local-to-world-coordinates/%f,%f" % (tileId, x, y)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


def world_to_local_coordinates_batch(stack, z, data, render=None, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(), **kwargs):
    ''''''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return world_to_local_coordinates_batch(
            stack, z, data, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'session': session}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates" % (z)
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    return r.json()


# FIXME different inputs than world_to_local?
def local_to_world_coordinates_batch(stack, data, z, render=None, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return local_to_world_coordinates_batch(
            stack, data, z, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'session': session}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/local-to-world-coordinates" % (z)
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    return r.json()


def world_to_local_coordinates_array(stack, dataarray, tileId, z=0,
                                     render=None, host=None, port=None,
                                     owner=None, project=None,
                                     session=requests.session(), **kwargs):
    ''''''

    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return world_to_local_coordinates_array(
            stack, dataarray, tileId, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'session': session, 'z': z}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates" % (z)
    dlist = []
    for i in range(dataarray.shape[0]):
        d = {}
        d['tileId'] = tileId
        d['world'] = [dataarray[i, 0], dataarray[i, 1]]
        dlist.append(d)
    jsondata = json.dumps(dlist)
    r = session.put(request_url, data=jsondata,
                    headers={"content-type": "application/json"})
    json_answer = r.json()
    try:
        answer = np.zeros(dataarray.shape)
        for i, coord in enumerate(json_answer):
            c = coord['local']
            answer[i, 0] = c[0]
            answer[i, 1] = c[1]
        return answer
    except:
        logger.error(json_answer)


def local_to_world_coordinates_array(stack, dataarray, tileId, z=0,
                                     render=None, host=None, port=None,
                                     owner=None, project=None,
                                     session=requests.session(), **kwargs):
    ''''''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return local_to_world_coordinates_array(
            stack, dataarray, tileId, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'session': session, 'z': z}))

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/local-to-world-coordinates" % (z)
    dlist = []
    for i in range(dataarray.shape[0]):
        d = {}
        d['tileId'] = tileId
        d['local'] = [dataarray[i, 0], dataarray[i, 1]]
        dlist.append(d)
    jsondata = json.dumps(dlist)
    r = session.put(request_url, data=jsondata,
                    headers={"content-type": "application/json"})
    json_answer = r.json()
    try:
        answer = np.zeros(dataarray.shape)
        print dataarray.shape
        print len(json_answer)
        for i, coord in enumerate(json_answer):
            c = coord['world']
            answer[i, 0] = c[0]
            answer[i, 1] = c[1]
        return answer
    except:
        logger.error(json_answer)
