#!/usr/bin/env python3
"""Pezzi grafici dell'orologio per il Kindle.

Il Kindle non può usare Python, quindi prepariamo qui piccole immagini
(cifre, due punti, giorno della settimana, numero del giorno, mese) e un file
pos.sh con le coordinate. Sul Kindle dash.sh le incolla con fbink:
il risultato è identico all'anteprima.

Uso: python3 clock.py   -> genera kindle/dashboard/clock/
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kindle" / "dashboard" / "clock"

W = 600
M = 36
CLOCK_H = 222          # altezza zona orologio (deve combaciare con render.py)
DIG_TOP = 22           # bordo alto delle cifre
DIG_H = 180            # altezza delle cifre in pixel
GAP = 16               # spazio tra ora e colonna data

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _font(name, size):
    return ImageFont.truetype(str(ROOT / "fonts" / name), size)


def _font_cifre():
    # trova la dimensione che dà cifre alte esattamente DIG_H pixel
    size = 200
    for _ in range(6):
        f = _font("Antonio-Bold.ttf", size)
        b = f.getbbox("0123456789")
        size = round(size * DIG_H / (b[3] - b[1]))
    f = _font("Antonio-Bold.ttf", size)
    return f, f.getbbox("0123456789")[1]


def _ink(f, ch):
    """Riquadro reale dell'inchiostro di un glifo (x0, x1), misurato disegnandolo."""
    from PIL import ImageOps
    img = Image.new("L", (int(f.size * 1.5), int(f.size * 1.5)), 255)
    ImageDraw.Draw(img).text((f.size // 4, 0), ch, font=f, fill=0)
    bb = ImageOps.invert(img).getbbox()
    return bb[0] - f.size // 4, bb[2] - f.size // 4


def layout():
    f, top_off = _font_cifre()
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    # celle strette: larghezza reale del glifo più largo + un filo d'aria
    cella = max(_ink(f, str(n))[1] - _ink(f, str(n))[0] for n in range(10)) + 8
    ci = _ink(f, ":")
    colon = ci[1] - ci[0] + 22
    xs = [M, M + cella, M + 2 * cella, M + 2 * cella + colon, M + 3 * cella + colon]
    fine_ora = M + 4 * cella + colon
    col_x = fine_ora + GAP
    col_w = W - M - col_x
    return {
        "font": f, "top_off": top_off, "cella": cella, "colon": colon, "xs": xs,
        "col_x": col_x, "col_w": col_w,
        # colonna data: in alto il giorno della settimana, in mezzo il numero,
        # in basso il mese; allineati al bordo alto e basso delle cifre
        "wd_y": DIG_TOP - 8, "wd_h": 34,
        "day_y": DIG_TOP + 38, "day_h": 76,
        "mon_y": DIG_TOP + DIG_H - 26, "mon_h": 32,
    }


def _pezzo(w, h, testo, f, y_testo, fill=0):
    img = Image.new("L", (w, h), 255)
    ImageDraw.Draw(img).text((0, y_testo), testo, font=f, fill=fill)
    return img


def _testo_in_alto(f, testo):
    """y per cui il bordo alto delle lettere maiuscole cade a 0."""
    return -f.getbbox("ÈM")[1] if testo else 0


def pezzi():
    """Ritorna {nome: Image} con tutte le immagini dell'orologio."""
    L = layout()
    f = L["font"]
    h = DIG_H + 6
    p = {}
    for n in range(10):
        img = Image.new("L", (L["cella"], h), 255)
        dd = ImageDraw.Draw(img)
        w = dd.textlength(str(n), font=f)
        x0, x1 = _ink(f, str(n))
        dd.text(((L["cella"] - (x1 - x0)) / 2 - x0, -L["top_off"]), str(n), font=f, fill=0)
        p[f"d{n}"] = img
    img = Image.new("L", (L["colon"], h), 255)
    ImageDraw.Draw(img).text((11 - _ink(f, ":")[0], -L["top_off"]), ":", font=f, fill=0)
    p["colon"] = img

    def adatta(nome, size, testi):
        """Stessa dimensione per tutti i testi del gruppo, la più grande che ci sta."""
        while size > 10 and max(_font(nome, size).getlength(t) for t in testi) > L["col_w"]:
            size -= 1
        return _font(nome, size)

    giorni = [g.upper() for g in GIORNI]
    fw = adatta("Inter-SemiBold.ttf", 18, giorni)
    for i, t in enumerate(giorni, 1):
        p[f"wd{i}"] = _pezzo(L["col_w"], L["wd_h"], t, fw, 8 - fw.getbbox("M")[1])

    fd = adatta("Inter-ExtraBold.ttf", 72, [str(n) for n in range(1, 32)])
    for n in range(1, 32):
        p[f"day{n}"] = _pezzo(L["col_w"], L["day_h"], str(n), fd, -fd.getbbox("0")[1] + 4)

    fm = adatta("Inter-Regular.ttf", 21, MESI)
    for i, m in enumerate(MESI, 1):
        # il fondo delle lettere coincide con il fondo delle cifre
        y = 26 - fm.getbbox("n")[3]
        p[f"m{i}"] = _pezzo(L["col_w"], L["mon_h"], m, fm, y)
    return p


def componi(img, hhmm, giorno_sett, giorno, mese):
    """Incolla l'orologio su img (usato per l'anteprima). giorno_sett 1=lunedì."""
    L = layout()
    p = pezzi()
    nomi = [f"d{hhmm[0]}", f"d{hhmm[1]}", "colon", f"d{hhmm[3]}", f"d{hhmm[4]}"]
    for x, n in zip(L["xs"], nomi):
        img.paste(p[n], (x, DIG_TOP))
    img.paste(p[f"wd{giorno_sett}"], (L["col_x"], L["wd_y"]))
    img.paste(p[f"day{giorno}"], (L["col_x"], L["day_y"]))
    img.paste(p[f"m{mese}"], (L["col_x"], L["mon_y"]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    for nome, img in pezzi().items():
        img.save(OUT / f"{nome}.png", optimize=True)
    L = layout()
    xs = L["xs"]
    (OUT / "pos.sh").write_text(
        "# generato da clock.py - non modificare a mano\n"
        f"DIG_Y={DIG_TOP}\nX_H1={xs[0]}\nX_H2={xs[1]}\nX_COLON={xs[2]}\nX_M1={xs[3]}\nX_M2={xs[4]}\n"
        f"COL_X={L['col_x']}\nWD_Y={L['wd_y']}\nDAY_Y={L['day_y']}\nMON_Y={L['mon_y']}\n"
        f"CLOCK_H={CLOCK_H}\n")
    print("generati", len(list(OUT.glob('*.png'))), "pezzi in", OUT, "| colonna data larga", L["col_w"], "px")


if __name__ == "__main__":
    main()
