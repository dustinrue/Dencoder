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
  print "  -A, --album       STR  Set the album title"
  print "  -a, --artist      STR  Set the artist information"
  print "  -b, --tempo       NUM  Set the tempo (beats per minute)"
  print "  -c, --comment     STR  Set a general comment"
  print "  -C, --copyright   STR  Set the copyright information"
  print "  -d, --disk        NUM  Set the disk number"
  print "  -D, --disks       NUM  Set the number of disks"
  print "  -e, --encodedby   STR  Set the name of the person or company who encoded the file"
  print "  -E, --tool        STR  Set the software used for encoding"
  print "  -g, --genre       STR  Set the genre name"
  print "  -G, --grouping    STR  Set the grouping name"
  print "  -H, --hdvideo     NUM  Set the HD flag (1/0)"
  print '  -i, --type        STR  Set the Media Type(tvshow, movie, music, ...)"'
  print "  -I, --cnid        NUM  Set the cnID"
  print "  -l, --longdesc    NUM  Set the short description"
  print "  -L, --lyrics      NUM  Set the lyrics"
  print "  -m, --description STR  Set the short description"
  print "  -M, --episode     NUM  Set the episode number"
  print "  -n, --season      NUM  Set the season number"
  print "  -N, --network     STR  Set the TV network"
  print "  -o, --episodeid   STR  Set the TV episode ID"
  print "  -P, --picture     PTH  Set the picture as a .png"
  print "  -s, --song        STR  Set the song title"
  print "  -S  --show        STR  Set the TV show"
  print "  -t, --track       NUM  Set the track number"
  print "  -T, --tracks      NUM  Set the number of tracks"
  print "  -w, --writer      STR  Set the composer information"
  print "  -y, --year        NUM  Set the release date"
  print "  -R, --albumartist STR  Set the album artist"
  print '  -r, --remove      STR  Remove tags by code (e.g. "-r cs"'
  print "                        removes the comment and song tags)"
  print
  print "example: %s -f \"Friends.mpg\" -p \"AppleTV 2\" -s \"The one\"" % sys.argv[0]

if (len(sys.argv) < 2):
  usage()
  sys.exit(2)
try:

  opts, args = getopt.getopt(sys.argv[1:], "A:a:b:c:C:d:D:e:E:g:G:H:i:I:l:L:m:M:n:N:o:P:s:S:t:T:w:y:R:r:",
                             ["album=","artist=","tempo=","comment=","copyright=","disk=","disks=",
                              "encodedby=","tool=","genre=","grouping=","hdivdeo=","type=",
                              "cnid=","longdesc=","lyrics=","description=","episode=","season=",
                              "network=","episodeid=","picture=","song=","show=","track=",
                              "tracks=","writer=","year=","albumartist=","remove="])
except:
  usage()
  sys.exit(2)

# I don't doubt there is a better way to do what I'm doing below
# and I'd happily take suggestions
dict = {}
for opt, arg in opts:
  if opt in ('-f',      '--file'):
    dict['sourcefile']  = arg
  elif opt in ("-p",    '--preset'):
    dict['preset']      = arg
  elif opt in ('-A',    '--album'):
    dict['album']       = arg
  elif opt in ('-a',    '--artist'):
    dict['artist']      = arg
  elif opt in ('-b',    '--tempo'):
    dict['tempo']       = arg
  elif opt in ('-c',    '--comment'):
    dict['comment']     = arg
  elif opt in ('-C',    '--copyright'):
    dict['copyright']   = arg
  elif opt in ('-d',    '--disk'):
    dict['disk']        = arg
  elif opt in ('-D',    '--disks'):
    dict['disks']       = arg
  elif opt in ('e',     '--encodedby'):
    dict['encodedby']   = arg
  elif opt in ('-E',    '--tool'):
    dict['tool']        = arg
  elif opt in ('-g',    '--genre'):
    dict['genre']       = arg
  elif opt in ('-G',    '--grouping'):
    dict['grouping']    = arg
  elif opt in ('-H',    '--hdvideo'):
    dict['hdvideo']     = arg
  elif opt in ('-i',    '--type'):
    dict['type']        = arg
  elif opt in ('-I',    '--cnid'):
    dict['cnid']        = arg
  elif opt in ('-l',    '--longdesc'):
    dict['longdesc']    = arg
  elif opt in ('-L',    '--lyrics'):
    dict['lyrics']      = arg
  elif opt in ('-m',    '--description'):
    dict['description'] = arg
  elif opt in ('-M',    '--episode'):
    dict['episode']     = arg
  elif opt in ('-n',    '--season'):
    dict['season']      = arg
  elif opt in ('-N',    '--network'):
    dict['network']     = arg
  elif opt in ('-o',    '--episodeid'):
    dict['episodeid']   = arg
  elif opt in ('-P',    '--picture'):
    dict['picture']     = arg
  elif opt in ('-s',    '--song'):
    dict['song']        = arg
  elif opt in ('-S',    '--show'):
    dict['show']        = arg
  elif opt in ('-t',    '--track'):
    dict['track']       = arg
  elif opt in ('-T',    '--tracks'):
    dict['tracks']      = arg
  elif opt in ('-w',    '--writer'):
    dict['writer']      = arg
  elif opt in ('-y',    '--year'):
    dict['year']        = arg
  elif opt in ('-R',    '--albumartist'):
    dict['albumarist']  = arg
  elif opt in ('-r',    '--remove'):
    dict['remove']      = arg
    
    
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

