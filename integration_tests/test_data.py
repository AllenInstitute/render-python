import os
from jinja2 import Environment, FileSystemLoader
import json

def render_json_template(env, template_file, **kwargs):
    template = env.get_template(template_file)
    d = json.loads(template.render(**kwargs))
    return d

example_dir = os.environ.get('RENDER_EXAMPLE_DATA','/var/www/render/examples/')

test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
example_env = Environment(loader=FileSystemLoader(test_files_dir))


render_host = os.environ.get('RENDER_HOST','renderservice')
render_port = os.environ.get('RENDER_PORT',8080)
client_script_location = os.environ.get('RENDER_CLIENT_SCRIPTS',
                          ('/var/www/render/render-ws-java-client/'
                          'src/main/scripts/'))

render_params = {
    'host':render_host,
    'port':render_port,
    'owner':'test',
    'project':'test_project',
    'client_scripts':client_script_location
}

tilespec_file = os.path.join(example_dir,'example_1','cycle1_step1_acquire_tiles.json')
tform_file = os.path.join(example_dir,'example_1','cycle1_step1_acquire_transforms.json')
test_pool_size = os.environ.get('RENDER_PYTHON_TEST_POOL_SIZE',3)

multi_channel_dir = os.path.join(example_dir,'multichannel-test')

test_2_channels_d = render_json_template(example_env,
    'test_2_channels.json',
    multi_channel_example_dir=multi_channel_dir)

