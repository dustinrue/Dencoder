#!/bin/bash
if [ -f /Library/LaunchDaemons/com.dustinrue.dencoder.plist ]; then
  launchctl unload -F /Library/LaunchDaemons/com.dustinrue.dencoder.plist
fi
exit 0
