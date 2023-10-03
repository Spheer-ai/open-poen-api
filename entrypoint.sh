#!/bin/sh
set -e
service ssh start

# this does not seem to work completely. FQN for BNG is not extracted properly...
eval $(printenv | sed -n "s/^\([^=]\+\)=\(.*\)$/export \1=\2/p" | sed 's/"/\\\"/g' | sed '/=/s//="/' | sed 's/$/"/' >> /etc/profile)

# exec open-poen add-user markdewijk@spheer.ai --superuser --role user --password "test"
exec uvicorn open_poen_api:app --host 0.0.0.0 --port 8000