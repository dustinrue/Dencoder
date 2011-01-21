#!/usr/bin/env python
import subprocess
import signal
import time
import select
import ConfigParser
import logging
import logging.config
from os import fork, setsid, umask, dup2, getpid, chdir, setuid, setgid, kill, path
from sys import stdin, stdout, stderr
import pybonjour
logging.config.fileConfig("/usr/local/etc/dencoder/logger.conf")
logger = logging.getLogger('dencoder')

name    = 'RabbitMQ'
regtype = '_amqp._tcp'
port    = int('5672')

rmqpid = 0


def startRabbitMQ():
  global rmqpid
  logger.info('starting RabbitMQ')
  args = ['/opt/rabbitmq/sbin/rabbitmq-server']
  p = subprocess.Popen(args,stdout=open('/tmp/rabbitmq-server.log', 'w'),stderr=open('/tmp/rabbitmq-server.error','w'),env={"PATH":"/opt/local/bin:/opt/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/git/bin:/usr/X11/bin:/usr/local/mysql/bin/:/opt/erlang/bin/","HOME":"/tmp"})
  rmqpid = p.pid
  if (rmqpid > 0):
    logger.info('successfully started RabbitMQ with pid %i' % rmqpid)
  return p

def stopRabbitMQ():
  global rmqpid
  logger.info('shutting down')
  logger.info('killing RabbitMQ at pid %i' % rmqpid)
  kill(rmqpid,signal.SIGTERM)
  return

def handleSigTerm(thing1,thing2):
  stopRabbitMQ()


signal.signal(signal.SIGTERM,handleSigTerm)



def register_callback(sdRef, flags, errorCode, name, regtype, domain):
  return


sdRef = pybonjour.DNSServiceRegister(name = name,
                                     regtype = regtype,
                                     port = port,
                                     callBack = register_callback)

try:
  ready = select.select([sdRef], [], [])
  if sdRef in ready[0]:
    pybonjour.DNSServiceProcessResult(sdRef)
  logger.info('successfully registered ourselves with bonjour')
except:
  logger.info('failed to register ourselves using bonjour')
  logger.info('this is not a critical error but you\'ll need to manually configure the clients')


rmqProcess = startRabbitMQ()
rmqProcess.wait()
sdRef.close()
