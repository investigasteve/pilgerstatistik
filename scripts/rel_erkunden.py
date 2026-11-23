"""Erkundung: Gibt es beim Ministerium (datos.gob.es) eine Datei mit E-Mail-Adressen der Entidades Locales?"""
import json, pathlib, re, urllib.request

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "gemeinden" / "rel_erkundung.txt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
zeilen = []


def get(u, t=40, roh=False):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
        b = r.read()
        return b if roh else b.decode("utf-8", "replace")


for ds in ("e05250001-base-general-de-datos-de-entidades-locales", "e05232701-registro-de-entidades-locales-busqueda-por-municipios", "e05232701-registro-de-alcaldes"):
    zeilen.append("== " + ds)
    try:
        j = json.loads(get("https://datos.gob.es/apidata/catalog/dataset/" + ds + ".json"))
        it = j["result"]["items"][0]
        zeilen.append("titel: " + json.dumps(it.get("title"), ensure_ascii=False)[:200])
        for d in it.get("distribution", []):
            zeilen.append("  dist: " + str(d.get("accessURL")) + " | " + json.dumps(d.get("format"), ensure_ascii=False)[:60])
    except Exception as e:
        zeilen.append("Fehler: " + str(e)[:120])
OUT.write_text("\n".join(zeilen), encoding="utf-8")
print("\n".join(zeilen))
