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

import pybonjour
import pika
import select

class AMQPConnection:
    

    def __init__(self):
        self.hosts        = []
        self.resolved     = []
        self.selectedHost = None
        self.channel      = None
        self.connection   = None
        self.queueName    = ''
        self.bjTimeout    = 5
        self.findAMQPHost()
    
    def __resolve_callback(self,sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
      if errorCode == pybonjour.kDNSServiceErr_NoError:
        self.hosts.append(hosttarget)
        self.resolved.append(True)


    def __browse_callback(self,sdRef, flags, interfaceIndex, errorCode, serviceName,
                        regtype, replyDomain):

      if errorCode != pybonjour.kDNSServiceErr_NoError:

        return

      if not (flags & pybonjour.kDNSServiceFlagsAdd):
        # needs testing but this should happen when the RabbitMQ server is 
        # going away as advertised by Bonjour
        return

      # we get here when we've successfully queried for _amqp._tcp
      #logger.info(' [*] Found a RabbitMQ server, resolving')


      resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                                  interfaceIndex,
                                                  serviceName,
                                                  regtype,
                                                  replyDomain,
                                                  self.__resolve_callback)

      try:
        while not self.resolved:
            ready = select.select([resolve_sdRef], [], [], self.bjTimeout)
            if resolve_sdRef not in ready[0]:
                #logger.critical( 'Resolve timed out')
                break
            pybonjour.DNSServiceProcessResult(resolve_sdRef)
        else:
            self.resolved.pop()
      finally:
            resolve_sdRef.close()


    """ When a message is received from the AMQP server this function is called.
        We need to get the body of the message back to main """
        
    def __messageReceivedCallBack(self,incomingChannel,incomingHeader,incomingBody):
        print "message received"
        """ It's quite possible I'm assigning something to itself here """
        self.channel = incomingChannel
        
        """ For the purpose of this project, the header is junk """
        self.header = incomingHeader
        self.body   = incomingBody
        
        return 0
        
        
    def ackAMQPMessage(self,method):
      # acknowledge that the message was received.  Here we're telling 
      # the message queue that we're done with the job.  Future versions
      # of this client should be able to kill an encode and NOT ack the message.
      # This way other clients can take over and do the encode in the event that
      # another client failed to encode the file for whatever reason.
      #logger.debug(" [*] sending message ack")
      self.channel.basic_ack(delivery_tag = method.delivery_tag)
      

    def setQueueName(self, incomingQueueName, incomingPreFetchCount = 1):

          
      self.connection = pika.AsyncoreConnection(pika.ConnectionParameters(host=self.getSelectedHost()))
      self.channel = self.connection.channel()
      
      # declare a queue named encodejobs in case it hasn't already
      # been declared.  The server will places messages here.
      self.queueName = incomingQueueName
      self.channel.queue_declare(queue=self.queueName)
      
      
      # prefetch_count=1 causes this client to just get 1
      # message from the queue.  By doing this any new client
      # that connects to the message bus will be able to get
      # any messages left in the queue instead of only new ones
      # that were added after an existing client connected.  
      # This is important so that you can scale up your encode
      # cluster on the fly
      self.channel.basic_qos(prefetch_count=incomingPreFetchCount)
      self.channel.basic_consume("__messageReceivedCallBack",
                            queue=self.queueName)
      
    def doLoop(self):
        print "entering loop"
        
        pika.asyncore_loop()

    def findAMQPHost(self):
      browse_sdRef = pybonjour.DNSServiceBrowse(regtype = '_amqp._tcp',
                                                callBack = self.__browse_callback)
      try:
        while not self.hosts:
       #   logger.debug(' [*] doing bonjour resolve')
          ready = select.select([browse_sdRef], [], [])
        #  logger.debug(' [*] return from ready')
          if browse_sdRef in ready[0]:
            pybonjour.DNSServiceProcessResult(browse_sdRef)
      except IOError:
        #logger.debug(' [*] unknown error while attemping to resolve AMQP host')
        pass
      finally:
        browse_sdRef.close()
      
      # if this script is unable to handle multiple AMQP servers and so we
      # attempt to deal with it, and bail if we can't
      if len(self.hosts) > 1:
        # lets see if we're seeing multiple records for the same host
        if len(self.hosts) == self.hosts.count(self.hosts[0]):
          #logger.debug(' [*] found multiple hosts but they are all the same')
          self.selectedHost = self.hosts[0]
        else:
          print 'found too many AMQP (RabbitMQ) hosts, unable to cope!'
          return 0
      elif len(self.hosts) == 1:
        self.selectedHost = self.hosts[0]
        return 1
      else:
        #logger.critical(' [*] couldn\'t resolve any AMQP hosts')

        return 0

    def getSelectedHost(self):
        return self.selectedHost