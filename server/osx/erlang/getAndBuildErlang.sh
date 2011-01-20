#!/bin/bash
# edit the version to switch which version you want to build
VERSION=R14B01

URL=http://www3.erlang.org/download/otp_src_${VERSION}.tar.gz
mkdir tmp
cd tmp
curl -o otp_src_${VERSION}.tar.gz $URL
tar zxvf otp_src_${VERSION}.tar.gz
cd otp_src_${VERSION}
./configure --prefix=/opt/erlang --exec-prefix=/opt/erlang && make  
echo "doing make install, provide sudo password"
sudo make install
cd ../..
mkdir -p buildroot/opt/erlang
cp -a /opt/erlang/* buildroot/opt/erlang/
rm -rf tmp
