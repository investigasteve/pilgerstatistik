#!/usr/bin/env python3
"""Erzeugt data/statistik-voll.json für die Statistikseite: Jahres- und Monatswerte je Dimension
(Weg, Land, Region, Startort, Motiv, Geschlecht, Alter, Fortbewegung, Beruf), kompakt über Namenslisten."""
import sqlite3, json, os, collections
HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.path.join(HIER, '..', 'data')
con = sqlite3.connect(os.path.join(DATEN, 'pilgerstatistik.sqlite'))

namen = collections.defaultdict(list)
index = {}
def idx(dim, name):
    k = (dim, name)
    if k not in index:
        index[k] = len(namen[dim]); namen[dim].append(name)
    return index[k]

jahr = collections.defaultdict(lambda: collections.defaultdict(list))
for j, d, n, w in con.execute("SELECT jahr, dimension, name, wert FROM werte ORDER BY dimension, jahr, wert DESC"):
    jahr[d][str(j)].append([idx(d, n), w])

monat = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
for j, m, d, n, w in con.execute("SELECT jahr, monat, dimension, name, wert FROM monate ORDER BY dimension, jahr, monat, wert DESC"):
    monat[d][str(j)][str(m)].append([idx(d, n), w])

gesamt = collections.defaultdict(dict)
for j, m, n, w in con.execute("SELECT jahr, monat, name, wert FROM monat_kennzahlen"):
    gesamt[str(j)].setdefault(str(m), {})[n] = w

sprache = {l: s for l, s, h in con.execute("SELECT land, sprache, hinweis FROM land_sprache") if s}
stand = con.execute("SELECT MAX(stand) FROM tagesstand").fetchone()[0]
kenn = collections.defaultdict(dict)
for j, n, w in con.execute("SELECT jahr, name, wert FROM kennzahlen"):
    kenn[str(j)][n] = w

out = {'stand': stand, 'namen': namen, 'jahr': jahr, 'monat': monat, 'gesamt': gesamt,
       'sprache_land': sprache, 'kennzahlen': kenn}
pfad = os.path.join(DATEN, 'statistik-voll.json')
with open(pfad, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print('geschrieben', pfad, os.path.getsize(pfad) // 1024, 'KB')
