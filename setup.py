from setuptools import setup

with open('requirements.txt', 'r') as f:
    required = f.read().splitlines()

setup(name='render-python',
      version='1.0',
      description=' a python API setup to interact via python with render '
                  'databases see https://github.com/saalfeldlab/render',
      author='Forrest Collman,Eric Perlman,Sharmi Seshamani',
      author_email='forrest.collman@gmail.com',
      url='https://github.com/fcollman/render-python',
      packages=['renderapi'],
      install_requires=required)
