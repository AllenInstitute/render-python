#!/usr/bin/env python
import logging
from time import strftime
import requests
from .errors import RenderError
from .utils import jbool, NullHandler, post_json, put_json
from .render import (format_baseurl, format_preamble,
                     renderaccess)
import json

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class StackVersion:
    """StackVersion, metadata about a stack

    Attributes
    ----------
    cycleNumber : int
        cycleNumber, use as you wish to track versions (default None)
    cycleStepNumber : int
        cycleStepNumber, use as you with to track versions (default None)
    stackResolutionX : float
        stackResolutionX, resolution of scale = 1.0 in nm
    stackResolutionY : float
        stackResolutionY, resolution of scale = 1.0 in nm
    stackResolutionZ : float
        stackResolutionZ, resolution of scale = 1.0 in nm
    mipmapPathBuilder : str
        path to mipmap builder (?)
    materializedBoxRootPath : str
        path to materializer (?)
    createTimeStamp : str
        time stamp of stack creation (default to now)
    versionNotes : str
        notes about this stack (optional)
    """
    def __init__(self, cycleNumber=None, cycleStepNumber=None,
                 stackResolutionX=None, stackResolutionY=None,
                 stackResolutionZ=None,
                 materializedBoxRootPath=None, mipmapPathBuilder=None,
                 versionNotes=None,
                 createTimestamp=None, **kwargs):
        self.cycleNumber = cycleNumber
        self.cycleStepNumber = cycleStepNumber
        self.stackResolutionX = stackResolutionX
        self.stackResolutionY = stackResolutionY
        self.stackResolutionZ = stackResolutionZ
        self.mipmapPathBuilder = mipmapPathBuilder
        self.materializedBoxRootPath = materializedBoxRootPath
        self.createTimestamp = (strftime('%Y-%M-%dT%H:%M:%S.00Z') if
                                createTimestamp is None else createTimestamp)
        self.versionNotes = versionNotes

    def to_dict(self):
        """serialization function

        Returns
        -------
        dict
            json compatible verson of this object
        """
        d = {}
        d.update(({'cycleNumber': self.cycleNumber}
                  if self.cycleNumber is not None else {}))
        d.update(({'cycleStepNumber': self.cycleStepNumber}
                  if self.cycleStepNumber is not None else {}))
        d.update(({'stackResolutionX': self.stackResolutionX}
                  if self.stackResolutionX is not None else {}))
        d.update(({'stackResolutionY': self.stackResolutionY}
                  if self.stackResolutionY is not None else {}))
        d.update(({'stackResolutionZ': self.stackResolutionZ}
                  if self.stackResolutionZ is not None else {}))
        d.update(({'createTimestamp': self.createTimestamp}
                  if self.createTimestamp is not None else {}))
        d.update(({'mipmapPathBuilder': self.mipmapPathBuilder}
                  if self.mipmapPathBuilder is not None else {}))
        d.update(({'versionNotes': self.versionNotes}
                  if self.versionNotes is not None else {}))
        d.update(({'materializedBoxRootPath': self.materializedBoxRootPath}
                  if self.materializedBoxRootPath is not None else {}))
        return d

    def from_dict(self, d):
        """deserialization function

        Parameters
        ----------
        d : dict
            dictionary to update the properties of this object
        """
        self.__dict__.update({k: v for k, v in d.items()})


@renderaccess
def set_stack_metadata(stack, sv, host=None, port=None, owner=None,
                       project=None, session=requests.session(),
                       render=None, **kwargs):
    """sets the stack metadata for a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to set the metadata for
    sv : StackVersion
        metadata for the stack
    render : renderapi.render.RenderClient
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.response
        response from server

    """
    request_url = format_preamble(host, port, owner, project, stack)
    logger.debug(request_url)
    return post_json(session, request_url, sv.to_dict())


@renderaccess
def get_full_stack_metadata(stack, host=None, port=None, owner=None,
                            project=None, session=requests.session(),
                            render=None, **kwargs):
    """get stack metadata for stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get the metadata for
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    dict
        metadata of the stack

    Raises
    ------
        RenderError
    """
    request_url = format_preamble(host, port, owner, project, stack)

    logger.debug(request_url)
    r = session.get(request_url)

    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


def get_stack_metadata(*args, **kwargs):
    """get the stack version metadata for a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get the metadata for
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    StackVersion
        metadata of the stack

    Raises
    ------
        RenderError

    """
    j = get_full_stack_metadata(*args, **kwargs)
    try:
        sv = StackVersion()
        sv.from_dict(j['currentVersion'])
        return sv
    except Exception as e:
        logger.error(e)
        raise RenderError(e)


@renderaccess
def set_stack_state(stack, state='LOADING', host=None, port=None,
                    owner=None, project=None,
                    session=requests.session(), render=None, **kwargs):
    """
    set state of selected stack.

    TODO there is a limited direction in which these stack changes can go

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to set state for
    state : str
        state of stack, one of ['LOADING', 'COMPLETE', 'OFFLINE', 'READ_ONLY']
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response

    Raises
    ------
    RenderError
    """
    if state not in ['LOADING', 'COMPLETE', 'OFFLINE', 'READ_ONLY']:
        raise RenderError('state {} not in known states {}'.format(
            state, ['LOADING', 'COMPLETE', 'OFFLINE', 'READ_ONLY']))
    request_url = format_preamble(
        host, port, owner, project, stack) + "/state/%s" % state
    logger.debug(request_url)
    r = session.put(request_url, data=None,
                    headers={"content-type": "application/json"})
    if (r.status_code != 201):
        logger.error(r.text)
        raise RenderError(r.text)
    return r


@renderaccess
def likelyUniqueId(host=None, port=None,
                   session=requests.session(), render=None, **kwargs):
    """return hex-code nearly-unique id from render server

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    str
        string representation of hex-code
    """
    request_url = '{}/likelyUniqueId'.format(format_baseurl(host, port))
    r = session.get(request_url, data=None,
                    headers={"content-type": "text/plain"})
    return r.text


def make_stack_params(host, port, owner, project, stack):
    """utility function to turn host,port,owner,project,stack combinations
    to java CLI based argument list for subprocess calling

    Parameters
    ----------
    host : str
        render server
    port : int
        render server port
    owner : str
        render owner
    project : str
        render project
    stack : str
        render stack

    Returns
    -------
    :obj:`list` of :obj:`str`
        java CLI list of arguments for subprocess calling

    """
    baseurl = format_baseurl(host, port)
    project_params = ['--baseDataUrl', baseurl,
                      '--owner', owner, '--project', project]
    stack_params = project_params + ['--stack', stack]
    return stack_params


@renderaccess
def delete_stack(stack, host=None, port=None, owner=None,
                 project=None, session=requests.session(),
                 render=None, **kwargs):
    """deletes a stack from render server

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to delete
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response

    """
    request_url = format_preamble(host, port, owner, project, stack)
    r = session.delete(request_url)
    logger.debug(r.text)
    return r


@renderaccess
def delete_section(stack, z, host=None, port=None, owner=None,
                   project=None, session=requests.session(),
                   render=None, **kwargs):
    """removes a single z from a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to delete section from
    z : float
        z value to delete
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response
    """
    request_url = '{}/z/{}'.format(
        format_preamble(host, port, owner, project, stack), z)
    r = session.delete(request_url)
    logger.debug(r.text)
    return r


@renderaccess
def delete_tile(stack, tileId, host=None, port=None, owner=None,
                project=None, session=requests.session(),
                render=None, **kwargs):
    """
    removes a tile from a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to delete tile from
    tileId : str
        tileId of tilespec to remove from stack
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response

    """
    request_url = '{}/tile/{}'.format(
        format_preamble(host, port, owner, project, stack), tileId)
    r = session.delete(request_url)
    logger.debug(r.text)
    return r


@renderaccess
def create_stack(stack, cycleNumber=None, cycleStepNumber=None,
                 stackResolutionX=None, stackResolutionY=None,
                 stackResolutionZ=None, force_resolution=True,
                 host=None, port=None, owner=None, project=None,
                 session=requests.session(), render=None, **kwargs):
    """creates a new stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        render stack name to create
    cycleNumber : int
        cycleNumber to use to track stages
    cycleStepNumber : int
        cycleStepNumber to use to track stages
    stackResolutionX : float
        resolution of x pixels at scale=1.0
    stackResolutionY : float
        resolution of y pixels at scale=1.0
    stackResoluiontZ : float
        resolution of z sections at scale=1.0
    force_resolution : bool
        fill in resolution of 1.0 for missing resolutions
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response

    Raises
    ------
        RenderError
    """
    if force_resolution:
        stackResolutionX, stackResolutionY, stackResolutionZ = [
            (1.0 if res is None else res)
            for res in [stackResolutionX, stackResolutionY, stackResolutionZ]]
        logger.debug('forcing resolution x:{}, y:{}, z:{}'.format(
            stackResolutionX, stackResolutionY, stackResolutionZ))

    sv = StackVersion(
        cycleNumber=cycleNumber, cycleStepNumber=cycleStepNumber,
        stackResolutionX=stackResolutionX, stackResolutionY=stackResolutionY,
        stackResolutionZ=stackResolutionZ)
    request_url = format_preamble(host, port, owner, project, stack)
    logger.debug("stack version {} {}".format(request_url, sv.to_dict()))
    r = post_json(session, request_url, sv.to_dict())
    try:
        return r
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def clone_stack(inputstack, outputstack, skipTransforms=False, toProject=None,
                zs=None, close_stack=True, host=None, port=None,
                owner=None, project=None, session=None, render=None, **kwargs):
    """clone a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    inputstack : str
        name of input stack to clone
    outputstack : str
        name of destination stack. if exists, must be LOADING
    skipTransforms : bool
        boolean whether to strip transformations in new stack (default=False)
    toProject : str
        string name of destination project (default same as inputstack)
    zs : :obj:`list` of :obj:`float` or None
        list of selected z values to clone into stack (optional)
    close_stack : bool
        whether to set stack to COMPLETE when finished
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    requests.session.response
        server response
    """
    session = requests.session() if session is None else session
    sv = StackVersion(**kwargs)
    newstack_project = project
    qparams = {}
    if zs is not None:
        qparams['z'] = [float(i) for i in zs]
    if skipTransforms is not None:
        qparams['skipTransforms'] = jbool(skipTransforms)
    if toProject is not None:
        qparams['toProject'] = toProject
        newstack_project = toProject

    request_url = '{}/cloneTo/{}'.format(format_preamble(
        host, port, owner, project, inputstack), outputstack)

    logger.debug(request_url)
    r = put_json(session, request_url, sv.to_dict(), params=qparams)

    if close_stack:
        set_stack_state(outputstack, 'COMPLETE', host, port, owner,
                        newstack_project)
    return r


@renderaccess
def get_z_values_for_stack(stack, project=None, host=None, port=None,
                           owner=None, session=requests.session(),
                           render=None, **kwargs):
    """get a list of z values for which there are tiles in the stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get z values for
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    :obj:`list` of :obj:`float`
        z values in stack

    Raises
    ------
    RenderError
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + "/zValues/"
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


def get_z_value_for_section(stack, sectionId, **kwargs):
    """DEPRECATED (use :func:`get_section_z_value`) instead"""
    logger.warning(
        "DEPRECATED, use renderapi.stack.get_section_z_value instead")
    return get_section_z_value(stack, sectionId, **kwargs)


# haven't fully supported this yet
# @renderaccess
# def put_resolved_tilespecs(stack, json_dict, host=None, port=None,
#                            owner=None, project=None,
#                            session=requests.session(),
#                            render=None, **kwargs):
#     request_url = format_preamble(
#         host, port, owner, project, stack) + "/resolvedTiles"
#     r = post_json(session, request_url, json_dict)
#     return r


@renderaccess
def get_bounds_from_z(stack, z, host=None, port=None, owner=None,
                      project=None, session=requests.session(),
                      render=None, **kwargs):
    """get a bounds dictionary for a specific z

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get bounds from
    z : float
        z value to get bounds for
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    dict
        bounds with keys minY,minY,maxX,maxY,minZ,maxZ

    Raises
    ------
    RenderError

    """
    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/%f/bounds' % (z)

    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_stack_bounds(stack, host=None, port=None, owner=None, project=None,
                     session=requests.session(), render=None, **kwargs):
    """get bounds of a whole stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get bounds from
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    dict
        bounds with keys minY,minY,maxX,maxY,minZ,maxZ

    Raises
    ------
    RenderError

    """
    request_url = format_preamble(
        host, port, owner, project, stack) + '/bounds'
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_sectionId_for_z(stack, z, host=None, port=None, owner=None,
                        project=None, session=requests.session(),
                        render=None, **kwargs):
    """returns the sectionId associated with a particular z value

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to look within
    sectionId : str
        sectionId to find z value
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    float
        z value of sectionId

    Raises
    ------
    RenderError

    """
    sectionData = get_stack_sectionData(
        stack, host, port, owner, project, session)
    try:
        return next(sd['sectionId'] for sd in sectionData if sd['z'] == z)
    except Exception as e:
        logger.error(e)
        raise RenderError('Could not find z value %f in stack %s' % (z, stack))


@renderaccess
def get_stack_sectionData(stack, host=None, port=None, owner=None,
                          project=None, session=requests.session(),
                          render=None, **kwargs):
    """returns information about the sectionIds of each slice in stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        name of stack to get data about
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    dict
        sectionData as below
        ::
            [{
                "sectionId": "string",
                "z": 0,
                "tileCount": 0,
                "minX": 0,
                "maxX": 0,
                "minY": 0,
                "maxY": 0
            }]
    Raises
    ------
    RenderError
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + '/sectionData'
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_section_z_value(stack, sectionId, host=None, port=None,
                        owner=None, project=None, session=requests.session(),
                        render=None, **kwargs):
    """get the z value for a specific sectionId (string)

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        render stack string to look within
    sectionId : str
        sectionId to find z value
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    float
        z value of section

    Raises
    ------
    RenderError
    """
    request_url = format_preamble(
        host, port, owner, project, stack) + "/section/%s/z" % sectionId
    r = session.get(request_url)
    try:
        return float(r.json())
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)


@renderaccess
def get_stack_tileIds(stack, host=None, port=None, owner=None, project=None,
                      session=requests.session(), render=None, **kwargs):
    """get tileIds for a stack

    :func:`renderapi.render.renderaccess` decorated function

    Parameters
    ----------
    stack : str
        stack to get tileIds
    render : renderapi.render.Render
        render connect object
    session : requests.sessions.Session
        session object (default start a new one)

    Returns
    -------
    :obj:`list` of :obj:`str`
        list of tileIds in stack

    Raises
    ------
    RenderError
    """
    request_url = '{}/tileIds'.format(
        format_preamble(host, port, owner, project, stack))
    r = session.get(request_url)
    try:
        # FIXME render bug return non-json formatted answer
        # return r.json()
        return json.loads(r.text.replace("'", '"'))
    except Exception as e:
        logger.error(e)
        logger.error(r.text)
        raise RenderError(r.text)
