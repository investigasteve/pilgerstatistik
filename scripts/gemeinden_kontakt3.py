"""Dritter Durchgang: Adressen der Kultur-, Fest- und Tourismusabteilung (CC) je Gemeinde."""
import concurrent.futures, csv, html, pathlib, re, urllib.parse, urllib.request

D = pathlib.Path(__file__).resolve().parent.parent / "data" / "gemeinden"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml", "Accept-Language": "es-ES,es;q=0.9"}
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
SKIP = ("example", "sentry", "wixpress", ".png", ".jpg", ".gif", ".webp", "domain.", "email.com", "tuemail", "tucorreo", "protection", "usuario@", "nombre@")
LINK = re.compile(r'href=["\']([^"\']+)["\']', re.I)
KEY = re.compile(r"cultur|festa|festej|fiesta|turism|agenda|xuventude|juventud|educaci", re.I)
CCREG = re.compile(r"cultur|festa|festej|fiesta|turism|xuvent|juvent|educ|prensa|comunic", re.I)


def get(url, t=12):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
        return r.read().decode("utf-8", "replace")


def cf(h):
    out = []
    for m in re.findall(r'data-cfemail="([0-9a-f]+)"', h):
        k = int(m[:2], 16)
        out.append("".join(chr(int(m[i:i + 2], 16) ^ k) for i in range(2, len(m), 2)))
    return out


def mails(h):
    h = html.unescape(h).replace("[at]", "@").replace("(at)", "@")
    f = set(m.lower().strip(".") for m in MAIL.findall(h)) | set(x.lower() for x in cf(h))
    return {m for m in f if not any(s in m for s in SKIP) and len(m) < 60}


def suche(site):
    base = site if site.startswith("http") else "http://" + site
    base = base if base.endswith("/") else base + "/"
    start = None
    for b in dict.fromkeys([base, base.replace("http://", "https://"), base.replace("://www.", "://"), base.replace("http://", "https://").replace("://www.", "://")]):
        try:
            start = get(b)
            base = b
            break
        except Exception:
            pass
    if start is None:
        return "", "Seite nicht erreichbar"
    links = []
    for l in LINK.findall(start):
        if KEY.search(l) and not l.startswith(("mailto", "tel", "javascript", "#")) and not re.search(r"\.(pdf|jpg|png|doc|zip)$", l, re.I):
            u = urllib.parse.urljoin(base, l)
            if urllib.parse.urlparse(u).netloc.replace("www.", "") == urllib.parse.urlparse(base).netloc.replace("www.", "") and u not in links:
                links.append(u)
    gefunden = {}
    for u in links[:8]:
        try:
            for m in mails(get(u)):
                gefunden.setdefault(m, u)
        except Exception:
            continue
    # Adressen der Startseite mit Kultur-/Tourismus-Namen zählen ebenfalls
    for m in mails(start):
        gefunden.setdefault(m, base)
    cc = [m for m in gefunden if CCREG.search(m.split("@")[0])]
    if cc:
        return "; ".join(sorted(cc)[:3]), "Adressname"
    if links and gefunden:
        rest = sorted(gefunden)
        return "; ".join(rest[:2]), "Unterseite " + gefunden[rest[0]].replace(base, "/")[:50]
    return "", "keine Kulturseite gefunden"


def main():
    rows = list(csv.DictReader(open(D / "gemeinden_kontakt.csv", encoding="utf-8-sig"), delimiter=";"))
    for r in rows:
        r.setdefault("cc_email", "")
        r.setdefault("cc_quelle", "")

    def eins(r):
        if r["webseite"]:
            r["cc_email"], r["cc_quelle"] = suche(r["webseite"])
            if r["cc_email"] == r["email"]:
                r["cc_email"], r["cc_quelle"] = "", "gleich wie Hauptadresse"
        print(r["gemeinde"], "|", r["cc_email"], "|", r["cc_quelle"], flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(eins, rows))
    with open(D / "gemeinden_kontakt.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)
    print("mit CC:", sum(1 for r in rows if r["cc_email"]), "von", len(rows))


if __name__ == "__main__":
    main()
