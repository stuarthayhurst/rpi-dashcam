#!/usr/bin/bash

#Install the service
install -m 0664 data/rpi-dashcam.service /etc/systemd/system/rpi-dashcam.service

#Set the program's path
programPath="$(dirname "$(readlink -f "$0")")"
sed -i "s|PROGRAM_PATH|$programPath|g" /etc/systemd/system/rpi-dashcam.service

#Set up the service
systemctl daemon-reload
systemctl enable rpi-dashcam.service
