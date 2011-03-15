#!/usr/bin/env python
#

try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup

version = "0.4.0"

setup(
    name="dencoder",
    version=version,
    author="Dustin Rue",
    py_modules=['dencoder','dencoderCommon','dencoderAMQP'],
    scripts=['send2dencoder.py',
             'dencoder.py',
             'setDencoderHost.py',
             'setDencoderBasePath.py'],
    author_email="ruedu@dustinrue.com",
    url="http://www.webscalesauce.com/",
    description="Dencoder is great",
)


