#!/usr/bin/env python3
"""Erkundung: Wie ist der Jahres-Filter (Slicer „Año“) im Power-BI-Bericht aufgebaut?"""
import json, pathlib, datetime
from playwright.sync_api import sync_playwright

BERICHT = ("https://app.powerbi.com/view?r=eyJrIjoiNDNhNDQwYzItMjUxMi00ZTE1LWJmZDUtYWRiM2M2YjllZjA3IiwidCI6"
           "ImUzZWVhZTM4LTMwYzUtNDVjNy1hMjc0LWFlZGE5ZjNkNTI3MCJ9")
ROOT = pathlib.Path(__file__).resolve().parent.parent
ZIEL = ROOT / "data" / "erkundung"
ZIEL.mkdir(parents=True, exist_ok=True)
out = {"datum": datetime.date.today().isoformat(), "schritte": []}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1600, "height": 1000}, locale="es-ES")
    s = ctx.new_page()
    s.goto(BERICHT, wait_until="networkidle", timeout=90000)
    s.wait_for_timeout(8000)
    # alle Visuals mit Titel/Text
    visuals = s.evaluate("""() => [...document.querySelectorAll('visual-container, .visualContainer, [class*=visual-container]')].map(v => {
        const r = v.getBoundingClientRect();
        return {cls: v.className.toString().slice(0,80), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: (v.innerText||'').slice(0,80).replace(/\\n/g,' | ')};
    })""")
    out["visuals"] = visuals
    # Slicer-Kandidaten
    kand = s.evaluate("""() => [...document.querySelectorAll('[class*=slicer], [aria-label*="Año"], [title*="Año"]')].map(e => ({tag: e.tagName, cls: e.className.toString().slice(0,100), aria: e.getAttribute('aria-label'), txt: (e.innerText||'').slice(0,60).replace(/\\n/g,' | ')})).slice(0,40)""")
    out["slicer"] = kand
    s.screenshot(path=str(ZIEL / "start.png"))
    # Versuch: Dropdown öffnen
    for sel in ["[aria-label*='Año'] .slicer-dropdown-menu", ".slicer-dropdown-menu", "[class*=slicer-dropdown]", "[class*=dropdown-chevron]"]:
        try:
            el = s.locator(sel).first
            if el.count():
                out["schritte"].append("klick " + sel)
                el.click(timeout=4000)
                s.wait_for_timeout(2500)
                break
        except Exception as e:
            out["schritte"].append(f"fehler {sel}: {str(e)[:100]}")
    s.screenshot(path=str(ZIEL / "dropdown.png"))
    out["optionen"] = s.evaluate("""() => [...document.querySelectorAll('[role=option], [class*=slicerItemContainer], .slicerText, [class*=slicer-dropdown-popup] *')].map(e => (e.innerText||'').trim()).filter(t => t && t.length < 30).slice(0,60)""")
    (ZIEL / "erkundung.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    b.close()
