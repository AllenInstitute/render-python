'''
default settings for render tests
'''
import os

DEFAULT_RENDER = {
    'host': 'http://renderhost',
    'port': 8080,
    'owner': 'renderowner',
    'project': 'renderproject',
    'client_scripts': '/path/to/client_scripts'
    }

DEFAULT_RENDER_CLIENT = dict(DEFAULT_RENDER, **{
    'client_script': '/path/to/client_scripts/run_ws_client.sh',
    'memGB': '2G'})

DEFAULT_RENDER_ENVIRONMENT_VARIABLES = {
    'RENDER_HOST': DEFAULT_RENDER['host'],
    'RENDER_PORT': DEFAULT_RENDER['port'],
    'RENDER_OWNER': DEFAULT_RENDER['owner'],
    'RENDER_PROJECT': DEFAULT_RENDER['project'],
    'RENDER_CLIENT_SCRIPTS': DEFAULT_RENDER['client_scripts']
    }

DEFAULT_RENDER_CLIENT_ENVIRONMENT_VARIABLES = dict(
    DEFAULT_RENDER_ENVIRONMENT_VARIABLES, **{
        'RENDER_CLIENT_SCRIPT': DEFAULT_RENDER_CLIENT['client_script'],
        'RENDER_CLIENT_HEAP': DEFAULT_RENDER_CLIENT['memGB']})

TEST_TILESPECS_FILE = os.path.join(os.path.dirname(
    __file__), 'test_files', 'tilespecs.json')
