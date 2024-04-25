#!/bin/bash
set -e

service ssh start

/bin/sh /app/loop_script.sh >> /home/loop_script.log 2>&1 & disown $!

# this does not seem to work completely. FQN for BNG is not extracted properly...
# this ensures we have the right ENV variables when we SSH into the container.
eval $(printenv | sed -n "s/^\([^=]\+\)=\(.*\)$/export \1=\2/p" | sed 's/"/\\\"/g' | sed '/=/s//="/' | sed 's/$/"/' >> /etc/profile)

exec uvicorn open_poen_api:app --host 0.0.0.0 --port 8000