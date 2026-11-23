"""Ordnet jeden Ort (ortzentren.csv) per Nominatim-Rückwärtssuche seiner Gemeinde (INE-Code) zu."""
import csv, difflib, json, pathlib, re, time, unicodedata, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data" / "gemeinden"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9/ ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def varianten(name):
    # "Coruña, A" -> "a coruna"; "Iruña/Pamplona" -> beide Teile
    out = set()
    for teil in re.split(r"/", name):
        n = norm(teil)
        m = re.match(r"^(.*), (a|o|as|os|el|la|los|las|l|les|sa|es)$", n)
        if m:
            out.add(m.group(2) + " " + m.group(1))
            out.add(m.group(1))
        out.add(n)
    return out


def holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": "investigasteve-pilgerportal/1.0 (steffenpfeiffer.es)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    gem = list(csv.DictReader(open(D / "gemeinden-buergermeister.csv", encoding="utf-8-sig"), delimiter=";"))
    index = {}
    for g in gem:
        for v in varianten(g["gemeinde"]):
            index.setdefault(v, []).append(g)
    orte = list(csv.DictReader(open(D / "ortzentren.csv", encoding="utf-8")))
    out = []
    for o in orte:
        lat, lng = o["lat"], o["lng"]
        a = {}
        if lat and lng:
            try:
                j = holen("https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode({"lat": lat, "lon": lng, "zoom": 10, "format": "jsonv2", "accept-language": "es", "addressdetails": 1}))
                a = j.get("address", {})
            except Exception as e:
                a = {"fehler": str(e)[:80]}
            time.sleep(1.2)
        else:
            try:
                j = holen("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": o["ort"] + ", Galicia, España", "format": "jsonv2", "accept-language": "es", "addressdetails": 1, "limit": 1}))
                a = (j[0].get("address", {}) if j else {})
            except Exception as e:
                a = {"fehler": str(e)[:80]}
            time.sleep(1.2)
        kand = [a.get(k) for k in ("municipality", "city", "town", "village", "city_district", "county") if a.get(k)]
        prov = norm(a.get("province") or a.get("state_district") or "")
        treffer, score, wie = None, 0.0, ""
        for k in kand:
            for v in varianten(k):
                if v in index:
                    c = index[v]
                    if len(c) > 1 and prov:
                        c2 = [g for g in c if norm(g["provinz"].split(",")[0]) in prov or prov in norm(g["provinz"])]
                        c = c2 or c
                    treffer, score, wie = c[0], 1.0, "exakt:" + k
                    break
            if treffer:
                break
        if not treffer and kand:
            alle = list(index.keys())
            for k in kand:
                m = difflib.get_close_matches(norm(k), alle, n=1, cutoff=0.86)
                if m:
                    treffer, score, wie = index[m[0]][0], 0.86, "ähnlich:" + k
                    break
        out.append({
            "ort_key": o["ort_key"], "camino": o["camino"], "ort": o["ort"], "lat": lat, "lng": lng,
            "nominatim": " | ".join(kand), "ine": treffer["ine"] if treffer else "", "gemeinde": treffer["gemeinde"] if treffer else "",
            "provinz": treffer["provinz"] if treffer else "", "buergermeister": treffer["buergermeister"] if treffer else "",
            "treffer": wie if treffer else "OFFEN",
        })
        print(o["ort_key"], o["ort"], "->", out[-1]["gemeinde"] or "OFFEN", flush=True)
    felder = list(out[0].keys())
    with open(D / "orte_gemeinde.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=felder, delimiter=";")
        w.writeheader()
        w.writerows(out)
    print("fertig:", sum(1 for r in out if r["ine"]), "von", len(out))


if __name__ == "__main__":
    main()
