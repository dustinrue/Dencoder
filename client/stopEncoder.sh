#!/bin/bash
if [ -f /var/run/dencoder.py.pid ]; then
  kill `cat /var/run/dencoder.py.pid`
  rm -f /var/run/dencoder.py.pid
fi
