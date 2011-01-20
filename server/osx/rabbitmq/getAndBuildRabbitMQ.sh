#!/bin/bash
VERSION="2.2.0"
URL=http://www.rabbitmq.com/releases/rabbitmq-server/v${VERSION}/rabbitmq-server-generic-unix-${VERSION}.tar.gz

mkdir tmp
cd tmp
curl -o rabbitmq-server-generic-unix-${VERSION}.tar.gz $URL
tar zxvf rabbitmq-server-generic-unix-${VERSION}.tar.gz
mkdir -p ../buildroot/opt/rabbitmq
cp -a rabbitmq_server-${VERSION}/* ../buildroot/opt/rabbitmq
cd ..
rm -rf ./tmp
. ./populateBuildRoot.sh
