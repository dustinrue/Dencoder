#!/bin/bash
chown root:wheel /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist
launchctl load -F /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist
launchctl load -w /Library/LaunchDaemons/com.dustinrue.dencoderserver.plist
exit 0
