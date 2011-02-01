#!/bin/bash
VERSION="1.9.1"
URL=http://mp4v2.googlecode.com/files/mp4v2-$VERSION.tar.bz2

curl -o mp4v2-$VERSION.tar.bz2 $URL
tar jxvf mp4v2-$VERSION.tar.bz2
cd mp4v2-$VERSION
./configure --prefix=/tmp/mp4v2build && make -j3 && make install
cd ..
pushd /tmp/mp4v2build
find . -type f > /tmp/mp4v2files
popd

rm -rf mp4v2-$VERSION
rm -rf /tmp/mp4v2build
tar jxvf mp4v2-$VERSION.tar.bz2
cd mp4v2-$VERSION
clear
./configure && make -j3 && sudo make install
cd ..
cd /usr/local
for I in `cat /tmp/mp4v2files`
do
  tar rvf /tmp/mp4v2.tar $I
done
cd -
mkdir -p pkgroot/usr/local
cd pkgroot/usr/local
tar xvf /tmp/mp4v2.tar
cd -
rm -rf mp4v2-$VERSION*
rm -f /tmp/mp4v2.tar
rm -f /tmp/mp4v2files
if [ -f /sbin/lfconfig ]; then
  # probably linux
  sudo ldconfig -vv
fi
