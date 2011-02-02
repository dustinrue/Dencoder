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
import getopt
import os
import json
import ConfigParser
from dencoderCommon import findAMQPHost

config = ConfigParser.RawConfigParser()

# The OS X installer packages install to /usr/local
# but on Linux systems it's customary to install packages
# to the "normal" bin location in /usr.  
# To support this I need to place the config file in a 
# different location depending on the OS in question
if sys.platform == "darwin":
  config.read('/usr/local/etc/dencoder/dencoder.cfg')
else:
  config.read('/etc/dencoder/dencoder.cfg')

RabbitMQServer = findAMQPHost()

def usage():
  print "%s takes the following arguments:" % sys.argv[0]
  print
  print "Required"
  print "  -f, --file=        name of the source file"
  print "  -p, --preset=      HandBrake preset to use for encoding"
  print
  print "iTunes Metadata"
  print "  -t, --title=       title of the output file"
  print "  -d, --description= description of the output file"
  print "  -H,                set flag indicating that the show is HD"
  print "  -s, --season=      season number"
  print "  -e, --episode=     episode number"
  print
  print "example: %s -f \"Friends.mpg\" -p \"AppleTV 2\" -t \"The one\"" % sys.argv[0]

if (len(sys.argv) < 2):
  usage()
  sys.exit(2)
try: 
  opts, args = getopt.getopt(sys.argv[1:], "f:p:t:d:Hs:e:",["file=","preset=","title=","description=","season=","episode="])
except GetoptError:
  usage()
  sys.exit(2)
  
dict = {}
for opt, arg in opts:
  if opt in ("-f", "--file"):
    dict['sourcefile'] = arg
  elif opt in ("-p", "--preset"):
    dict['preset'] = arg
  elif opt in ("-t", "title"):
    dict['title'] = arg
  elif opt in ('-d', '--description'):
    dict['description'] = arg
  elif opt in ('-s','--season'):
    dict['season'] = arg
  elif opt in ('-e','--episode'):
    dict['season']
    
    


basename, extension = os.path.splitext(dict['sourcefile'])
dict['outputfile'] = basename + '.m4v'


message = json.dumps(dict)


connection = pika.AsyncoreConnection(pika.ConnectionParameters(
               RabbitMQServer))
channel = connection.channel()
channel.queue_declare(queue='encodejobs')
channel.basic_publish(exchange='',
                      routing_key='encodejobs',
                      body=message)
print " [x] Enqueued '" + dict['sourcefile'] + " for encoding'"
connection.close()

