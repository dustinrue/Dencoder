#!/usr/bin/env python
import sys
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('/usr/local/etc/dencoder/dencoder.cfg')

basePath = sys.argv[1]
config.set('Dencoder','basePath',basePath)

with open('/usr/local/etc/dencoder/dencoder.cfg','wb') as configfile:
  config.write(configfile)
