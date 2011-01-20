#!/bin/bash
mkdir -p buildroot/Library/LaunchDaemons
mkdir -p buildroot/opt/rabbitmq/sbin
cp resources/com.dustinrue.dencoderserver.plist buildroot/Library/LaunchDaemons
cp resources/rabbitmq-service.py buildroot/opt/rabbitmq/sbin
