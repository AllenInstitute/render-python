#!/usr/bin/env python
from setuptools import setup

with open('test/requirements.txt','r') as f:
    test_required = f.read().splitlines()

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
      install_requires=required,
      setup_requires=['pytest-runner','flake8'],
      tests_require = test_required)
