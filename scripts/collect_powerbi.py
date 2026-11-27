#!/usr/bin/env python3
"""Tägliche Abfrage des öffentlichen Power-BI-Berichts der Oficina del Peregrino.

Der Bericht wird in einem unsichtbaren Browser geöffnet. Alle Datenantworten, die der
Bericht selbst anfordert, werden gesichert (roh und als CSV) und mit Datum abgelegt.
Eine Datei diagnose.json hält fest, was gefunden wurde.
"""
import datetime, gzip, json, pathlib, re, sys, traceback
from playwright.sync_api import sync_playwright

BERICHT = ("https://app.powerbi.com/view?r=eyJrIjoiNDNhNDQwYzItMjUxMi00ZTE1LWJmZDUtYWRiM2M2YjllZjA3IiwidCI6"
           "ImUzZWVhZTM4LTMwYzUtNDVjNy1hMjc0LWFlZGE5ZjNkNTI3MCJ9")
ROOT = pathlib.Path(__file__).resolve().parent.parent
HEUTE = datetime.date.today().isoformat()
ZIEL = ROOT / "data" / "powerbi" / HEUTE
SCHLUESSEL = ("querydata", "modelsandexploration", "conceptualschema", "exploration")


def dekodiere(antwort):
    """Wandelt eine querydata-Antwort (DSR-Format) in Tabellen um: Liste von Zeilenlisten."""
    tabellen = []
    for res in (antwort.get("results") or []):
        daten = (((res.get("result") or {}).get("data")) or {})
        dsr = daten.get("dsr") or {}
        for ds in dsr.get("DS", []):
            werte = ds.get("ValueDicts", {})
            for ph in ds.get("PH", []):
                for name, zeilen in ph.items():
                    if not isinstance(zeilen, list) or not zeilen or not isinstance(zeilen[0], dict):
                        continue
                    schema = None
                    for z in zeilen:
                        if "S" in z:
                            schema = z["S"]
                            break
                    if not schema:
                        continue
                    n = len(schema)
                    kopf = [s.get("N", "") for s in schema]
                    wb = [s.get("DN") for s in schema]
                    vorher = [None] * n
                    ausgabe = [kopf]
                    for z in zeilen:
                        if "S" in z:
                            schema = z["S"]
                        c = list(z.get("C", []))
                        r = z.get("R", 0)
                        o = z.get("Ø", 0)
                        zeile, k = [], 0
                        for j in range(n):
                            if r & (1 << j):
                                v = vorher[j]
                            elif o & (1 << j):
                                v = None
                            else:
                                v = c[k] if k < len(c) else None
                                k += 1
                                if wb[j] and isinstance(v, int) and wb[j] in werte and v < len(werte[wb[j]]):
                                    v = werte[wb[j]][v]
                            zeile.append(v)
                        vorher = zeile
                        ausgabe.append(zeile)
                    tabellen.append(ausgabe)
    return tabellen


def csv_text(tabelle):
    import csv, io
    s = io.StringIO()
    csv.writer(s, lineterminator="\n").writerows(tabelle)
    return s.getvalue()


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    # Zeitpunkt dieser Erfassung (UTC), damit die Seite weiss, ob der Tagesstand vor oder nach Buerschluss entstand
    (ZIEL / "erfasst.txt").write_text(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n", encoding="utf-8")
    diag = {"datum": HEUTE, "antworten": [], "seiten": [], "fehler": []}
    funde = []
    anfragen = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="es-ES")
        seite = ctx.new_page()

        def bei_antwort(a):
            u = a.url.lower()
            if any(k in u for k in SCHLUESSEL):
                try:
                    funde.append((a.url, a.status, a.text()))
                except Exception as e:
                    diag["fehler"].append(f"Antwort nicht lesbar: {a.url[:120]} {e}")

        def bei_anfrage(r):
            if "querydata" in r.url.lower() and r.method == "POST":
                try:
                    anfragen.append({"url": r.url, "body": r.post_data, "header": {k: v for k, v in r.headers.items() if k.lower().startswith("x-powerbi") or k.lower() in ("content-type", "activityid", "requestid")}})
                except Exception as e:
                    diag["fehler"].append(f"Anfrage nicht lesbar: {e}")

        seite.on("response", bei_antwort)
        seite.on("request", bei_anfrage)
        try:
            seite.goto(BERICHT, wait_until="networkidle", timeout=90000)
            seite.wait_for_timeout(8000)
        except Exception as e:
            diag["fehler"].append(f"Laden: {e}")

        def sichere_ansicht(name):
            try:
                seite.screenshot(path=str(ZIEL / f"{name}.png"), full_page=True)
                text = seite.inner_text("body")
                (ZIEL / f"{name}.txt").write_text(text, encoding="utf-8")
                diag["seiten"].append({"name": name, "zeichen": len(text), "titel": seite.title()})
            except Exception as e:
                diag["fehler"].append(f"Ansicht {name}: {e}")

        sichere_ansicht("seite-1")

        # Weitere Berichtsseiten (falls es eine Seitennavigation gibt)
        for sel in ("[role=tab]", ".navigation-pane-item", "[class*=pageNavigator] [role=button]",
                    "[class*=pbi-page] [role=button]", "button[aria-label*=Page i]", "button[aria-label*=Página i]"):
            try:
                n = seite.locator(sel).count()
            except Exception:
                n = 0
            diag.setdefault("navigation", {})[sel] = n
            if 1 < n <= 15:
                for i in range(n):
                    try:
                        seite.locator(sel).nth(i).click(timeout=5000)
                        seite.wait_for_load_state("networkidle", timeout=30000)
                        seite.wait_for_timeout(4000)
                        sichere_ansicht(f"seite-{i + 1}-{sel[:12].strip('[.]')}")
                    except Exception as e:
                        diag["fehler"].append(f"Navigation {sel} #{i}: {e}")
                break
        browser.close()

    nr = 0
    for url, status, body in funde:
        nr += 1
        eintrag = {"nr": nr, "url": url[:200], "status": status, "bytes": len(body)}
        try:
            if nr <= 3 and not (ZIEL.parent / "_modell.json.gz").exists():
                with gzip.open(ZIEL.parent / "_modell.json.gz", "wt", encoding="utf-8") as f:
                    f.write(body) if nr == 1 else None
            if "querydata" in url.lower():
                tabs = dekodiere(json.loads(body))
                eintrag["tabellen"] = [len(t) - 1 for t in tabs]
                namen = {}
                for res in json.loads(body).get("results", []):
                    for sel in (((res.get("result") or {}).get("data") or {}).get("descriptor") or {}).get("Select", []):
                        namen[sel.get("Value")] = sel.get("Name")
                for i, t in enumerate(tabs, 1):
                    if t and namen:
                        t = [[namen.get(c, c) for c in t[0]]] + t[1:]
                    (ZIEL / f"abfrage-{nr:02d}-{i:02d}.csv").write_text(csv_text(t), encoding="utf-8")
        except Exception:
            eintrag["fehler"] = traceback.format_exc(limit=2)
        diag["antworten"].append(eintrag)

    with gzip.open(ZIEL / "anfragen.json.gz", "wt", encoding="utf-8") as f:
        json.dump(anfragen, f, ensure_ascii=False)
    (ZIEL / "diagnose.json").write_text(json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")
    zusammen = f"Antworten: {len(diag['antworten'])}, Seiten: {len(diag['seiten'])}, Fehler: {len(diag['fehler'])}"
    print(zusammen)
    sys.exit(0 if diag["antworten"] else 1)


if __name__ == "__main__":
    main()
