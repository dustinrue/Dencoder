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
from simplejson import loads
from os import fork, setsid, umask, dup2, getpid, chdir, setuid, setgid, kill, path, uname
from pwd import getpwnam
from grp import getgrnam
from sys import stdin, stdout, stderr
import pybonjour
import select
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
hblog          = config.get('Dencoder','hblog')
hberr          = config.get('Dencoder','hberr')
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

def ackAMQPMessage(ch,method):
  # ackknowledge that the message was received.  Here we're telling 
  # the message queue that we're done with the job.  Future versions
  # of this client should be able to kill an encode and NOT ack the message.
  # This way other clients can take over and do the encode in the event that
  # another client failed to encode the file for whatever reason.
  logger.debug(" [*] sending message ack")
  ch.basic_ack(delivery_tag = method.delivery_tag)

def dojob_callback(ch, method, header, body):
  global hbpid
  try:
    json = loads(body)
    filename = json['sourcefile']
    outfile  = json['outputfile']
    preset   = json['preset']
  except:
    gNotify(growl,"dencoder on %s received an invalid message" % (hostname(),))
    logger.info(' [*] recieved an invalid request, ignoring but ack\'ing the message to remove from queue')
    ackAMQPMessage(ch,method)
    return
  logger.debug(" [*] Received job with filename %r" % (filename,))
  if not checkPaths():
    logger.critical(' [*] unable to read the source file (%s), check paths' % filename)
    return
  hbStatus = encodeVideo(filename,outfile,preset)
  if not (hbStatus):
    logger.debug(' [*] handbrake didn\'t exit cleanly, not acking message')
    
    # FIX ME: not acking the message prevents client from getting another one
    ackAMQPMessage(ch,method)
  else:
    ackAMQPMessage(ch,method)
  logger.info(" [*] Done")
  hbpid = 0
  logger.info (' [*] Waiting for encode jobs. Issue kill to %i to end' % (getpid(),))

def stopEncodes():
  if (hbpid > 0):
    logger.debug(' [*] killing HandiBrakeCLI at pid %i' % (hbpid,))
    kill(hbpid,signal.SIGTERM)

def disconnectRabbitMQ():
  global channel
  channel.close()
  
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



def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
  logger.debug(' [*] in resolve_callback')
  if errorCode == pybonjour.kDNSServiceErr_NoError:
    hosts.append(hosttarget)
    resolved.append(True)
  logger.debug(' [*] leaving resolve_callback')


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
  logger.info(' [*] attempting bonjour lookup')
  if errorCode != pybonjour.kDNSServiceErr_NoError:
    return

  if not (flags & pybonjour.kDNSServiceFlagsAdd):
    # needs testing but this should happen when the RabbitMQ server is 
    # going away as advertised by Bonjour
    logger.info( ' [*] RabbitMQ is going away')
    return

  # we get here when we've successfully queried for _amqp._tcp
  logger.info(' [*] Found a RabbitMQ server, resolving')

  resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                              interfaceIndex,
                                              serviceName,
                                              regtype,
                                              replyDomain,
                                              resolve_callback)

  try:
    while not resolved:
      ready = select.select([resolve_sdRef], [], [], bjTimeout)
      if resolve_sdRef not in ready[0]:
        logger.critical( 'Resolve timed out')
        break
      pybonjour.DNSServiceProcessResult(resolve_sdRef)
    else:
      resolved.pop()
  finally:
    resolve_sdRef.close()




def findAMQHost():

  browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                            callBack = browse_callback)
  try:
    while not hosts:
      logger.debug(' [*] doing bonjour resolve')
      ready = select.select([browse_sdRef], [], [])
      logger.debug(' [*] return from ready')
      if browse_sdRef in ready[0]:
        pybonjour.DNSServiceProcessResult(browse_sdRef)
  except:
    logger.debug(' [*] unknown error while attemping to resolve AMQP host')
  finally:
    browse_sdRef.close()
  
  
  # if this script is unable to handle multiple AMQP servers and so we
  # attempt to deal with it, and bail if we can't
  if len(hosts) > 1:
    # lets see if we're seeing multiple records for the same host
    if len(hosts) == hosts.count(hosts[0]):
      logger.debug(' [*] found multiple hosts but they are all the same')
      RabbitMQServer = hosts[0]
    else:
      logger.critical('found too many AMQP (RabbitMQ) hosts, unable to cope!')
      return 0
  elif len(hosts) == 1:
    RabbitMQServer = hosts[0]
  else:
    logger.critical(' [*] couldn\'t resolve any AMQP hosts')
    return 0

  return RabbitMQServer




def declareAMQPQueue():
  logging.debug(' [*] in declareAMQPQueue')
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
    # on OS X we can cause dencoder.py to run when a file system is mounted,
    # should an option exist here to check for darwin and then exit now
    # if darwin is detected knowing that dencoder.py will simply restart
    # when a new FS is mounted?
    waitAndSee()
    continue
    

  RabbitMQServer = findAMQHost()
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


