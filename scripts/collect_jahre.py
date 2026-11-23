#!/usr/bin/env python3
"""Jahresreihe aus dem Power-BI-Bericht: wählt im Filter „Año“ nacheinander jedes Jahr,
liest die Kennzahl „Peregrinos“ und sichert die Datenantworten (CSV) je Jahr.
Ausgabe: data/jahre-powerbi/<jahr>/abfrage-NN.csv und data/jahre-powerbi.json"""
import datetime, json, os, pathlib, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collect_powerbi import BERICHT, dekodiere, csv_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
ZIEL = ROOT / "data" / "jahre-powerbi"
ZIEL.mkdir(parents=True, exist_ok=True)
ZAHL = re.compile(r"^\d{4}$")


def zahl(t):
    t = re.sub(r"[^\d]", "", t or "")
    return int(t) if t else None


def kennzahlen(seite):
    texte = seite.evaluate("""() => [...document.querySelectorAll('.visualContainer')].map(v => (v.innerText||'').trim().replace(/\\n/g,' | ')).filter(t => /^(Peregrinos|Españoles|Extranjeros) \\|/.test(t))""")
    k = {}
    for t in texte:
        n, w = t.split(" | ", 1)
        k[n.lower()] = zahl(w)
    return k


def main():
    ergebnis = {"stand": datetime.date.today().isoformat(), "jahre": {}, "fehler": []}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1600, "height": 1000}, locale="es-ES")
        s = ctx.new_page()
        aktuell = []

        def bei_antwort(a):
            if "querydata" in a.url.lower():
                try:
                    aktuell.append(a.text())
                except Exception:
                    pass

        s.on("response", bei_antwort)
        s.goto(BERICHT, wait_until="networkidle", timeout=90000)
        s.wait_for_timeout(8000)
        menue = s.locator(".slicer-dropdown-menu[aria-label='Año']").first

        def oeffnen():
            if s.locator(".slicerItemContainer").count() == 0:
                menue.click(timeout=5000)
                s.wait_for_timeout(1500)

        def finde(jahr):
            """Sucht den Eintrag; scrollt die Liste bei Bedarf."""
            for _ in range(14):
                el = s.locator(".slicerItemContainer", has_text=str(jahr))
                for i in range(el.count()):
                    if (el.nth(i).inner_text() or "").strip() == str(jahr):
                        return el.nth(i)
                try:
                    s.evaluate('''() => {
                        const it = document.querySelector('.slicerItemContainer');
                        let e = it;
                        while (e && !(e.scrollHeight > e.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(e).overflowY))) e = e.parentElement;
                        if (e) e.scrollTop += Math.max(60, e.clientHeight * 0.6);
                    }''')
                except Exception:
                    pass
                s.wait_for_timeout(350)
                try:
                    box = s.locator('.slicerItemContainer').first.bounding_box()
                    if box:
                        s.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        s.mouse.wheel(0, 150)
                        s.wait_for_timeout(300)
                except Exception:
                    pass
                ergebnis.setdefault('scroll_log', []).append(s.evaluate("() => [...document.querySelectorAll('.slicerItemContainer')].map(e => (e.innerText||'').trim()).join(',')"))
            return None

        oeffnen()
        sichtbar = s.evaluate("() => [...document.querySelectorAll('.slicerItemContainer')].map(e => (e.innerText||'').trim())")
        ergebnis["sichtbar_beim_oeffnen"] = sichtbar
        wahl = os.environ.get('JAHRE')
        liste = [int(x) for x in wahl.split(',')] if wahl else list(range(2026, 2002, -1))
        for jahr in liste:
            t0 = time.time()
            print('Jahr', jahr, flush=True)
            try:
                oeffnen()
                el = finde(jahr)
                if el is None:
                    ergebnis["fehler"].append(f"{jahr}: Eintrag nicht gefunden")
                    continue
                aktuell.clear()
                try:
                    el.click(timeout=5000, force=True)
                except Exception:
                    el.evaluate('e => e.click()')
                s.wait_for_timeout(5000)
                try:
                    s.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                k = kennzahlen(s)
                d = ZIEL / str(jahr)
                d.mkdir(parents=True, exist_ok=True)
                n = 0
                for text in list(aktuell):
                    try:
                        for t in dekodiere(json.loads(text)):
                            n += 1
                            (d / f"abfrage-{n:02d}.csv").write_text(csv_text(t), encoding="utf-8")
                    except Exception as e:
                        ergebnis["fehler"].append(f"{jahr}: Antwort nicht lesbar {e}")
                ergebnis["jahre"][str(jahr)] = {"kennzahlen": k, "tabellen": n}
                print('  ', k, n, 'Tabellen', round(time.time() - t0), 's', flush=True)
                s.screenshot(path=str(d / "ansicht.png"))
                (ROOT / 'data' / 'jahre-powerbi.json').write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding='utf-8')
            except Exception as e:
                ergebnis["fehler"].append(f"{jahr}: {str(e)[:150]}")
                print('  Fehler', str(e)[:150], flush=True)
        b.close()
    (ROOT / "data" / "jahre-powerbi.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
