#!/usr/bin/env python3
"""Genera l'immagine della dashboard per Kindle (600x800, scala di grigi).

La parte alta (0..CLOCK_H) resta bianca: lì il Kindle disegna da solo
orologio e data ogni minuto. Con --preview la riempiamo con un orologio
d'esempio, solo per vedere come verrà.
"""
import argparse
import datetime as dt
import json
import math
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H = 600, 800
CLOCK_H = 222
LAT, LON, CITTA = 44.39603, 7.81764, "Mondovì"
TZ = ZoneInfo("Europe/Rome")

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
GIORNI_BREVI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# Codici meteo WMO usati da Open-Meteo -> (descrizione, icona)
WMO = {
    0: ("Sereno", "sole"), 1: ("Quasi sereno", "sole"), 2: ("Poco nuvoloso", "parz"),
    3: ("Coperto", "nuvola"), 45: ("Nebbia", "nebbia"), 48: ("Nebbia gelata", "nebbia"),
    51: ("Pioviggine", "pioggia"), 53: ("Pioviggine", "pioggia"), 55: ("Pioviggine fitta", "pioggia"),
    56: ("Pioviggine gelata", "pioggia"), 57: ("Pioviggine gelata", "pioggia"),
    61: ("Pioggia debole", "pioggia"), 63: ("Pioggia", "pioggia"), 65: ("Pioggia forte", "pioggia"),
    66: ("Pioggia gelata", "pioggia"), 67: ("Pioggia gelata", "pioggia"),
    71: ("Neve debole", "neve"), 73: ("Neve", "neve"), 75: ("Neve forte", "neve"), 77: ("Nevischio", "neve"),
    80: ("Rovesci", "pioggia"), 81: ("Rovesci", "pioggia"), 82: ("Rovesci forti", "pioggia"),
    85: ("Rovesci di neve", "neve"), 86: ("Rovesci di neve", "neve"),
    95: ("Temporale", "temporale"), 96: ("Temporale e grandine", "temporale"), 99: ("Temporale e grandine", "temporale"),
}


def font(name, size):
    return ImageFont.truetype(str(ROOT / "fonts" / name), size)


def meteo():
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}&timezone=Europe%2FRome&forecast_days=5"
           "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
           "&hourly=temperature_2m,weather_code,precipitation"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def parola_del_giorno(oggi):
    parole = json.loads((ROOT / "parole.json").read_text(encoding="utf-8"))
    # Indice stabile: giorni dall'1/1/2026, così ogni giorno ne arriva una nuova
    n = (oggi - dt.date(2026, 1, 1)).days
    return parole[n % len(parole)]


# ---------- icone meteo disegnate a mano (vettoriali, nitide su e-ink) ----------

def _sole(d, cx, cy, r, w):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=w)
    for i in range(8):
        a = i * math.pi / 4
        d.line([cx + math.cos(a) * r * 1.45, cy + math.sin(a) * r * 1.45,
                cx + math.cos(a) * r * 1.95, cy + math.sin(a) * r * 1.95], fill=0, width=w)


def _nuvola(d, cx, cy, s, w, fill=255):
    # tre cerchi + base piatta
    parts = [(-0.45, 0.05, 0.38), (0.0, -0.18, 0.5), (0.45, 0.08, 0.34)]
    for ox, oy, rr in parts:
        d.ellipse([cx + (ox - rr) * s, cy + (oy - rr) * s, cx + (ox + rr) * s, cy + (oy + rr) * s],
                  fill=0)
    d.rectangle([cx - 0.45 * s, cy + 0.05 * s, cx + 0.45 * s, cy + 0.42 * s], fill=0)
    inset = w
    for ox, oy, rr in parts:
        d.ellipse([cx + (ox - rr) * s + inset, cy + (oy - rr) * s + inset,
                   cx + (ox + rr) * s - inset, cy + (oy + rr) * s - inset], fill=fill)
    d.rectangle([cx - 0.45 * s, cy + 0.05 * s + inset, cx + 0.45 * s, cy + 0.42 * s - inset], fill=fill)


def icona(d, tipo, cx, cy, s):
    """Icona centrata in (cx, cy) che sta dentro un quadrato di lato s."""
    w = max(2, int(s / 16))
    if tipo == "sole":
        _sole(d, cx, cy, s * 0.24, w)
    elif tipo == "parz":
        _sole(d, cx - s * 0.17, cy - s * 0.14, s * 0.16, w)
        _nuvola(d, cx + s * 0.08, cy + s * 0.12, s * 0.5, w)
    elif tipo == "nuvola":
        _nuvola(d, cx, cy + s * 0.08, s * 0.6, w)
    elif tipo in ("pioggia", "neve", "temporale"):
        _nuvola(d, cx, cy - s * 0.04, s * 0.6, w)
        y0 = cy + s * 0.26
        for ox in (-0.2, 0.0, 0.2):
            x = cx + ox * s
            if tipo == "pioggia":
                d.line([x + s * 0.04, y0, x - s * 0.04, y0 + s * 0.16], fill=0, width=w)
            elif tipo == "neve":
                r = s * 0.045
                d.ellipse([x - r, y0 + s * 0.08 - r, x + r, y0 + s * 0.08 + r], fill=0)
        if tipo == "temporale":
            p = [(cx + s * 0.05, y0 - s * 0.02), (cx - s * 0.08, y0 + s * 0.12),
                 (cx + s * 0.03, y0 + s * 0.12), (cx - s * 0.06, y0 + s * 0.24)]
            d.line(p, fill=0, width=w, joint="curve")
    elif tipo == "nebbia":
        for i in range(4):
            y = cy - s * 0.24 + i * s * 0.16
            off = s * 0.08 if i % 2 else 0
            d.line([cx - s * 0.36 + off, y, cx + s * 0.36 - off, y], fill=0, width=w)


# ---------- helpers testo ----------

def testo_centrato(d, x0, x1, y, txt, f, fill=0):
    w = d.textlength(txt, font=f)
    d.text((x0 + (x1 - x0 - w) / 2, y), txt, font=f, fill=fill)


def a_capo(d, txt, f, larghezza):
    righe, riga = [], ""
    for parola in txt.split():
        prova = (riga + " " + parola).strip()
        if d.textlength(prova, font=f) <= larghezza:
            riga = prova
        else:
            righe.append(riga)
            riga = parola
    if riga:
        righe.append(riga)
    return righe


GRIGIO = 110      # testo secondario
GRIGIO_CHIARO = 170
M = 36            # margine: tutto è allineato a questa griglia
CW = W - 2 * M    # larghezza utile

FASCE = [("Mattina", 6, 12), ("Pomeriggio", 12, 18), ("Sera", 18, 24), ("Notte", 24, 30)]
FASCE_DOMANI = {"Mattina": "Domattina", "Pomeriggio": "Domani pom.", "Sera": "Domani sera", "Notte": "Domani notte"}


def mm(v, prefisso=""):
    """Millimetri leggibili: 0 mm, 0,4 mm, 12 mm."""
    v = v or 0
    if v < 0.05:
        return f"{prefisso}0 mm"
    t = f"{v:.1f}".replace(".", ",") if v < 10 else f"{v:.0f}"
    return f"{prefisso}{t} mm"


def sezione(d, y, titolo, destra=None):
    """Intestazione di sezione: etichetta spaziata + linea sottile fino al margine."""
    f = font("Inter-SemiBold.ttf", 13)
    x = M
    for ch in titolo:
        d.text((x, y), ch, font=f, fill=GRIGIO)
        x += d.textlength(ch, font=f) + 1.6
    fine = W - M
    if destra:
        fr = font("Inter-Regular.ttf", 13)
        wr = d.textlength(destra, font=fr)
        d.text((W - M - wr, y), destra, font=fr, fill=GRIGIO)
        fine = W - M - wr - 12
    d.line([x + 10, y + 8, fine, y + 8], fill=GRIGIO_CHIARO, width=1)


def fasce_orarie(dati, adesso):
    """Le prossime 4 parti della giornata, a partire da quella in corso."""
    h = dati["hourly"]
    per_ora = {t: i for i, t in enumerate(h["time"])}
    oggi = adesso.date()
    ora = adesso.hour if adesso.hour >= 6 else adesso.hour + 24  # 0-5 = notte di "ieri sera"
    base = oggi if adesso.hour >= 6 else oggi - dt.timedelta(days=1)
    slot = []
    for giorno in (0, 1):
        for nome, a, b in FASCE:
            if giorno == 0 and b <= ora:
                continue
            idx = []
            for hh in range(a, b):
                t = dt.datetime.combine(base, dt.time()) + dt.timedelta(days=giorno, hours=hh)
                k = t.strftime("%Y-%m-%dT%H:00")
                if k in per_ora:
                    idx.append(per_ora[k])
            if not idx:
                continue
            temps = [h["temperature_2m"][i] for i in idx]
            slot.append({
                "nome": nome if giorno == 0 else FASCE_DOMANI[nome],
                "tmin": round(min(temps)), "tmax": round(max(temps)),
                "codice": max(h["weather_code"][i] for i in idx),
                "mm": sum((h["precipitation"][i] or 0) for i in idx),
            })
    return slot[:4]


def disegna(dati, adesso, preview=False):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    if preview:  # orologio d'esempio: sul Kindle lo disegna dash.sh con gli stessi valori
        testo_centrato(d, 0, W, 4, adesso.strftime("%H:%M"), font("Inter-ExtraBold.ttf", 150))
        data = f"{GIORNI[adesso.weekday()].capitalize()} {adesso.day} {MESI[adesso.month - 1]}"
        testo_centrato(d, 0, W, 170, data, font("Inter-SemiBold.ttf", 30))

    cur, day = dati["current"], dati["daily"]

    # ---------- OGGI ----------
    y = CLOCK_H + 8
    sezione(d, y, f"ADESSO · {CITTA.upper()}",
            f"alba {day['sunrise'][0][-5:]}  ·  tramonto {day['sunset'][0][-5:]}")
    desc, tipo = WMO.get(cur["weather_code"], ("—", "nuvola"))
    icona(d, tipo, M + 42, y + 76, 84)
    ft = font("Inter-ExtraBold.ttf", 84)
    temp = f"{round(cur['temperature_2m'])}°"
    d.text((M + 100, y + 22), temp, font=ft, fill=0)
    d.text((M + 104, y + 118), desc, font=font("Inter-SemiBold.ttf", 20), fill=0)

    stats = [
        ("MIN / MAX", f"{round(day['temperature_2m_min'][0])}° / {round(day['temperature_2m_max'][0])}°"),
        ("PIOGGIA", f"{day['precipitation_probability_max'][0] or 0}%"),
        ("UMIDITÀ", f"{cur['relative_humidity_2m']}%"),
        ("PRECIPITAZIONI", mm(day['precipitation_sum'][0])),
    ]
    sx0, colw = 340, 112
    for k, (etichetta, valore) in enumerate(stats):
        cx = sx0 + (k % 2) * colw
        cy = y + 36 + (k // 2) * 52
        d.text((cx, cy), etichetta, font=font("Inter-SemiBold.ttf", 11), fill=GRIGIO)
        d.text((cx, cy + 14), valore, font=font("Inter-SemiBold.ttf", 22), fill=0)

    # ---------- PARTI DELLA GIORNATA ----------
    y = CLOCK_H + 162
    sezione(d, y, "DURANTE LA GIORNATA")
    col = CW / 4
    for i, s in enumerate(fasce_orarie(dati, adesso)):
        x0 = M + i * col
        if i:
            d.line([x0, y + 30, x0, y + 128], fill=GRIGIO_CHIARO, width=1)
        testo_centrato(d, x0, x0 + col, y + 26, s["nome"], font("Inter-SemiBold.ttf", 16), fill=0)
        _, t = WMO.get(s["codice"], ("", "nuvola"))
        icona(d, t, x0 + col / 2, y + 70, 50)
        tt = f"{s['tmin']}°" if s["tmin"] == s["tmax"] else f"{s['tmin']}–{s['tmax']}°"
        testo_centrato(d, x0, x0 + col, y + 100, tt, font("Inter-SemiBold.ttf", 20))
        testo_centrato(d, x0, x0 + col, y + 124, mm(s["mm"], "pioggia "), font("Inter-Regular.ttf", 13), fill=GRIGIO)

    # ---------- PROSSIMI 3 GIORNI ----------
    y = CLOCK_H + 316
    sezione(d, y, "PROSSIMI GIORNI")
    col = CW / 3
    for i in range(1, 4):
        x0 = M + (i - 1) * col
        data = dt.date.fromisoformat(day["time"][i])
        _, t = WMO.get(day["weather_code"][i], ("", "nuvola"))
        icona(d, t, x0 + 24, y + 54, 48)
        tx = x0 + 58
        d.text((tx, y + 24), GIORNI[data.weekday()].capitalize(), font=font("Inter-SemiBold.ttf", 17), fill=0)
        d.text((tx, y + 45), f"{round(day['temperature_2m_min'][i])}° / {round(day['temperature_2m_max'][i])}°",
               font=font("Inter-Regular.ttf", 17), fill=0)
        d.text((tx, y + 66), f"pioggia {day['precipitation_probability_max'][i] or 0}%",
               font=font("Inter-Regular.ttf", 13), fill=GRIGIO)

    # ---------- PAROLA DEL GIORNO ----------
    y = CLOCK_H + 418
    sezione(d, y, "PAROLA DEL GIORNO", f"agg. {adesso.strftime('%H:%M')}")
    p = parola_del_giorno(adesso.date())
    fw = font("Playfair-Bold.ttf", 40)
    d.text((M, y + 16), p["parola"], font=fw, fill=0)
    d.text((M + d.textlength(p["parola"], font=fw) + 12, y + 36), p["categoria"],
           font=font("Playfair-Italic.ttf", 17), fill=GRIGIO)
    fy = y + 72
    fdef = font("Inter-Regular.ttf", 18)
    for riga in a_capo(d, p["definizione"], fdef, CW)[:3]:
        d.text((M, fy), riga, font=fdef, fill=0)
        fy += 24
    fy += 6
    fes = font("Playfair-Italic.ttf", 17)
    esempio = "«" + p["esempio"].strip("«»") + "»"
    for riga in a_capo(d, esempio, fes, CW)[:2]:
        d.text((M, fy), riga, font=fes, fill=70)
        fy += 22
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out" / "dashboard.png"))
    ap.add_argument("--preview", action="store_true", help="disegna anche un orologio d'esempio")
    a = ap.parse_args()
    adesso = dt.datetime.now(TZ)
    img = disegna(meteo(), adesso, preview=a.preview)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out, optimize=True)
    print("salvato", a.out)


if __name__ == "__main__":
    main()
