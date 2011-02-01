#!/bin/bash
rm -rf buildroot/*
mkdir -p buildroot/usr/local/bin
mkdir -p buildroot/usr/local/etc/dencoder
mkdir -p buildroot/Library/LaunchDaemons
mkdir -p buildroot/System/Library/Services
cp ../../dencoder.py              buildroot/usr/local/bin
cp ../../send2dencoder.py         buildroot/usr/local/bin
cp ../../setDencoder*             buildroot/usr/local/bin
cp ../../utility/osx/HandBrakeCLI buildroot/usr/local/bin
cp ../../conf/osx/*               buildroot/usr/local/etc/dencoder/
cp ../../initscripts/osx/com.dustinrue.dencoder.plist buildroot/Library/LaunchDaemons
cp -a ../../services/* buildroot/System/Library/Services/
cd buildroot
cd ../../../buildscripts/mp4v2/pkgroot
tar cvf - * | (cd -; tar xvf - )
