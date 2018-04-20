#!/usr/bin/env python
'''
coordinate mapping functions for render api
'''
from .render import format_preamble, renderaccess
from .utils import NullHandler, renderdumps, renderdump, get_json
from .client import coordinateClient
from .errors import RenderError
import requests
import json
import numpy as np
import logging
import tempfile
import os

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


@renderaccess
def world_to_local_coordinates(stack, z, x, y, host=None,
                               port=None, owner=None, project=None,
                               session=requests.session(),
                               render=None, **kwargs):
    """maps an world x,y,z coordinate in stack to a local coordinate
    Parameters
    ----------
    stack : str
        render stack to map coordinates through
    z : float
        z coordinate to map
    x : float
        x coordinate to map
    y : float
        y coordinate to map
    session : requests.session.Session
        session  object used in request
    render : renderapi.render.Render
        render connect object
    Returns
    -------
    json
        list of dictionaries of local coordinates following this pattern
        ::

            [
                {
                    "tileId": "string",
                    "visible": false,
                    "local": [
                        [0,0],
                        [1,0]...
                    ],
                    "error": "string"
                }
            ]
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%d/world-to-local-coordinates/%f,%f" % (z, x, y)
    return get_json(session, request_url)


@renderaccess
def local_to_world_coordinates(stack, tileId, x, y,
                               host=None, port=None, owner=None, project=None,
                               session=requests.session(),
                               render=None, **kwargs):
    """convert coordinate from local to world with webservice request

    Parameters
    ----------
    stack : str
        render stack to map coordinates through
    z : float
        z coordinate to map
    x : float
        x coordinate to map
    y : float
        y coordinate to map
    session : requests.session.Session
         session object used in request
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    dict
        dictionary of world coordinates following this pattern
        ::

            {
                "tileId": "string",
                "visible": false,
                "world": [
                    [0,0],
                    [1,0]...
                ],
                "error": "string"
            }

    """
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/tile/%s/local-to-world-coordinates/%f,%f" % (tileId, x, y)
    return get_json(session, request_url)


@renderaccess
def world_to_local_coordinates_batch(stack, d, z, host=None,
                                     port=None, owner=None, project=None,
                                     execute_local=False,
                                     session=requests.session(),
                                     render=None, **kwargs):

    """convert coordinate parameters from world to local

    Parameters
    ----------
    stack : str
        stack to map coordinates
    d : list[dict]
        list of  dictionary of world coordinates to map following this schema
          ::

            [ {
                "tileId": "string",
                "world": [
                    [0,0],
                    [1,0]...
                ],
                "error": "string"
                }]
    z : float
        z coordinate to map
    execute_local : boolean
         (Default value = False)
    session : requests.session.Session
        session object used in request
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    list[list[dict]]
        list of lists of dictionaries containing local positions
        that overlap with this point, (one world point may map
        to multiple local points) following..
        ::

           [[ {
            "tileId": "string",
            "visible": True,False,
            "local": [
                [0,0],
                [1,0]...
            ],
            "error": "string"
            }]
            ]

    """
    if (execute_local is True):
        raise NotImplementedError("local execution not yet implemented")

    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%s/world-to-local-coordinates" % (str(z))
    r = session.put(request_url, data=renderdumps(d),
                    headers={"content-type": "application/json"})
    return r.json()


@renderaccess
def local_to_world_coordinates_batch(stack, d, z, host=None,
                                     port=None, owner=None, project=None,
                                     session=requests.session(),
                                     render=None, **kwargs):
    """convert coordinate parameters from local to world

    Parameters
    ----------
    stack : str

    d : list[dict]
        list of dictionary of local coordinates to map
        ::
            [ {
            "tileId": "string",
            "local": [
                [0,0],
                [1,0]...
            ],
            "error": "string"
            }]

    z : float
        z coordinate to map from
    session :
         (Default value = requests.session()
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    list[dict]
        list of dictionaries containing world coordinates

        ::

            [ {
            "tileId": "string",
            "world": [
                [0,0],
                [1,0]...
            ],
            "error": "string"
            }]
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + \
        "/z/%s/local-to-world-coordinates" % (str(z))
    r = session.put(request_url, data=renderdumps(d),
                    headers={"content-type": "application/json"})
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


def package_point_match_data_into_json(dataarray, tileId,
                                       local_or_world='local'):
    """Convert a set of points defined by a numpy array and a tileId to a json
    for use in the renderapi

    Parameters
    ----------
    dataarray : numpy.array
        a Nx2 array of points

    tileId : str
        a tileId to package them into
    local_or_world :
        whether this should be represented as a local or world coordinate
         (Default value = 'local')

    Returns
    -------
    dict
        dictionary representation of those points and tileId
        following

        ::

            {
                "tileId": "string",
                "world": [
                    [0,0],
                    [1,0]...
                ],
                "error": "string"
            }
    """
    dlist = []
    for i in range(dataarray.shape[0]):
        d = {}
        d['tileId'] = tileId
        d[local_or_world] = [dataarray[i, 0], dataarray[i, 1]]
        dlist.append(d)
    return dlist


def unpackage_world_to_local_point_match_from_json(json_answer, tileId):
    """Converts a dictionary answer from a world>local
    coordinates call from a dictionary to numpy array format

    Parameters
    ----------
    json_answer : list[dict]
        json reponse from a world>local call (N long)

    tileId : str
        tileId to extract, usually the world tileId passed in

    Returns
    -------
    numpy.array
        Nx2 array of local points
    """
    answer = np.zeros((len(json_answer), 2))
    for i, local_answer in enumerate(json_answer):
        coord = next(ans for ans in local_answer if ans['tileId'] == tileId)
        c = coord['local']
        answer[i, 0] = c[0]
        answer[i, 1] = c[1]
    return answer


# @renderaccess
# def old_world_to_local_coordinates_array(stack, dataarray, tileId, z=0,
#                                          host=None, port=None,
#                                          owner=None, project=None,
#                                          session=requests.session(),
#                                          render=None, **kwargs):
#     ''''''

#     request_url = format_preamble(
#         host, port, owner, project, stack) + \
#         "/z/%d/world-to-local-coordinates" % (z)
#     dlist = []
#     for i in range(dataarray.shape[0]):
#         d = {}
#         d['tileId'] = tileId
#         d['world'] = [dataarray[i, 0], dataarray[i, 1]]
#         dlist.append(d)
#     jsondata = json.dumps(dlist)
#     r = session.put(request_url, data=jsondata,
#                     headers={"content-type": "application/json"})
#     json_answer = r.json()
#     try:
#         answer = np.zeros(dataarray.shape)
#         for i, coord in enumerate(json_answer):
#             c = coord['local']
#             answer[i, 0] = c[0]
#             answer[i, 1] = c[1]
#         return answer
#     except Exception as e:
#         logger.error(e)
#         logger.error(json_answer)


def unpackage_local_to_world_point_match_from_json(json_answer):
    """converts a local>world call json response into a numpy array

    Parameters
    ----------
    json_answer : list[dict]
        response from a local>world call (N long)

    Returns
    -------
    numpy.array
        Nx2 numpy array of coordinates
    """
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
    """map world to local coordinates using numpy array

    Parameters
    ----------
    stack : str
        render stack to map
    dataarray : numpy.array
        Nx2 numpy array of points to world points to map
    tileId : str
        tileId to map from and to
    z : float
        z coordinate to map
    render : renderapi.render.Render
        render connect object
    doClientSide : boolean
         (Default value = False)
    number_of_threads : int
         (Default value = 20)
    session : requests.session.Session
         session object used in request

    Returns
    -------
    numpy.array:
        Nx2 numpy array of points in local coordinates
    """
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


# @renderaccess
# def old_local_to_world_coordinates_array(stack, dataarray, tileId, z=0,
#                                          host=None, port=None,
#                                          owner=None, project=None,
#                                          session=requests.session(),
#                                          render=None, **kwargs):
#     ''''''
#     request_url = format_preamble(
#         host, port, owner, project, stack) + \
#         "/z/%d/local-to-world-coordinates" % (z)
#     dlist = []
#     for i in range(dataarray.shape[0]):
#         d = {}
#         d['tileId'] = tileId
#         d['local'] = [dataarray[i, 0], dataarray[i, 1]]
#         dlist.append(d)
#     jsondata = json.dumps(dlist)
#     r = session.put(request_url, data=jsondata,
#                     headers={"content-type": "application/json"})
#     json_answer = r.json()
#     try:
#         answer = np.zeros(dataarray.shape)
#         logger.debug('shape {}'.format(dataarray.shape))
#         logger.debug('length of json_answer {}'.format(len(json_answer)))
#         for i, coord in enumerate(json_answer):
#             c = coord['world']
#             answer[i, 0] = c[0]
#             answer[i, 1] = c[1]
#         return answer
#     except Exception as e:
#         logger.error(e)
#         logger.error(json_answer)


@renderaccess
def local_to_world_coordinates_array(stack, dataarray, tileId, z,
                                     render=None, host=None, port=None,
                                     owner=None, project=None,
                                     client_script=None,
                                     doClientSide=False, number_of_threads=20,
                                     session=requests.session(), **kwargs):
    """map local to world coordinates using numpy array

    Parameters
    ----------
    stack : str
        render stack to map
    dataarray : numpy.array
        Nx2 array of points in local coordinates
    tileId : str
        tile to map points from
    z : float
        z position to map
    render : renderapi.render.Render
        render connect object
    doClientSide : boolean
         (Default value = False)
    number_of_threads : int
         (Default value = 20)
    session : requests.session.Session
         session object used in request
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    numpy.array
        Nx2 numpy array in world coordinates

    """
    jsondata = package_point_match_data_into_json(dataarray, tileId, 'local')
    if doClientSide:
        json_answer = local_to_world_coordinates_clientside(
            stack, [[lp] for lp in jsondata], z, host=host, port=port,
            owner=owner, project=project, client_script=client_script,
            number_of_threads=number_of_threads)
    else:
        json_answer = local_to_world_coordinates_batch(
            stack, jsondata, z, host=host, port=port, owner=owner,
            project=project, session=session)
    return unpackage_local_to_world_point_match_from_json(json_answer)


def map_coordinates_clientside(stack, jsondata, z, host, port, owner,
                               project, client_script, isLocalToWorld=False,
                               store_injson=False, store_outjson=False,
                               number_of_threads=20, memGB='1G'):
    """map coordinates using the java client library

    Parameters
    ----------
    stack : str
         stack to map
    jsondata : dict
         json dictionary to map following the pattern of local>world or world>local
    z : float
         z position to map
    isLocalToWorld : boolean
         whether transform is local to world (False implies world to local)
    store_injson : boolean
         whether to store input json file (created with tempfile)
    store_outjson : boolean
         whether to store  output json file (created with tempfile)
    number_of_threads : int
         threads to execute clientside computation
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    json
        json data as would be returned by client calls
        of local>world or world>local
    """  # noqa: E501
    # write point match json to temp file on disk
    with tempfile.NamedTemporaryFile(
            prefix='render_coordinates_in_', suffix='.json',
            mode='w', delete=False) as f:
        logger.debug('jsondata:{}'.format(jsondata))
        json_inpath = f.name
        renderdump(jsondata, f)

    # get a temporary location for the output
    with tempfile.NamedTemporaryFile(
            prefix='render_coordinates_out_', suffix='.json',
            delete=False) as f:
        json_outpath = f.name
    # call the java client
    coordinateClient(stack, z, fromJson=json_inpath, toJson=json_outpath,
                     localToWorld=isLocalToWorld,
                     numberOfThreads=number_of_threads,
                     host=host, port=port, owner=owner, project=project,
                     client_script=client_script, memGB=memGB)

    # return the json results
    with open(json_outpath, 'r') as f:
        j = json.load(f)
    if not store_injson:
        os.remove(json_inpath)
    if not store_outjson:
        os.remove(json_outpath)

    return j


@renderaccess
def world_to_local_coordinates_clientside(stack, jsondata, z,
                                          host=None, port=None, owner=None,
                                          project=None, client_script=None,
                                          number_of_threads=20,
                                          render=None, **kwargs):
    """map_coordinates_clientside for mapping world to local

    Parameters
    ----------
    stack : str
        render stack to map
    jsondata : dict
        world coordinates in dictionary format
    z : float
        z coordinate to map
    number_of_threads : int
        number of threads to use when doing parallelization
    render : renderapi.render.Render
        render connect object

    Returns
    -------
    json
        local coordinates in dictionary format
    """

    return map_coordinates_clientside(stack, jsondata, z,
                                      host=host, port=port, owner=owner,
                                      project=project,
                                      client_script=client_script,
                                      isLocalToWorld=False,
                                      number_of_threads=number_of_threads)


@renderaccess
def local_to_world_coordinates_clientside(stack, jsondata, z,
                                          host=None, port=None, owner=None,
                                          project=None, client_script=None,
                                          number_of_threads=20,
                                          render=None, **kwargs):
    """map_coordinates_clientside for mapping local to world

    Parameters
    ----------
    stack : str
        render stack to map
    jsondata : list[dict]
        local coordinates in dictionary format
    z : float
        z position to map
    number_of_threads : int
        threads for java client script to use during mapping

    Returns
    -------
    dict
        world coordinates in dictionary format
    """
    return map_coordinates_clientside(stack, jsondata, z,
                                      host=host, port=port, owner=owner,
                                      project=project,
                                      client_script=client_script,
                                      isLocalToWorld=True,
                                      number_of_threads=number_of_threads)
