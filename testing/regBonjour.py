import select
import sys
import time
import pybonjour


name    = sys.argv[1]
regtype = sys.argv[2]
port    = int(sys.argv[3])


def register_callback(sdRef, flags, errorCode, name, regtype, domain):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        print 'Registered service:'
        print '  name    =', name
        print '  regtype =', regtype
        print '  domain  =', domain


sdRef = pybonjour.DNSServiceRegister(name = name,
                                     regtype = regtype,
                                     port = port,
                                     callBack = register_callback)

try:
  ready = select.select([sdRef], [], [])
  if sdRef in ready[0]:
    pybonjour.DNSServiceProcessResult(sdRef)
finally:
  time.sleep(5)
  sdRef.close()
