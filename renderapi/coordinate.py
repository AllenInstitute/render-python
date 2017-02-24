#!/usr/bin/env python
'''
coordinate mapping functions for render api
'''

from .render import Render, format_preamble, renderaccess
import logging
import requests
import json
logger = logging.getLogger(__name__)


@renderaccess
def world_to_local_coordinates(stack, z, x, y, host=None,
                               port=None, owner=None, project=None,
                               session=requests.session(),
                               render=None, **kwargs):
    ''''''
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates/%f,%f" % (z, x, y)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


@renderaccess
def local_to_world_coordinates(stack, tileId, x, y,
                               host=None, port=None, owner=None, project=None,
                               session=requests.session(),
                               render=None, **kwargs):
    ''''''
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/local-to-world-coordinates/%f,%f" % (tileId, x, y)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


@renderaccess
def world_to_local_coordinates_batch(stack, z, data, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    ''''''
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates" % (z)
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    return r.json()


# FIXME different inputs than world_to_local?
@renderaccess
def local_to_world_coordinates_batch(stack, data, z, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/local-to-world-coordinates" % (z)
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    return r.json()


@renderaccess
def world_to_local_coordinates_array(stack, dataarray, tileId, z=0,
                                     host=None, port=None,
                                     owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    ''''''

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


@renderaccess
def local_to_world_coordinates_array(stack, dataarray, tileId, z=0,
                                     host=None, port=None,
                                     owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    ''''''
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
