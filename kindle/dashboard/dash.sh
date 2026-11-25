#!/bin/sh
# Dashboard e-ink per Kindle (jailbreak hdnext).
# - Ogni minuto: ridisegna orologio e data. Con LUCE=0 il Kindle dorme tra un
#   minuto e l'altro (batteria per settimane); con LUCE=1 resta sveglio e illuminato.
# - Ogni ora: accende il Wi-Fi, scarica l'immagine (meteo + parola), lo rispegne.
# - Per USCIRE: premi il tasto di accensione (o collega il cavo USB).
#   Il Kindle torna normale entro pochi secondi.

DIR=/mnt/us/dashboard
. "$DIR/config.sh"

LOG="$DIR/log.txt"
IMG="$DIR/dashboard.png"
# Ora italiana con cambio automatico ora legale/solare
export TZ='CET-1CEST,M3.5.0,M10.5.0/3'

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >>"$LOG"; }

# tieni il log piccolo
[ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 200000 ] && tail -n 300 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"

FBINK=""
for f in /mnt/us/libkh/bin/fbink /var/local/kmc/bin/fbink /mnt/us/usbnet/bin/fbink /usr/bin/fbink; do
    [ -x "$f" ] && FBINK="$f" && break
done
[ -z "$FBINK" ] && FBINK="$(command -v fbink)"
if [ -z "$FBINK" ]; then log "ERRORE: fbink non trovato"; exit 1; fi

. "$DIR/clock/pos.sh"

RTC=/sys/class/rtc/rtc1
[ -e "$RTC/wakealarm" ] || RTC=/sys/class/rtc/rtc0

STOP=/tmp/dashboard.stop
rm -f "$STOP"

batteria() { lipc-get-prop com.lab126.powerd battLevel 2>/dev/null; }

luce_on() {
    [ "$LUCE" = "1" ] || return 0
    liv="$LUCE_LIVELLO"
    [ -z "$liv" ] && liv="$LUCE_INIZIALE"
    [ -z "$liv" ] || [ "$liv" = "0" ] && liv=12
    lipc-set-prop com.lab126.powerd flIntensity "$liv" 2>>"$LOG"
}

disegna_orologio() {
    # l'orologio è composto da piccole immagini preparate da clock.py
    ora="$(date +%H%M)"; g=$(date +%u); m=$(date +%m); m=${m#0}; d=$(date +%d); d=${d#0}
    C="$DIR/clock"
    pz() { "$FBINK" -q -b -g file="$C/$1.png",x="$2",y="$3" 2>>"$LOG"; }
    pz "d$(echo "$ora" | cut -c1)" "$X_H1" "$DIG_Y"
    pz "d$(echo "$ora" | cut -c2)" "$X_H2" "$DIG_Y"
    pz colon "$X_COLON" "$DIG_Y"
    pz "d$(echo "$ora" | cut -c3)" "$X_M1" "$DIG_Y"
    pz "d$(echo "$ora" | cut -c4)" "$X_M2" "$DIG_Y"
    pz "wd$g" "$COL_X" "$WD_Y"
    pz "day$d" "$COL_X" "$DAY_Y"
    pz "m$m" "$COL_X" "$MON_Y"
    # aggiorna solo la zona dell'orologio (refresh parziale, niente lampeggio)
    # e aspetta che lo schermo abbia finito (-w)
    "$FBINK" -q -w -s top=0,left=0,width=600,height=$((CLOCK_H - 4)) 2>>"$LOG"
}

wifi_on() {
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    i=0
    while [ $i -lt 40 ]; do
        [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
        sleep 1; i=$((i + 1))
    done
    return 1
}
wifi_off() { lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null; }

scarica_immagine() {
    if ! wifi_on; then log "Wi-Fi non connesso"; wifi_off; return 1; fi
    sleep 2
    ok=1
    for opt in "" "-k"; do
        if curl -sSfL $opt --max-time 40 -o "$IMG.tmp" "$IMAGE_URL" 2>>"$LOG"; then ok=0; break; fi
    done
    # sincronizza l'ora quando possibile
    ntpdate -s pool.ntp.org >/dev/null 2>&1 || true
    wifi_off
    if [ $ok -eq 0 ] && [ -s "$IMG.tmp" ]; then mv "$IMG.tmp" "$IMG"; log "immagine aggiornata (batteria $(batteria)%)"; return 0; fi
    log "download fallito"; return 1
}

mostra_immagine() {
    if [ -s "$IMG" ]; then
        "$FBINK" -q -w -c -f -g file="$IMG" 2>>"$LOG"
    else
        "$FBINK" -q -w -c -f -m -y 20 "Nessuna immagine: controlla il Wi-Fi"
    fi
}

aspetta_fino_a() {  # $1 = epoch. Ritorna 1 se bisogna uscire (tasto/USB)
    target=$1
    if [ "$LUCE" = "1" ]; then
        # luce accesa: niente sospensione (spegnerebbe la luce), solo attesa
        while [ "$(date +%s)" -lt "$target" ]; do
            [ -f "$STOP" ] && { log "tasto o USB: esco"; return 1; }
            sleep 2
        done
        [ -f "$STOP" ] && return 1
        return 0
    fi
    now=$(date +%s)
    [ $((target - now)) -lt 3 ] && return 0
    echo 0 >"$RTC/wakealarm" 2>/dev/null
    echo "$target" >"$RTC/wakealarm" 2>/dev/null
    sync
    sleep 1   # margine extra: lascia finire l'aggiornamento e-ink prima di dormire
    echo mem >/sys/power/state 2>/dev/null
    after=$(date +%s)
    if [ $((target - after)) -gt 5 ]; then
        log "svegliato prima del previsto ($((target - after))s): esco"
        return 1
    fi
    return 0
}

esci() {
    log "uscita dalla dashboard"
    kill $W1 $W2 2>/dev/null
    rm -f "$STOP"
    echo 0 >"$RTC/wakealarm" 2>/dev/null
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    "$FBINK" -q -c -f -m -y 20 "Riavvio dell'interfaccia Kindle..."
    start lab126_gui 2>/dev/null || /etc/init.d/framework start 2>/dev/null
    exit 0
}

# ---------------- avvio ----------------
log "avvio dashboard (fbink=$FBINK rtc=$RTC luce=$LUCE)"
LUCE_INIZIALE="$(lipc-get-prop com.lab126.powerd flIntensity 2>/dev/null)"
"$FBINK" -q -c -f -m -y 20 "Avvio dashboard..."
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
sleep 2
stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
sleep 3
luce_on
# "sentinelle": tasto di accensione o cavo USB -> file di stop
( lipc-wait-event com.lab126.powerd goingToScreenSaver,outOfScreenSaver >/dev/null 2>&1; touch "$STOP" ) &
W1=$!
( lipc-wait-event com.lab126.hal usbPlugIn >/dev/null 2>&1; touch "$STOP" ) &
W2=$!

ultimo_download=0
primo=1
while true; do
    now=$(date +%s)
    if [ $primo -eq 1 ] || [ $((now - ultimo_download)) -ge $((REFRESH_MIN * 60)) ]; then
        scarica_immagine && ultimo_download=$(date +%s)
        [ $primo -eq 1 ] && ultimo_download=$(date +%s)   # non riprovare a ogni minuto se manca il Wi-Fi
        mostra_immagine
        primo=0
    fi
    disegna_orologio
    # prossimo minuto esatto
    now=$(date +%s)
    next=$(( (now / 60 + 1) * 60 ))
    aspetta_fino_a "$next" || esci
done
