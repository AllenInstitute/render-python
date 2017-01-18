#!/usr/bin/env python
import json
import logging
from time import strftime
import requests
from render import Render, format_baseurl, format_preamble


class StackVersion:
    def __init__(self, cycleNumber=1, cycleStepNumber=1, stackResolutionX=1,
                 stackResolutionY=1, stackResolutionZ=1,
                 materializedBoxRootPath=None, versionNotes="",
                 createTimestamp=None):
        self.cycleNumber = cycleNumber
        self.cycleStepNumber = cycleStepNumber
        self.stackResolutionX = stackResolutionX
        self.stackResolutionY = stackResolutionY
        self.stackResolutionZ = stackResolutionZ
        self.materializedBoxRootPath = materializedBoxRootPath
        if createTimestamp is None:
            createTimestamp = strftime('%Y-%M-%dT%H:%M:%S.00Z')
        self.createTimestamp = createTimestamp
        self.versionNotes = versionNotes

    def to_dict(self):
        d = {}
        d['cycleNumber'] = self.cycleNumber
        d['cycleStepNumber'] = self.cycleStepNumber
        d['stackResolutionX'] = self.stackResolutionX
        d['stackResolutionY'] = self.stackResolutionY
        d['stackResolutionZ'] = self.stackResolutionZ
        d['createTimestamp'] = self.createTimestamp
        d["materializedBoxRootPath"] = "string"
        d['mipmapPathBuilder'] = {'numberOfLevels': 0}
        d['versionNotes'] = self.versionNotes
        return d

    def from_dict(self, d):
        for key in d.keys():
            eval('self.%s=d[%s]' % (key, key))


def set_stack_state(stack, render=None, state='LOADING', host=None, port=None,
                    owner=None, project=None, session=requests.session(),
                    verbose=False, **kwargs):

    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return set_stack_state(
            stack, **render.make_kwargs(
                host=host, port=port, owner=owner, project=project,
                **{'verbose': verbose, 'state': state, 'session': session}))

    assert state in ['LOADING', 'COMPLETE', 'OFFLINE']
    request_url = format_preamble(
        host, port, owner, project, stack) + "/state/%s" % state
    if verbose:
        request_url
    r = session.put(request_url, data=None,
                    headers={"content-type": "application/json"})
    return r


def likelyUniqueId(render=None, host=None, port=None,
                   session=requests.session(), **kwargs):
    '''return hex-code nearly-unique id from render server'''
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return likelyUniqueId(**render.make_kwargs(host=host, port=port,
                              **{'session': session}))

    request_url = '{}/likelyUniqueId'.format(format_baseurl(host, port))
    return session.get(request_url, data=None,
                       headers={"content-type": "application/json"})


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
    logging.debug(r.text)
    return r


def create_stack(self, stack, cycleNumber=1, cycleStepNumber=1,
                 host=None, port=None, owner=None, project=None, verbose=False,
                 session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return create_stack(stack, **render.make_kwargs(
            host=host, port=port, owner=owner, project=project,
            **{'session': session, 'cycleNumber': cycleNumber,
               'cycleStepNumber': cycleStepNumber, 'verbose': verbose}))

    sv = StackVersion(
        cycleNumber=cycleNumber, cycleStepNumber=cycleStepNumber)
    request_url = format_preamble(host, port, owner, project, stack)
    if verbose:
        print "stack version2", request_url, sv.to_dict()
    payload = json.dumps(sv.to_dict())
    r = session.post(request_url, data=payload,
                     headers={"content-type": "application/json",
                              "Accept": "application/json"})
    try:
        return r
    except:
        logging.error(r.text)
        return None
