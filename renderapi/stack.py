#!/usr/bin/env python
import json
import logging
from time import strftime
import requests
from .render import Render, format_baseurl, format_preamble
from .utils import jbool

logger = logging.getLogger(__name__)


class StackVersion:
    def __init__(self, cycleNumber=1, cycleStepNumber=1, stackResolutionX=0,
                 stackResolutionY=0, stackResolutionZ=0,
                 materializedBoxRootPath=None, versionNotes="",
                 createTimestamp=None, **kwargs):
        self.cycleNumber = cycleNumber
        self.cycleStepNumber = cycleStepNumber
        self.stackResolutionX = stackResolutionX
        self.stackResolutionY = stackResolutionY
        self.stackResolutionZ = stackResolutionZ
        self.materializedBoxRootPath = materializedBoxRootPath
        self.createTimestamp = (strftime('%Y-%M-%dT%H:%M:%S.00Z') if
                                createTimestamp is None else createTimestamp)
        self.versionNotes = versionNotes

    def to_dict(self):
        d = {}
        d['cycleNumber'] = self.cycleNumber
        d['cycleStepNumber'] = self.cycleStepNumber
        d['stackResolutionX'] = self.stackResolutionX
        d['stackResolutionY'] = self.stackResolutionY
        d['stackResolutionZ'] = self.stackResolutionZ
        d['createTimestamp'] = self.createTimestamp
        d["materializedBoxRootPath"] = self.materializedBoxRootPath
        d['mipmapPathBuilder'] = {'numberOfLevels': 0}
        d['versionNotes'] = self.versionNotes
        return d

    def from_dict(self, d):
        for key in d.keys():
            eval('self.%s=d[%s]' % (key, key))


def set_stack_state(stack, state='LOADING', host=None, port=None,
                    owner=None, project=None, render=None,
                    session=requests.session(), **kwargs):

    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return set_stack_state(
            stack, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'state': state, 'session': session}))

    assert state in ['LOADING', 'COMPLETE', 'OFFLINE']
    request_url = format_preamble(
        host, port, owner, project, stack) + "/state/%s" % state
    logger.debug(request_url)
    r = session.put(request_url, data=None,
                    headers={"content-type": "application/json"})
    return r


def likelyUniqueId(host=None, port=None, render=None,
                   session=requests.session(), **kwargs):
    '''return hex-code nearly-unique id from render server'''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return likelyUniqueId(**render.make_kwargs(host=host, port=port,
                              **{'session': session}))

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


def delete_stack(stack, render=None, host=None, port=None, owner=None,
                 project=None, session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return delete_stack(stack, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            **{'session': session}))

    request_url = format_preamble(host, port, owner, project, stack)
    r = session.delete(request_url)
    logger.debug(r.text)
    return r


def create_stack(stack, cycleNumber=1, cycleStepNumber=1, render=None,
                 host=None, port=None, owner=None, project=None,
                 session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return create_stack(stack, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            **{'session': session, 'cycleNumber': cycleNumber,
               'cycleStepNumber': cycleStepNumber}))

    sv = StackVersion(
        cycleNumber=cycleNumber, cycleStepNumber=cycleStepNumber)
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


def clone_stack(inputstack, outputstack, render=None, host=None, port=None,
                owner=None, project=None, skipTransforms=False, toProject=None,
                z=None, session=None, **kwargs):
    '''
    result:
        cloned stack in LOADING state with tiles in layers specified by z'
    '''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return clone_stack(inputstack, outputstack, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            session=session, skipTransforms=skipTransforms,
            toProject=toProject, **kwargs))

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
