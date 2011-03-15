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
import time
import re
import os
import logging
hosts = []
resolved = []
bjTimeout = 5
channel = ''
logger = logging.getLogger()

def copyInLogger(incoming_logger):
    logger = incoming_logger
    
def hostname():
  return re.sub(r'\..*', '', os.uname()[1])
  
    
def waitAndSee():
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

def gNotify(message):
  logger.debug(' [*] in gNotify')
  
  try:
    for g in growl:
      logger.debug(' [*] attempting to send Growl notification')
      logger.debug(' [*] sending %s' % message)
      g.notify('message','Dencoder',message)
    logger.debug(' [*] leaving gNotify')
  except:
    logger.debug('failed to issue growl notification, growl not defined?')