#!/usr/bin/env python
import sys
import os
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('/usr/local/etc/dencoder/dencoder.cfg')

RabbitMQServer = config.get('Dencoder','RabbitMQServer')
host = sys.argv[1]
config.set('Dencoder','RabbitMQServer',host)

with open('/usr/local/etc/dencoder/dencoder.cfg','wb') as configfile:
  config.write(configfile)
