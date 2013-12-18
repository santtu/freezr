#!/usr/bin/env python
from setuptools import setup

with open('requirements.txt') as f:
    lines = f.read().splitlines()
    lines = [line[14:] if line.startswith('# setup-only: ') else line
             for line in lines]

    install_requires = [line for line in lines
                        if not (line.startswith('-e ') or
                                line.startswith('http://'))]

    dependency_links = [line for line in lines
                        if line.startswith('http://')]

setup(name='freezr',
      version='0.1.0',
      description='Web service for starting and stopping projects in AWS',
      url='http://github.com/santtu/freezr',
      author='Santeri Paavolainen',
      author_email='santtu@iki.fi',
      license='GPLv3',
      packages=['freezr'],
      zip_safe=False,
      install_requires=install_requires,
      dependency_links=dependency_links,
      )
