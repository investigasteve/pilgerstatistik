"""Holt Webseite und E-Mail der Gemeinden aus Wikidata (INE-Code) und ergänzt aus der Gemeindeseite."""
import concurrent.futures, csv, json, pathlib, re, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data" / "gemeinden"
UA = {"User-Agent": "pilgerportal-gemeindenkontakt/1.0 (+https://steffenpfeiffer.es)"}
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SKIP = ("example", "sentry", "wixpress", ".png", ".jpg", "domain.", "email.com", "tuemail", "tucorreo")


def get(url, timeout=8):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def wikidata(ines):
    werte = " ".join('"%s"' % i[:5] for i in ines)
    q = "SELECT ?ine ?site ?mail WHERE { VALUES ?ine { %s } ?m wdt:P772 ?ine . OPTIONAL { ?m wdt:P856 ?site } OPTIONAL { ?m wdt:P968 ?mail } }" % werte
    j = json.loads(get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q), 90))
    out = {}
    for b in j["results"]["bindings"]:
        e = out.setdefault(b["ine"]["value"], {"site": "", "mail": set()})
        if "site" in b and not e["site"]:
            e["site"] = b["site"]["value"]
        if "mail" in b:
            e["mail"].add(b["mail"]["value"].replace("mailto:", "").strip().lower())
    return out


def mails_von(site):
    if not site:
        return set(), ""
    gefunden, quelle = set(), ""
    base = site if site.startswith("http") else "http://" + site
    base = base if base.endswith("/") else base + "/"
    for pfad in ("", "contacto", "contactar", "es/contacto", "contact", "gl/contacto", "aviso-legal"):
        try:
            h = get(urllib.parse.urljoin(base, pfad), 8)
        except Exception:
            continue
        for m in MAIL.findall(h):
            m = m.lower().strip(".")
            if not any(s in m for s in SKIP):
                gefunden.add(m)
        if gefunden:
            quelle = "/" + pfad
            break
    return gefunden, quelle


def main():
    og = list(csv.DictReader(open(D / "orte_gemeinde.csv", encoding="utf-8-sig"), delimiter=";"))
    gem = {}
    for r in og:
        if r["ine"]:
            gem.setdefault(r["ine"], r)
    wd = {}
    ines = sorted(gem)
    for i in range(0, len(ines), 40):
        try:
            wd.update(wikidata(ines[i:i + 40]))
        except Exception as e:
            print("Wikidata-Fehler", e)
        time.sleep(2)
    def eins(ine):
        r = gem[ine]
        w = wd.get(ine[:5], {"site": "", "mail": set()})
        mails, wo = set(w["mail"]), "wikidata" if w["mail"] else ""
        if not mails and w["site"]:
            m2, q = mails_von(w["site"])
            mails, wo = m2, ("website" + q) if m2 else ""
        o = {"ine": ine, "gemeinde": r["gemeinde"], "provinz": r["provinz"], "webseite": w["site"],
             "email": "; ".join(sorted(mails)[:3]), "email_quelle": wo or "OFFEN"}
        print(ine, r["gemeinde"], "|", w["site"], "|", o["email"], flush=True)
        return o

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        out = list(ex.map(eins, ines))
    with open(D / "gemeinden_kontakt.csv", "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=list(out[0].keys()), delimiter=";")
        wr.writeheader()
        wr.writerows(out)
    print("mit E-Mail:", sum(1 for o in out if o["email"]), "von", len(out))


if __name__ == "__main__":
    main()
