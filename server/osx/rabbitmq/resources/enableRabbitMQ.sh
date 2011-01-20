#!/bin/bash
chown root:wheel /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist
chown -r root:wheel /opt/rabbitmq
launchctl load -w /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist
exit 0
