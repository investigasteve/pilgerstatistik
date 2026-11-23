#!/usr/bin/env python3
"""Monatsreihe aus dem Power-BI-Bericht: Filter „Año“ + „Mes“, je Monat alle Datenantworten.
Umgebung: JAHRE (kommagetrennt), MONATE (optional, z. B. 1,2), ERKUNDEN=1 (nur Filter anzeigen).
Ausgabe: data/monate-powerbi/<jahr>/<monat>/abfrage-NN.csv, data/monate-powerbi.json"""
import datetime, json, os, pathlib, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collect_powerbi import BERICHT, dekodiere, csv_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
ZIEL = ROOT / "data" / "monate-powerbi"
ZIEL.mkdir(parents=True, exist_ok=True)


def zahl(t):
    t = re.sub(r"[^\d]", "", t or "")
    return int(t) if t else None


def kennzahlen(s):
    texte = s.evaluate("""() => [...document.querySelectorAll('.visualContainer')].map(v => (v.innerText||'').trim().replace(/\\n/g,' | ')).filter(t => /^(Peregrinos|Españoles|Extranjeros) \\|/.test(t))""")
    k = {}
    for t in texte:
        n, w = t.split(" | ", 1)
        k[n.lower()] = zahl(w)
    return k


def eintraege(s):
    return s.evaluate("() => [...document.querySelectorAll('.slicerItemContainer')].map(e => (e.innerText||'').trim())")


def main():
    ergebnis = {"stand": datetime.date.today().isoformat(), "monate": {}, "fehler": [], "log": []}
    alt = ROOT / "data" / "monate-powerbi.json"
    if alt.exists():
        try:
            ergebnis["monate"] = json.loads(alt.read_text(encoding="utf-8")).get("monate", {})
        except Exception:
            pass
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1600, "height": 1000}, locale="es-ES")
        s = ctx.new_page()
        aktuell = []
        s.on("response", lambda a: aktuell.append(a.text()) if "querydata" in a.url.lower() and not a.request.failure else None)
        s.goto(BERICHT, wait_until="networkidle", timeout=90000)
        s.wait_for_timeout(8000)

        def oeffne(name):
            if s.locator(".slicerItemContainer").count():
                s.keyboard.press("Escape"); s.wait_for_timeout(500)
            s.locator(f".slicer-dropdown-menu[aria-label='{name}']").first.click(timeout=8000)
            s.wait_for_timeout(1500)

        def sichtbar_treffer(text):
            el = s.locator(".slicerItemContainer:visible")
            for i in range(el.count()):
                if (el.nth(i).inner_text() or "").strip().lower() == text.lower():
                    return el.nth(i)
            return None

        def finde(text):
            t = sichtbar_treffer(text)
            if t is not None:
                return t
            # nicht sichtbar: über das Suchfeld des geöffneten Filters
            for sel in ("input.searchInput:visible", "input[placeholder*='uscar' i]:visible", "input[aria-label*='uscar' i]:visible", ".slicer-dropdown-popup input:visible", "input[type=text]:visible"):
                feld = s.locator(sel).first
                try:
                    if feld.count():
                        feld.click(timeout=2000)
                        feld.fill(text)
                        s.wait_for_timeout(1500)
                        t = sichtbar_treffer(text)
                        ergebnis["log"].append(f"suche {text} via {sel}: {'ok' if t is not None else 'leer'}")
                        if t is not None:
                            return t
                except Exception as e:
                    ergebnis["log"].append(f"suche {sel}: {str(e)[:80]}")
            ergebnis["log"].append(f"nicht gefunden {text}: " + ",".join(eintraege(s)))
            return None

        def waehle(name, text):
            oeffne(name)
            el = finde(text)
            if el is None:
                return False
            try:
                el.click(force=True, timeout=5000)
            except Exception:
                el.evaluate("e => e.click()")
            s.wait_for_timeout(4000)
            s.keyboard.press("Escape"); s.wait_for_timeout(800)
            return True

        oeffne("Mes")
        mes_liste = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        ergebnis["mes_sichtbar"] = eintraege(s)
        ergebnis["mes_eintraege"] = mes_liste
        print("Mes-Einträge:", mes_liste, flush=True)
        s.keyboard.press("Escape"); s.wait_for_timeout(500)
        if os.environ.get("ERKUNDEN"):
            oeffne("Mes")
            ergebnis["dom"] = s.evaluate("""() => {
              const v = [...document.querySelectorAll('.slicerItemContainer')].filter(e => e.offsetParent !== null && e.getBoundingClientRect().height > 0);
              const out = {sichtbar: v.map(e => e.innerText.trim()), ketten: []};
              if (v[0]) { let e = v[0]; for (let i = 0; i < 8 && e; i++, e = e.parentElement) out.ketten.push({tag: e.tagName, cls: e.className && e.className.toString().slice(0,80), sh: e.scrollHeight, ch: e.clientHeight, oy: getComputedStyle(e).overflowY}); }
              out.inputs = [...document.querySelectorAll('input')].map(i => ({cls: i.className, ph: i.placeholder, vis: i.offsetParent !== null}));
              out.scrollbars = [...document.querySelectorAll('[class*=scroll]')].filter(e => e.offsetParent !== null).slice(0,15).map(e => ({cls: e.className.toString().slice(0,80), sh: e.scrollHeight, ch: e.clientHeight}));
              return out; }""")
            s.keyboard.press("End"); s.wait_for_timeout(800)
            ergebnis["nach_end"] = [e for e in eintraege(s)]
            s.keyboard.press("PageDown"); s.wait_for_timeout(800)
            ergebnis["nach_pagedown"] = eintraege(s)
            s.screenshot(path=str(ZIEL / "erkunden.png"))
            (ROOT / "data" / "monate-powerbi.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
            return
        monate = [m for m in mes_liste if m and m.lower() not in ("todas", "seleccionar todo")]
        wahl = os.environ.get("MONATE")
        if wahl:
            idx = [int(x) for x in wahl.split(",")]
            monate = [monate[i - 1] for i in idx if 0 < i <= len(monate)]
        for jahr in [int(x) for x in os.environ.get("JAHRE", "2025").split(",")]:
            if not waehle("Año", str(jahr)):
                ergebnis["fehler"].append(f"{jahr}: Jahr nicht gefunden"); continue
            # Mes ist standardmäßig komplett angehakt: einmal „Seleccionar todo“ = alles abwählen (= kein Filter)
            waehle("Mes", "Seleccionar todo")
            ergebnis["log"].append(f"{jahr} nach Abwahl: {kennzahlen(s)}")
            for monat in monate:
                t0 = time.time()
                try:
                    aktuell.clear()
                    if not waehle("Mes", monat):
                        ergebnis["fehler"].append(f"{jahr} {monat}: nicht gefunden"); continue
                    s.wait_for_timeout(2000)
                    k = kennzahlen(s)
                    nr = mes_liste.index(monat)
                    d = ZIEL / str(jahr) / re.sub(r"\W+", "_", monat)
                    d.mkdir(parents=True, exist_ok=True)
                    n = 0
                    for text in list(aktuell):
                        try:
                            for t in dekodiere(json.loads(text)):
                                n += 1
                                (d / f"abfrage-{n:02d}.csv").write_text(csv_text(t), encoding="utf-8")
                        except Exception as e:
                            ergebnis["fehler"].append(f"{jahr} {monat}: {e}")
                    ergebnis["monate"].setdefault(str(jahr), {})[monat] = {"kennzahlen": k, "tabellen": n}
                    print(jahr, monat, k, n, round(time.time() - t0), "s", flush=True)
                    # Auswahl wieder aufheben (Klick auf denselben Eintrag)
                    waehle("Mes", monat)
                except Exception as e:
                    ergebnis["fehler"].append(f"{jahr} {monat}: {str(e)[:120]}")
                    print("Fehler", jahr, monat, str(e)[:120], flush=True)
                (ROOT / "data" / "monate-powerbi.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
            s.screenshot(path=str(ZIEL / str(jahr) / "ansicht.png"))
        b.close()
    (ROOT / "data" / "monate-powerbi.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
