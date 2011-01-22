#!/bin/bash
rm -rf /tmp/dencoder
mkdir  /tmp/dencoder
mkdir -p /tmp/dencoder/DEBIAN
mkdir -p /tmp/dencoder/usr/bin
mkdir -p /tmp/dencoder/etc/dencoder
#mkdir -p /tmp/dencoder/DEBIAN/etc/init.d
cp ../../dencoder.py /tmp/dencoder/usr/bin/
cp ../../conf/debian/* /tmp/dencoder/etc/dencoder/
#cp ../../initscripts/debian/* /tmp/dencoder/etc/init.d/
cd /tmp/dencoder/DEBIAN
find . -type f -exec md5sum {} ";" >> md5sum
cd -
cp control /tmp/dencoder/DEBIAN
cp debian-binary /tmp/dencoder/DEBIAN
dpkg -b /tmp/dencoder .
