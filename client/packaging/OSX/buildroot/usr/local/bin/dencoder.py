#!/usr/bin/env python
import subprocess
import signal
import pika
import time
import ConfigParser
import logging
import logging.config
from simplejson import loads
from os import fork, setsid, umask, dup2, getpid, chdir, setuid, setgid, kill, path
from pwd import getpwnam
from grp import getgrnam
from sys import stdin, stdout, stderr
import pybonjour
import select


config = ConfigParser.RawConfigParser()
config.read('/usr/local/etc/dencoder/dencoder.cfg')

# get config options
hbpath         = config.get('Dencoder','hbpath')
hblog          = config.get('Dencoder','hblog')
hberr          = config.get('Dencoder','hberr')
#RabbitMQServer = config.get('Dencoder','RabbitMQServer')
basePath       = config.get('Dencoder','basePath') 
sourcePath     = config.get('Dencoder','sourcePath')
destPath       = config.get('Dencoder','destPath')
user           = config.get('Dencoder','user')
group          = config.get('Dencoder','group')
background     = config.get('Dencoder','background')
bjTimeout      = int(config.get('Dencoder','bjTimeout'))
regtype        = '_amqp._tcp'
resolved       = []
hosts          = []


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
  setgid(getgrnam(group).gr_gid)
  setuid(getpwnam(user).pw_uid)
  chdir('/')

if (background != "false"):
  doFork()



# setup the logger
logging.config.fileConfig("/usr/local/etc/dencoder/logger.conf")
logger = logging.getLogger('dencoder')
logger.info(' [+] starting up')

outfile = open('/tmp/encoder.py.pid','w',0)
outfile.write('%i' % getpid())
outfile.close

def checkPaths():
  logger.debug("checking path " + basePath + sourcePath)
  if (path.exists(basePath + sourcePath)):
    return
  else:
    logger.info("Exiting because source path doesn't exist, is the file system mounted?")
    exit()

def dencoderSetup():
  global hbpid
  hbpid = 0

def encodeVideo(filename,outfile,preset):
  global hbpid
  logger.debug(" params are %s %s %s" % (filename, outfile, preset,))
  logger.info(" [-] encoding " + filename + " using " + preset)
  args = [hbpath,'-Z',preset,'-i',basePath+sourcePath+filename,'-o',basePath+destPath+outfile]
  p = subprocess.Popen(args,stdout=open(hblog, 'w'),stderr=open(hberr,'w'))
  hbpid = p.pid
  logger.info(" [-] HandBrakeCLI started with pid %i" % (p.pid),)
  p.wait()
  return p

def dojob_callback(ch, method, header, body):
  global hbpid
  try:
    json = loads(body)
    filename = json['sourcefile']
    outfile  = json['outputfile']
    preset   = json['preset']
  except:
    logger.info(' [+] recieved an invalid request, ignoring but ack\'ing the message to remove from queue')
    ch.basic_ack(delivery_tag = method.delivery_tag)
    return
  logger.debug(" [-] Received job with filename %r" % (filename,))
  checkPaths()
  process = encodeVideo(filename,outfile,preset)
  logger.debug(" [-] sending message ack")
  ch.basic_ack(delivery_tag = method.delivery_tag)
  logger.info(" [-] Done")
  hbpid = 0
  logger.info (' [+] Waiting for encode jobs. Issue kill to %i to end' % (getpid(),))

def stopEncodes():
  global hbpid
  if (hbpid > 0):
    logger.debug(' [+] killing HandiBrakeCLI at pid %i' % (hbpid,))
    kill(hbpid,signal.SIGTERM)

def disconnectRabbitMQ():
  global channel
  channel.close()

def handleSigTerm(thing1,thing2):
  logger.info(' [+] SIGTERM received')
  logger.info(' [+] shutting down...')
  logger.info(' [+] terminating any running encodes...')
  disconnectRabbitMQ()
  stopEncodes()
  logger.info(' [+] good bye')
  exit()



def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        hosts.append(hosttarget)
        resolved.append(True)


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if not (flags & pybonjour.kDNSServiceFlagsAdd):
        logger.info( 'Service removed')
        return

    logger.info('Service added; resolving')

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

### I can't get bonjour stuff working on the server side so for now
### everyone is stuck manually setting this config option
browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                          callBack = browse_callback)

try:
    ready = select.select([browse_sdRef], [], [])
    if browse_sdRef in ready[0]:
       pybonjour.DNSServiceProcessResult(browse_sdRef)
except KeyboardInterrupt:
    pass
finally:
    browse_sdRef.close()


if len(hosts) > 1:
   logger.critical('found too many AMQP (RabbitMQ) hosts, unable to cope!')
   exit()
RabbitMQServer = hosts[0]
  
checkPaths()
signal.signal(signal.SIGTERM,handleSigTerm)

logger.info(' [+] connecting to RabbitMQ @%s' %(RabbitMQServer,))
try:
  connection = pika.AsyncoreConnection(pika.ConnectionParameters(host=RabbitMQServer))
  global channel
  channel = connection.channel()
  logger.info(' [+] connected')
except:
  logger.info(' [+] failed to connect to RabbitMQ!')
  logger.info(' [+] unable to cope, shutting down.  Please check RabbitMQ host and configuration')
  exit()

channel.queue_declare(queue='encodejobs')

channel.basic_qos(prefetch_count=1)
channel.basic_consume(dojob_callback,
                      queue='encodejobs')
logger.debug(' [+] entering pika.asyncore_loop')
logger.info(' [+] Waiting for encode jobs. Issue kill to %i to end' % (getpid(),))

dencoderSetup()

pika.asyncore_loop()
