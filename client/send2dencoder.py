#!/usr/bin/env python
import pika
import sys
import os
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('/usr/local/etc/dencoder/dencoder.cfg')

RabbitMQServer = config.get('Dencoder','RabbitMQServer')
if len(sys.argv) < 3:
  print 'Usage: ' + sys.argv[0] + ' <source filename> <output filename> <preset>'
  exit()

sourcefile = sys.argv[1]
basename, extension = os.path.splitext(sourcefile)
outputfile = basename + '.m4v'
preset     = sys.argv[2]

message = '{"sourcefile": "' + sourcefile + '",\
            "outputfile": "' + outputfile + '",\
            "preset": "' + preset + '"}'

connection = pika.AsyncoreConnection(pika.ConnectionParameters(
               RabbitMQServer))
channel = connection.channel()
channel.queue_declare(queue='encodejobs')
channel.basic_publish(exchange='',
                      routing_key='encodejobs',
                      body=message)
print " [x] Enqueued '" + sourcefile + " for encoding'"
connection.close()

