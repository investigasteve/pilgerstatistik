#!/usr/bin/env python3
"""Pilgerstatistik-Datenbank: fuehrt alle vorhandenen Daten zusammen.

Quellen
  data/jahre/alle-jahre.csv            Jahresberichte 2004-2019 (PDF)
  data/jahre-powerbi/<jahr>/abfrage-*  Power-BI, Jahresstand 2019-2026
  data/powerbi/<datum>/abfrage-*       Power-BI, taeglicher Stand (laufendes Jahr)

Ausgabe
  data/pilgerstatistik.sqlite   Datenbank (Tabellen: werte, tagesstand, land_sprache, quellen)
  data/pilgerdaten.csv          Langformat der Jahreswerte (jahr;dimension;name;wert;quelle)
  data/tagesstand.csv           Langformat der taeglichen Staende
  data/statistik.json           kompakte Fassung fuer die Webseite

Dimensionen: weg, land, region, startort, motiv, geschlecht, alter, fortbewegung, beruf
"""
import csv, glob, gzip, json, os, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PDF_DIM = {"Caminos": "weg", "Países": "land", "Autonomías": "region", "Procedencias": "startort",
           "Motivos": "motiv", "Sexos": "geschlecht", "Edades": "alter", "Medios": "fortbewegung",
           "Profesiones": "beruf"}

# Pilgersprache je Land (abgeleitet, keine Angabe der Pilgerstelle).
SPRACHEN = {
    "Spanisch": ["España", "México", "Argentina", "Colombia", "Chile", "Perú", "Venezuela", "Ecuador", "Uruguay",
                 "Bolivia", "Paraguay", "Cuba", "Costa Rica", "Panamá", "Guatemala", "Honduras", "El Salvador",
                 "Nicaragua", "República Dominicana", "Puerto Rico", "Guinea Ecuatorial"],
    "Englisch": ["Estados Unidos", "Reino Unido", "Irlanda", "Canadá", "Australia", "Nueva Zelanda", "Sudáfrica"],
    "Deutsch": ["Alemania", "Austria", "Suiza", "Liechtenstein"],
    "Italienisch": ["Italia"],
    "Portugiesisch": ["Portugal", "Brasil", "Angola", "Mozambique"],
    "Französisch": ["Francia", "Bélgica", "Belgica", "Luxemburgo", "Mónaco"],
    "Koreanisch": ["Corea del Sur", "Corea", "Corea del Norte", "Corea del norte"],
    "Polnisch": ["Polonia"],
    "Niederländisch": ["Países Bajos", "Holanda"],
    "Tschechisch": ["República Checa", "Chequia"],
    "Slowakisch": ["Eslovaquia"],
    "Ungarisch": ["Hungría"],
    "Japanisch": ["Japón"],
    "Chinesisch": ["China", "Taiwán", "Hong Kong"],
    "Russisch": ["Rusia", "Bielorrusia"],
    "Ukrainisch": ["Ucrania"],
    "Schwedisch": ["Suecia"],
    "Norwegisch": ["Noruega"],
    "Dänisch": ["Dinamarca"],
    "Finnisch": ["Finlandia"],
    "Rumänisch": ["Rumanía", "Rumania"],
    "Kroatisch": ["Croacia"],
    "Slowenisch": ["Eslovenia"],
    "Litauisch": ["Lituania"],
    "Lettisch": ["Letonia"],
    "Estnisch": ["Estonia"],
    "Griechisch": ["Grecia"],
    "Bulgarisch": ["Bulgaria"],
    "Hebräisch": ["Israel"],
    "Katalanisch": ["Andorra"],
    "Arabisch": ["Arabia Saudita", "Arabia Saudí", "Emiratos Arabes Unidos", "Emiratos Árabes Unidos", "Egipto", "Argelia", "Marruecos"],
    "Albanisch": ["Albania"],
    "Türkisch": ["Turquía"],
}
LAND_SPRACHE = {land: s for s, ls in SPRACHEN.items() for land in ls}


def zahl(s):
    """Power-BI-Wert wie 244754L / 0.29D / 5E-05D -> (wert, ist_ganzzahl)."""
    s = (s or "").strip()
    if not s:
        return None, False
    m = re.fullmatch(r"(-?[0-9.]+(?:E[-+]?[0-9]+)?)([LD])", s)
    if not m:
        return None, False
    return float(m.group(1)), m.group(2) == "L"


def lies_tabellen(ordner):
    """Gibt je Dimension die groesste Ganzzahl-Tabelle eines Power-BI-Ordners zurueck."""
    best = {}
    for f in sorted(glob.glob(str(ordner / "abfrage-*.csv"))):
        with open(f, encoding="utf-8-sig", newline="") as fh:
            r = list(csv.reader(fh))
        if len(r) < 3 or r[0][:2] != ["G0", "M0"]:
            continue
        zeilen = []
        for z in r[1:]:
            if len(z) < 2:
                continue
            w, ganz = zahl(z[1])
            if w is None or not ganz:
                zeilen = None
                break
            zeilen.append((z[0].strip(), int(w)))
        if not zeilen:
            continue
        namen = {n for n, _ in zeilen}
        if "Camino Francés" in namen:
            dim = "weg"
        elif "Religioso" in namen:
            dim = "motiv"
        elif "España" in namen:
            dim = "land"
        elif "Sarria" in namen:
            dim = "startort"
        elif {"Madrid", "Galicia"} <= namen or ("Madrid" in namen and "Cataluña" in namen):
            dim = "region"
        else:
            continue
        if len(zeilen) > len(best.get(dim, [])):
            best[dim] = zeilen
    return best


def baue():
    werte = {}       # (jahr, dim, name) -> (wert, quelle, prio)
    prio = {"pdf": 1, "powerbi-jahr": 2, "powerbi-tag": 3}

    def setze(jahr, dim, name, wert, quelle):
        k = (jahr, dim, name)
        if k not in werte or prio[quelle] >= prio[werte[k][1]]:
            werte[k] = (wert, quelle)

    # 1) PDF-Jahresberichte
    pdf = DATA / "jahre" / "alle-jahre.csv"
    if pdf.exists():
        with open(pdf, encoding="utf-8-sig", newline="") as fh:
            for z in csv.DictReader(fh):
                dim = PDF_DIM.get(z["tabelle"])
                if not dim or not z["wert"]:
                    continue
                try:
                    setze(int(z["jahr"]), dim, z["name"].strip(), int(float(z["wert"])), "pdf")
                except ValueError:
                    pass
    # 2) Power-BI Jahresstaende
    for d in sorted(glob.glob(str(DATA / "jahre-powerbi" / "[0-9]*"))):
        jahr = int(os.path.basename(d))
        for dim, zeilen in lies_tabellen(Path(d)).items():
            for n, w in zeilen:
                if n:
                    setze(jahr, dim, n, w, "powerbi-jahr")
    # 3) Tagesstaende (laufendes Jahr, Stand je Datum)
    tag = {}
    for d in sorted(glob.glob(str(DATA / "powerbi" / "20??-??-??"))):
        stand = os.path.basename(d)
        for dim, zeilen in lies_tabellen(Path(d)).items():
            for n, w in zeilen:
                if n:
                    tag[(stand, dim, n)] = w
    # laufendes Jahr = juengster Tagesstand (Jahr aus dem Datum)
    if tag:
        letzter = max(s for (s, _, _) in tag)
        for (s, d, n), w in tag.items():
            if s == letzter:
                setze(int(letzter[:4]), d, n, w, "powerbi-tag")
    # Kennzahlen 2026 aus jahre-powerbi.json
    kj = DATA / "jahre-powerbi.json"
    gesamt = {}
    if kj.exists():
        j = json.loads(kj.read_text(encoding="utf-8"))
        for jahr, v in j.get("jahre", {}).items():
            k = v.get("kennzahlen", {})
            for key, name in (("peregrinos", "Pilger gesamt"), ("españoles", "Spanier"), ("extranjeros", "Ausländer")):
                if key in k:
                    gesamt[(int(jahr), name)] = int(k[key])
    return werte, tag, gesamt


def schreibe(werte, tag, gesamt):
    db = DATA / "pilgerstatistik.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE werte(jahr INTEGER, dimension TEXT, name TEXT, wert INTEGER, quelle TEXT,
                       PRIMARY KEY(jahr, dimension, name));
    CREATE TABLE tagesstand(stand TEXT, dimension TEXT, name TEXT, wert INTEGER,
                            PRIMARY KEY(stand, dimension, name));
    CREATE TABLE kennzahlen(jahr INTEGER, name TEXT, wert INTEGER, PRIMARY KEY(jahr, name));
    CREATE TABLE land_sprache(land TEXT PRIMARY KEY, sprache TEXT, hinweis TEXT);
    CREATE TABLE quellen(kuerzel TEXT PRIMARY KEY, beschreibung TEXT);
    """)
    con.executemany("INSERT INTO werte VALUES(?,?,?,?,?)",
                    [(j, d, n, w, q) for (j, d, n), (w, q) in sorted(werte.items())])
    con.executemany("INSERT INTO tagesstand VALUES(?,?,?,?)",
                    [(s, d, n, w) for (s, d, n), w in sorted(tag.items())])
    con.executemany("INSERT INTO kennzahlen VALUES(?,?,?)", [(j, n, w) for (j, n), w in sorted(gesamt.items())])
    laender = sorted({n for (_, d, n) in werte if d == "land"} | {n for (_, d, n) in tag if d == "land"})
    zeilen = []
    for l in laender:
        s = LAND_SPRACHE.get(l)
        hinweis = "abgeleitet aus dem Land" if s else "nicht zugeordnet"
        if l == "España":
            hinweis = "abgeleitet; Landessprachen (Galicisch, Katalanisch, Baskisch) nicht trennbar"
        zeilen.append((l, s or "", hinweis))
    con.executemany("INSERT INTO land_sprache VALUES(?,?,?)", zeilen)
    con.executemany("INSERT INTO quellen VALUES(?,?)", [
        ("pdf", "Jahresberichte der Oficina del Peregrino 2004-2019"),
        ("powerbi-jahr", "Power-BI-Bericht Oficina del Peregrino, Jahresstand (Filter Año)"),
        ("powerbi-tag", "Power-BI-Bericht Oficina del Peregrino, laufendes Jahr, juengster Tagesstand"),
    ])
    con.execute("CREATE VIEW sprache_jahr AS SELECT w.jahr, COALESCE(NULLIF(s.sprache,''),'unbekannt') AS sprache, "
                "SUM(w.wert) AS wert FROM werte w LEFT JOIN land_sprache s ON s.land=w.name "
                "WHERE w.dimension='land' GROUP BY 1,2")
    con.commit()
    con.close()

    with open(DATA / "pilgerdaten.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["jahr", "dimension", "name", "wert", "quelle"])
        for (j, d, n), (v, q) in sorted(werte.items()):
            w.writerow([j, d, n, v, q])
    with open(DATA / "tagesstand.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["stand", "dimension", "name", "wert"])
        for (s, d, n), v in sorted(tag.items()):
            w.writerow([s, d, n, v])

    # kompaktes JSON fuer die Webseite
    out = {"stand": max([s for (s, _, _) in tag] or [""]), "kennzahlen": {}, "jahre": {}, "aktuell": {},
           "sprachen": {}}
    for (j, n), v in gesamt.items():
        out["kennzahlen"].setdefault(str(j), {})[n] = v
    for (j, d, n), (v, q) in werte.items():
        out["jahre"].setdefault(str(j), {}).setdefault(d, {})[n] = v
    if out["stand"]:
        for (s, d, n), v in tag.items():
            if s == out["stand"]:
                out["aktuell"].setdefault(d, {})[n] = v
    con = sqlite3.connect(db)
    for j, s, v in con.execute("SELECT jahr, sprache, wert FROM sprache_jahr"):
        out["sprachen"].setdefault(str(j), {})[s] = v
    con.close()
    (DATA / "statistik.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def main():
    werte, tag, gesamt = baue()
    out = schreibe(werte, tag, gesamt)
    jahre = sorted({j for (j, _, _) in werte})
    print("Jahre:", jahre[0], "-", jahre[-1], "| Jahreswerte:", len(werte), "| Tagesstaende:", len(tag),
          "| Staende:", len({s for (s, _, _) in tag}))
    for d in ("weg", "land", "region", "startort", "motiv", "geschlecht", "alter", "fortbewegung", "beruf"):
        js = sorted({j for (j, dd, _) in werte if dd == d})
        print(f"  {d:13s} {len([1 for k in werte if k[1]==d]):6d} Werte, Jahre {js[0] if js else '-'}-{js[-1] if js else '-'}")


if __name__ == "__main__":
    main()
