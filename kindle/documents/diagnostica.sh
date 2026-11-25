#!/bin/sh
# Name: Diagnostica dashboard
# Author: Kindle Dashboard
# Raccoglie informazioni utili in /mnt/us/dashboard/diagnostica.txt
OUT=/mnt/us/dashboard/diagnostica.txt
DIR=/mnt/us/dashboard
FB=/mnt/us/libkh/bin/fbink
{
  echo "== data"; date; TZ='CET-1CEST,M3.5.0,M10.5.0/3' date
  echo "== fbink"; ls -l /mnt/us/libkh/bin/ 2>&1; "$FB" -h 2>&1 | head -5
  echo "== test clear"; "$FB" -k top=0,left=0,width=600,height=218 2>&1; echo "rc=$?"
  echo "== test ttf px"; "$FB" -m -t regular="$DIR/fonts/Inter-ExtraBold.ttf",px=150,top=4,bottom=0,left=0,right=0 "12:34" 2>&1; echo "rc=$?"
  echo "== test ttf size"; "$FB" -m -t regular="$DIR/fonts/Inter-SemiBold.ttf",size=20,top=170,bottom=0,left=0,right=0 "prova" 2>&1; echo "rc=$?"
  echo "== test refresh"; "$FB" -s top=0,left=0,width=600,height=218 2>&1; echo "rc=$?"
  echo "== backlight"; ls -la /sys/class/backlight/ 2>&1
  for b in /sys/class/backlight/*; do echo "$b"; cat "$b/brightness" "$b/max_brightness" "$b/actual_brightness" 2>&1; done
  echo "== powerd"; lipc-get-prop com.lab126.powerd flIntensity 2>&1; lipc-get-prop com.lab126.powerd flMaxIntensity 2>&1
  lipc-get-prop com.lab126.powerd battLevel 2>&1; lipc-get-prop com.lab126.powerd status 2>&1
  echo "== rtc"; ls /sys/class/rtc/ 2>&1; cat /sys/power/state 2>&1
  echo "== tools"; for t in curl ntpdate setsid nohup rtcwake lipc-set-prop gasgauge-info; do printf "%s: " "$t"; command -v "$t" || echo NO; done
  echo "== jobs"; initctl list 2>/dev/null | grep -i -E "gui|framework|powerd|wifi|cmd"
  echo "== log"; tail -n 60 "$DIR/log.txt" 2>&1
} >"$OUT" 2>&1
"$FB" -q -m -y 30 "Diagnostica salvata" 2>/dev/null
