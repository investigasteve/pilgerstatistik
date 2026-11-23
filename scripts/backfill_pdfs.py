#!/usr/bin/env python3
"""Lädt die Jahresberichte der Oficina del Peregrino (PDF) und liest die Tabellen aus.

Je Bericht: Sexos, Medios, Motivos, Edades, Países, Autonomías, Caminos, Procedencias, Profesiones
(Spalten Nombre | Valor | %). Ergebnis: data/jahre/<jahr>.json und data/jahre/alle-jahre.csv.
"""
import csv, datetime, json, pathlib, re, subprocess, sys, unicodedata, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "pdf"
JAHRE = ROOT / "data" / "jahre"
URL = "https://oficinadelperegrino.com/wp-content/uploads/2016/02/peregrinaciones{jahr}.pdf"
TABELLEN = ["Sexos", "Medios", "Motivos", "Edades", "Países", "Autonomías", "Caminos", "Procedencias", "Profesiones"]


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


KOEPFE = {norm(t): t for t in TABELLEN}
ZEILE = re.compile(r"^\s*(?P<name>\D.*?)\s{1,}(?P<wert>\d{1,3}(?:\.\d{3})+|\d+)\s+(?P<pct>\d+(?:,\d+)?)\s*$")


def zahl(s):
    return int(s.replace(".", ""))


def lies_text(text):
    """Teilt den Text in Tabellen. Gibt {tabelle: [(name, wert, prozent), ...]} zurück."""
    aus, aktuell = {}, None
    for roh in text.splitlines():
        z = roh.strip()
        if not z:
            continue
        k = KOEPFE.get(norm(re.sub(r"[:\s]+$", "", z)))
        if k:
            aktuell = k
            aus.setdefault(k, [])
            continue
        if aktuell is None or norm(z).startswith("nombre"):
            continue
        m = ZEILE.match(roh)
        if m:
            aus[aktuell].append((m["name"].strip(), zahl(m["wert"]), float(m["pct"].replace(",", "."))))
    return {k: v for k, v in aus.items() if v}


def hole(jahr):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    ziel = PDF_DIR / f"peregrinaciones{jahr}.pdf"
    if ziel.exists() and ziel.stat().st_size > 1000:
        return ziel
    req = urllib.request.Request(URL.format(jahr=jahr), headers={"User-Agent": "Mozilla/5.0 pilgerstatistik"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ziel.write_bytes(r.read())
        return ziel
    except Exception as e:
        print(f"{jahr}: nicht geladen ({e})")
        return None


def main():
    JAHRE.mkdir(parents=True, exist_ok=True)
    von = int(sys.argv[1]) if len(sys.argv) > 1 else 2004
    bis = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.date.today().year
    zeilen = []
    for jahr in range(von, bis + 1):
        pdf = hole(jahr)
        if not pdf:
            continue
        text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        tab = lies_text(text)
        (JAHRE / f"{jahr}.json").write_text(json.dumps(tab, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{jahr}: {', '.join(f'{k}={len(v)}' for k, v in tab.items()) or 'keine Tabellen erkannt'}")
        for t, rows in tab.items():
            for n, w, p in rows:
                zeilen.append([jahr, t, n, w, p])
    # alle Jahre zusammen (bestehende Jahre bleiben erhalten)
    alle = {}
    gesamt = JAHRE / "alle-jahre.csv"
    if gesamt.exists():
        for r in csv.reader(gesamt.open(encoding="utf-8")):
            if r and r[0] != "jahr":
                alle[(r[0], r[1], r[2])] = r
    for r in zeilen:
        alle[(str(r[0]), r[1], r[2])] = [str(x) for x in r]
    with gesamt.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["jahr", "tabelle", "name", "wert", "prozent"])
        w.writerows(sorted(alle.values(), key=lambda r: (r[0], r[1], -int(r[3]))))


if __name__ == "__main__":
    main()
