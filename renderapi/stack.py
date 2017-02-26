#!/usr/bin/env python
import json
import logging
from time import strftime
import requests
from .render import Render, format_baseurl, format_preamble, renderaccess
from .utils import jbool

logger = logging.getLogger(__name__)


class StackVersion:
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
        self.__dict__.update({k: v for k, v in d.items()})


@renderaccess
def set_stack_state(stack, state='LOADING', host=None, port=None,
                    owner=None, project=None,
                    session=requests.session(),  render=None, **kwargs):
    assert state in ['LOADING', 'COMPLETE', 'OFFLINE']
    request_url = format_preamble(
        host, port, owner, project, stack) + "/state/%s" % state
    logger.debug(request_url)
    r = session.put(request_url, data=None,
                    headers={"content-type": "application/json"})
    return r


@renderaccess
def likelyUniqueId(host=None, port=None,
                   session=requests.session(), render=None, **kwargs):
    '''return hex-code nearly-unique id from render server'''
    request_url = '{}/likelyUniqueId'.format(format_baseurl(host, port))
    r = session.get(request_url, data=None,
                    headers={"content-type": "text/plain"})
    return r.text


def make_stack_params(host, port, owner, project, stack):
    '''utility function to turn host,port,owner,project,stack combinations
    to java CLI based argument list for subprocess calling
    returns [--baseDataUrl,self.format_baseurl(host,port),--owner
    '''
    baseurl = format_baseurl(host, port)
    project_params = ['--baseDataUrl', baseurl,
                      '--owner', owner, '--project', project]
    stack_params = project_params + ['--stack', stack]
    return stack_params


@renderaccess
def delete_stack(stack, host=None, port=None, owner=None,
                 project=None, session=requests.session(),
                 render=None, **kwargs):
    request_url = format_preamble(host, port, owner, project, stack)
    r = session.delete(request_url)
    logger.debug(r.text)
    return r


@renderaccess
def create_stack(stack, cycleNumber=None, cycleStepNumber=None,
                 stackResolutionX=None, stackResolutionY=None,
                 stackResolutionZ=None, force_resolution=True,
                 host=None, port=None, owner=None, project=None,
                 session=requests.session(), render=None, **kwargs):
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
    payload = json.dumps(sv.to_dict())
    r = session.post(request_url, data=payload,
                     headers={"content-type": "application/json",
                              "Accept": "application/json"})
    try:
        return r
    except:
        logger.error(r.text)


# FIXME multiple z indices require multiple params?
@renderaccess
def clone_stack(inputstack, outputstack, host=None, port=None,
                owner=None, project=None, skipTransforms=False, toProject=None,
                z=None, session=None, render=None, **kwargs):
    '''
    result:
        cloned stack in LOADING state with tiles in layers specified by z'
    '''
    if z is not None:
        zs = [float(i) for i in z]  # TODO test me
    session = requests.session() if session is None else session
    sv = StackVersion(**kwargs)
    request_url = '{}/{}'.format(format_preamble(
        host, port, owner, project, inputstack), outputstack)

    logger.debug(request_url)
    r = session.put(request_url, params={
        'z': zs, 'toProject': toProject,
        'skipTransforms': jbool(skipTransforms)},
                    data=json.dumps(sv.to_dict()))

    return r


@renderaccess
def get_z_values_for_stack(stack, project=None, host=None, port=None,
                           owner=None, session=requests.session(),
                           render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + "/zValues/"
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


@renderaccess
def get_z_value_for_section(stack, sectionId, project=None,
                            host=None, port=None, owner=None,
                            session=requests.session(), render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + "/section/%s/z" % (sectionId)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


@renderaccess
def put_resolved_tilespecs(stack, data, host=None, port=None,
                           owner=None, project=None,
                           session=requests.session(), render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + "/resolvedTiles"
    r = session.put(request_url, data=data,
                    headers={"content-type": "application/json",
                             "Accept": "text/plain"})
    return r


@renderaccess
def get_bounds_from_z(stack, z, host=None, port=None, owner=None,
                      project=None, session=requests.session(),
                      render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + '/z/%f/bounds' % (z)

    r = session.get(request_url)
    try:
        return r.json()
    except:
        logger.error(r.text)


@renderaccess
def get_section_z_value(stack, sectionId, host=None, port=None,
                        owner=None, project=None, session=requests.session(),
                        render=None, **kwargs):
    request_url = format_preamble(
        host, port, owner, project, stack) + "/section/%s/z" % sectionId
    r = session.get(request_url)
    try:
        return float(r.json())
    except:
        logger.error(r.text)
    return float(process_simple_url_request(request_url, session))
