"""Zweiter Durchgang: für Gemeinden ohne E-Mail die Kontaktseiten über Links der Startseite finden."""
import concurrent.futures, csv, html, pathlib, re, urllib.parse, urllib.request

D = pathlib.Path(__file__).resolve().parent.parent / "data" / "gemeinden"
UA = {"User-Agent": "pilgerportal-gemeindenkontakt/1.0 (+https://steffenpfeiffer.es)"}
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
SKIP = ("example", "sentry", "wixpress", ".png", ".jpg", ".gif", ".webp", "domain.", "email.com", "tuemail", "tucorreo", "protection", "usuario@", "nombre@")
LINK = re.compile(r'href=["\']([^"\']+)["\']', re.I)
KEY = re.compile(r"contact|contacta|atenci|sede|oficina|ayuntamiento|concello|institucional|aviso|legal|privacidad|alcald|organiz|telefon|directorio", re.I)


def get(url, t=8):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
        return r.read().decode("utf-8", "replace")


def cf(h):
    out = []
    for m in re.findall(r'data-cfemail="([0-9a-f]+)"', h):
        k = int(m[:2], 16)
        out.append("".join(chr(int(m[i:i + 2], 16) ^ k) for i in range(2, len(m), 2)))
    return out


def mails(h):
    h = html.unescape(h).replace("[at]", "@").replace("(at)", "@").replace(" arroba ", "@")
    f = set(m.lower().strip(".") for m in MAIL.findall(h)) | set(x.lower() for x in cf(h))
    return {m for m in f if not any(s in m for s in SKIP) and len(m) < 60}


def suche(site):
    base = site if site.startswith("http") else "http://" + site
    base = base if base.endswith("/") else base + "/"
    try:
        start = get(base)
    except Exception:
        return set(), "Seite nicht erreichbar"
    m = mails(start)
    if m:
        return m, "start"
    links = []
    for l in LINK.findall(start):
        if KEY.search(l) and not l.startswith(("mailto", "tel", "javascript", "#")) and not re.search(r"\.(pdf|jpg|png|doc|zip)$", l, re.I):
            u = urllib.parse.urljoin(base, l)
            if urllib.parse.urlparse(u).netloc.replace("www.", "") == urllib.parse.urlparse(base).netloc.replace("www.", "") and u not in links:
                links.append(u)
    for u in links[:10]:
        try:
            m = mails(get(u))
        except Exception:
            continue
        if m:
            return m, u.replace(base, "/")[:60]
    return set(), "keine Adresse gefunden"


def main():
    rows = list(csv.DictReader(open(D / "gemeinden_kontakt.csv", encoding="utf-8-sig"), delimiter=";"))
    todo = [r for r in rows if not r["email"] and r["webseite"]]

    def eins(r):
        m, q = suche(r["webseite"])
        if m:
            r["email"], r["email_quelle"] = "; ".join(sorted(m)[:3]), "website:" + q
        else:
            r["email_quelle"] = "OFFEN (" + q + ")"
        print(r["gemeinde"], "|", r["email"], "|", r["email_quelle"], flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(eins, todo))
    with open(D / "gemeinden_kontakt.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)
    print("mit E-Mail:", sum(1 for r in rows if r["email"]), "von", len(rows))


if __name__ == "__main__":
    main()
