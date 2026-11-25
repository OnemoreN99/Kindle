#!/bin/sh
# Dashboard e-ink per Kindle (jailbreak hdnext).
# - Ogni minuto: si sveglia, ridisegna orologio e data, torna in sospensione.
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

RTC=/sys/class/rtc/rtc1
[ -e "$RTC/wakealarm" ] || RTC=/sys/class/rtc/rtc0

GIORNI="Lunedì Martedì Mercoledì Giovedì Venerdì Sabato Domenica"
MESI="gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre"
nth() { echo "$2" | cut -d' ' -f"$1"; }

batteria() { lipc-get-prop com.lab126.powerd battLevel 2>/dev/null || gasgauge-info -c 2>/dev/null | tr -dc '0-9'; }

disegna_orologio() {
    ora="$(date +%H:%M)"
    g=$(date +%u); m=$(date +%m); m=${m#0}; d=$(date +%d); d=${d#0}
    data="$(nth "$g" "$GIORNI") $d $(nth "$m" "$MESI")"
    # pulisci la zona dell'orologio senza aggiornare lo schermo
    "$FBINK" -q -b -k top=0,left=0,width=600,height=$((CLOCK_H - 4))
    "$FBINK" -q -b -m -t regular="$DIR/fonts/Inter-ExtraBold.ttf",px=150,top=4,bottom=0,left=0,right=0 "$ora"
    "$FBINK" -q -b -m -t regular="$DIR/fonts/Inter-SemiBold.ttf",px=30,top=170,bottom=0,left=0,right=0 "$data"
    b="$(batteria)"
    [ -n "$b" ] && [ "$b" -lt 20 ] && "$FBINK" -q -b -t regular="$DIR/fonts/Inter-SemiBold.ttf",px=16,top=6,left=480,right=0,bottom=0 "batt. $b%"
    # aggiorna solo quella zona (refresh parziale, niente lampeggio)
    "$FBINK" -q -s top=0,left=0,width=600,height=$((CLOCK_H - 4))
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
    if [ $ok -eq 0 ] && [ -s "$IMG.tmp" ]; then mv "$IMG.tmp" "$IMG"; log "immagine aggiornata"; return 0; fi
    log "download fallito"; return 1
}

mostra_immagine() {
    if [ -s "$IMG" ]; then
        "$FBINK" -q -c -f -g file="$IMG" 2>>"$LOG"
    else
        "$FBINK" -q -c -f -m -y 20 "Nessuna immagine: controlla il Wi-Fi"
    fi
}

dormi_fino_a() {  # $1 = epoch di sveglia. Ritorna 1 se svegliato prima (tasto/USB)
    target=$1
    now=$(date +%s)
    [ $((target - now)) -lt 3 ] && return 0
    echo 0 >"$RTC/wakealarm" 2>/dev/null
    echo "$target" >"$RTC/wakealarm" 2>/dev/null
    sync
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
    echo 0 >"$RTC/wakealarm" 2>/dev/null
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    "$FBINK" -q -c -f -m -y 20 "Riavvio dell'interfaccia Kindle..."
    start lab126_gui 2>/dev/null || /etc/init.d/framework start 2>/dev/null
    exit 0
}

# ---------------- avvio ----------------
log "avvio dashboard (fbink=$FBINK rtc=$RTC)"
"$FBINK" -q -c -f -m -y 20 "Avvio dashboard..."
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
sleep 2
stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
sleep 3

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
    dormi_fino_a "$next" || esci
done
