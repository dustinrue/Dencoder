#!/bin/bash
easy_install pika
easy_install simplejson
easy_install pybonjour
chown root:wheel /Library/LaunchDaemons/com.dustinrue.dencoder.plist
launchctl load -F /Library/LaunchDaemons/com.dustinrue.dencoder.plist
launchctl load -w /Library/LaunchDaemons/com.dustinrue.dencoder.plist
exit 0
