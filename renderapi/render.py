#!/usr/bin/env python
import logging
import os
import json
import subprocess
import sys
import tempfile
import requests
import numpy as np


class Render(object):
    def __init__(self, host=None, port=None, owner=None, project=None,
                 client_scripts=None):
        self.DEFAULT_HOST = host
        self.DEFAULT_PORT = port
        self.DEFAULT_PROJECT = project
        self.DEFAULT_OWNER = owner
        self.DEFAULT_CLIENT_SCRIPTS = client_scripts

        logging.debug('Render object created with '
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

    def process_defaults(self, host, port, owner, project,
                         client_scripts=None):
        '''
        utility function which will convert arguments to default arguments if
            they are None allows Render object to be used with defaults if
            lazy, but allows projects/hosts/owners to be changed from call
            to call if desired.  used by many functions convert default None
            arguments to default values.
        '''
        if host is None:
            host = self.DEFAULT_HOST
        if port is None:
            port = self.DEFAULT_PORT
        if owner is None:
            owner = self.DEFAULT_OWNER
        if project is None:
            project = self.DEFAULT_PROJECT
        if client_scripts is None:
            client_scripts = self.DEFAULT_CLIENT_SCRIPTS
        return (host, port, owner, project, client_scripts)

    def get_z_values_for_stack(self, stack, project=None, host=None, port=None,
                               owner=None, session=requests.session(),
                               verbose=False):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        request_url = self.format_preamble(
            host, port, owner, project, stack) + "/zValues/"
        if verbose:
            print request_url
        r = session.get(request_url)
        try:
            return r.json()
        except:
            print(r.text)
            return None

    def get_z_value_for_section(self, stack, sectionId, project=None,
                                host=None, port=None, owner=None,
                                session=requests.session()):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        request_url = self.format_preamble(
            host, port, owner, project, stack) + "/section/%s/z" % (sectionId)
        r = session.get(request_url)
        try:
            return r.json()
        except:
            print(r.text)
            return None

    def put_resolved_tilespecs(self, stack, data, host=None, port=None,
                               owner=None, project=None,
                               session=requests.session(), verbose=False):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        request_url = self.format_preamble(
            host, port, owner, project, stack) + "/resolvedTiles"
        if verbose:
            print request_url

        r = session.put(request_url, data=data,
                        headers={"content-type": "application/json",
                                 "Accept": "text/plain"})
        return r

    def get_bounds_from_z(self, stack, z, host=None, port=None, owner=None,
                          project=None, session=requests.session()):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        request_url = self.format_preamble(
            host, port, owner, project, stack) + '/z/%f/bounds' % (z)
        return self.process_simple_url_request(request_url, session)

    #
    # API for doing the bulk requests locally (i.e., to be run on the cluster)
    # Full documentation here: http://wiki.int.janelia.org/wiki/display/flyTEM/Coordinate+Mapping+Tools
    #

    MAP_COORD_SCRIPT = "/groups/flyTEM/flyTEM/render/bin/map-coord.sh"
    def batch_local_work(self, stack, z, data, host=None, port=None,
                         owner=None, project=None, localToWorld=False,
                         deleteTemp=True, threads=16):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        fromJson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='w', delete=False)
        fromJson.write(data)
        fromJson.flush()
        fromJson.close()

        toJson = tempfile.NamedTemporaryFile(
            suffix=".json", mode='r', delete=False)
        toJson.close()

        #cmd = "%s --owner %s --project %s --stack %s --z %d --fromJson %s --toJson %s --baseDataUrl http://tem-services.int.janelia.org:8080/render-ws/v1 --numberOfThreads %d" % (MAP_COORD_SCRIPT, owner, project, stack, z, fromJson.name, toJson.name, threads)
        cmd = ("%s --owner %s --project %s --stack %s --z %d --fromJson %s "
               "--toJson %s --baseDataUrl http://10.40.3.162:8080/render-ws/v1 "
               "--numberOfThreads %d") % (
               MAP_COORD_SCRIPT, owner, project, stack, z,
               fromJson.name, toJson.name, threads)

        if localToWorld:
            cmd = cmd + " --localToWorld"
        try:
            rc = subprocess.call(cmd, shell="True")
            if rc != 0:
                raise Exception("Invalid return code (%d): %s" % (rc, cmd))

            with open(toJson.name) as f:
                outdata = json.load(f)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return json.loads("{}")

        if deleteTemp:
            os.unlink(fromJson.name)
            os.unlink(toJson.name)

        return outdata

    def world_to_local_coordinates_batch_local(self, stack, z, data, host=None,
                                               port=None, owner=None,
                                               project=None):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        return batch_local_work(stack, z, data, host, port, owner, project,
                                localToWorld=False)

    def local_to_world_coordinates_batch_local(self, stack, z, data, host=None,
                                               port=None, owner=None,
                                               project=None):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        return batch_local_work(stack, z, data, host, port, owner, project,
                                localToWorld=True)

    def get_section_z_value(self, stack, sectionId, host=None, port=None,
                            owner=None, project=None, verbose=False,
                            session=requests.session()):
        (host, port, owner, project, client_scripts) = self.process_defaults(
            host, port, owner, project)
        request_url = self.format_preamble(
            host, port, owner, project, stack) + "/section/%s/z" % sectionId
        return float(self.process_simple_url_request(request_url, session))


class RenderClient(Render):
    '''Draft object for render_webservice_client.sh calls'''
    def __init__(self, client_script=None, *args, **kwargs):
        super(RenderClient, self).__init__(**kwargs)
        self.client_script = client_script

    def make_kwargs(self, *args, **kwargs):
        return super(RenderClient, self).make_kwargs(
            client_script=self.client_script, *args, **kwargs)


def connect(host=None, port=None, owner=None, project=None,
            client_scripts=None,json_dict=None,**kwargs):

    '''helper function to connect to a render instance'''
    if host is None:
        if 'RENDER_HOST' not in os.environ:
            host = str(raw_input("Enter Render Host: "))
            if host == '':
                logging.critical('Render Host must not be empty!')
                raise ValueError('Render Host must not be empty!')
            # host = (host if host.startswith('http')
            #         else 'http://{}'.format(host))
        else:
            host = os.environ['RENDER_HOST']

    if port is None:
        if 'RENDER_PORT' not in os.environ:
            port = str(int(raw_input("Enter Render Port: ")))
            if port == '':
                # TODO better (no) port handling
                logging.critical('Render Port must not be empty!')
                raise ValueError('Render Port must not be empty!')
        else:
            port = int(os.environ['RENDER_PORT'])

    if project is None:
        if 'RENDER_PROJECT' not in os.environ:
            project = str(raw_input("Enter Render Project: "))
        else:
            project = str(os.environ['RENDER_PROJECT'])
        if project == '':
            logging.critical('Render Project must not be empty!')
            raise ValueError('Render Project must not be empty!')

    if owner is None:
        if 'RENDER_OWNER' not in os.environ:
            owner = str(raw_input("Enter Render Owner: "))
        else:
            owner = str(os.environ['RENDER_OWNER'])
        if owner == '':
            logging.critical('Render Owner must not be empty!')
            raise ValueError('Render Owner must not be empty!')

    # TODO should client_scripts be required?
    if client_scripts is None:
        if 'RENDER_CLIENT_SCRIPTS' not in os.environ:
            client_scripts = str(raw_input(
                "Enter Render Client Scripts location: "))
        else:
            client_scripts = str(os.environ['RENDER_CLIENT_SCRIPTS'])
        if client_scripts == '':
            logging.critical('Render Client Scripts must '
                             'not be empty!')
            raise ValueError('Render Client Scripts must '
                             'not be empty!')

    return Render(host=host, port=port, owner=owner, project=project,
                  client_scripts=client_scripts)


def format_baseurl(host, port):
    return 'http://%s:%d/render-ws/v1' % (host, port)


def format_preamble(host, port, owner, project, stack):
    preamble = "%s/owner/%s/project/%s/stack/%s" % (
        format_baseurl(host, port), owner, project, stack)
    return preamble


def get_owners(host=None, port=None, render=None,
               session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_owners(**render.make_kwargs(
            host=host, port=port,
            **{'session': session}))

    request_url = "%s/owners/" % format_baseurl(host, port)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logging.error(r.text)


def get_stack_metadata_by_owner(owner=None, host=None, port=None, render=None,
                                session=requests.session(),
                                verbose=False, **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_stack_metadata_by_owner(**render.make_kwargs(
            owner=owner, host=host, port=port,
            **{'session': session, 'verbose': verbose}))

    request_url = "%s/owner/%s/stacks/" % (
        format_baseurl(host, port), owner)
    if verbose:
        logging.debug(request_url)
    r = session.get(request_url)
    try:
        return r.json()
    except:
        logging.error(r.text)


def get_projects_by_owner(owner=None, host=None, port=None, render=None,
                          session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_projects_by_owner(**render.make_kwargs(
            owner=owner, host=host, port=port,
            **{'session': session}))

    metadata = get_stack_metadata_by_owner(owner)
    projects = list(set([m['stackId']['project'] for m in metadata]))
    return projects


def get_stacks_by_owner_project(owner=None, project=None, host=None,
                                port=None, render=None,
                                session=requests.session(), **kwargs):
    if render is not None:
        if not isinstance(render, Render):
            raise ValueError('invalid Render object specified!')
        return get_projects_by_owner(**render.make_kwargs(
            owner=owner, host=host, port=port, project=project,
            **{'session': session}))

    metadata = get_stack_metadata_by_owner(owner)
    stacks = ([m['stackId']['stack'] for m in metadata
               if m['stackId']['project'] == project])
    return stacks
