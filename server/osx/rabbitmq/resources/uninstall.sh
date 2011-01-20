#!/bin/bash
if [ -d /opt/rabbitmq ]; then
  rm -rf /opt/rabbitmq
fi

if [ -f /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist ]; then
  launchctl unload -w /Library/LaunchDaemons/com.dustinrue.dencoder.plist
  rm -f /Library/LaunchDaemons/com.dustinrue.dencoder.plist
fi
