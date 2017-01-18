#!/usr/bin/env python
import json
import logging
import requests
from renderapi import Render


def format_baseurl(host, port):
    return 'http://%s:%d/render-ws/v1' % (host, port)


def format_preamble(host, port, owner, project, stack):
    preamble = "%s/owner/%s/project/%s/stack/%s" % (
        format_baseurl(host, port), owner, project, stack)
    return preamble


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
