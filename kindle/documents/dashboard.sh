#!/bin/sh
# Name: Dashboard
# Author: Kindle Dashboard
# Avvia la dashboard in background (sopravvive allo spegnimento dell'interfaccia)
cd /mnt/us/dashboard || exit 1
if command -v setsid >/dev/null 2>&1; then
    setsid nohup /bin/sh /mnt/us/dashboard/dash.sh >/dev/null 2>&1 &
else
    nohup /bin/sh /mnt/us/dashboard/dash.sh >/dev/null 2>&1 &
fi
exit 0
