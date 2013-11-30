#!/usr/bin/env python
from setuptools import setup
import os

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='freezr',
      version='0.1.0',
      description='Web service for starting and stopping projects in AWS',
      url='http://github.com/santtu/freezr',
      author='Santeri Paavolainen',
      author_email='santtu@iki.fi',
      license='GPLv3',
      packages=['freezr'],
      zip_safe=False,
      install_requires=required,
      )
