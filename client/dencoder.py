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
# other bits of this script come from the following sources

# pybonjour - http://code.google.com/p/pybonjour/
# python documentation - http://docs.python.org/

import subprocess
import signal
import pika
import time
import ConfigParser
import logging
import logging.config
import json
from os import fork, setsid, umask, dup2, getpid, chdir, setuid, setgid, kill, path, uname
from pwd import getpwnam
from grp import getgrnam
from sys import stdin, stdout, stderr
from dencoderCommon import findAMQPHost
import sys
import socket
import re

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

# get config options
hbpath         = config.get('Dencoder','hbpath')
mp4tagsPath    = config.get('Dencoder','mp4tagsPath')
hblog          = config.get('Dencoder','hblog')
hberr          = config.get('Dencoder','hberr')
mp4tagslog     = config.get('Dencoder','mp4tagslog')
mp4tagserr     = config.get('Dencoder','mp4tagserr')
basePath       = config.get('Dencoder','basePath') 
sourcePath     = config.get('Dencoder','sourcePath')
destPath       = config.get('Dencoder','destPath')
user           = config.get('Dencoder','user')
group          = config.get('Dencoder','group')
background     = config.get('Dencoder','background')
enableGrowl    = config.get('Dencoder','enableGrowl')
bjTimeout      = int(config.get('Dencoder','bjTimeout'))
regtype        = '_amqp._tcp'
resolved       = []


if enableGrowl == "True":
  import Growl
  
  # the config file contains a string, convert it to a list
  growlHosts = eval(config.get('Dencoder','growlHosts'))



def doFork():
  if fork(): exit(0)
  umask(0)
  setsid()
  if fork(): exit(0)

  stdout.flush()
  stderr.flush()

  si = open('/dev/null')
  so = open('/dev/null','w')
  se = open('/dev/null','w')

  dup2(si.fileno(),stdin.fileno())
  dup2(so.fileno(),stdout.fileno())
  dup2(se.fileno(),stderr.fileno())

  # drop privs
  # setgid(getgrnam(group).gr_gid)
  # setuid(getpwnam(user).pw_uid)
  chdir('/')


# launchd on OS X seems to handle placing things in the background.
# The default config for OS X prevents this script from running in the
# the background.  On Linux systems this value should be set to true.

if background == "True":
  doFork()


def setupLogging():
  # setup the logger
  # just like before, we need to load the correct logging
  # config file
  if sys.platform == "darwin":
    logging.config.fileConfig("/usr/local/etc/dencoder/logger.conf")
  else:
    logging.config.fileConfig("/etc/dencoder/logger.conf")

  return logging.getLogger('dencoder')


def writePid():
  logger.debug(' [*] writing pid file')
  try:
    outfile = open('/var/run/dencoder.py.pid','w',0)
    outfile.write('%i' % getpid())
    outfile.close
    logger.debug(' [*] successfully wrote pid file')
  except:
    logger.critical(' [*] failed to write the pid file, is dencoder client already running?')
    shutdownDencoder()

def checkPaths():
  logger.debug(' [*] checking paths')
  return (path.exists(basePath + sourcePath))

def dencoderSetup():
  logger.debug(' [*] in dencoderSetup')
  global hbpid
  hbpid = 0

def encodeVideo(filename,outfile,preset):
  global hbpid
  logger.debug(" [*] params are %s %s %s" % (filename, outfile, preset,))
  gNotify(growl,"dencoder on %s is encoding %s using %s" % (hostname(),filename,preset,))
  logger.info(" [*] encoding " + filename + " using " + preset)
  args = [hbpath,'-Z',preset,'-i',basePath+sourcePath+filename,'-o',basePath+destPath+outfile,'--main-feature']
  p = subprocess.Popen(args,stdout=open(hblog, 'w'),stderr=open(hberr,'w'))

  hbpid = p.pid
  logger.info(" [*] HandBrakeCLI started with pid %i" % (p.pid),)
 
  hbStatus = p.wait()
  gNotify(growl,"dencoder on %s has finished encoding %s using %s" % (hostname(),filename,preset,))
  return hbStatus

def writeMetadata(filename,metadata):
  # these options are used to tag the file
  try:
    show        = metadata['show']
    title       = metadata['title']
    description = metadata['description']
    season      = metadata['season']
    episode     = metadata['episode']
    hd          = metadata['hd']
  except:
    return
  
  
  logger.debug(' [*] writing metadata using mp4tags')
  logger.debug(' [*] received title=%s, description=%s, season=%d, episode=%d' % (title,description,int(season),int(episode),))
  gNotify(growl,"%s is tagging %s" % (filename,hostname(),))
  
  # build the argument list for mp4tags
  # FIXME: take advantage of the properties of a dictionary
  # to make building the args list easier
  args = [mp4tagsPath,'-S',"'" + show + "'",'-o',"'" + title + "'",'-m',"'" +
          description + "'",'-M',episode, '-n',season,
          basePath+destPath+filename]
  logger.debug(' [*] mp4tags args are %r' % args)
  p = subprocess.Popen(args,stdout=open(mp4tagslog, 'w'),stderr=open(mp4tagserr,'w'))
  p.wait()
  return

def dojob_callback(ch, method, header, body):
  global hbpid
  try:
    print body
    request = json.loads(body)
    
    
    # these options are required to do the encode
    filename    = request['sourcefile']
    outfile     = request['outputfile']
    preset      = request['preset']
    

  except:
    gNotify(growl,"dencoder on %s received an invalid message" % (hostname(),))
    logger.debug('error message is %s' % sys.exc_info()[0])
    logger.info(' [*] recieved an invalid request, ignoring but ack\'ing the message to remove from queue')
    ackAMQPMessage(ch,method)
    return
  logger.debug(" [*] Received job with filename %s" % filename)
  if not checkPaths():
    logger.critical(' [*] unable to read the source file (%s), check paths' % filename)
    return
  #hbStatus = encodeVideo(filename,outfile,preset)
  hbStatus = True
  if not (hbStatus):
    logger.debug(' [*] handbrake didn\'t exit cleanly, not acking message')
    
    # FIX ME: not acking the message prevents client from getting another one
    ackAMQPMessage(ch,method)
  else:
    # tag the file
    writeMetadata(outfile,request)
    
    ackAMQPMessage(ch,method)

  logger.info(" [*] Done")
  hbpid = 0
  logger.info (' [*] Waiting for encode jobs. Issue kill to %i to end' % (getpid(),))

def stopEncodes():
  if (hbpid > 0):
    logger.debug(' [*] killing HandiBrakeCLI at pid %i' % (hbpid,))
    kill(hbpid,signal.SIGTERM)


  
def shutdownDencoder():
  gNotify(growl,'Dencoder on %s is shutting down' % (hostname(),) )
  logger.info(' [*] SIGTERM received')
  logger.info(' [*] shutting down...')
  logger.info(' [*] terminating any running encodes...')
  disconnectRabbitMQ()
  stopEncodes()
  logger.info(' [*] good bye')
  exit()

def handleSigTerm(thing1,thing2):
  shutdownDencoder()


def waitAndSee():
  logger.info(' [*] sleeping for 20 seconds')
  time.sleep(20)
  
def initGrowlNotifier():
  listOfGrowlInstances = []
 
  if enableGrowl == "False":
    return
  

  for host in growlHosts:
    hostname = host[0]
    password = host[1]
    
    
    if hostname is not None and hostname is not "localhost" and password is not None:
      logger.debug(' [*] adding remote growl instance using using %s and %s' % (hostname,password,))
      
      tmp = Growl.GrowlNotifier('Dencoder',['message'],[],'',hostname,password)
      tmp.register()
      listOfGrowlInstances.append(tmp)
    else:
      logger.debug(' [*] adding local growl instance')
      tmp = Growl.GrowlNotifier('Dencoder',['message'])
      tmp.register()
      listOfGrowlInstances.append(tmp)
    
  return listOfGrowlInstances

def hostname():
  return re.sub(r'\..*', '', uname()[1])
  
def gNotify(growl,message):
  logger.debug(' [*] in gNotify')
  
  if enableGrowl == "False":
    logger.debug(' [*] leaving gNotify because enableGrowl is false')
    return
  
  for g in growl:
    logger.debug(' [*] attempting to send Growl notification')
    logger.debug(' [*] sending %s' % message)
    g.notify('message','Dencoder',message)
  logger.debug(' [*] leaving gNotify')
  
def disconnectRabbitMQ():
  try:
    global channel
    channel.close()
  except:
    pass
  
def ackAMQPMessage(ch,method):
  # acknowledge that the message was received.  Here we're telling 
  # the message queue that we're done with the job.  Future versions
  # of this client should be able to kill an encode and NOT ack the message.
  # This way other clients can take over and do the encode in the event that
  # another client failed to encode the file for whatever reason.
  #logger.debug(" [*] sending message ack")
  ch.basic_ack(delivery_tag = method.delivery_tag)
  
def declareAMQPQueue():
  #logging.debug(' [*] in declareAMQPQueue')
  # declare a queue named encodejobs in case it hasn't already
  # been declared.  The server will places messages here.
  channel.queue_declare(queue='encodejobs')

  # prefetch_count=1 causes this client to just get 1
  # message from the queue.  By doing this any new client
  # that connects to the message bus will be able to get
  # any messages left in the queue instead of only new ones
  # that were added after an existing client connected.  
  # This is important so that you can scale up your encode
  # cluster on the fly
  channel.basic_qos(prefetch_count=1)
  channel.basic_consume(dojob_callback,
                        queue='encodejobs')

# be ready to handle a SIGTERM and SIGINT
signal.signal(signal.SIGTERM,handleSigTerm)
signal.signal(signal.SIGINT,handleSigTerm)


# start logging
logger = setupLogging()
logger.info(' [*] dencoder is starting, please standby')


# this is the big loop
wasConnected = False
while True:
  hosts = []
  growl = []
 

  
  if wasConnected is True:
    wasConnected = False
    gNotify(growl,"Connection to AMQP server lost on %s" % (hostname(),))
  
  
  writePid()
  dencoderSetup()
  # check to see if paths exist
  # ensure that configured paths exist.  If they don't, HandBrakeCLI will
  # immediately fail but as the script is currently written it'll still
  # ack the message.  This ack tells RabbitMQ the encode was successful, 
  # even though it wasn't
  if not checkPaths():
    logger.critical(" [*] source path (%s) doesn't exist, is the file system mounted?" % (basePath + sourcePath,))

    if sys.platform == "darwin":
      shutdownDencoder()
    else:
      waitAndSee()
      continue
    

  RabbitMQServer = findAMQPHost()
  if not RabbitMQServer:
    waitAndSee()
    continue


  try:
    growl = initGrowlNotifier()
  except:
    logger.debug(' [*] growl must be disabled, because we got here')
    
  logger.info(' [*] connecting to RabbitMQ @%s' %(RabbitMQServer,))
  try:
    connection = pika.AsyncoreConnection(pika.ConnectionParameters(host=RabbitMQServer))
    channel = connection.channel()
    logger.info(' [*] connected')
  except:
    logger.critical(' [*] failed to connect to RabbitMQ!')
    logger.critical(' [*] Please check RabbitMQ host and configuration')
    waitAndSee()
    continue





  logger.debug(' [*] entering pika.asyncore_loop')
  logger.info(' [*] Waiting for encode jobs. Issue kill to %i to end' % (getpid(),))


  declareAMQPQueue()
  gNotify(growl,'Dencoder on %s is now available for encoding jobs' % (hostname(),))
  wasConnected = True
  pika.asyncore_loop()


