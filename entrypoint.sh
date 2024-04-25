#!/bin/sh
set -e

service ssh start

# -RUN (crontab -l ; echo "0 * * * * cd /app && /usr/local/bin/open-poen retrieve-all-payments >> /var/log/cron.log 2>&1") | crontab
echo "* * * * * echo 'hello world' >> /home/cron.log 2>&1" | crontab -
service cron start

# this does not seem to work completely. FQN for BNG is not extracted properly...
eval $(printenv | sed -n "s/^\([^=]\+\)=\(.*\)$/export \1=\2/p" | sed 's/"/\\\"/g' | sed '/=/s//="/' | sed 's/$/"/' >> /etc/profile)

exec uvicorn open_poen_api:app --host 0.0.0.0 --port 8000