#!/usr/bin/env python
import subprocess
import signal
import time
from os import fork, setsid, umask, dup2, getpid, chdir, setuid, setgid, kill, path
from sys import stdin, stdout, stderr
import pybonjour

rmqpid = 0

def startRabbitMQ():
  args = ['/opt/rabbitmq/sbin/rabbitmq-server']
  p = subprocess.Popen(args,stdout=open('/tmp/rabbitmq-server.log', 'w'),stderr=open('/tmp/rabbitmq-server.error','w'),env={"PATH":"/opt/local/bin:/opt/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/git/bin:/usr/X11/bin:/usr/local/mysql/bin/:/opt/erlang/bin/","HOME":"/tmp"})
  rmqpid = p.pid
  p.wait()
  return p

def stopRabbitMQ():
  kill(rmqpid,signal.SIGTERM)
  return

def handleSigTerm(thing1,thing2):
  stopRabbitMQ()




signal.signal(signal.SIGTERM,handleSigTerm)
name    = 'RabbitMQ'
regtype = '_amqp._tcp'
port    = int('5672')


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
finally:
  startRabbitMQ()
  
  
sdRef.close()
