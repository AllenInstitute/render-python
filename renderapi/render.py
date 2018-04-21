#!/usr/bin/env python
import logging
import os
import requests
from .utils import defaultifNone, NullHandler, fitargspec, get_json
from .errors import ClientScriptError
from decorator import decorator
from six.moves import input as raw_input

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class Render(object):
    """Render object to store connection settings for render server.
    Baseclass that doesn't require client_scripts definition
    for client side java processing.

    See :func:`connect` for parameter definitions.

    Attributes
    ----------
    DEFAULT_HOST : str
        render host to which make_kwargs will default
    DEFAULT_PORT : int
        render port to which make_kwargs will default
    DEFAULT_OWNER : str
        render owner to which make_kwargs will default
    DEFAULT_PROJECT : str
        render project to which make_kwargs will default
    DEFAULT_CLIENT_SCRIPTS : str
        render client scripts path to which make_kwargs will default

    """

    def __init__(self, host=None, port=None, owner=None, project=None,
                 client_scripts=None, **kwargs):
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
        """"kwargs to which the render object falls back.  Depends on:
        self.DEFAULT_HOST, self.DEFAULT_OWNER, self.DEFAULT_PORT,
        self.DEFAULT_PROJECT, self.DEFAULT_CLIENT_SCRIPTS

        Returns
        -------
        dict
            default keyword arguments
        """
        return self.make_kwargs()

    def make_kwargs(self, host=None, port=None, owner=None, project=None,
                    client_scripts=None, **kwargs):
        """make kwargs using this render object's defaults and any
        designated kwargs passed in

        Parameters
        ----------
        host : str or None
            render webservice host
        port : int or None
            render webservice port
        owner : str or None
            render webservice owner
        project : str or None
            render webservice project
        client_scripts : str or None
            render java client script location
        **kwargs
            all other keyword arguments passed through

        Returns
        -------
        dict
            keyword arguments with missing
            host,port,owner,project,client_scripts filled in with defaults
        """
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
        """run function from object
            technically shorter than adding render=Render to kwargs

        Parameters
        ----------
        f : func
            renderapi function you want to call
        *args
            args passed to that function
        **kwargs
            kwargs passed to that function

        Returns
        -------
        func
            function with this :class:`Render` instance in
            keyword arguments as render=

        Examples
        --------
        >>> render = Render('server',8080)
        >>> metadata = render.run(renderapi.render.get_stack_metadata_by_owner, 'myowner')

        """  # noqa: E501
        # FIXME WARNING I think renderaccess can default to
        # another render if defined in args (test/squash)
        kwargs['render'] = self
        return f(*args, **kwargs)


class RenderClient(Render):
    """Render object to run java client commands via a wrapped client script.
    Should use :func:`connect` to create and for documentation of parameters.

    Attributes
    ----------
    DEFAULT_HOST : str
        render host to which make_kwargs will default
    DEFAULT_PORT : int
        render port to which make_kwargs will default
    DEFAULT_OWNER : str
        render owner to which make_kwargs will default
    DEFAULT_PROJECT : str
        render project to which make_kwargs will default
    DEFAULT_CLIENT_SCRIPTS : str
        render client scripts path to which make_kwargs will default
    client_script : str
        location of wrapper script for java client with input same as Render
        java client's run_ws_client.sh
    memGB : str
        string defining heap in GB to be utilized by
        java clients (default '1G' for 1 GB)
    """

    client_script_wrapper = 'run_ws_client.sh'

    def __init__(self, client_script=None, memGB=None, validate_client=True,
                 *args, **kwargs):
        """Initialize RenderClient object extending Render to
        running java client scripts

        Parameters
        ----------
        client_script : str
            path to script with same inputs as
            Render Java Client 'run_ws_client.sh'
        memGB : str
            string defining heap to be utilized by java clients in GB
            (defaults to '1G' for 1GB)
        validate_client : bool
            whether to validate that client script is a file

        Raises
        ------
        ClientScriptError
            if render client script cannot be found
        """
        super(RenderClient, self).__init__(**kwargs)
        if validate_client:
            if client_script is None:
                if self.DEFAULT_CLIENT_SCRIPTS is None:
                    raise ClientScriptError(
                        'No RenderClient script specified!')
                else:
                    logger.debug("Attempting to derive client script "
                                 "from client_scripts variable {}".format(
                                     self.DEFAULT_CLIENT_SCRIPTS))
                    client_script = self.clientscript_from_clientscripts(
                        self.DEFAULT_CLIENT_SCRIPTS)

            if not os.path.isfile(client_script):
                raise ClientScriptError('Client script {} not found!'.format(
                    client_script))
        if self.client_script_wrapper not in os.path.basename(client_script):
            logger.warning(
                'Unrecognized client script {}!'.format(client_script))
        self.client_script = client_script

        if memGB is None:
            logger.warning(
                'No default Java heap specified -- defaulting to 1G')
            memGB = '1G'
        self.memGB = memGB

    @classmethod
    def clientscript_from_clientscripts(cls, client_scripts):
        return os.path.join(client_scripts, cls.client_script_wrapper)

    def make_kwargs(self, *args, **kwargs):
        """method to fill in default properties of RenderClient object

        Parameters
        ----------
        *args
            args used to initialize RenderClient
        **kwargs
            kwargs used to initialize RenderClient

        Returns
        -------
        dict
            keyword arguments with missing
            host,port,owner,project,client_scripts,client_script,memGB
            filled in with defaults
        """
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
            force_http=True, validate_client=True, web_only=False, **kwargs):
    """helper function to create a :class:`Render` instance, or
    :class:`RenderClient` if sufficent parameters are provided.
    Will default to using environment variables if not specified in call,
    and prompt user for any parameters that are not given.

    Parameters
    ----------
    host : str
        hostname for target render server -- will prepend
        "http://" if host does not begin with 'http' and
        force_http keyword evaluates True.
        Can be set by environment variable RENDER_HOST.
    port : str, int, or None
        port for target render server.
        Optional as in 'http://hostname[:port]'.
        Can be set by environment variable RENDER_PORT.
    owner : str
        owner for render-ws.
        Can be set by environment variable RENDER_OWNER.
    project : str
        project for render webservice.
        Can be set by environment variable RENDER_PROJECT.
    client_scripts : str
        directory path for render-ws-java-client scripts.
        Can be set by environment variable RENDER_CLIENT_SCRIPTS.
    client_script : str, optional
        path to a wrapper for java client classes.
        Used only in RenderClient.
        Can be set by environment variable RENDER_CLIENT_SCRIPT.
    memGB : str
        heap size in GB for java client scripts,
        example for 1 GB: '1G'.  Used only in RenderClient.
        Can be set by environment variable RENDER_CLIENT_HEAP.
    force_http : bool
        whether to prepend
        'http://' to render host if it does not begin with 'http'
    validate_client : bool
        whether to validate existence of RenderClient run_ws_client.sh script
    web_only : bool
        whether to check environment variables/prompt user
        for client_scripts directory if not in arguments

    Returns
    -------
    Render
        a connect object to simplify specifying what render
        server to connect to
        (returns :class:`RenderClient` if sufficent parameters are passed)

    Raises
    ------
    ValueError
        if empty user input is given for required field

    """
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

    if client_scripts is None and not web_only:
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
            client_script = RenderClient.clientscript_from_clientscripts(
                client_scripts)
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


@decorator
def renderaccess(f, *args, **kwargs):
    """Decorator allowing functions asking for host, port, owner, project
    to default to a connection defined by a :class:`Render` object
    using its :func:`RenderClient.make_kwargs` method.

    You can if you wish specify any of the arguments, in which case they
    will not be filled in by the default values, but you don't have to.

    As such, the documentation omits describing the parameters which are
    natural to expect will be filled in by the renderaccess decorator.

    Parameters
    ----------
    f : func
        function to decorate
    Returns
    -------
    func
        decorated function

    Examples
    --------
    >>> render = renderapi.render.connect('server',8080,'me','my_project')
    >>> stacks = renderapi.render.get_stacks_by_owner_project(render=render)
    """
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


def format_baseurl(host, port):
    """format host and port to a standard template render-ws url

    Parameters
    ----------
    host : str
        host of render server
    port : int or None
        port of render server

    Returns
    -------
    str
        a url to the render endpoint at that
        host/port combination (append render-ws/v1)
    """
    # return 'http://%s:%d/render-ws/v1' % (host, port)
    server = '{}{}'.format(host, ('' if port is None else ':{}'.format(port)))
    return '{}/render-ws/v1'.format(server)


def format_preamble(host, port, owner, project, stack):
    """format host, port, owner, project, and stack parameters
    to the access point to stack-based apis

    Parameters
    ----------
    host : str
        render host
    port : int
        render host port
    owner : str
        render owner
    project : str
        render project
    stack : str
        render stack

    Returns
    -------
    str
        a url to the endpoint for that host, port,
        owner, project, stack combination
    """
    preamble = "%s/owner/%s/project/%s/stack/%s" % (
        format_baseurl(host, port), owner, project, stack)
    return preamble


@renderaccess
def get_owners(host=None, port=None, session=requests.session(),
               render=None, **kwargs):
    """return list of owners across all Projects and Stacks for a render server

    :func:`renderaccess` decorated function

    Parameters
    ----------
    host : str
        render host (defaults to host from render)
    port : int
        render port (default to port from render)
    session : requests.Session
        requests session
    render : RenderClient
        RenderClient connection object

    Returns
    -------
    list
        list of strings containing all render owners

    """
    request_url = "%s/owners/" % format_baseurl(host, port)
    return get_json(session, request_url)


@renderaccess
def get_stack_metadata_by_owner(owner=None, host=None, port=None,
                                session=requests.session(),
                                render=None, **kwargs):
    """return metadata for all stacks belonging to particular
        owner on render server

    :func:`renderaccess` decorated function

    Parameters
    ----------
    owner : str
        render owner
    render : RenderClient
        render connect object
    session : requests.sessions.Session
        http session to use

    Returns
    -------
    dict
        stackInfo metadata, TODO example
    """
    request_url = "%s/owner/%s/stacks/" % (
        format_baseurl(host, port), owner)
    logger.debug(request_url)
    return get_json(session, request_url)


@renderaccess
def get_projects_by_owner(owner=None, host=None, port=None,
                          session=requests.session(), render=None, **kwargs):
    """return list of projects belonging to a single owner for render stack

    :func:`renderaccess` decorated function

    Parameters
    ----------
    owner : str
        render owner
    render : RenderClient
        render connect object
    session : requests.sessions.Session
        http session to use

    Returns
    -------
    :obj:`list` of :obj:`unicode`
        render projects by this owner

    """
    metadata = get_stack_metadata_by_owner(owner=owner, host=host,
                                           port=port, session=session)
    projects = list(set([m['stackId']['project'] for m in metadata]))
    return projects


@renderaccess
def get_stacks_by_owner_project(owner=None, project=None, host=None,
                                port=None, session=requests.session(),
                                render=None, **kwargs):
    """return list of stacks belonging to an owner's project on render server

    :func:`renderaccess` decorated function

    Parameters
    ----------
    owner : str
        render owner
    project : str
        render project
    render : RenderClient
        render connect object
    session : requests.sessions.Session
        http session to use

    Returns
    -------
    :obj:`list` of :obj:`str`
        render stacks by this owner in this project

    """
    metadata = get_stack_metadata_by_owner(owner=owner, host=host,
                                           port=port, session=session)
    stacks = ([m['stackId']['stack'] for m in metadata
               if m['stackId']['project'] == project])
    return stacks
