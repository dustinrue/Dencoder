#!/usr/bin/env python

#  This file is part of Dencoder.
#
#  Dencoder is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Dencoder is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Dencoder.  If not, see <http://www.gnu.org/licenses/>.


# various bits of this script are copyright 2011 Dustin Rue <ruedu@dustinrue.com>
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

