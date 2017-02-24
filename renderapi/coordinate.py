#!/usr/bin/env python
'''
coordinate mapping functions for render api
'''

from .render import Render, format_preamble
from .client import call_run_ws_client
import requests
import json
import numpy as np
import logging
import tempfile
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


def world_to_local_coordinates_batch(stack, data,z, render=None, host=None,
                                     port=None, owner=None, project=None, execute_local=True,
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
        "/z/%s/world-to-local-coordinates" % (str(z))
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
        "/z/%s/local-to-world-coordinates" % (str(z))
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json"})
    try:
        return r.json()
    except:
        logger.error(r.text)

def package_point_match_data_into_json(dataarray,tileId,local_or_world='local'):
    dlist = []
    for i in range(dataarray.shape[0]):
        d = {}
        d['tileId'] = tileId
        d[local_or_world] = [dataarray[i, 0], dataarray[i, 1]]
        dlist.append(d)
    return json.dumps(dlist)

def unpackage_point_match_data_from_json(json_answer,local_or_world='local'):
    answer = np.zeros((len(json_answer),2))
    if type(json_answer[0]) == list:
        json_answer = json_answer[0]
    for i, coord in enumerate(json_answer):
        c = coord[local_or_world]
        answer[i, 0] = c[0]
        answer[i, 1] = c[1]
    return answer

def world_to_local_coordinates_array(stack, dataarray, tileId, z,
                                     render=None, host=None, port=None,
                                     owner=None, project=None, client_script = None,
                                     doClientSide = False,number_of_threads=20,
                                     session=requests.session(), **kwargs):
    ''''''

    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return world_to_local_coordinates_array(
            stack, dataarray, tileId, z, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_script = client_script,
                **{'session': session,'doClientSide':doClientSide,'number_of_threads':20}))

    jsondata =   package_point_match_data_into_json(dataarray,tileId,'world')
    if doClientSide:
        json_answer = world_to_local_coordinates_clientside(stack,jsondata,tileId,z,
                                                            host=host,port=port,owner=owner,
                                                            project=project,
                                                            client_script=client_script,
                                                            number_of_threads=number_of_threads)
    else:
        json_answer = world_to_local_coordinates_batch(stack,jsondata,z,
                                                       host=host,port=port,
                                                       owner=owner,project=project,
                                                       session=session)
    #try:
    return unpackage_point_match_data_from_json(json_answer,'local')
    #except:
    #    logger.error('could not unpackage world_to_local answer')
    #    logger.error(json_answer)

def local_to_world_coordinates_array(stack, dataarray, tileId, z,
                                     render=None, host=None, port=None,
                                     owner=None, project=None, client_script = None,
                                     doClientSide = False, number_of_threads=20,
                                     session=requests.session(), **kwargs):
    ''''''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return local_to_world_coordinates_array(
            stack, dataarray, tileId, z,**render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_script = client_script,
                **{'session': session,'doClientSide':doClientSide,'number_of_threads':number_of_threads}))

    jsondata = package_point_match_data_into_json(dataarray,tileId,'local')
    if doClientSide:
        json_answer = local_to_world_coordinates_clientside(stack,jsondata,tileId,z,
                                                            host=host,port=port,owner=owner,project=project,
                                                            client_script=client_script,
                                                            number_of_threads=number_of_threads)
    else:
        json_answer = local_to_world_coordinates_batch(stack,jsondata,z,
                                                       host=host,port=port,owner=owner,
                                                       project=project,session=session)
    #try:
    return unpackage_point_match_data_from_json(json_answer,'world')
    #except:
    #    logger.error('could not unpackage local_to_world answer')
    #    logger.error(json_answer)

def map_coordinates_clientside(stack,jsondata,tileId,z,host,port,owner,project,client_script,isLocalToWorld=False,number_of_threads=20):
    #write point match json to temp file on disk
    json_infile,json_inpath = tempfile.mkstemp(prefix='render_coordinates_in_',suffix='.json')
    fp = open(json_inpath,'w')
    fp.write(jsondata)
    fp.close()

    #json.dump(jsondata,open(json_inpath,'w'))

    #get a temporary location for the output
    json_outpath = tempfile.mktemp(prefix='render_coordinates_out_',suffix='.json')



    #define arguments
    args = ['--baseDataUrl','http://%s:%d/render-ws/v1'%(host,port),
            '--owner',owner,
            '--project',project,
            '--stack',stack,
            '--z',str(z),
            '--fromJson',json_inpath,
            '--toJson',json_outpath,
            '--numberOfThreads',str(number_of_threads)]
    if isLocalToWorld:
        args+=['--localToWorld']

    #call the java client
    call_run_ws_client('org.janelia.render.client.CoordinateClient', add_args=args, client_script=client_script)

    #return the json results
    #try:
    return json.load(open(json_outpath,'r'))
    #except:
    #    logger.error('failed to load json after map_coordinates_clientside:\n%s'%json.dumps(jsondata))

def world_to_local_coordinates_clientside(stack,jsondata,tileId,z,render=None,
                                          host=None,port=None,owner=None,
                                          project=None,client_script=None,
                                          number_of_threads=20,
                                          session=requests.session(),**kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return world_to_local_coordinates_clientside(
            stack, dataarray, tileId, z,**render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_script=client_script,
                **{'session': session,'number_of_threads':20}))

    return map_coordinates_clientside(stack,jsondata,tileId,z,
                                      host=host,port=port,owner=owner,
                                      project=project,client_script=client_script,
                                      isLocalToWorld=False,number_of_threads=number_of_threads)

def local_to_world_coordinates_clientside(stack,jsondata,tileId,z,render=None,
                                          host=None,port=None,owner=None,
                                          project=None,client_script=None,
                                          number_of_threads=20,
                                          session=requests.session(),**kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return local_to_world_coordinates_clientside(
            stack, dataarray, tileId, z,**render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                client_script=client_script,
                **{'session': session,'number_of_threads':20}))

    return map_coordinates_clientside(stack,jsondata,tileId,z,
                                      host=host,port=port,owner=owner,
                                      project=project,client_script=client_script,
                                      isLocalToWorld=True,number_of_threads=number_of_threads)