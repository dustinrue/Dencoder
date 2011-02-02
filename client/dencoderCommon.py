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
import pybonjour
import select
hosts = []
resolved = []
bjTimeout = 5
  
def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
 # logger.debug(' [*] in resolve_callback')
  if errorCode == pybonjour.kDNSServiceErr_NoError:
    hosts.append(hosttarget)
    resolved.append(True)
 # logger.debug(' [*] leaving resolve_callback')


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):

  #logger.info(' [*] attempting bonjour lookup')
  if errorCode != pybonjour.kDNSServiceErr_NoError:

    return

  if not (flags & pybonjour.kDNSServiceFlagsAdd):
    # needs testing but this should happen when the RabbitMQ server is 
    # going away as advertised by Bonjour
  #  logger.info( ' [*] RabbitMQ is going away')
    return

  # we get here when we've successfully queried for _amqp._tcp
  #logger.info(' [*] Found a RabbitMQ server, resolving')


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
        #logger.critical( 'Resolve timed out')
        break
      pybonjour.DNSServiceProcessResult(resolve_sdRef)
    else:
      resolved.pop()
  finally:
    resolve_sdRef.close()



def findAMQPHost():
  
  browse_sdRef = pybonjour.DNSServiceBrowse(regtype = '_amqp._tcp',
                                            callBack = browse_callback)
  try:
    while not hosts:
   #   logger.debug(' [*] doing bonjour resolve')
      ready = select.select([browse_sdRef], [], [])
    #  logger.debug(' [*] return from ready')
      if browse_sdRef in ready[0]:
        pybonjour.DNSServiceProcessResult(browse_sdRef)
  except:
    #logger.debug(' [*] unknown error while attemping to resolve AMQP host')
    pass
  finally:
    browse_sdRef.close()
  
  
  # if this script is unable to handle multiple AMQP servers and so we
  # attempt to deal with it, and bail if we can't
  if len(hosts) > 1:
    # lets see if we're seeing multiple records for the same host
    if len(hosts) == hosts.count(hosts[0]):
      #logger.debug(' [*] found multiple hosts but they are all the same')
      RabbitMQServer = hosts[0]
    else:
      #logger.critical('found too many AMQP (RabbitMQ) hosts, unable to cope!')
      return 0
  elif len(hosts) == 1:
    RabbitMQServer = hosts[0]
  else:
    #logger.critical(' [*] couldn\'t resolve any AMQP hosts')

    return 0

  return RabbitMQServer