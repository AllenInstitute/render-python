#!/usr/bin/env python
import logging
import os
from functools import wraps
import requests
import json
from .utils import defaultifNone, NullHandler, fitargspec, post_json, put_json
from .errors import ClientScriptError

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Render(object):
    '''
    Render object to store connection settings for render server
    '''
    def __init__(self, host=None, port=None, owner=None, project=None,
                 client_scripts=None):
        self.DEFAULT_HOST = host
        self.DEFAULT_PORT = port
        self.DEFAULT_PROJECT = project
        self.DEFAULT_OWNER = owner
        self.DEFAULT_CLIENT_SCRIPTS = client_scripts

        logger.debug('Render object created with '
                     'host={h}, port={p}, project={pr}, '
                     'owner={o}, scripts={s}'.format(
                          h=self.DEFAULT_HOST, p=self.DEFAULT_PORT,
                          pr=self.DEFAULT_PROJECT, o=self.DEFAULT_OWNER,
                          s=self.DEFAULT_CLIENT_SCRIPTS))

    @property
    def DEFAULT_KWARGS(self):
        '''
        kwargs to which the render object falls back.  Depends on:
            self.DEFAULT_HOST, self.DEFAULT_OWNER, self.DEFAULT_PORT,
            self.DEFAULT_PROJECT, self.DEFAULT_CLIENT_SCRIPTS
        '''
        return self.make_kwargs()

    def make_kwargs(self, host=None, port=None, owner=None, project=None,
                    client_scripts=None, **kwargs):
        '''
        make kwargs using this render object's defaults and any
            designated kwargs passed in
        '''
        processed_kwargs = {
            'host': self.DEFAULT_HOST if host is None else host,
            'port': self.DEFAULT_PORT if port is None else port,
            'owner': self.DEFAULT_OWNER if owner is None else owner,
            'project': self.DEFAULT_PROJECT if project is None else project,
            'client_scripts': (self.DEFAULT_CLIENT_SCRIPTS if client_scripts
                               is None else client_scripts)}
        processed_kwargs.update(kwargs)
        return processed_kwargs

    def run(self, f, *args, **kwargs):
        '''
        run function from object
            technically shorter than adding render=Render to kwargs
        '''
        # FIXME WARNING I think renderaccess can default to
        # another render if defined in args (test/squash)
        kwargs['render'] = self
        return f(*args, **kwargs)


class RenderClient(Render):
    '''
    Render object to run java client commands via a wrapped client script.
        This is a work in progress.
    '''
    def __init__(self, client_script=None, memGB=None, validate_client=True,
                 *args, **kwargs):
        super(RenderClient, self).__init__(**kwargs)
        if validate_client:
            if client_script is None:
                raise ClientScriptError('No RenderClient script specified!')
            elif not os.path.isfile(client_script):
                raise ClientScriptError('Client script {} not found!'.format(
                    client_script))
        if 'run_ws_client.sh' not in os.path.basename(client_script):
            logger.warning(
                'Unrecognized client script {}!'.format(client_script))
        self.client_script = client_script

        if memGB is None:
            logger.warning(
                'No default Java heap specified -- defaulting to 1G')
            memGB = '1G'
        self.memGB = memGB

    def make_kwargs(self, *args, **kwargs):
        # hack to get dictionary defaults to work
        client_script = defaultifNone(
            kwargs.pop('client_script', None), self.client_script)
        memGB = defaultifNone(kwargs.pop('memGB', None), self.memGB)
        return super(RenderClient, self).make_kwargs(
            client_script=client_script,
            memGB=memGB,
            *args, **kwargs)


def connect(host=None, port=None, owner=None, project=None,
            client_scripts=None, client_script=None, memGB=None,
            force_http=True, validate_client=True, **kwargs):
    '''
    helper function to connect to a render instance
        can default to using environment variables if not specified in call.
    input:
        host -- string hostname for target render server -- will prepend
            "http://" if not found and force_http keyword evaluates True.
            Can be set by environment variable RENDER_HOST.
        port -- string, int, or None port for target render server.
            Optional as in 'http://hostname[:port]'.
            Can be set by environment variable RENDER_PORT.
        owner -- string owner for render-ws.
            Can be set by environment variable RENDER_OWNER.
        project -- string project for render webservice.
            Can be set by environment variable RENDER_PROJECT.
        client_scripts -- string specifying directory path
            for render-ws-java-client scripts.
            Can be set by environment variable RENDER_CLIENT_SCRIPTS.
        client_script -- string path to a wrapper for java client classes.
            Used only in RenderClient.
            Can be set by environment variable RENDER_CLIENT_SCRIPT.
        memGB -- string specifying heap size in GB for java client scripts,
            example for 1 GB: '1G'.  Used only in RenderClient.
            Can be set by environment variable RENDER_CLIENT_HEAP.
        force_http -- boolean determining whether to prepend
            'http://' to render host
    returns:
        RenderClient or Render object
    '''
    if host is None:
        if 'RENDER_HOST' not in os.environ:
            host = str(raw_input("Enter Render Host: "))
            if host == '':  # pragma: no cover
                logger.critical('Render Host must not be empty!')
                raise ValueError('Render Host must not be empty!')
        else:
            host = os.environ['RENDER_HOST']
    if force_http:
        host = (host if host.startswith('http')
                else 'http://{}'.format(host))

    if port is None:
        if 'RENDER_PORT' not in os.environ:
            port = str(int(raw_input("Enter Render Port: ")))
            if port == '':  # pragma: no cover
                # TODO better (no) port handling
                logger.critical('Render Port must not be empty!')
                raise ValueError('Render Port must not be empty!')
        else:
            port = int(os.environ['RENDER_PORT'])

    if project is None:
        if 'RENDER_PROJECT' not in os.environ:
            project = str(raw_input("Enter Render Project: "))
        else:
            project = str(os.environ['RENDER_PROJECT'])
        if project == '':  # pragma: no cover
            logger.critical('Render Project must not be empty!')
            raise ValueError('Render Project must not be empty!')

    if owner is None:
        if 'RENDER_OWNER' not in os.environ:
            owner = str(raw_input("Enter Render Owner: "))
        else:
            owner = str(os.environ['RENDER_OWNER'])
        if owner == '':  # pragma: no cover
            logger.critical('Render Owner must not be empty!')
            raise ValueError('Render Owner must not be empty!')

    # TODO should client_scripts be required?
    if client_scripts is None:
        if 'RENDER_CLIENT_SCRIPTS' not in os.environ:
            client_scripts = str(raw_input(
                "Enter Render Client Scripts location: "))
        else:
            client_scripts = str(os.environ['RENDER_CLIENT_SCRIPTS'])
        if client_scripts == '':  # pragma: no cover
            logger.critical('Render Client Scripts must '
                            'not be empty!')
            raise ValueError('Render Client Scripts must '
                             'not be empty!')
    if client_script is None:
        if 'RENDER_CLIENT_SCRIPT' not in os.environ:
            # client_script = str(raw_input("Enter Render Client Script: "))
            client_script = os.path.join(client_scripts, 'run_ws_client.sh')
        else:
            client_script = str(os.environ['RENDER_CLIENT_SCRIPT'])

    if memGB is None:
        if 'RENDER_CLIENT_HEAP' not in os.environ:
            pass
        else:
            memGB = str(os.environ['RENDER_CLIENT_HEAP'])

    try:
        return RenderClient(client_script=client_script, memGB=memGB,
                            host=host, port=port,
                            owner=owner, project=project,
                            client_scripts=client_scripts,
                            validate_client=validate_client)
    except ClientScriptError as e:
        logger.info(e)
        logger.warning(
            'Could not initiate render Client -- falling back to web')
        return Render(host=host, port=port, owner=owner, project=project,
                      client_scripts=client_scripts)


def renderaccess(f):
    '''
    decorator allowing functions asking for host, port, owner, project
        to default to a connection defined by a render object kwarg
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        args, kwargs = fitargspec(f, args, kwargs)
        render = kwargs.get('render')
        if render is not None:
            if isinstance(render, Render):
                return f(*args, **render.make_kwargs(**kwargs))
            else:
                raise ValueError(
                    'invalid Render object type {} specified!'.format(
                        type(render)))
        else:
            return f(*args, **kwargs)
    return wrapper


def format_baseurl(host, port):
    '''format host and port to a standard template render-ws url'''
    # return 'http://%s:%d/render-ws/v1' % (host, port)
    server = '{}{}'.format(host, ('' if port is None else ':{}'.format(port)))
    return '{}/render-ws/v1'.format(server)


def format_preamble(host, port, owner, project, stack):
    '''
    format host, port, owner, project, and stack parameters
       to the access point to stack-based apis
    '''
    preamble = "%s/owner/%s/project/%s/stack/%s" % (
        format_baseurl(host, port), owner, project, stack)
    return preamble


@renderaccess
def get_owners(host=None, port=None, session=requests.session(),
               render=None, **kwargs):
    '''
    return list of owners across all Projects and Stacks for a render server
    '''
    request_url = "%s/owners/" % format_baseurl(host, port)
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)


@renderaccess
def get_stack_metadata_by_owner(owner=None, host=None, port=None,
                                session=requests.session(),
                                render=None, **kwargs):
    '''
    return metadata for all stacks belonging to particular
        owner on render server
    TODO example
    '''
    request_url = "%s/owner/%s/stacks/" % (
        format_baseurl(host, port), owner)
    logger.debug(request_url)
    r = session.get(request_url)
    try:
        return r.json()
    except Exception as e:
        logger.error(e)
        logger.error(r.text)


@renderaccess
def get_projects_by_owner(owner=None, host=None, port=None,
                          session=requests.session(), render=None, **kwargs):
    '''return list of projects belonging to a single owner for render stack'''
    metadata = get_stack_metadata_by_owner(owner=owner, host=host,
                                           port=port, session=session)
    projects = list(set([m['stackId']['project'] for m in metadata]))
    return projects


@renderaccess
def get_stacks_by_owner_project(owner=None, project=None, host=None,
                                port=None, session=requests.session(),
                                render=None, **kwargs):
    '''
    return list of stacks belonging to an owner's project on render server
    '''
    metadata = get_stack_metadata_by_owner(owner=owner, host=host,
                                           port=port, session=session)
    stacks = ([m['stackId']['stack'] for m in metadata
               if m['stackId']['project'] == project])
    return stacks
