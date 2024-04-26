#!/bin/sh
while true
do
  cd /app
  /usr/local/bin/open-poen retrieve-all-payments
  sleep 3600
done
