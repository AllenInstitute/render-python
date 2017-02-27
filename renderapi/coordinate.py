#!/usr/bin/env python
'''
coordinate mapping functions for render api
'''
from .render import Render, format_preamble, renderaccess
from .client import call_run_ws_client
import requests
import json
import numpy as np
import logging
import tempfile

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
def world_to_local_coordinates_batch(stack, data, z, host=None,
                                     port=None, owner=None, project=None,
                                     execute_local=True,
                                     session=requests.session(),
                                     render=None, **kwargs):

    ''''''
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%s/world-to-local-coordinates" % (str(z))
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    return r.json()


@renderaccess
def local_to_world_coordinates_batch(stack, data, z, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%s/local-to-world-coordinates" % (str(z))
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    try:
        return r.json()
    except:
        logger.error(r.text)


def package_point_match_data_into_json(dataarray, tileId,
                                       local_or_world='local'):
    dlist = []
    for i in range(dataarray.shape[0]):
        d = {}
        d['tileId'] = tileId
        d[local_or_world] = [dataarray[i, 0], dataarray[i, 1]]
        dlist.append(d)
    return json.dumps(dlist)


def unpackage_world_to_local_point_match_from_json(json_answer, tileId):
    answer = np.zeros((len(json_answer), 2))
    for i, local_answer in enumerate(json_answer):
        coord = next(ans for ans in local_answer if ans['tileId'] == tileId)
        c = coord['local']
        answer[i, 0] = c[0]
        answer[i, 1] = c[1]
    return answer


@renderaccess
def old_world_to_local_coordinates_array(stack, dataarray, tileId, z=0,
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


def unpackage_local_to_world_point_match_from_json(json_answer):
    logger.debug("json_answer_length %d" % len(json_answer))
    answer = np.zeros((len(json_answer), 2))
    for i, coord in enumerate(json_answer):
        c = coord['world']
        answer[i, 0] = c[0]
        answer[i, 1] = c[1]
    return answer


@renderaccess
def world_to_local_coordinates_array(stack, dataarray, tileId, z,
                                     render=None, host=None, port=None,
                                     owner=None, project=None,
                                     client_script=None,
                                     doClientSide=False, number_of_threads=20,
                                     session=requests.session(), **kwargs):
    ''''''
    jsondata = package_point_match_data_into_json(dataarray, tileId, 'world')
    if doClientSide:
        json_answer = world_to_local_coordinates_clientside(
            stack, jsondata, z, host=host, port=port, owner=owner,
            project=project, client_script=client_script,
            number_of_threads=number_of_threads)
    else:
        json_answer = world_to_local_coordinates_batch(
            stack, jsondata, z, host=host, port=port, owner=owner,
            project=project, session=session)
    return unpackage_world_to_local_point_match_from_json(json_answer, tileId)


@renderaccess
def old_local_to_world_coordinates_array(stack, dataarray, tileId, z=0,
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


@renderaccess
def local_to_world_coordinates_array(stack, dataarray, tileId, z,
                                     render=None, host=None, port=None,
                                     owner=None, project=None,
                                     client_script=None,
                                     doClientSide=False, number_of_threads=20,
                                     session=requests.session(), **kwargs):
    ''''''
    jsondata = package_point_match_data_into_json(dataarray, tileId, 'local')
    if doClientSide:
        json_answer = local_to_world_coordinates_clientside(
            stack, jsondata, z, host=host, port=port, owner=owner,
            project=project, client_script=client_script,
            number_of_threads=number_of_threads)
    else:
        json_answer = local_to_world_coordinates_batch(
            stack, jsondata, z, host=host, port=port, owner=owner,
            project=project, session=session)
    return unpackage_local_to_world_point_match_from_json(json_answer)


def map_coordinates_clientside(stack, jsondata, z, host, port, owner,
                               project, client_script, isLocalToWorld=False,
                               number_of_threads=20,memGB=1):
    # write point match json to temp file on disk
    json_infile, json_inpath = tempfile.mkstemp(
        prefix='render_coordinates_in_', suffix='.json')
    with open(json_inpath, 'w') as fp:
        fp.write(jsondata)

    # json.dump(jsondata,open(json_inpath,'w'))

    # get a temporary location for the output
    json_outpath = tempfile.mktemp(
        prefix='render_coordinates_out_', suffix='.json')

    # call the java client
    renderapi.client.coordinateClient(stack, z, fromJson=json_inpath, toJson=json_outpath, localToWorld=isLocalToWorld,
                     numberOfThreads=number_of_threads, host=host,port=port, owner=owner,project=project, client_script=client_script,
                     memGB=memGB)

    # return the json results
    return json.load(open(json_outpath, 'r'))


@renderaccess
def world_to_local_coordinates_clientside(stack, jsondata, z,
                                          host=None, port=None, owner=None,
                                          project=None, client_script=None,
                                          number_of_threads=20,
                                          session=requests.session(),
                                          render=None, **kwargs):

    return map_coordinates_clientside(stack, jsondata, z,
                                      host=host, port=port, owner=owner,
                                      project=project,
                                      client_script=client_script,
                                      isLocalToWorld=False,
                                      number_of_threads=number_of_threads)


@renderaccess
def local_to_world_coordinates_clientside(stack, jsondata, tileId, z,
                                          host=None, port=None, owner=None,
                                          project=None, client_script=None,
                                          number_of_threads=20,
                                          session=requests.session(),
                                          render=None, **kwargs):
    return map_coordinates_clientside(stack, jsondata, tileId, z,
                                      host=host, port=port, owner=owner,
                                      project=project,
                                      client_script=client_script,
                                      isLocalToWorld=True,
                                      number_of_threads=number_of_threads)
