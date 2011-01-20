#!/bin/bash
if [ -f /tmp/encoder.py.pid ]; then
  kill `cat /tmp/encoder.py.pid`
  rm -f /tmp/encoder.py.pid
fi
